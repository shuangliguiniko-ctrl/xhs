from pathlib import Path
import json
import sys
import tempfile
import unittest

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from userresearch_xhscrawler_cockpitux.analysis.advanced import (
    enrich_text_features,
    run_network_analysis,
    run_predictive_analysis,
)
from userresearch_xhscrawler_cockpitux.analysis.engine import _taxonomy_rules
from userresearch_xhscrawler_cockpitux.crawler.adapters import _parse_mediacrawler_output, browser_records, collect_records
from userresearch_xhscrawler_cockpitux.storage import ProjectPaths


class AdvancedAnalysisTests(unittest.TestCase):
    def test_project_taxonomy_override(self):
        config = {"analysis": {"taxonomy": {"features": {"HUD显示系统": ["AR-HUD", "抬头显示"]}}}}
        rules = _taxonomy_rules(config, "features", {"fallback": ["fallback"]})
        self.assertEqual(rules, {"HUD显示系统": ["AR-HUD", "抬头显示"]})

    def test_mediacrawler_jsonl_bridge_and_deidentification(self):
        with tempfile.TemporaryDirectory(prefix="xhs-mediacrawler-") as temp:
            root = Path(temp) / "xhs" / "jsonl"
            root.mkdir(parents=True)
            fixture_value = "fixture-" + "only"
            content = {
                "note_id": "n1", "title": "AR-HUD体验", "desc": "夜间显示清晰", "time": 1767225600000,
                "nickname": "测试用户", "creator_hash": "author-fingerprint", "liked_count": "12", "collected_count": 3,
                "comment_count": 1, "share_count": 2, "source_keyword": "AR-HUD 体验",
                "note_url": f"https://www.xiaohongshu.com/explore/n1?xsec_token={fixture_value}&foo=bar",
                "xsec_token": fixture_value,
            }
            comment = {"comment_id": "c1", "note_id": "n1", "content": "有时重影", "create_time": 1767225600, "nickname": "评论者", "like_count": 4}
            (root / "search_contents_2026-08-10.jsonl").write_text(json.dumps(content, ensure_ascii=False) + "\n", encoding="utf-8")
            (root / "search_comments_2026-08-10.jsonl").write_text(json.dumps(comment, ensure_ascii=False) + "\n", encoding="utf-8")
            config = {"crawler": {"retain_author_fields": False}}
            posts, comments, failures = _parse_mediacrawler_output(Path(temp), config)
            self.assertEqual((len(posts), len(comments), len(failures)), (1, 1, 0))
            self.assertEqual(posts[0]["author_name"], "")
            self.assertNotIn("xsec_token", posts[0]["url"])
            self.assertNotIn("creator_hash", posts[0]["raw_data"])
            self.assertNotIn("xsec_token", posts[0]["raw_data"]["note_url"])
            self.assertEqual(comments[0]["parent_id"], posts[0]["record_id"])

    def test_mediacrawler_global_limit_round_robins_keywords(self):
        with tempfile.TemporaryDirectory(prefix="xhs-balanced-sample-") as temp:
            root = Path(temp) / "xhs" / "jsonl"
            root.mkdir(parents=True)
            rows = []
            for keyword in ("座舱", "语音", "HUD"):
                for index in range(4):
                    rows.append({"note_id": f"{keyword}-{index}", "title": keyword, "desc": "体验记录", "source_keyword": keyword})
            (root / "search_contents.jsonl").write_text(
                "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8"
            )
            config = {"crawler": {"retain_author_fields": False, "keywords": ["座舱", "语音", "HUD"], "max_notes": 5}}
            posts, _, failures = _parse_mediacrawler_output(Path(temp), config)
            counts = {keyword: sum(post["source_keyword"] == keyword for post in posts) for keyword in config["crawler"]["keywords"]}
            self.assertEqual(len(posts), 5)
            self.assertEqual(counts, {"座舱": 2, "语音": 2, "HUD": 1})
            self.assertFalse(failures)

    def test_mediacrawler_config_documents_venv_interpreter(self):
        source = (ROOT / "src" / "userresearch_xhscrawler_cockpitux" / "crawler" / "adapters.py").read_text(encoding="utf-8")
        self.assertNotIn("Path(configured_python).expanduser().resolve()", source)
        self.assertIn("Path(configured_python).expanduser()", source)

    def test_mediacrawler_can_exclude_persisted_comments(self):
        with tempfile.TemporaryDirectory(prefix="xhs-no-comments-") as temp:
            root = Path(temp) / "xhs" / "jsonl"
            root.mkdir(parents=True)
            (root / "search_contents.jsonl").write_text(
                json.dumps({"note_id": "n1", "title": "座舱", "desc": "体验", "source_keyword": "座舱"}, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            (root / "search_comments.jsonl").write_text(
                json.dumps({"comment_id": "c1", "note_id": "n1", "content": "评论"}, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            posts, comments, failures = _parse_mediacrawler_output(
                Path(temp), {"crawler": {"retain_author_fields": False, "include_comments": False}}
            )
            self.assertEqual(len(posts), 1)
            self.assertEqual(comments, [])
            self.assertFalse(failures)

    def test_mediacrawler_honors_per_keyword_limit(self):
        source = (ROOT / "src" / "userresearch_xhscrawler_cockpitux" / "crawler" / "adapters.py").read_text(encoding="utf-8")
        self.assertNotIn('max(20, int(config["crawler"].get("max_notes_per_keyword", 20)))', source)

    def test_predictive_gate_and_complete_model(self):
        rows = []
        for index in range(120):
            rows.append({
                "record_id": f"r{index}",
                "clean_text": "HUD显示清晰稳定" if index % 2 else "HUD重影看不清",
                "sentiment": "正向" if index % 2 else "负向",
                "record_type": "post" if index % 3 else "comment",
                "source_keyword": "HUD体验" if index % 4 else "AR-HUD",
                "like_count": index % 17,
                "favorite_count": index % 9,
                "comment_count": index % 7,
                "share_count": index % 5,
            })
        frame = enrich_text_features(pd.DataFrame(rows))
        skipped = run_predictive_analysis(frame, {"analysis": {"predictive": {"enabled": True, "task": "classification", "target": "sentiment", "features": ["text_length"], "minimum_rows": 200}}})
        self.assertEqual(skipped["status"], "skipped")
        config = {"analysis": {"predictive": {"enabled": True, "task": "classification", "target": "sentiment", "features": ["text_length", "engagement_total", "record_type", "source_keyword"], "split": "iid", "minimum_rows": 80, "minimum_class_rows": 20}}}
        result = run_predictive_analysis(frame, config)
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["metrics"]["test_rows"], 24)
        self.assertEqual({row["model"] for row in result["tables"]["model_comparison"]}, {"naive", "linear", "nonlinear"})
        self.assertTrue(result["tables"]["feature_importance"])

    def test_network_and_browser_bridge(self):
        frame = pd.DataFrame([
            {"feature_labels": ["HUD显示"], "pain_point_labels": ["重影"], "need_labels": ["清晰可读"]},
            {"feature_labels": ["HUD显示"], "pain_point_labels": ["重影"], "need_labels": ["清晰可读"]},
        ])
        network = run_network_analysis(frame, {"analysis": {"network": {"min_edge_count": 2}}})
        self.assertGreaterEqual(network["metrics"]["edges"], 1)
        with tempfile.TemporaryDirectory(prefix="xhs-browser-") as temp:
            source = Path(temp) / "browser.jsonl"
            source.write_text(json.dumps({"keyword": "HUD", "note": {"note_id": "n1", "title": "HUD体验", "content": "清晰"}, "comments": [{"comment_id": "c1", "content": "晚上有重影"}]}, ensure_ascii=False) + "\n", encoding="utf-8")
            config = {"crawler": {"input_path": str(source), "max_notes": 10, "retain_author_fields": False}}
            posts, comments, failures = browser_records(config)
            self.assertEqual((len(posts), len(comments), len(failures)), (1, 1, 0))
            self.assertEqual(comments[0]["parent_id"], posts[0]["record_id"])

    def test_hybrid_merges_browseract_and_mediacrawler_by_stable_id(self):
        with tempfile.TemporaryDirectory(prefix="xhs-hybrid-") as temp:
            root = Path(temp)
            browser = root / "browseract.jsonl"
            browser.write_text(
                json.dumps({"keyword": "HUD", "note": {"note_id": "same", "title": "HUD体验", "content": "显示清晰"}}, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            media = root / "media" / "xhs" / "jsonl"
            media.mkdir(parents=True)
            (media / "search_contents.jsonl").write_text(
                "\n".join([
                    json.dumps({"note_id": "same", "title": "HUD体验", "desc": "显示清晰", "source_keyword": "HUD"}, ensure_ascii=False),
                    json.dumps({"note_id": "second", "title": "仪表体验", "desc": "信息层级清楚", "source_keyword": "仪表"}, ensure_ascii=False),
                ]) + "\n",
                encoding="utf-8",
            )
            config = {
                "crawler": {
                    "adapter": "hybrid", "browseract_input_path": str(browser), "mediacrawler_input_path": str(root / "media"),
                    "input_path": None, "max_notes": 10, "retain_author_fields": False, "include_comments": False,
                    "keywords": ["HUD", "仪表"],
                }
            }
            paths = ProjectPaths(root / "project").create()
            result = collect_records(config, paths)
            self.assertEqual(result["posts"], 2)
            self.assertEqual(result["overlap_records"], 1)
            self.assertEqual(result["source_counts"], {"browseract": 1, "mediacrawler": 2})


if __name__ == "__main__":
    unittest.main()
