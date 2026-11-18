"""
7-Dimensional University MA Program Analyzer & Difficulty Scoring Engine.
Combines real-time web scraping with Local Ollama LLM extraction and a deterministic
academic parser so results are fast, accurate, and resilient on a 2020 Mac.
"""

import hashlib
import re
from typing import Any, Dict, List, Optional

from agent.ollama_client import OllamaClient
from agent.scraper import scrape_university_url
from agent.storage import log_agent_action, save_program


def _slugify_id(url: str, title: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", (title or url).lower()).strip("-")[:42]
    digest = hashlib.md5(url.encode("utf-8")).hexdigest()[:6]
    return f"{base}-{digest}"


def _detect_location_and_university(url: str, text: str, title: str, matched: Optional[Dict[str, Any]]) -> Dict[str, str]:
    if matched:
        country = matched["country"]
        return {
            "university": matched["university"],
            "country": country,
            "city": matched["city"],
            "region_group": "Magyarország" if country == "Magyarország" else "Európa",
            "category": matched.get("category", "Politikatudomány"),
        }

    u_low = url.lower()
    t_low = (title + " " + text[:2500]).lower()

    domain_map = [
        ("elte.hu", "Eötvös Loránd Tudományegyetem (ELTE)", "Magyarország", "Budapest"),
        ("uni-corvinus.hu", "Budapesti Corvinus Egyetem", "Magyarország", "Budapest"),
        ("ppke.hu", "Pázmány Péter Katolikus Egyetem (PPKE)", "Magyarország", "Budapest"),
        ("uni-nke.hu", "Nemzeti Közszolgálati Egyetem (NKE)", "Magyarország", "Budapest"),
        ("pte.hu", "Pécsi Tudományegyetem (PTE)", "Magyarország", "Pécs"),
        ("u-szeged.hu", "Szegedi Tudományegyetem (SZTE)", "Magyarország", "Szeged"),
        ("unideb.hu", "Debreceni Egyetem (DE)", "Magyarország", "Debrecen"),
        ("uni-miskolc.hu", "Miskolci Egyetem (ME)", "Magyarország", "Miskolc"),
        ("uni-bge.hu", "Budapesti Gazdasági Egyetem (BGE)", "Magyarország", "Budapest"),
        ("uni-milton.hu", "Milton Friedman Egyetem", "Magyarország", "Budapest"),
        ("ceu.edu", "Central European University (CEU)", "Ausztria", "Bécs (Vienna)"),
        ("kuleuven.be", "KU Leuven", "Belgium", "Leuven"),
        ("uva.nl", "University of Amsterdam (UvA)", "Hollandia", "Amszterdam"),
        ("universiteitleiden.nl", "Leiden University", "Hollandia", "Leiden / Hága"),
        ("sciencespo.fr", "Sciences Po Paris", "Franciaország", "Párizs"),
        ("lse.ac.uk", "London School of Economics (LSE)", "Egyesült Királyság", "London"),
        ("ox.ac.uk", "University of Oxford", "Egyesült Királyság", "Oxford"),
        ("unibo.it", "University of Bologna (UniBo)", "Olaszország", "Bologna"),
        ("hertie-school.org", "Hertie School", "Németország", "Berlin"),
        ("fu-berlin.de", "Freie Universität Berlin", "Németország", "Berlin"),
        ("uni-konstanz.de", "University of Konstanz", "Németország", "Konstanz"),
    ]
    for dom, uni, country, city in domain_map:
        if dom in u_low:
            return {
                "university": uni,
                "country": country,
                "city": city,
                "region_group": "Magyarország" if country == "Magyarország" else "Európa",
                "category": _infer_category(t_low),
            }

    is_hu = u_low.endswith(".hu") or ".hu/" in u_low or "magyarország" in t_low or "budapest" in t_low
    country = "Magyarország" if is_hu else "Európa"
    city = "Budapest" if "budapest" in t_low else ("Bécs" if "vienna" in t_low else "Európai Campus")
    uni_name = title.split("|")[-1].split("–")[-1].strip() if "|" in title or "–" in title else title[:60]
    return {
        "university": uni_name or "Egyetemi Mesterképzés",
        "country": country,
        "city": city,
        "region_group": "Magyarország" if country == "Magyarország" else "Európa",
        "category": _infer_category(t_low),
    }


def _infer_category(text_lower: str) -> str:
    has_ir = any(k in text_lower for k in ["nemzetközi tanulmányok", "international relations", "international politics", "diplomacy", "diplomácia"])
    has_pol = any(k in text_lower for k in ["politikatudomány", "political science", "ma in politics", "politológia"])
    has_pe = any(k in text_lower for k in ["politikai gazdaságtan", "political economy"])
    has_sec = any(k in text_lower for k in ["biztonság", "védelempolitika", "security"])
    if has_pe:
        return "Politikai gazdaságtan / Politikatudomány"
    if has_sec:
        return "Nemzetközi kapcsolatok / Biztonságpolitika"
    if has_ir and has_pol:
        return "Politikatudomány / Nemzetközi kapcsolatok"
    if has_ir:
        return "Nemzetközi kapcsolatok"
    return "Politikatudomány"


def _extract_duration_and_ects(text: str) -> Dict[str, Any]:
    t_low = text.lower()
    ects = 120
    duration = "2 év (4 félév)"

    if re.search(r"\b60\s*(?:ects|ec|sp\.|kredit)", t_low) and not re.search(r"\b120\s*(?:ects|ec|kredit)", t_low):
        ects = 60
        duration = "1 év (2 félév / 12 hónap)"
    elif re.search(r"\b90\s*ects", t_low) or "12 months full-time" in t_low:
        ects = 90
        duration = "1 év (12 hónap intenzív)"
    elif "1 year" in t_low and "2 years" in t_low:
        ects = 120
        duration = "2 év (4 félév, 120 ECTS) / 1 éves (60 ECTS) opcióval"
    elif "one-year" in t_low or "1-year" in t_low or "12 months" in t_low:
        ects = 60
        duration = "1 év (2 félév / 60 ECTS)"
    elif "4 félév" in t_low or "2 év" in t_low or "two-year" in t_low or "2 years" in t_low:
        ects = 120
        duration = "2 év (4 félév / 120 ECTS)"

    return {"duration": duration, "ects": ects}


def _extract_language_and_tuition(text: str, country: str) -> Dict[str, str]:
    t_low = text.lower()
    if "magyar és angol" in t_low or "magyar vagy angol" in t_low or "angol és magyar" in t_low:
        lang = "Magyar és Angol"
    elif "csak angol nyelven" in t_low or "language: english" in t_low or "language of instruction english" in t_low or country != "Magyarország":
        lang = "Angol (English)"
    else:
        lang = "Magyar"

    tuition = "Állami ösztöndíjas / Önköltséges"
    if "corvinus ösztöndíj" in t_low:
        tuition = "Corvinus Ösztöndíjjal térítésmentes (vagy 990 000 Ft/félév)"
    elif "480 000 ft" in t_low:
        tuition = "Állami ösztöndíjas / 480 000 Ft/félév (+80 000 Ft angol nyelvi hozzájárulás)"
    elif "12,000 eur" in t_low:
        tuition = "12 000 EUR/év (CEU tandíjmentességi és megélhetési ösztöndíjakkal)"
    elif country == "Magyarország":
        tuition = "Állami ösztöndíjas és önköltséges (~350 000–550 000 Ft/félév)"
    elif country in ("Hollandia", "Belgium", "Olaszország", "Franciaország"):
        tuition = "EU-s hallgatói kedvezményes tandíj (~1 100–2 600 EUR/év) + ösztöndíjak"
    elif "Egyesült Királyság" in country:
        tuition = "Nemzetközi / UK mesterszakos tandíj + kiválósági ösztöndíjak"

    return {"language": lang, "tuition": tuition}


def _extract_courses_and_focus(text: str, category: str) -> Dict[str, Any]:
    # Check for explicit course lists in text
    courses: List[str] = []
    specializations: List[str] = []

    course_patterns = [
        r"(?:Főbb tantárgyak|Kötelező tárgyak\*?|Core Courses|Courses|A képzés által érintett témák, tantárgyak)[:\s]+([^\n]+(?:\n[^\n]+){0,6})",
    ]
    for pat in course_patterns:
        m = re.search(pat, text, re.I)
        if m:
            raw_block = m.group(1)
            # Split by comma or newline
            parts = re.split(r"[,•\n;]+", raw_block)
            for p in parts:
                clean_p = p.strip(" -*.\t")
                if 4 <= len(clean_p) <= 75 and not clean_p.lower().startswith(("felvételi", "teljes", "letölthető", "a teljesség")):
                    if clean_p not in courses:
                        courses.append(clean_p)

    # Extract specializations
    spec_match = re.search(
        r"(?:Specializációk|Választható modulok|Specializations|Specialization Tracks)[:\s]+([^\n]+(?:\n[^\n]+){0,4})",
        text,
        re.I,
    )
    if spec_match:
        raw_spec = spec_match.group(1)
        for sp in re.split(r"[,;\n•]+|\d+\)", raw_spec):
            c_sp = sp.strip(" -*.\t")
            if 4 <= len(c_sp) <= 70 and c_sp not in specializations:
                specializations.append(c_sp)

    # Fallback domain-specific courses if webpage only linked a PDF
    if len(courses) < 4:
        if "gazdaság" in category.lower():
            courses = [
                "Empirical Analytical Methods (Empirikus elemzési módszerek)",
                "Political Economy in Macroeconomics",
                "Political and Economic Systems and Transitions",
                "Public Economics and Public Choice",
                "State and Globalization / State and Governance",
                "International Political Economy",
            ]
        elif "nemzetközi" in category.lower():
            courses = [
                "Nemzetközi kapcsolatok elméletei (IR Theories)",
                "Nemzetközi politikai gazdaságtan (IPE)",
                "Diplomácia és külpolitikai elemzés",
                "Európai Unió intézményrendszere és külkapcsolatai",
                "Biztonságpolitika, geopolitika és konfliktuskutatás",
                "Társadalomtudományi kutatásmódszertan",
                "Nemzetközi jog és emberi jogok",
            ]
        else:
            courses = [
                "Kortárs politikaelméletek (Contemporary Political Theory)",
                "Összehasonlító politikatudomány és intézménytan (Comparative Politics)",
                "Kvantitatív és kvalitatív kutatásmódszertan",
                "Pártok, választási rendszerek és politikai viselkedés",
                "Közpolitikai elemzés és kormányzás (Public Policy & Governance)",
                "Politikai gazdaságtan (Political Economy)",
                "Politikai kommunikáció és szakdolgozati kutatószeminárium",
            ]

    # Focus summary
    focus_match = re.search(r"(?:Fókusz(?: és modulok| és specializációk)?|Focus(?: & Specializations)?)[:\s]+([^\n]+)", text, re.I)
    if focus_match:
        focus = focus_match.group(1).strip()
    else:
        focus = (
            f"{category} fókuszú mesterképzés elméleti, összehasonlító intézménytani és "
            f"empirikus kutatásmódszertani képzéssel."
        )

    return {
        "focus": focus,
        "courses": courses[:10],
        "specializations": specializations[:6],
    }


def _extract_admissions(text: str, country: str) -> Dict[str, Any]:
    adm_match = re.search(
        r"(?:Felvételi követelmények|Admission Requirements|Jelentkezési feltételek)[:\s]+([^\n]+(?:\n[^\n]+){0,4})",
        text,
        re.I,
    )
    if adm_match:
        summary = " ".join(adm_match.group(1).split())
    elif country == "Magyarország":
        summary = (
            "Alapszakos (BA) diploma politikatudomány / nemzetközi tanulmányok területen (vagy 60 kredit előzetes kreditelismeréssel), "
            "szóbeli felvételi vizsga megadott szakirodalom és motivációs beszélgetés alapján (Felvi.hu)."
        )
    else:
        summary = (
            "Politikatudományi vagy társadalomtudományi BA diploma módszertani előképzettséggel, "
            "C1 angol nyelvvizsga (IELTS 7.0 / TOEFL 100), motivációs levél, kutatási terv és akadémiai ajánlólevelek."
        )

    t_low = text.lower()
    lang_req = "C1 angol (IELTS 7.0 / TOEFL 94–100+)" if ("ielts 7" in t_low or "toefl 100" in t_low or country != "Magyarország") else "B2 komplex nyelvvizsga / angol szaknyelvi kompetencia"
    exam_type = (
        "Szóbeli felvételi vizsga (kötelező irodalom + motiváció, 99+1 pont)"
        if country == "Magyarország"
        else "Dokumentumalapú szelektív bírálat (GPA, kutatási terv, ajánlólevelek) + esetenként interjú"
    )
    credits_req = (
        "Teljes beszámítású BA (Politikatudomány / Nemzetközi tanulmányok) vagy 40–60 társadalomtudományi kredit"
        if country == "Magyarország"
        else "180–240 ECTS BA diploma politikatudományi és empirikus kutatásmódszertani kreditekkel"
    )

    return {
        "admission_requirements": summary[:520],
        "admission_details": {
            "degree_and_credits": credits_req,
            "language_exam": lang_req,
            "exam_or_interview": exam_type,
        },
    }


def _calculate_difficulty(
    url: str,
    text: str,
    country: str,
    ects: int,
    courses: List[str],
) -> Dict[str, Any]:
    """
    Compute a multi-dimensional difficulty score (1.0 - 10.0) across 4 academic criteria:
    1) Selectivity (Felvételi szelektivitás)
    2) Methodology (Kvantitatív és módszertani szigor)
    3) Workload (Féléves olvasmány- és kutatási terhelés / intenzitás)
    4) Language & Academic Output (Idegen nyelvi és publikációs/szakdolgozati elvárások)
    """
    t_low = (url + " " + text + " " + " ".join(courses)).lower()

    # 1. Selectivity (1-10)
    selectivity = 6.5
    if any(k in t_low for k in ["lse.ac.uk", "sciencespo.fr", "ox.ac.uk"]):
        selectivity = 9.5
    elif any(k in t_low for k in ["ceu.edu", "uva.nl", "universiteitleiden.nl", "kuleuven.be"]):
        selectivity = 8.4
    elif any(k in t_low for k in ["uni-corvinus.hu", "ajk.elte.hu", "tatk.elte.hu"]):
        selectivity = 7.4
    elif any(k in t_low for k in ["unibo.it", "ppke.hu", "uni-nke.hu", "pte.hu"]):
        selectivity = 6.8

    # 2. Methodology / Quantitative rigor (1-10)
    methodology = 6.4
    quant_hits = sum(
        1
        for kw in [
            "programming with r",
            "statistics",
            "quantitative",
            "kvantitatív",
            "empirical analytical",
            "econometrics",
            "qca",
            "machine learning",
            "game theory",
            "statisztika",
            "macroeconomics",
        ]
        if kw in t_low
    )
    methodology = min(9.6, 6.2 + quant_hits * 0.55)

    # 3. Workload / Pacing intensity (1-10)
    workload = 7.0
    if ects == 60 or ects == 90:
        # 1-year intensive Master's packs core courses + thesis into 10-12 months
        workload += 1.4
    if "15,000 words" in t_low or "10,000-word" in t_low or "phd-level" in t_low:
        workload += 0.8
    if "kötelező, nyolchetes szakmai gyakorlat" in t_low or "three academic semesters" in t_low:
        workload += 0.5
    workload = min(9.6, round(workload, 1))

    # 4. Language & Academic demands (1-10)
    lang_academic = 6.8
    if "ielts 7.0" in t_low or "toefl 100" in t_low or "c1" in t_low:
        lang_academic = 8.8
    elif "language: english" in t_low or "nyelv angol" in t_low or "angol nyelven" in t_low:
        lang_academic = 7.9

    overall = round(
        selectivity * 0.28 + methodology * 0.27 + workload * 0.25 + lang_academic * 0.20,
        1,
    )

    if overall >= 8.7:
        label = "Rendkívül magas / Nemzetközi elit szint"
    elif overall >= 7.8:
        label = "Magas / Erősen kutatás- és módszertan-orientált"
    elif overall >= 7.0:
        label = "Erős akadémiai szint / Mérsékelten szelektív"
    else:
        label = "Közepes / Kiegyensúlyozott elméleti-gyakorlati terhelés"

    rationale_parts = []
    if selectivity >= 8.2:
        rationale_parts.append("magas nemzetközi felvételi szelektivitás (C1 angol, erős GPA és kutatási terv)")
    else:
        rationale_parts.append("szakirányú BA kreditekre és szóbeli felvételi irodalomra épülő bemenet")

    if methodology >= 7.8:
        rationale_parts.append("komoly kvantitatív és empirikus módszertani elvárások (statisztika / R / politikai gazdaságtan)")
    else:
        rationale_parts.append("elsősorban kvalitatív, intézménytani és elemző szemináriumi fókusz")

    if ects in (60, 90):
        rationale_parts.append("sűrített, 1 éves intenzív képzési tempó gyors szakdolgozat-leadással")
    else:
        rationale_parts.append("2 éves (4 féléves, 120 ECTS) kiegyensúlyozottabb ütemezés")

    rationale = "A nehézségi indexet meghatározza: " + "; ".join(rationale_parts) + "."

    return {
        "difficulty_score": overall,
        "difficulty_label": label,
        "difficulty_breakdown": {
            "selectivity": round(selectivity, 1),
            "methodology": round(methodology, 1),
            "workload": round(workload, 1),
            "language_academic": round(lang_academic, 1),
        },
        "difficulty_rationale": rationale,
    }


def analyze_program_from_url(
    url: str,
    ollama_client: Optional[OllamaClient] = None,
    use_ollama: bool = True,
) -> Dict[str, Any]:
    """
    Scrape a live university URL, extract all 7 comparison dimensions,
    enrich with local Ollama LLM if available, and persist to SQLite.
    """
    scraped = scrape_university_url(url, crawl_subpages=True)
    matched = scraped.get("matched_target")
    text = scraped.get("text", "")
    title = matched["title"] if matched else scraped.get("title", url)

    loc_uni = _detect_location_and_university(scraped["url"], text, title, matched)
    dur_info = _extract_duration_and_ects(text)
    lang_tuition = _extract_language_and_tuition(text, loc_uni["country"])
    curr_info = _extract_courses_and_focus(text, loc_uni["category"])
    adm_info = _extract_admissions(text, loc_uni["country"])
    diff_info = _calculate_difficulty(
        scraped["url"], text, loc_uni["country"], dur_info["ects"], curr_info["courses"]
    )

    program_name = title
    if "–" in title:
        program_name = title.split("–", 1)[1].strip()
    elif "|" in title:
        program_name = title.split("|", 1)[0].strip()

    degree_type = "MSc" if "msc" in title.lower() or "master of science" in text.lower() else "MA"
    extraction_engine = "Élő Web Scraper + Akadémiai Szabálymotor"

    # Optional enrichment via Local Ollama LLM on the user's 2020 Mac
    client = ollama_client or OllamaClient()
    if use_ollama:
        status = client.check_status()
        if status.get("online"):
            prompt = (
                "Te egy felsőoktatási elemző AI ügynök vagy. A megadott egyetemi honlapszöveg alapján "
                "nyerd ki magyar nyelven a mesterszak adatait JSON formátumban az alábbi kulcsokkal:\n"
                '{\n'
                '  "program_name": "pontos szaknév",\n'
                '  "focus": "2-3 mondatos összefoglaló a képzés fókuszáról magyarul",\n'
                '  "courses": ["tantárgy 1", "tantárgy 2", "tantárgy 3", "tantárgy 4", "tantárgy 5"],\n'
                '  "admission_requirements": "felvételi követelmények tömör összefoglalása magyarul",\n'
                '  "difficulty_rationale": "a képzés nehézségének 2 mondatos indoklása magyarul"\n'
                '}\n\n'
                f"URL: {scraped['url']}\n"
                f"SZÖVEG:\n{text[:3200]}"
            )
            ok, llm_resp, used_model = client.chat(
                messages=[{"role": "user", "content": prompt}],
                json_mode=True,
                timeout=25.0,
            )
            if ok and llm_resp:
                parsed = client.extract_json_object(llm_resp)
                if parsed:
                    if parsed.get("focus") and len(str(parsed["focus"])) > 20:
                        curr_info["focus"] = str(parsed["focus"])
                    if isinstance(parsed.get("courses"), list) and len(parsed["courses"]) >= 3:
                        curr_info["courses"] = [str(c) for c in parsed["courses"][:10]]
                    if parsed.get("admission_requirements") and len(str(parsed["admission_requirements"])) > 20:
                        adm_info["admission_requirements"] = str(parsed["admission_requirements"])
                    if parsed.get("difficulty_rationale") and len(str(parsed["difficulty_rationale"])) > 20:
                        diff_info["difficulty_rationale"] = str(parsed["difficulty_rationale"])
                    extraction_engine = f"Élő Web Scraper + Helyi Ollama ({used_model})"

    program_record: Dict[str, Any] = {
        "id": matched["key"] if matched else _slugify_id(scraped["url"], title),
        "program_name": program_name,
        "degree_type": degree_type,
        "category": loc_uni["category"],
        "university": loc_uni["university"],
        "faculty": "",
        "country": loc_uni["country"],
        "city": loc_uni["city"],
        "region_group": loc_uni["region_group"],
        "duration": dur_info["duration"],
        "ects": dur_info["ects"],
        "language": lang_tuition["language"],
        "tuition": lang_tuition["tuition"],
        "focus": curr_info["focus"],
        "specializations": curr_info["specializations"],
        "courses": curr_info["courses"],
        "admission_requirements": adm_info["admission_requirements"],
        "admission_details": adm_info["admission_details"],
        "difficulty_score": diff_info["difficulty_score"],
        "difficulty_label": diff_info["difficulty_label"],
        "difficulty_breakdown": diff_info["difficulty_breakdown"],
        "difficulty_rationale": diff_info["difficulty_rationale"],
        "source_url": scraped["url"],
        "crawled_urls": scraped["crawled_urls"],
        "raw_excerpt": text[:2500],
        "extraction_engine": extraction_engine,
    }

    saved = save_program(program_record)
    log_agent_action(
        action_type="LIVE_URL_ANALYZE",
        query_or_url=scraped["url"],
        status="SUCCESS" if scraped["live_fetched"] else "SNAPSHOT_ENRICHED",
        details=f"{saved['university']} – {saved['program_name']} (Nehézség: {saved['difficulty_score']}/10, { len(scraped['crawled_urls']) } oldal)",
    )
    return saved
