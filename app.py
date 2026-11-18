"""
FastAPI Backend for PolSci & International Relations MA AI Agent.
Provides real-time web search, multi-page university URL scraping, 7-dimensional
comparison, and local Ollama LLM integration optimized for a 2020 Mac.
"""

import os
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from agent.analyzer import analyze_program_from_url
from agent.comparator import answer_advisor_question, build_comparison_report
from agent.ollama_client import OllamaClient
from agent.scraper import OFFICIAL_UNIVERSITY_TARGETS, resolve_search_targets
from agent.storage import (
    clear_all_programs,
    delete_program,
    get_program,
    get_recent_logs,
    init_db,
    list_programs,
    log_agent_action,
)

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")

app = FastAPI(
    title="PolSci & IR MA AI Ügynök (HU + EU)",
    description="Magyar és európai egyetemek politikatudományi és nemzetközi kapcsolatok mesterszakjainak élő webes összesítő és összehasonlító AI ügynöke (2020 Mac / Ollama optimalizált).",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

ollama_client = OllamaClient()


class AnalyzeUrlRequest(BaseModel):
    url: str
    use_ollama: bool = True


class LiveSearchRequest(BaseModel):
    query: str
    max_targets: int = 3
    use_ollama: bool = True


class CompareRequest(BaseModel):
    program_ids: Optional[List[str]] = None


class ChatRequest(BaseModel):
    question: str
    program_ids: Optional[List[str]] = None


class OllamaConfigRequest(BaseModel):
    model: str
    base_url: Optional[str] = None


def bootstrap_initial_live_scrape() -> None:
    """
    On first launch, live-scrape a balanced starter set of Hungarian and European
    Political Science & International Relations MA programs if the local DB is empty.
    """
    init_db()
    existing = list_programs()
    if existing:
        return
    starter_urls = [
        "https://www.ajk.elte.hu/kepzesek/ma",
        "https://tatk.elte.hu/mesterszakok/nemzetkozi",
        "https://www.uni-corvinus.hu/post/landing-page/mesterkepzesek/politikai-gazdasagtan/",
        "https://btk.ppke.hu/ma-felvetelizoknek-2",
        "https://www.ceu.edu/academics/degrees/ma-politics-2-years",
        "https://www.kuleuven.be/programmes/master-international-politics",
        "https://www.uva.nl/en/masters/masters-programmes/political-science",
        "https://www.universiteitleiden.nl/en/education/study-programmes/master/political-science",
    ]
    for u in starter_urls:
        try:
            # Fast live scrape on startup
            analyze_program_from_url(u, ollama_client=ollama_client, use_ollama=False)
        except Exception as exc:
            log_agent_action("BOOTSTRAP_ERROR", u, "ERROR", str(exc))


@app.on_event("startup")
def on_startup() -> None:
    bootstrap_initial_live_scrape()


@app.get("/api/status")
def api_status() -> Dict[str, Any]:
    programs = list_programs()
    return {
        "ollama": ollama_client.check_status(),
        "programs_count": len(programs),
        "hungarian_count": sum(1 for p in programs if p["region_group"] == "Magyarország"),
        "european_count": sum(1 for p in programs if p["region_group"] != "Magyarország"),
        "logs": get_recent_logs(20),
        "discovery_targets": [
            {
                "key": t["key"],
                "title": t["title"],
                "university": t["university"],
                "country": t["country"],
                "city": t["city"],
                "category": t["category"],
                "url": t["url"],
            }
            for t in OFFICIAL_UNIVERSITY_TARGETS
        ],
    }


@app.post("/api/ollama/config")
def api_ollama_config(req: OllamaConfigRequest) -> Dict[str, Any]:
    ollama_client.model = req.model.strip()
    if req.base_url:
        ollama_client.base_url = req.base_url.strip().rstrip("/")
    log_agent_action("OLLAMA_CONFIG", ollama_client.model, "UPDATED", f"Host: {ollama_client.base_url}")
    return ollama_client.check_status()


@app.post("/api/ollama/pull")
def api_ollama_pull(req: OllamaConfigRequest) -> Dict[str, Any]:
    log_agent_action("OLLAMA_PULL", req.model, "STARTED", "Modell letöltése folyamatban...")
    res = ollama_client.pull_model(req.model.strip())
    log_agent_action(
        "OLLAMA_PULL",
        req.model,
        "SUCCESS" if res.get("ok") else "ERROR",
        res.get("status") or res.get("error", ""),
    )
    return res


@app.get("/api/programs")
def api_list_programs(
    region: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
) -> List[Dict[str, Any]]:
    return list_programs(region=region, category=category, search=search)


@app.post("/api/agent/analyze-url")
def api_analyze_url(req: AnalyzeUrlRequest) -> Dict[str, Any]:
    url = req.url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    program = analyze_program_from_url(
        url=url,
        ollama_client=ollama_client,
        use_ollama=req.use_ollama,
    )
    return {
        "ok": True,
        "program": program,
        "logs": get_recent_logs(10),
    }


@app.post("/api/agent/live-search")
def api_live_search(req: LiveSearchRequest) -> Dict[str, Any]:
    query = req.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Kérlek adj meg egy keresőkifejezést vagy URL-t!")

    max_t = max(1, min(req.max_targets, 6))
    log_agent_action("LIVE_WEB_SEARCH", query, "RUNNING", f"Célpontok keresése (max {max_t} egyetem)...")

    targets = resolve_search_targets(query, max_targets=max_t)
    analyzed_programs: List[Dict[str, Any]] = []
    trace_steps: List[Dict[str, str]] = []

    for t in targets:
        target_url = t["url"]
        trace_steps.append(
            {
                "title": t.get("title", target_url),
                "url": target_url,
                "source": t.get("source", "live"),
            }
        )
        prog = analyze_program_from_url(
            url=target_url,
            ollama_client=ollama_client,
            use_ollama=req.use_ollama,
        )
        analyzed_programs.append(prog)

    log_agent_action(
        "LIVE_WEB_SEARCH",
        query,
        "COMPLETED",
        f"{len(analyzed_programs)} képzés élőben kinyerve és elemezve.",
    )
    return {
        "ok": True,
        "query": query,
        "targets_found": trace_steps,
        "analyzed_programs": analyzed_programs,
        "logs": get_recent_logs(12),
    }


@app.post("/api/agent/compare")
def api_compare(req: CompareRequest) -> Dict[str, Any]:
    all_progs = list_programs()
    if req.program_ids:
        id_set = set(req.program_ids)
        selected = [p for p in all_progs if p["id"] in id_set]
    else:
        selected = all_progs
    report = build_comparison_report(selected, ollama_client=ollama_client)
    report["programs"] = selected
    return report


@app.post("/api/agent/chat")
def api_chat(req: ChatRequest) -> Dict[str, Any]:
    all_progs = list_programs()
    if req.program_ids:
        id_set = set(req.program_ids)
        selected = [p for p in all_progs if p["id"] in id_set]
    else:
        selected = all_progs
    log_agent_action("ADVISOR_CHAT", req.question[:80], "ANSWERED", f"{len(selected)} képzés kontextusával")
    return answer_advisor_question(req.question, selected, ollama_client=ollama_client)


@app.delete("/api/programs/{program_id}")
def api_delete_program(program_id: str) -> Dict[str, Any]:
    deleted = delete_program(program_id)
    return {"ok": deleted, "id": program_id}


@app.post("/api/programs/clear")
def api_clear_programs() -> Dict[str, Any]:
    count = clear_all_programs()
    log_agent_action("CLEAR_DB", "Összes képzés törlése", "CLEARED", f"{count} rekord törölve")
    return {"ok": True, "deleted_count": count}


@app.get("/api/export/markdown", response_class=PlainTextResponse)
def api_export_markdown() -> str:
    progs = list_programs()
    comp = build_comparison_report(progs, ollama_client=None)
    md_lines = [
        "# Magyar és Európai Politikatudományi & Nemzetközi Kapcsolatok MA Összehasonlító Jelentés",
        "",
        "## 1. Strukturált 7-Dimenziós Összehasonlító Táblázat",
        "",
        "| Egyetem & Képzés | Hossz (Kredit) | Helyszín | Fókusz | Főbb Tantárgyak | Felvételi Követelmények | Nehézség (1–10) |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
    ]
    for p in progs:
        courses_short = ", ".join(p.get("courses", [])[:5])
        md_lines.append(
            f"| **{p['university']}**<br>{p['program_name']} ({p['degree_type']}) "
            f"| {p['duration']} ({p['ects']} ECTS) "
            f"| {p['city']}, {p['country']} "
            f"| {p['focus']} "
            f"| {courses_short} "
            f"| {p['admission_requirements']} "
            f"| **{p['difficulty_score']}/10** ({p['difficulty_label']}) |"
        )
    md_lines.extend(["", "## 2. Összehasonlító Szintézis", "", comp["synthesis_markdown"]])
    return "\n".join(md_lines)


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def serve_index() -> FileResponse:
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))
