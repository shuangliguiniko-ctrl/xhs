from __future__ import annotations

from collections import Counter
from itertools import combinations
import math
import re
from typing import Any

import numpy as np
import pandas as pd

from ..models import module_result


LABEL_COLUMNS = [
    "emotion_labels", "feature_labels", "scenario_labels", "purpose_labels",
    "pain_point_labels", "need_labels",
]


def _labels(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item)]
    return [item for item in str(value or "").split("|") if item]


def _engagement(frame: pd.DataFrame) -> pd.Series:
    columns = [name for name in ["like_count", "favorite_count", "comment_count", "share_count"] if name in frame]
    if not columns:
        return pd.Series(np.zeros(len(frame)), index=frame.index)
    return frame[columns].apply(pd.to_numeric, errors="coerce").fillna(0).sum(axis=1)


def _evidence(frame: pd.DataFrame, limit: int = 5) -> list[dict[str, Any]]:
    if frame.empty:
        return []
    ranked = frame.assign(_engagement=_engagement(frame)).sort_values("_engagement", ascending=False).head(limit)
    return [
        {
            "record_id": str(row.get("record_id", "")),
            "record_type": str(row.get("record_type", "")),
            "source_keyword": str(row.get("source_keyword", "")),
            "publish_time": str(row.get("publish_time", "")),
            "excerpt": str(row.get("clean_text", ""))[:320],
            "engagement": int(row.get("_engagement", 0)),
        }
        for _, row in ranked.iterrows()
    ]


def enrich_text_features(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    text = result["clean_text"].fillna("").astype(str)
    result["text_length"] = text.str.len()
    result["emoji_count"] = text.map(lambda value: len(re.findall(r"[\U0001F300-\U0001FAFF]", value)))
    result["question_count"] = text.str.count(r"[?？]")
    result["exclamation_count"] = text.str.count(r"[!！]")
    result["uncertainty_count"] = text.map(lambda value: sum(value.count(term) for term in ["可能", "好像", "似乎", "不确定", "听说", "据说"]))
    result["engagement_total"] = _engagement(result)
    return result


def run_text_diagnostics(frame: pd.DataFrame) -> dict[str, Any]:
    payload = module_result("text_diagnostics", "2.0")
    text = frame["clean_text"].fillna("").astype(str)
    tokens = [token for values in frame.get("_tokens", pd.Series([[]] * len(frame))) for token in _labels(values)]
    lengths = frame["text_length"] if "text_length" in frame else text.str.len()
    payload["metrics"] = {
        "records": int(len(frame)),
        "median_text_length": round(float(lengths.median()), 2),
        "p90_text_length": round(float(lengths.quantile(0.9)), 2),
        "empty_text_share": round(float((text.str.strip() == "").mean()), 4),
        "emoji_record_share": round(float((frame.get("emoji_count", 0) > 0).mean()), 4),
        "question_record_share": round(float((frame.get("question_count", 0) > 0).mean()), 4),
        "lexical_diversity": round(len(set(tokens)) / max(1, len(tokens)), 4),
        "source_keyword_count": int(frame.get("source_keyword", pd.Series(dtype=str)).nunique()),
    }
    payload["tables"]["length_quantiles"] = [
        {"quantile": label, "characters": round(float(lengths.quantile(value)), 2)}
        for label, value in [("p10", .1), ("p25", .25), ("p50", .5), ("p75", .75), ("p90", .9)]
    ]
    payload["limitations"] = ["Lexical and punctuation diagnostics describe the collected text, not the platform population."]
    payload["status"] = "complete"
    return payload


def run_cohort_analysis(frame: pd.DataFrame, config: dict[str, Any]) -> dict[str, Any]:
    settings = config.get("analysis", {}).get("comparative", {})
    columns = settings.get("group_columns") or ["source_keyword", "record_type"]
    columns = [column for column in columns if column in frame]
    payload = module_result("comparative_analysis", "2.0", {"group_columns": columns})
    tables: dict[str, Any] = {}
    warnings: list[str] = []
    for column in columns:
        rows = []
        for label, subset in frame.groupby(column, dropna=False):
            n = len(subset)
            rows.append({
                "group": str(label or "未知"),
                "count": int(n),
                "share": round(n / max(1, len(frame)), 4),
                "positive_share": round(float((subset["sentiment"] == "正向").mean()), 4),
                "negative_share": round(float((subset["sentiment"] == "负向").mean()), 4),
                "median_engagement": round(float(_engagement(subset).median()), 2),
                "small_group": n < 30,
                "evidence_ids": [str(value) for value in subset["record_id"].head(5)],
            })
            if n < 30:
                warnings.append(f"{column}={label} has n={n}, below the descriptive small-group threshold of 30.")
        tables[column] = sorted(rows, key=lambda item: item["count"], reverse=True)
    payload["tables"] = tables
    payload["metrics"] = {"records": int(len(frame)), "group_columns": len(columns)}
    payload["warnings"] = sorted(set(warnings))
    payload["limitations"] = ["Group differences are descriptive associations shaped by keyword and ranking selection."]
    payload["status"] = "complete" if columns else "skipped"
    if not columns:
        payload["warnings"].append("No requested comparison column exists in the dataset.")
    return payload


def run_network_analysis(frame: pd.DataFrame, config: dict[str, Any]) -> dict[str, Any]:
    settings = config.get("analysis", {}).get("network", {})
    source_columns = settings.get("label_columns") or ["feature_labels", "pain_point_labels", "need_labels"]
    source_columns = [column for column in source_columns if column in frame]
    nodes: Counter[str] = Counter()
    edges: Counter[tuple[str, str]] = Counter()
    for _, row in frame.iterrows():
        labels = []
        for column in source_columns:
            labels.extend(f"{column.replace('_labels', '')}:{label}" for label in _labels(row[column]) if not label.startswith("未识别"))
        labels = sorted(set(labels))
        nodes.update(labels)
        edges.update(combinations(labels, 2))
    min_edge = int(settings.get("min_edge_count", 2))
    payload = module_result("cooccurrence_network", "2.0", {"label_columns": source_columns, "min_edge_count": min_edge})
    payload["tables"] = {
        "nodes": [{"id": name, "label": name.split(":", 1)[-1], "kind": name.split(":", 1)[0], "count": int(count)} for name, count in nodes.most_common(60)],
        "edges": [{"source": pair[0], "target": pair[1], "count": int(count)} for pair, count in edges.most_common(120) if count >= min_edge],
    }
    payload["metrics"] = {"nodes": len(payload["tables"]["nodes"]), "edges": len(payload["tables"]["edges"]), "records": len(frame)}
    payload["limitations"] = ["Edges mean same-record co-occurrence; they do not establish sequence, influence, or causality."]
    payload["status"] = "complete"
    return payload


def run_experience_analysis(frame: pd.DataFrame, config: dict[str, Any]) -> dict[str, Any]:
    payload = module_result("experience_research", "2.0")
    total = max(1, len(frame))
    pain_counts = Counter(label for value in frame.get("pain_point_labels", []) for label in _labels(value) if not label.startswith("未识别"))
    need_counts = Counter(label for value in frame.get("need_labels", []) for label in _labels(value) if not label.startswith("未识别"))
    themes = []
    opportunities = []
    for rank, (pain, count) in enumerate(pain_counts.most_common(8), start=1):
        mask = frame["pain_point_labels"].map(lambda value: pain in _labels(value))
        subset = frame.loc[mask]
        linked_needs = Counter(label for value in subset.get("need_labels", []) for label in _labels(value) if not label.startswith("未识别"))
        need = linked_needs.most_common(1)[0][0] if linked_needs else "仍需访谈澄清"
        negative_share = float((subset["sentiment"] == "负向").mean()) if len(subset) else 0.0
        coverage = count / total
        evidence = _evidence(subset, 5)
        severity = "高" if negative_share >= .5 else "中" if negative_share >= .25 else "低"
        strength = "强" if count >= max(3, math.ceil(total * .1)) and len(evidence) >= 3 else "中" if count >= 2 else "弱"
        theme = {
            "rank": rank,
            "title": pain,
            "supporting_signals": int(count),
            "record_coverage": round(coverage, 4),
            "severity": severity,
            "signal_strength": strength,
            "observation": f"{count}/{total} 条有效记录命中“{pain}”，其中负向基线占 {negative_share:.1%}。",
            "insight_statement": f"用户在“{pain}”相关情境中需要“{need}”，这意味着产品团队应先验证触发场景与任务损失，再决定方案。",
            "how_might_we": f"我们如何在不预设具体方案的前提下，降低“{pain}”对核心任务的干扰？",
            "opportunity_type": "产品变化" if need != "仍需访谈澄清" else "战略问题",
            "evidence": evidence,
        }
        themes.append(theme)
        opportunities.append({
            "label": pain,
            "impact": round(min(1.0, .6 * negative_share + .4 * min(1.0, coverage * 4)), 4),
            "evidence_confidence": round(min(1.0, len({item["record_id"] for item in evidence}) / 5) * min(1.0, count / max(3, total * .08)), 4),
            "count": int(count),
            "need": need,
        })
    emotional = []
    for label, count in Counter(label for value in frame.get("emotion_labels", []) for label in _labels(value) if label != "无法判断").most_common(10):
        subset = frame[frame["emotion_labels"].map(lambda value: label in _labels(value))]
        emotional.append({"emotion": label, "count": int(count), "intensity_proxy": round(float(subset.get("exclamation_count", 0).mean()), 3), "evidence": _evidence(subset, 3)})
    contradictions = frame[(frame["sentiment"] == "混合") | (frame.get("pain_point_labels", "").map(lambda value: len(_labels(value)) > 1))]
    payload["tables"] = {
        "direct_quotes": _evidence(frame, 10),
        "pain_points": [{"label": key, "count": int(value), "share": round(value / total, 4)} for key, value in pain_counts.most_common()],
        "unmet_needs": [{"label": key, "count": int(value), "share": round(value / total, 4)} for key, value in need_counts.most_common()],
        "emotional_signals": emotional,
        "contradictions": _evidence(contradictions, 8),
        "themes": themes,
        "opportunities": sorted(opportunities, key=lambda item: item["impact"] * item["evidence_confidence"], reverse=True),
    }
    payload["metrics"] = {"themes": len(themes), "contradiction_candidates": len(contradictions), "records": len(frame)}
    payload["warnings"] = ["Observed behavior cannot be inferred reliably from a social post unless the text describes a concrete action; candidates require human review."]
    payload["limitations"] = ["Themes use transparent rule-coded signals and are not substitutes for confirmed interview synthesis."]
    payload["status"] = "complete"
    return payload


def _predictive_skip(config: dict[str, Any], reason: str, warnings: list[str] | None = None) -> dict[str, Any]:
    payload = module_result("predictive_modeling", "2.0", config)
    payload["status"] = "skipped"
    payload["metrics"] = {"reason": reason}
    payload["warnings"] = warnings or []
    payload["limitations"] = ["No predictive claim is made when the modeling gate is not satisfied."]
    return payload


def run_predictive_analysis(frame: pd.DataFrame, config: dict[str, Any]) -> dict[str, Any]:
    settings = dict(config.get("analysis", {}).get("predictive", {}))
    if not settings.get("enabled", False):
        return _predictive_skip(settings, "disabled")
    target = str(settings.get("target") or "")
    task = str(settings.get("task") or "")
    features = [str(value) for value in settings.get("features", [])]
    if not target or target not in frame:
        return _predictive_skip(settings, "target_missing_or_not_found")
    if task not in {"classification", "regression"}:
        return _predictive_skip(settings, "task_must_be_classification_or_regression")
    forbidden = {target, "record_id", "content_id", "parent_id", "url", "raw_data", "clean_text", "title", "content"}
    leaking = sorted(set(features) & forbidden)
    if leaking:
        return _predictive_skip(settings, "leakage_or_identifier_features", [f"Excluded forbidden features: {', '.join(leaking)}"])
    features = [name for name in features if name in frame and name not in forbidden]
    if not features:
        return _predictive_skip(settings, "no_usable_features")
    work = frame[[target, *features] + [name for name in [settings.get("time_column"), settings.get("group_column")] if name and name in frame and name not in features]].copy()
    work = work[work[target].notna()]
    minimum_rows = int(settings.get("minimum_rows", 80))
    if len(work) < minimum_rows:
        return _predictive_skip(settings, "insufficient_rows", [f"n={len(work)}; minimum_rows={minimum_rows}"])

    from sklearn.compose import ColumnTransformer
    from sklearn.dummy import DummyClassifier, DummyRegressor
    from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
    from sklearn.impute import SimpleImputer
    from sklearn.inspection import permutation_importance
    from sklearn.linear_model import LogisticRegression, Ridge
    from sklearn.metrics import balanced_accuracy_score, f1_score, mean_absolute_error, mean_squared_error, r2_score
    from sklearn.model_selection import GroupShuffleSplit, KFold, StratifiedKFold, cross_val_score, train_test_split
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import OneHotEncoder, StandardScaler

    X, y = work[features], work[target]
    if task == "classification":
        class_counts = y.astype(str).value_counts()
        minimum_class = int(settings.get("minimum_class_rows", 20))
        if len(class_counts) < 2 or int(class_counts.min()) < minimum_class:
            return _predictive_skip(settings, "insufficient_class_support", [f"class_counts={class_counts.to_dict()}, minimum_class_rows={minimum_class}"])
        y = y.astype(str)
    else:
        y = pd.to_numeric(y, errors="coerce")
        keep = y.notna(); X, y, work = X.loc[keep], y.loc[keep], work.loc[keep]
        if y.nunique() < 8:
            return _predictive_skip(settings, "regression_target_has_too_few_unique_values")

    split = str(settings.get("split") or "auto")
    time_column = settings.get("time_column")
    group_column = settings.get("group_column")
    test_size = float(settings.get("test_size", .2))
    if split == "auto":
        split = "time" if time_column in work and pd.to_datetime(work[time_column], errors="coerce").notna().mean() >= .8 else "group" if group_column in work else "iid"
    if split == "time":
        times = pd.to_datetime(work[time_column], errors="coerce") if time_column in work else pd.Series(pd.NaT, index=work.index)
        if times.notna().mean() < .8:
            return _predictive_skip(settings, "time_split_requested_but_time_unusable")
        order = times.sort_values().index; cut = max(1, int(len(order) * (1 - test_size)))
        train_index, test_index = order[:cut], order[cut:]
    elif split == "group":
        if group_column not in work or work[group_column].nunique() < 3:
            return _predictive_skip(settings, "group_split_requested_but_groups_unusable")
        splitter = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=42)
        train_pos, test_pos = next(splitter.split(X, y, groups=work[group_column]))
        train_index, test_index = X.index[train_pos], X.index[test_pos]
    else:
        train_index, test_index = train_test_split(X.index, test_size=test_size, random_state=42, stratify=y if task == "classification" else None)
        split = "iid-stratified" if task == "classification" else "iid-random"
    X_train, X_test, y_train, y_test = X.loc[train_index], X.loc[test_index], y.loc[train_index], y.loc[test_index]
    if task == "classification" and (y_train.nunique() < 2 or y_test.nunique() < 2):
        return _predictive_skip(settings, "holdout_lost_a_class", ["Adjust split or collect more data; the final holdout must contain multiple classes."])

    numeric = [name for name in features if pd.api.types.is_numeric_dtype(X[name])]
    categorical = [name for name in features if name not in numeric]
    transformers = []
    if numeric:
        transformers.append(("numeric", Pipeline([("impute", SimpleImputer(strategy="median")), ("scale", StandardScaler())]), numeric))
    if categorical:
        transformers.append(("categorical", Pipeline([("impute", SimpleImputer(strategy="most_frequent")), ("onehot", OneHotEncoder(handle_unknown="ignore"))]), categorical))
    processor = ColumnTransformer(transformers)
    if task == "classification":
        models = {
            "naive": DummyClassifier(strategy="prior"),
            "linear": LogisticRegression(max_iter=1200, class_weight="balanced", random_state=42),
            "nonlinear": RandomForestClassifier(n_estimators=240, min_samples_leaf=3, class_weight="balanced_subsample", random_state=42, n_jobs=1),
        }
        cv = StratifiedKFold(n_splits=3, shuffle=True, random_state=42)
        scoring = "balanced_accuracy"
    else:
        models = {
            "naive": DummyRegressor(strategy="median"),
            "linear": Ridge(alpha=1.0),
            "nonlinear": RandomForestRegressor(n_estimators=240, min_samples_leaf=3, random_state=42, n_jobs=1),
        }
        cv = KFold(n_splits=3, shuffle=True, random_state=42)
        scoring = "neg_mean_absolute_error"
    comparison = []
    fitted: dict[str, Any] = {}
    for name, estimator in models.items():
        pipe = Pipeline([("prepare", processor), ("model", estimator)])
        scores = cross_val_score(pipe, X_train, y_train, cv=cv, scoring=scoring, n_jobs=1)
        pipe.fit(X_train, y_train)
        fitted[name] = pipe
        comparison.append({"model": name, "cv_metric": scoring, "cv_mean": round(float(scores.mean()), 5), "cv_std": round(float(scores.std()), 5)})
    best_name = max(comparison, key=lambda row: row["cv_mean"])["model"]
    best = fitted[best_name]
    prediction = best.predict(X_test)
    if task == "classification":
        holdout = {"balanced_accuracy": round(float(balanced_accuracy_score(y_test, prediction)), 5), "macro_f1": round(float(f1_score(y_test, prediction, average="macro")), 5)}
        importance_scoring = "balanced_accuracy"
    else:
        holdout = {"mae": round(float(mean_absolute_error(y_test, prediction)), 5), "rmse": round(float(mean_squared_error(y_test, prediction) ** .5), 5), "r2": round(float(r2_score(y_test, prediction)), 5)}
        importance_scoring = "neg_mean_absolute_error"
    importance = permutation_importance(best, X_test, y_test, scoring=importance_scoring, n_repeats=8, random_state=42, n_jobs=1)
    importance_rows = sorted([
        {"feature": feature, "importance_mean": round(float(mean), 6), "importance_std": round(float(std), 6), "method": "holdout permutation importance"}
        for feature, mean, std in zip(features, importance.importances_mean, importance.importances_std)
    ], key=lambda row: row["importance_mean"], reverse=True)
    payload = module_result("predictive_modeling", "2.0", settings)
    payload["status"] = "complete"
    payload["metrics"] = {
        "task": task, "target": target, "rows": len(work), "train_rows": len(X_train), "test_rows": len(X_test),
        "split": split, "selected_model": best_name, "selection_metric": scoring, "holdout": holdout,
    }
    payload["tables"] = {
        "model_comparison": comparison,
        "feature_importance": importance_rows,
        "holdout_predictions": [{"record_index": str(index), "observed": str(observed), "predicted": str(predicted)} for index, observed, predicted in zip(X_test.index, y_test, prediction)],
    }
    payload["warnings"] = ["Model explanations are predictive associations, not causal effects."]
    payload["limitations"] = ["No hyperparameter search was run; results compare fixed reproducible baselines.", "Permutation importance can be unstable when predictors are correlated."]
    return payload
