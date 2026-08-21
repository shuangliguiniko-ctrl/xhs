from __future__ import annotations

from typing import Any


def validate_insights(insights: list[dict[str, Any]], total_records: int, evidence_minimum: int = 3) -> dict[str, Any]:
    counts = {"supported": 0, "qualified": 0, "insufficient": 0}
    validated = []
    for insight in insights:
        reasons = []
        evidence = insight.get("evidence", [])
        record_ids = {str(item.get("record_id")) for item in evidence if item.get("record_id")}
        source_keywords = {str(item.get("source_keyword")) for item in evidence if item.get("source_keyword")}
        count = int(insight.get("data_fact", {}).get("count", 0))
        denominator = int(insight.get("data_fact", {}).get("denominator", total_records))
        if denominator <= 0: reasons.append("missing denominator")
        if count <= 0: reasons.append("missing supporting count")
        if len(record_ids) < evidence_minimum: reasons.append(f"fewer than {evidence_minimum} distinct evidence records")
        if len(record_ids) >= evidence_minimum and len(source_keywords) < 2: reasons.append("evidence comes from fewer than two source keywords")
        if denominator < 30: reasons.append("small denominator below 30")
        if not insight.get("applicability"): reasons.append("missing applicability scope")
        if any("cause" in str(value).lower() or "导致" in str(value) for value in insight.get("interpretation", [])):
            reasons.append("causal language requires external validation")
        if not reasons:
            status = "supported"
        elif count > 0 and record_ids:
            status = "qualified"
        else:
            status = "insufficient"
        counts[status] += 1
        item = dict(insight)
        item["validation"] = {"status": status, "reasons": reasons or ["count, denominator, scope, and evidence threshold satisfied"]}
        validated.append(item)
    return {"summary": counts, "evidence_minimum": evidence_minimum, "insights": validated}
