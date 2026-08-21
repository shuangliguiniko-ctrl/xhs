from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from userresearch_xhscrawler_cockpitux.cleaning import _marketing, _near_duplicate_groups, _relevance, _research_terms, clean_text


class CleaningTests(unittest.TestCase):
    def test_pii_redaction(self):
        phone = "138" + "0013" + "8000"
        email = "sample" + "@" + "example.invalid"
        text = clean_text(f"加微信 abcde123，电话 {phone}，邮箱 {email}，关注 @汽车薯 https://example.invalid/path")
        self.assertIn("[PHONE]", text)
        self.assertIn("[EMAIL]", text)
        self.assertIn("[ACCOUNT]", text)
        self.assertNotIn("@汽车薯", text)
        self.assertEqual(clean_text("@"), "")
        self.assertIn("[URL]", text)

    def test_marketing_multisignal(self):
        score, label, reason = _marketing("商务合作，加微信 abcde123，领券下单", ["商务合作", "领券", "下单"])
        self.assertGreaterEqual(score, 0.55)
        self.assertEqual(label, "营销")
        self.assertIn("联系方式", reason)

    def test_relevance_and_near_duplicate(self):
        score, label, _ = _relevance("车机宠物主题更新体验", ["车机", "宠物主题"], [])
        self.assertEqual(label, "相关")
        groups = _near_duplicate_groups(["车机宠物主题终于更新了", "车机宠物主题终于更新了", "完全无关的售后问题"], 0.92)
        self.assertTrue(groups[0] or groups[1])

    def test_domain_query_expansion_for_relevance(self):
        terms = _research_terms(["智能座舱仪表盘与 HUD 产品体验", "HUD 看不清 重影"])
        self.assertIn("hud", terms)
        self.assertIn("仪表盘", terms)
        self.assertIn("重影", terms)
        self.assertNotIn("体验", terms)
        score, label, _ = _relevance("夜间 HUD 重影严重", terms, [])
        self.assertGreaterEqual(score, 0.35)
        self.assertEqual(label, "相关")
