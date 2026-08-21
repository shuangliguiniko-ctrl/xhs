from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from userresearch_xhscrawler_cockpitux.config import ASSET_ROOT, load_config, validate_config
from userresearch_xhscrawler_cockpitux.brief import resolve_brief
from userresearch_xhscrawler_cockpitux.interaction import config_summary, selection_catalog
from userresearch_xhscrawler_cockpitux.models import StandardRecord
from userresearch_xhscrawler_cockpitux.planner import build_crawl_plan


class ConfigAndModelTests(unittest.TestCase):
    def test_sample_config_is_explicit(self):
        config = load_config(ASSET_ROOT / "examples" / "sample_project.yaml")
        self.assertTrue(config["brief"]["confirmed"])
        self.assertEqual(config["analysis"]["mode"], "fast")
        self.assertEqual(config["analysis"]["profile"], "mixed")
        self.assertIn("experience", config["analysis"]["profiles"])
        self.assertEqual(config["llm"]["provider"], "none")
        self.assertEqual(config["workflow"]["mode"], "ai")

    def test_standard_record_validation(self):
        record = StandardRecord(record_id="r1", record_type="post", source_platform="xiaohongshu", content_id="c1", content="有效文本")
        self.assertEqual(record.to_dict()["record_id"], "r1")
        with self.assertRaises(ValueError):
            StandardRecord(record_id="", record_type="post", source_platform="x", content_id="c", content="x").validate()

    def test_plan_separates_executed_and_suggested_keywords(self):
        config = load_config(ASSET_ROOT / "examples" / "sample_project.yaml")
        brief = resolve_brief(config)
        plan = build_crawl_plan(config, brief)
        self.assertEqual(plan["executed_keywords"], config["crawler"]["keywords"])
        self.assertTrue(plan["suggested_keyword_expansions"])
        self.assertTrue(all(item["executed"] is False for item in plan["suggested_keyword_expansions"]))
        self.assertTrue(plan["decision_logic"]["execute_only_confirmed_keywords"])

    def test_selection_catalog_explains_engine_and_profile_separately(self):
        catalog = selection_catalog()
        self.assertIn("fast", catalog["topic_engines"])
        self.assertIn("experience", catalog["research_profiles"])
        summary = config_summary(load_config(ASSET_ROOT / "examples" / "sample_project.yaml"))
        self.assertEqual(summary["mode_requested"], "fast")
        self.assertEqual(summary["profile_requested"], "mixed")
        self.assertIn("ui", catalog["workflow_modes"])
        self.assertEqual(summary["workflow_mode"], "ai")

    def test_workflow_and_collection_modes_are_validated(self):
        config = load_config(ASSET_ROOT / "examples" / "sample_project.yaml")
        for workflow_mode in ("ai", "ui"):
            config["workflow"]["mode"] = workflow_mode
            for adapter in ("browseract", "mediacrawler", "hybrid", "import", "mock"):
                config["crawler"]["adapter"] = adapter
                validate_config(config)
        config["workflow"]["mode"] = "silent"
        with self.assertRaisesRegex(ValueError, "workflow.mode"):
            validate_config(config)
