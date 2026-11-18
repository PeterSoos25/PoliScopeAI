"""
Lightweight SQLite persistence for scraped & analyzed university MA programs.
Uses almost zero RAM on a 2020 Mac while persisting live-scraped results across sessions.
"""

import json
import os
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional

DB_PATH = os.environ.get(
    "POLSCI_DB_PATH",
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "programs.db"),
)


def get_connection() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_connection()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS programs (
                id TEXT PRIMARY KEY,
                program_name TEXT NOT NULL,
                degree_type TEXT NOT NULL,
                category TEXT NOT NULL,
                university TEXT NOT NULL,
                faculty TEXT,
                country TEXT NOT NULL,
                city TEXT NOT NULL,
                region_group TEXT NOT NULL,
                duration TEXT NOT NULL,
                ects INTEGER,
                language TEXT NOT NULL,
                tuition TEXT,
                focus TEXT NOT NULL,
                specializations_json TEXT NOT NULL,
                courses_json TEXT NOT NULL,
                admission_requirements TEXT NOT NULL,
                admission_details_json TEXT NOT NULL,
                difficulty_score REAL NOT NULL,
                difficulty_label TEXT NOT NULL,
                difficulty_breakdown_json TEXT NOT NULL,
                difficulty_rationale TEXT NOT NULL,
                source_url TEXT NOT NULL,
                crawled_urls_json TEXT NOT NULL,
                raw_excerpt TEXT,
                extraction_engine TEXT NOT NULL,
                analyzed_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS agent_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                action_type TEXT NOT NULL,
                query_or_url TEXT NOT NULL,
                status TEXT NOT NULL,
                details TEXT
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def save_program(program: Dict[str, Any]) -> Dict[str, Any]:
    init_db()
    conn = get_connection()
    now = datetime.utcnow().isoformat() + "Z"
    program["analyzed_at"] = program.get("analyzed_at") or now
    try:
        conn.execute(
            """
            INSERT OR REPLACE INTO programs (
                id, program_name, degree_type, category, university, faculty,
                country, city, region_group, duration, ects, language, tuition,
                focus, specializations_json, courses_json,
                admission_requirements, admission_details_json,
                difficulty_score, difficulty_label, difficulty_breakdown_json,
                difficulty_rationale, source_url, crawled_urls_json,
                raw_excerpt, extraction_engine, analyzed_at
            ) VALUES (
                ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?,
                ?, ?,
                ?, ?, ?,
                ?, ?, ?,
                ?, ?, ?
            )
            """,
            (
                program["id"],
                program["program_name"],
                program.get("degree_type", "MA"),
                program.get("category", "Politikatudomány"),
                program["university"],
                program.get("faculty", ""),
                program["country"],
                program["city"],
                program.get("region_group", "Európa" if program["country"] != "Magyarország" else "Magyarország"),
                program["duration"],
                int(program.get("ects", 120)),
                program.get("language", "Magyar / Angol"),
                program.get("tuition", ""),
                program["focus"],
                json.dumps(program.get("specializations", []), ensure_ascii=False),
                json.dumps(program.get("courses", []), ensure_ascii=False),
                program["admission_requirements"],
                json.dumps(program.get("admission_details", {}), ensure_ascii=False),
                float(program["difficulty_score"]),
                program.get("difficulty_label", "Közepesen nehéz"),
                json.dumps(program.get("difficulty_breakdown", {}), ensure_ascii=False),
                program.get("difficulty_rationale", ""),
                program["source_url"],
                json.dumps(program.get("crawled_urls", [program["source_url"]]), ensure_ascii=False),
                program.get("raw_excerpt", "")[:3500],
                program.get("extraction_engine", "Ollama + Hybrid"),
                program["analyzed_at"],
            ),
        )
        conn.commit()
    finally:
        conn.close()
    return program


def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    d = dict(row)
    d["specializations"] = json.loads(d.pop("specializations_json", "[]") or "[]")
    d["courses"] = json.loads(d.pop("courses_json", "[]") or "[]")
    d["admission_details"] = json.loads(d.pop("admission_details_json", "{}") or "{}")
    d["difficulty_breakdown"] = json.loads(d.pop("difficulty_breakdown_json", "{}") or "{}")
    d["crawled_urls"] = json.loads(d.pop("crawled_urls_json", "[]") or "[]")
    return d


def list_programs(
    region: Optional[str] = None,
    category: Optional[str] = None,
    search: Optional[str] = None,
) -> List[Dict[str, Any]]:
    init_db()
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM programs ORDER BY analyzed_at DESC, difficulty_score DESC"
        ).fetchall()
        items = [_row_to_dict(r) for r in rows]
        if region and region != "all":
            items = [i for i in items if i["region_group"].lower() == region.lower()]
        if category and category != "all":
            items = [i for i in items if category.lower() in i["category"].lower()]
        if search:
            q = search.lower().strip()
            items = [
                i
                for i in items
                if q in i["program_name"].lower()
                or q in i["university"].lower()
                or q in i["city"].lower()
                or q in i["country"].lower()
                or q in i["focus"].lower()
                or any(q in c.lower() for c in i["courses"])
            ]
        return items
    finally:
        conn.close()


def get_program(program_id: str) -> Optional[Dict[str, Any]]:
    init_db()
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM programs WHERE id = ?", (program_id,)).fetchone()
        return _row_to_dict(row) if row else None
    finally:
        conn.close()


def delete_program(program_id: str) -> bool:
    init_db()
    conn = get_connection()
    try:
        cur = conn.execute("DELETE FROM programs WHERE id = ?", (program_id,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def clear_all_programs() -> int:
    init_db()
    conn = get_connection()
    try:
        cur = conn.execute("DELETE FROM programs")
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()


def log_agent_action(action_type: str, query_or_url: str, status: str, details: str = "") -> None:
    init_db()
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO agent_logs (timestamp, action_type, query_or_url, status, details)
            VALUES (?, ?, ?, ?, ?)
            """,
            (datetime.utcnow().isoformat() + "Z", action_type, query_or_url, status, details),
        )
        conn.commit()
    finally:
        conn.close()


def get_recent_logs(limit: int = 25) -> List[Dict[str, Any]]:
    init_db()
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM agent_logs ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
