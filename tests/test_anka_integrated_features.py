# -*- coding: utf-8 -*-
"""ANKA AI Bütünleşik Modül ve Yetenek Testleri (Unittest & Standard Library)."""

import os
import sys
import shutil
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from anka.plugins.registry import PluginRegistry, BasePlugin
from anka.ai.router import InternalModelRouter, TaskType
from anka.memory.categorized import CategorizedMemory
from anka.files.rag_engine import AdvancedRAGEngine
from anka.core.agentic import AgenticComputerController, StepStatus
from anka.vision.analyzer import VisionAnalyzer
from anka.developer.coder import DeveloperCodingMode
from anka.digest.daily import DailyDigestSystem
from anka.security.center import SecurityCenter


class TestANKAIntegratedFeatures(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_plugin_registry(self):
        registry = PluginRegistry()
        plugins = registry.list_plugins()
        self.assertGreaterEqual(len(plugins), 4)
        names = [p["name"] for p in plugins]
        self.assertIn("WeatherSkill", names)
        self.assertIn("MediaControlSkill", names)

        res = registry.execute_action("WeatherSkill", "query", {"city": "Ankara"})
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["city"], "Ankara")

    def test_internal_model_router(self):
        router = InternalModelRouter()
        chat_route = router.route("chat")
        self.assertEqual(chat_route["task_type"], "chat")
        self.assertEqual(chat_route["temperature"], 0.7)

        coding_route = router.route("coding")
        self.assertEqual(coding_route["task_type"], "coding")
        self.assertEqual(coding_route["temperature"], 0.2)

    def test_categorized_memory(self):
        db_file = os.path.join(self.temp_dir, "test_cat_mem.db")
        memory = CategorizedMemory(db_path=db_file)

        memory.add("preferences", "Koyu Tema", key="ui_theme")
        memory.add("learned_facts", "Python harika bir dildir")

        summary = memory.get_user_summary()
        self.assertIn("Sizin hakkınızda bildiklerim", summary)
        self.assertIn("Python harika bir dildir", summary)

        results = memory.search("Python")
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0]["value"], "Python harika bir dildir")

    def test_rag_engine(self):
        db_file = os.path.join(self.temp_dir, "test_rag.db")
        doc_file = os.path.join(self.temp_dir, "ornek_belge.txt")

        with open(doc_file, "w", encoding="utf-8") as f:
            f.write("ANKA AI gelişmiş bir otonom Türkçe yapay zeka asistanıdır. RAG altyapısı belgeleri indeksler.")

        rag = AdvancedRAGEngine(db_path=db_file)
        with open(doc_file, "r", encoding="utf-8") as f:
            content = f.read()
        doc_id = rag.index_document(doc_file, content)
        self.assertGreater(doc_id, 0)

        results = rag.search_with_citation("otonom yapay zeka")
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0]["filename"], "ornek_belge.txt")

    def test_agentic_controller(self):
        controller = AgenticComputerController()
        plan = controller.create_plan("web araştırması yap")
        self.assertEqual(len(plan), 2)

        res = controller.execute_next_step(lambda step: "Başarılı")
        self.assertEqual(res["status"], "success")

    def test_developer_coding_mode(self):
        coder = DeveloperCodingMode(project_root=self.temp_dir)
        scan = coder.scan_project()
        self.assertEqual(scan["project_root"], self.temp_dir)

        change = coder.propose_code_change("test.py", "print('hello')")
        self.assertTrue(change["requires_user_approval"])

        success = coder.apply_code_change({
            "abs_path": os.path.join(self.temp_dir, "test.py"),
            "new_content": "print('hello')",
            "requires_user_approval": True,
        })
        self.assertTrue(success)
        self.assertTrue(os.path.exists(os.path.join(self.temp_dir, "test.py")))

    def test_daily_digest(self):
        db_file = os.path.join(self.temp_dir, "test_digest_mem.db")
        mem = CategorizedMemory(db_path=db_file)
        mem.add("learned_facts", "Yeni mimari tamamlandı")

        digest = DailyDigestSystem(memory=mem)
        report = digest.generate_digest(notes=["Alışverişe git"], tasks=["Testleri çalıştır"])

        self.assertEqual(report["notes_count"], 1)
        self.assertIn("Alışverişe git", report["report_text"])
        self.assertIn("Yeni mimari tamamlandı", report["report_text"])

    def test_security_center(self):
        perm_file = os.path.join(self.temp_dir, "perms.json")
        audit_db = os.path.join(self.temp_dir, "audit.db")

        sec = SecurityCenter(permissions_file=perm_file, audit_db=audit_db)
        perms = sec.get_permission_status()
        self.assertIsInstance(perms, dict)

        eval_res = sec.evaluate_request("system_shutdown")
        self.assertTrue(eval_res["allowed"])
        self.assertTrue(eval_res["requires_approval"])

        logs = sec.get_audit_logs()
        self.assertGreater(len(logs), 0)


if __name__ == "__main__":
    unittest.main()
