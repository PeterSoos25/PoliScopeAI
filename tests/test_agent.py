"""
Automated unit & integration tests for the PolSci & IR MA AI Agent.
Verifies live URL analysis, 7-dimensional extraction, difficulty scoring,
multi-university comparison synthesis, and advisor Q&A.
"""

import os
import tempfile
import unittest

# Use a temporary SQLite DB during tests
TEMP_DB = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
TEMP_DB.close()
os.environ["POLSCI_DB_PATH"] = TEMP_DB.name

from agent.analyzer import analyze_program_from_url
from agent.comparator import answer_advisor_question, build_comparison_report
from agent.scraper import resolve_search_targets, scrape_university_url
from agent.storage import init_db, list_programs


class TestPolSciAgent(unittest.TestCase):
    def setUp(self) -> None:
        init_db()

    def test_01_live_scrape_and_analyze_hungarian_and_european(self) -> None:
        # Analyze ELTE TáTK International Relations MA & CEU Vienna MA in Politics
        elte = analyze_program_from_url(
            "https://tatk.elte.hu/mesterszakok/nemzetkozi", use_ollama=False
        )
        ceu = analyze_program_from_url(
            "https://www.ceu.edu/academics/degrees/ma-politics-2-years", use_ollama=False
        )

        # Verify all 7 required comparison dimensions are populated
        for prog in (elte, ceu):
            self.assertTrue(prog["program_name"])
            self.assertTrue(prog["university"])
            self.assertTrue(prog["duration"])
            self.assertIn(prog["ects"], (60, 90, 120))
            self.assertTrue(prog["country"])
            self.assertTrue(prog["city"])
            self.assertTrue(prog["focus"])
            self.assertGreaterEqual(len(prog["courses"]), 4)
            self.assertTrue(prog["admission_requirements"])
            self.assertGreaterEqual(prog["difficulty_score"], 5.0)
            self.assertLessEqual(prog["difficulty_score"], 10.0)
            self.assertIn("selectivity", prog["difficulty_breakdown"])
            self.assertIn("methodology", prog["difficulty_breakdown"])

        # CEU should have higher quantitative/difficulty score than domestic average
        self.assertGreater(ceu["difficulty_score"], elte["difficulty_score"])

    def test_02_resolve_search_targets(self) -> None:
        hu_targets = resolve_search_targets("magyar politikatudomány MA", max_targets=3)
        self.assertGreaterEqual(len(hu_targets), 2)

        eu_targets = resolve_search_targets("Leiden Amsterdam KU Leuven Political Science", max_targets=3)
        self.assertEqual(len(eu_targets), 3)

    def test_03_comparison_and_advisor_chat(self) -> None:
        progs = list_programs()
        self.assertGreaterEqual(len(progs), 2)

        report = build_comparison_report(progs, ollama_client=None)
        self.assertEqual(report["count"], len(progs))
        self.assertIn("Összehasonlító Elemzés", report["synthesis_markdown"])

        ans = answer_advisor_question(
            "Melyik képzés a legnehezebb és mik a felvételi követelmények?",
            progs,
            ollama_client=None,
        )
        self.assertTrue(len(ans["answer"]) > 80)


if __name__ == "__main__":
    unittest.main()
