"""
Multi-University Comparative Synthesis & Grounded AI Advisor Engine.
Compares Hungarian and European Political Science & International Relations MA programs
across all 7 required dimensions and answers user questions using local Ollama + structured analytics.
"""

from typing import Any, Dict, List, Optional

from agent.ollama_client import OllamaClient


def build_comparison_report(
    programs: List[Dict[str, Any]],
    ollama_client: Optional[OllamaClient] = None,
) -> Dict[str, Any]:
    """
    Build a structured 7-dimension comparison matrix and executive synthesis
    for the selected university MA programs.
    """
    if not programs:
        return {
            "count": 0,
            "highlights": {},
            "synthesis_markdown": "Nincs kiválasztott képzés az összehasonlításhoz.",
            "engine": "none",
        }

    sorted_by_diff = sorted(programs, key=lambda p: p["difficulty_score"], reverse=True)
    hardest = sorted_by_diff[0]
    easiest = sorted_by_diff[-1]

    sorted_by_quant = sorted(
        programs,
        key=lambda p: p.get("difficulty_breakdown", {}).get("methodology", 0),
        reverse=True,
    )
    most_quant = sorted_by_quant[0]

    one_year_progs = [p for p in programs if p.get("ects", 120) <= 90]
    two_year_progs = [p for p in programs if p.get("ects", 120) >= 120]
    hu_progs = [p for p in programs if p.get("region_group") == "Magyarország"]
    eu_progs = [p for p in programs if p.get("region_group") != "Magyarország"]

    highlights = {
        "hardest_program": {
            "university": hardest["university"],
            "program_name": hardest["program_name"],
            "score": hardest["difficulty_score"],
        },
        "most_accessible_program": {
            "university": easiest["university"],
            "program_name": easiest["program_name"],
            "score": easiest["difficulty_score"],
        },
        "strongest_methodology": {
            "university": most_quant["university"],
            "program_name": most_quant["program_name"],
            "methodology_score": most_quant.get("difficulty_breakdown", {}).get("methodology", 7.0),
        },
        "hungarian_count": len(hu_progs),
        "european_count": len(eu_progs),
        "one_year_count": len(one_year_progs),
        "two_year_count": len(two_year_progs),
    }

    # Build analytical synthesis in Hungarian
    lines: List[str] = [
        f"### Összehasonlító Elemzés ({len(programs)} mesterszak alapján)",
        "",
        "#### 1. Képzési szerkezet, hossz és helyszín (Magyarország vs. Európa)",
    ]

    if hu_progs and eu_progs:
        lines.append(
            f"- **Magyarországi képzések ({len(hu_progs)} db):** Egységesen **2 éves (4 féléves, 120 ECTS)** bolognai struktúrát követnek "
            f"({', '.join(p['university'] for p in hu_progs)}). Előnyük az állami ösztöndíjas vagy Corvinus Ösztöndíjas finanszírozás és a mélyebb hazai/közép-európai intézményismeret."
        )
        lines.append(
            f"- **Európai nemzetközi képzések ({len(eu_progs)} db):** Gyakran kínálnak **1 éves intenzív (60–90 ECTS)** MSc/MA konstrukciót "
            f"({', '.join(p['university'] for p in eu_progs)}), amely gyorsabb munkaerőpiaci belépést ad, de sűrítettebb féléves terheléssel jár."
        )
    else:
        for p in programs:
            lines.append(
                f"- **{p['university']} – {p['program_name']}:** {p['duration']} ({p['ects']} ECTS), helyszín: {p['city']}, {p['country']} ({p['language']})."
            )

    lines.extend(
        [
            "",
            "#### 2. Fókusz és Tantárgyi Profil",
        ]
    )
    for p in programs:
        top_courses = ", ".join(p.get("courses", [])[:4])
        lines.append(
            f"- **{p['university']} ({p['program_name']}):** {p['focus']} *Kulcstárgyak:* {top_courses}."
        )

    lines.extend(
        [
            "",
            "#### 3. Felvételi Követelmények és Nehézségi Rangsor",
            f"- **Legmagasabb nehézségi index:** **{hardest['university']} – {hardest['program_name']}** (**{hardest['difficulty_score']}/10** – {hardest['difficulty_label']}). {hardest['difficulty_rationale']}",
            f"- **Legkiegyensúlyozottabb / legkönnyebben teljesíthető bemenet:** **{easiest['university']} – {easiest['program_name']}** (**{easiest['difficulty_score']}/10**).",
            f"- **Legerősebb kutatásmódszertani / kvantitatív fókusz:** **{most_quant['university']}** (módszertani szigor: **{most_quant.get('difficulty_breakdown', {}).get('methodology', 7.0)}/10**).",
            "",
            "#### 4. Kinek melyik képzés ajánlott?",
            f"- **Kutatói / PhD vagy adatelemzői karrierhez:** **{most_quant['university']} ({most_quant['program_name']})**, ahol a kutatásmódszertan és az empirikus elemzés kiemelt súlyú.",
            f"- **Diplomáciai, EU-s vagy nemzetközi szervezeti pályához:** "
            + (
                f"**{eu_progs[0]['university']}** vagy **{hu_progs[0]['university']}**"
                if (eu_progs and hu_progs)
                else f"**{programs[0]['university']} ({programs[0]['program_name']})**"
            )
            + " a nemzetközi intézményi és külpolitikai hálózat miatt.",
        ]
    )

    deterministic_synthesis = "\n".join(lines)
    engine_used = "Strukturált Akadémiai Összehasonlító Motor"

    # If local Ollama is running on the 2020 Mac, allow it to generate an additional custom executive commentary
    client = ollama_client or OllamaClient()
    status = client.check_status()
    if status.get("online"):
        compact_profiles = []
        for p in programs[:6]:
            compact_profiles.append(
                f"- {p['university']} | {p['program_name']} | Hossz: {p['duration']} | Hely: {p['city']}, {p['country']} | "
                f"Fókusz: {p['focus']} | Tárgyak: {', '.join(p['courses'][:5])} | "
                f"Felvételi: {p['admission_requirements']} | Nehézség: {p['difficulty_score']}/10"
            )
        prompt = (
            "Te egy egyetemi felvételi és politikatudományi szakértő AI ügynök vagy. "
            "Hasonlítsd össze magyar nyelven, tömören és strukturáltan az alábbi mesterszakokat "
            "a képzés hossza, helye, fókusza, tárgyai, felvételi követelményei és nehézsége alapján:\n\n"
            + "\n".join(compact_profiles)
        )
        ok, llm_text, used_model = client.chat(
            messages=[{"role": "user", "content": prompt}],
            json_mode=False,
            timeout=30.0,
        )
        if ok and len(llm_text.strip()) > 80:
            deterministic_synthesis = (
                f"{llm_text.strip()}\n\n---\n\n{deterministic_synthesis}"
            )
            engine_used = f"Helyi Ollama ({used_model}) + Strukturált Mátrix"

    return {
        "count": len(programs),
        "highlights": highlights,
        "synthesis_markdown": deterministic_synthesis,
        "engine": engine_used,
    }


def answer_advisor_question(
    question: str,
    programs: List[Dict[str, Any]],
    ollama_client: Optional[OllamaClient] = None,
) -> Dict[str, Any]:
    """
    Answer user questions in Hungarian grounded in the currently scraped university programs.
    Uses local Ollama LLM if active on the Mac, with an intelligent grounded analytical responder fallback.
    """
    client = ollama_client or OllamaClient()
    status = client.check_status()

    context_lines = []
    for p in programs[:10]:
        context_lines.append(
            f"[{p['university']} – {p['program_name']}]\n"
            f"  Hely: {p['city']}, {p['country']} | Hossz: {p['duration']} ({p['ects']} ECTS) | Nyelv: {p['language']} | Tandíj: {p.get('tuition', '')}\n"
            f"  Fókusz: {p['focus']}\n"
            f"  Tárgyak: {', '.join(p.get('courses', []))}\n"
            f"  Felvételi: {p['admission_requirements']}\n"
            f"  Nehézség: {p['difficulty_score']}/10 ({p['difficulty_label']}) – {p['difficulty_rationale']}\n"
            f"  Forrás: {p['source_url']}"
        )
    context_blob = "\n\n".join(context_lines)

    if status.get("online"):
        messages = [
            {
                "role": "system",
                "content": (
                    "Te egy magyar és európai politikatudományi / nemzetközi kapcsolatok MA tanácsadó AI ügynök vagy, "
                    "aki egy 2020-as Mac-en fut helyben. Válaszolj magyarul, pontosan, a megadott élőben legyűjtött "
                    "egyetemi adatokra támaszkodva."
                ),
            },
            {
                "role": "user",
                "content": f"ELEMZETT EGYETEMI KÉPZÉSEK ADATAI:\n{context_blob}\n\nFELHASZNÁLÓ KÉRDÉSE:\n{question}",
            },
        ]
        ok, resp_text, used_model = client.chat(messages=messages, timeout=35.0)
        if ok and resp_text.strip():
            return {
                "answer": resp_text.strip(),
                "engine": f"Ollama ({used_model})",
                "ollama_online": True,
            }

    # Grounded analytical response when Ollama is offline or warming up
    q_low = question.lower()
    if not programs:
        return {
            "answer": "Jelenleg nincs betöltött képzés. Használd a fenti Élő Webes Keresőt vagy kattints az egyik gyorsindító egyetemre!",
            "engine": "Hibrid Tanácsadó Motor",
            "ollama_online": False,
        }

    # Tailor response to question intent
    if any(k in q_low for k in ["nehéz", "nehez", "nehézség", "legnehezebb", "legkönnyebb", "szelektív"]):
        ranked = sorted(programs, key=lambda x: x["difficulty_score"], reverse=True)
        bullet_list = "\n".join(
            f"- **{p['university']} – {p['program_name']}**: **{p['difficulty_score']}/10** ({p['difficulty_label']}). "
            f"*Felvételi szelektivitás:* {p['difficulty_breakdown'].get('selectivity')}/10, "
            f"*Módszertani szigor:* {p['difficulty_breakdown'].get('methodology')}/10. {p['difficulty_rationale']}"
            for p in ranked
        )
        ans = (
            "### Képzések nehézségi rangsora és összehasonlítása\n\n"
            f"Az élőben elemzett {len(programs)} képzés nehézségi indexe (1–10-es skálán):\n\n"
            f"{bullet_list}\n\n"
            f"**Összegzés:** A legmagasabb elvárást a(z) **{ranked[0]['university']}** támasztja ({ranked[0]['difficulty_score']}/10), "
            f"míg a legkiegyensúlyozottabb bemeneti követelményekkel a(z) **{ranked[-1]['university']}** ({ranked[-1]['difficulty_score']}/10) rendelkezik."
        )
    elif any(k in q_low for k in ["felvételi", "felveteli", "nyelvvizsga", "ielts", "toefl", "kredit", "bekerül"]):
        bullet_list = "\n".join(
            f"- **{p['university']} ({p['program_name']})**: {p['admission_requirements']} "
            f"*(Nyelv: {p.get('admission_details', {}).get('language_exam', p['language'])})*"
            for p in programs
        )
        ans = (
            "### Felvételi követelmények összehasonlítása\n\n"
            f"{bullet_list}\n\n"
            "**Fő különbség:** A **magyarországi egyetemeken** (ELTE, Corvinus, PPKE, NKE, PTE) a Felvi.hu-n keresztüli jelentkezés, a BA kreditelismerés (40–60 kredit) "
            "és a **szóbeli felvételi vizsga** (megadott olvasmánylistával) a döntő. Az **európai egyetemeken** (CEU, KU Leuven, UvA, Leiden, Sciences Po, LSE) "
            "nincs szóbeli tételhúzás, viszont kötelező a **C1 angol nyelvvizsga (IELTS 7.0 / TOEFL 100)**, a magas BA átlag (GPA), az angol nyelvű kutatási terv és 2 akadémiai ajánlólevél."
        )
    elif any(k in q_low for k in ["tárgy", "targy", "tanterv", "kurzus", "módszertan", "statisztika", "fókusz"]):
        bullet_list = "\n".join(
            f"- **{p['university']} – {p['program_name']}**\n"
            f"  - *Fókusz:* {p['focus']}\n"
            f"  - *Főbb tárgyak:* {', '.join(p.get('courses', [])[:6])}"
            for p in programs
        )
        ans = f"### Tantárgyak és szakmai fókusz összehasonlítása\n\n{bullet_list}"
    elif any(k in q_low for k in ["hossz", "félév", "év", "idő", "tandíj", "ösztöndíj", "költség", "ár"]):
        bullet_list = "\n".join(
            f"- **{p['university']} ({p['city']}, {p['country']})**: **{p['duration']}** ({p['ects']} ECTS) | *Finanszírozás:* {p.get('tuition', 'Állami / Önköltséges')}"
            for p in programs
        )
        ans = f"### Képzési idő, helyszín és finanszírozás\n\n{bullet_list}"
    else:
        comp = build_comparison_report(programs, ollama_client=None)
        ans = comp["synthesis_markdown"]

    return {
        "answer": ans,
        "engine": "Strukturált Akadémiai Tanácsadó Motor (Kapcsold be az Ollama-t a szabad szöveges LLM generáláshoz!)",
        "ollama_online": False,
    }
