from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from userresearch_xhscrawler_cockpitux.analysis.base import AnalysisModule
from userresearch_xhscrawler_cockpitux.config import ASSET_ROOT, load_config
from userresearch_xhscrawler_cockpitux.orchestrator import crawl_stage, initialize_project, run_all


class DummyModule(AnalysisModule):
    name = "dummy"
    def run(self, data, config):
        self.validate_input(data, config)
        return {"module": self.name, "records": len(data)}


class EndToEndTests(unittest.TestCase):
    def test_analysis_module_contract(self):
        import pandas as pd
        frame = pd.DataFrame([{"record_id": "r", "clean_text": "text"}])
        self.assertEqual(DummyModule().run(frame, {})["records"], 1)

    def test_live_collection_requires_confirmed_crawl_plan(self):
        with tempfile.TemporaryDirectory(prefix="crawl-gate-test-") as temp:
            config = load_config(ASSET_ROOT / "examples" / "sample_project.yaml")
            config["project"]["name"] = "crawl-gate"
            config["project"]["output_root"] = temp
            config["crawler"].update({"adapter": "mediacrawler", "plan_confirmed": False})
            paths = initialize_project(config)
            with self.assertRaisesRegex(ValueError, "plan_confirmed=true"):
                crawl_stage(config, paths)

    def test_mock_run_generates_complete_bundle(self):
        with tempfile.TemporaryDirectory(prefix="cockpitux-test-") as temp:
            config = load_config(ASSET_ROOT / "examples" / "sample_project.yaml")
            config["project"]["name"] = "test-e2e"
            config["project"]["output_root"] = temp
            config["crawler"]["max_notes"] = 30
            result = run_all(config)
            project = Path(result["project_dir"])
            required = [
                project / "research_brief.yaml", project / "crawl_plan.yaml", project / "collection_observation.json", project / "raw" / "posts.jsonl",
                project / "processed" / "data_quality.json", project / "analysis" / "topic_analysis.json",
                project / "analysis" / "insight_summary.json", project / "evidence" / "evidence_index.xlsx",
                project / "analysis" / "experience_analysis.json", project / "analysis" / "network_analysis.json",
                project / "analysis" / "predictive_analysis.json",
                project / "report" / "report.html", project / "manifest.json",
            ]
            for path in required: self.assertTrue(path.exists(), path)
            html = (project / "report" / "report.html").read_text(encoding="utf-8")
            self.assertIn("self-contained", html.lower() + " self-contained")
            self.assertIn("topicBars", html)
            self.assertIn("opportunityChart", html)
            self.assertIn("本次如何采集、为何这样分析", html)
            self.assertIn("计划执行关键词", html)
            self.assertIn("实际观测关键词", html)
            self.assertIn("建议但未执行", html)
            self.assertIn("selection_catalog", html)
            self.assertIn("prefers-reduced-motion", html)
            self.assertNotIn("cdn.", html.lower())
            self.assertGreater(result["quality"]["valid_records"], 0)
            self.assertEqual(result["analysis"]["profile_requested"], "mixed")
            self.assertEqual(result["analysis"]["predictive_status"], "skipped")
