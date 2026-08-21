from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess  # nosec B404
import sys
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import pandas as pd

from ..models import StandardRecord
from ..config import SKILL_ROOT
from ..storage import ProjectPaths, now_iso, write_jsonl


COLUMN_ALIASES = {
    "content_id": ["content_id", "帖子ID", "笔记ID", "note_id", "id"],
    "title": ["title", "标题", "笔记标题"],
    "content": ["content", "正文", "内容", "笔记内容", "评论内容"],
    "publish_time": ["publish_time", "发布日期", "发布时间", "时间", "date"],
    "ip_location": ["ip_location", "发布地区", "IP属地", "location"],
    "like_count": ["like_count", "点赞数", "点赞量", "点赞"],
    "favorite_count": ["favorite_count", "收藏数", "收藏量", "收藏"],
    "comment_count": ["comment_count", "评论数", "评论量"],
    "share_count": ["share_count", "分享数", "分享量"],
    "author_name": ["author_name", "用户名", "作者", "昵称"],
    "url": ["url", "帖子链接", "笔记链接", "链接"],
    "source_keyword": ["source_keyword", "搜索关键词", "关键词"],
}


def _first(row: pd.Series, names: list[str], default: Any = "") -> Any:
    for name in names:
        if name in row.index and pd.notna(row[name]):
            return row[name]
    return default


def _int(value: Any) -> int:
    try:
        return max(0, int(float(str(value).replace(",", "").strip())))
    except (TypeError, ValueError):
        return 0


def _stable_id(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:20]


def _input_path(value: Any) -> Path:
    path = Path(str(value or "")).expanduser()
    return path.resolve() if path.is_absolute() else (SKILL_ROOT / path).resolve()


def _iso_time(value: Any) -> str:
    if value in (None, ""):
        return ""
    try:
        number = float(value)
        if number > 10_000_000_000:
            number /= 1000
        return datetime.fromtimestamp(number, tz=timezone.utc).isoformat()
    except (TypeError, ValueError, OSError, OverflowError):
        return str(value)


def _safe_url(value: Any) -> str:
    url = str(value or "").strip()
    if not url:
        return ""
    try:
        parts = urlsplit(url)
        query = [(key, item) for key, item in parse_qsl(parts.query, keep_blank_values=True) if key.lower() not in {"xsec_token", "token", "access_token"}]
        return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), ""))
    except ValueError:
        return re.sub(r"([?&](?:xsec_token|token|access_token)=)[^&#\s]+", r"\1[REDACTED]", url, flags=re.I)


def _minimal_raw(row: dict[str, Any], retain_author: bool) -> dict[str, Any]:
    blocked = {"xsec_token", "cookies", "cookie", "token", "access_token"}
    if not retain_author:
        blocked.update({"nickname", "user_id", "creator_id", "creator_hash", "avatar"})
    result: dict[str, Any] = {}
    for key, value in row.items():
        normalized_key = str(key).lower()
        if normalized_key in blocked:
            continue
        result[key] = _safe_url(value) if "url" in normalized_key else value
    return result


def _read_jsonl_files(base: Path, marker: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for source in sorted(base.rglob(f"*{marker}*.jsonl")):
        for line_number, line in enumerate(source.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
                if not isinstance(payload, dict):
                    raise ValueError("row is not a JSON object")
                rows.append(payload)
            except (json.JSONDecodeError, ValueError) as error:
                failures.append({"path": str(source), "line": line_number, "reason": str(error)})
    return rows, failures


def _parse_mediacrawler_output(destination: Path, config: dict[str, Any]) -> tuple[list[dict], list[dict], list[dict]]:
    content_rows, failures = _read_jsonl_files(destination, "contents")
    comment_rows, comment_failures = _read_jsonl_files(destination, "comments")
    failures.extend(comment_failures)
    retain_author = bool(config.get("crawler", {}).get("retain_author_fields"))
    posts_by_id: dict[str, dict[str, Any]] = {}
    keyword_by_note: dict[str, str] = {}
    for index, row in enumerate(content_rows):
        note_id = str(row.get("note_id") or row.get("content_id") or "").strip()
        if not note_id:
            failures.append({"row": index, "kind": "content", "reason": "missing note_id"})
            continue
        try:
            post = StandardRecord(
                record_id=f"xhs-post-{note_id}", record_type="post", source_platform="xiaohongshu",
                source_keyword=str(row.get("source_keyword") or ""), content_id=note_id,
                title=str(row.get("title") or ""), content=str(row.get("desc") or row.get("content") or ""),
                author_name=str(row.get("nickname") or "") if retain_author else "",
                publish_time=_iso_time(row.get("time") or row.get("publish_time")), crawl_time=now_iso(),
                ip_location=str(row.get("ip_location") or ""), like_count=_int(row.get("liked_count") or row.get("like_count")),
                favorite_count=_int(row.get("collected_count") or row.get("favorite_count")),
                comment_count=_int(row.get("comment_count")), share_count=_int(row.get("share_count")),
                url=_safe_url(row.get("note_url") or row.get("url")), raw_data=_minimal_raw(row, retain_author),
            ).to_dict()
        except ValueError as error:
            failures.append({"row": index, "kind": "content", "note_id": note_id, "reason": str(error)})
            continue
        if note_id not in posts_by_id:
            posts_by_id[note_id] = post
            keyword_by_note[note_id] = post["source_keyword"]
    comments_by_id: dict[str, dict[str, Any]] = {}
    comment_note_ids: dict[str, str] = {}
    for index, row in enumerate(comment_rows):
        comment_id = str(row.get("comment_id") or "").strip()
        note_id = str(row.get("note_id") or row.get("content_id") or "").strip()
        content = str(row.get("content") or "").strip()
        if not comment_id or not note_id or not content:
            failures.append({"row": index, "kind": "comment", "reason": "missing comment_id, note_id, or content"})
            continue
        parent_comment = str(row.get("parent_comment_id") or "").strip()
        post = posts_by_id.get(note_id, {})
        try:
            comment = StandardRecord(
                record_id=f"xhs-comment-{comment_id}", record_type="reply" if parent_comment else "comment",
                parent_id=f"xhs-comment-{parent_comment}" if parent_comment else f"xhs-post-{note_id}",
                source_platform="xiaohongshu", source_keyword=keyword_by_note.get(note_id, ""), content_id=comment_id,
                content=content, author_name=str(row.get("nickname") or "") if retain_author else "",
                publish_time=_iso_time(row.get("create_time") or row.get("publish_time")), crawl_time=now_iso(),
                ip_location=str(row.get("ip_location") or ""), like_count=_int(row.get("like_count")),
                url=str(post.get("url") or ""), raw_data=_minimal_raw(row, retain_author),
            ).to_dict()
        except ValueError as error:
            failures.append({"row": index, "kind": "comment", "comment_id": comment_id, "reason": str(error)})
            continue
        if comment_id not in comments_by_id:
            comments_by_id[comment_id] = comment
            comment_note_ids[comment_id] = note_id
    if not posts_by_id:
        failures.append({"reason": "MediaCrawler produced no recognizable content rows", "path": str(destination)})
    crawler = config.get("crawler", {})
    global_limit = max(1, int(crawler.get("max_notes", len(posts_by_id) or 1)))
    configured_keywords = [str(value) for value in crawler.get("keywords", []) if str(value).strip()]
    observed_keywords = list(dict.fromkeys(keyword_by_note.values()))
    keyword_order = list(dict.fromkeys([*configured_keywords, *observed_keywords]))
    buckets: dict[str, list[dict[str, Any]]] = {keyword: [] for keyword in keyword_order}
    for note_id, post in posts_by_id.items():
        buckets.setdefault(keyword_by_note.get(note_id, ""), []).append(post)
    posts: list[dict[str, Any]] = []
    while len(posts) < global_limit and any(buckets.values()):
        for keyword in keyword_order:
            bucket = buckets.get(keyword, [])
            if bucket:
                posts.append(bucket.pop(0))
                if len(posts) >= global_limit:
                    break
    selected_ids = {post["content_id"] for post in posts}
    comments = (
        [comment for comment_id, comment in comments_by_id.items() if comment_note_ids.get(comment_id) in selected_ids]
        if crawler.get("include_comments", True)
        else []
    )
    return posts, comments, failures


def _sanitize_crawler_log(value: str) -> str:
    value = re.sub(r"(?i)(xsec_token[=:'\"\s]+)[^&\s,'\"]+", r"\1[REDACTED]", value)
    value = re.sub(r"(?i)((?:cookie|cookies|access_token|token)[=:'\"\s]+)[^&\s,'\"]+", r"\1[REDACTED]", value)
    return value


def _normalize_import_row(row: pd.Series, index: int, retain_author: bool) -> dict[str, Any]:
    title = str(_first(row, COLUMN_ALIASES["title"])).strip()
    content = str(_first(row, COLUMN_ALIASES["content"])).strip()
    url = str(_first(row, COLUMN_ALIASES["url"])).strip()
    content_id = str(_first(row, COLUMN_ALIASES["content_id"])).strip() or _stable_id(url or f"{title}|{content}|{index}")
    record = StandardRecord(
        record_id=f"xhs-post-{content_id}", record_type="post", source_platform="xiaohongshu",
        source_keyword=str(_first(row, COLUMN_ALIASES["source_keyword"])), content_id=content_id,
        title=title, content=content, author_name=str(_first(row, COLUMN_ALIASES["author_name"])) if retain_author else "",
        publish_time=str(_first(row, COLUMN_ALIASES["publish_time"])), crawl_time=now_iso(),
        ip_location=str(_first(row, COLUMN_ALIASES["ip_location"])), like_count=_int(_first(row, COLUMN_ALIASES["like_count"])),
        favorite_count=_int(_first(row, COLUMN_ALIASES["favorite_count"])), comment_count=_int(_first(row, COLUMN_ALIASES["comment_count"])),
        share_count=_int(_first(row, COLUMN_ALIASES["share_count"])), url=url,
        raw_data={str(key): (None if pd.isna(value) else value) for key, value in row.to_dict().items()},
    )
    return record.to_dict()


def import_records(config: dict[str, Any]) -> tuple[list[dict], list[dict], list[dict]]:
    source = _input_path(config["crawler"].get("input_path"))
    if not source.exists():
        raise FileNotFoundError(f"crawler.input_path not found: {source}")
    suffix = source.suffix.lower()
    if suffix == ".csv":
        frame = None
        for encoding in ("utf-8-sig", "utf-8", "gb18030", "gbk"):
            try:
                frame = pd.read_csv(source, encoding=encoding)
                break
            except UnicodeDecodeError:
                continue
        if frame is None:
            raise ValueError("Unable to decode CSV")
    elif suffix in {".xlsx", ".xls"}:
        frame = pd.read_excel(source)
    elif suffix in {".jsonl", ".json"}:
        frame = pd.read_json(source, lines=suffix == ".jsonl")
    elif suffix == ".parquet":
        frame = pd.read_parquet(source)
    else:
        raise ValueError(f"Unsupported import type: {suffix}")
    limit = int(config["crawler"].get("max_notes", len(frame)))
    posts = [_normalize_import_row(row, int(index), bool(config["crawler"].get("retain_author_fields"))) for index, row in frame.head(limit).iterrows()]
    return posts, [], []


def browser_records(config: dict[str, Any]) -> tuple[list[dict], list[dict], list[dict]]:
    """Normalize persisted BrowserAct or legacy browser output.

    Browser interaction happens outside this adapter in the user's accessible session. This
    function only imports the locally persisted composite records and never handles cookies.
    """
    configured_source = config["crawler"].get("browseract_input_path") or config["crawler"].get("input_path") or ""
    source = _input_path(configured_source)
    if not source.exists():
        raise FileNotFoundError("browseract adapter requires crawler.browseract_input_path from an authorized BrowserAct collection")
    if source.suffix.lower() == ".jsonl":
        rows = [json.loads(line) for line in source.read_text(encoding="utf-8").splitlines() if line.strip()]
    else:
        payload = json.loads(source.read_text(encoding="utf-8"))
        rows = payload if isinstance(payload, list) else payload.get("records", [payload])
    posts: list[dict] = []
    comments: list[dict] = []
    failures: list[dict] = []
    retain_author = bool(config["crawler"].get("retain_author_fields"))
    limit = int(config["crawler"].get("max_notes", len(rows)))
    for index, composite in enumerate(rows[:limit]):
        note = composite.get("note") or composite.get("detail") or composite
        note_id = str(note.get("note_id") or note.get("content_id") or "").strip()
        if not note_id:
            failures.append({"row": index, "reason": "missing note_id"})
            continue
        post = StandardRecord(
            record_id=f"xhs-post-{note_id}", record_type="post", source_platform="xiaohongshu",
            source_keyword=str(composite.get("keyword") or composite.get("source_keyword") or ""),
            content_id=note_id, title=str(note.get("title") or ""), content=str(note.get("content") or ""),
            author_name=str(note.get("author") or "") if retain_author else "",
            publish_time=str(note.get("publish_time") or note.get("display_time") or ""),
            crawl_time=str(composite.get("collected_at") or now_iso()), like_count=_int(note.get("like_count")),
            favorite_count=_int(note.get("collect_count") or note.get("favorite_count")),
            comment_count=_int(note.get("comment_count")), share_count=_int(note.get("share_count")),
            url=_safe_url(note.get("url") or note.get("detail_url") or ""),
            raw_data={"source_adapters": ["browseract"], "browseract_source": True, "note": _minimal_raw(note, retain_author)},
        ).to_dict()
        posts.append(post)
        for comment_index, comment in enumerate(composite.get("comments") or []):
            comment_id = str(comment.get("comment_id") or _stable_id(f"{note_id}|{comment.get('content')}|{comment_index}"))
            parent_comment = str(comment.get("parent_comment_id") or "")
            comments.append(StandardRecord(
                record_id=f"xhs-comment-{comment_id}", record_type="reply" if comment.get("is_reply") else "comment",
                parent_id=f"xhs-comment-{parent_comment}" if parent_comment else post["record_id"],
                source_platform="xiaohongshu", source_keyword=post["source_keyword"], content_id=comment_id,
                content=str(comment.get("content") or ""), author_name=str(comment.get("author") or "") if retain_author else "",
                publish_time=str(comment.get("date") or ""), crawl_time=post["crawl_time"],
                ip_location=str(comment.get("location") or ""), like_count=_int(comment.get("like_count")),
                url=post["url"], raw_data={"source_adapters": ["browseract"], "browseract_source": True, "comment": _minimal_raw(comment, retain_author)},
            ).to_dict())
    return posts, comments, failures


def mock_records(config: dict[str, Any]) -> tuple[list[dict], list[dict], list[dict]]:
    subject = config.get("analysis", {}).get("subject") or "智能座舱宠物主题"
    keywords = config["crawler"].get("keywords") or [subject]
    positive = [
        "更新后宠物主题很治愈，上传自家猫咪照片就能生成动态屏保，孩子每天上车都很期待。",
        "语音助手识别快了很多，日常通勤用起来顺畅，OTA这次升级值得推荐。",
        "车机界面清爽，宠物动画不会挡住导航，情绪价值和实用性平衡得不错。",
        "第一次体验就被惊喜到，和家人一起设置宠物相框很有参与感。",
    ]
    negative = [
        "老款车型一直没有推送，等了很久还是无法使用宠物主题，真的失望。",
        "更新后偶尔卡顿，上传照片经常失败，希望尽快修复并说明兼容车型。",
        "功能入口太深，教程也不清楚，找了半天才发现只能部分车型使用。",
        "担心宠物照片上传后的隐私，页面没有说清楚保存时间和删除方式。",
    ]
    neutral = [
        "想问一下这个功能支持哪些车型，旧款什么时候能够OTA？",
        "记录一次车机宠物主题设置流程：打开应用、选择照片、确认生成。",
        "正在对比不同品牌的座舱宠物功能，主要关注流畅度、隐私和可定制性。",
        "官方发布了功能说明，评论区主要在讨论车型覆盖和更新时间。",
    ]
    corpus = positive + negative + neutral
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    requested = min(max(24, int(config["crawler"].get("max_notes", 48))), 96)
    posts: list[dict] = []
    comments: list[dict] = []
    for index in range(requested):
        body = corpus[index % len(corpus)]
        if index in {13, 39}:
            body = corpus[1]
        if index % 17 == 0:
            body += " 商务合作可私信，领券购买更优惠。"
        content_id = f"mock-{index + 1:04d}"
        time = (base + timedelta(days=index % 42)).isoformat()
        post = StandardRecord(
            record_id=f"xhs-post-{content_id}", record_type="post", source_platform="xiaohongshu",
            source_keyword=keywords[index % len(keywords)], content_id=content_id,
            title=f"{subject}体验记录 {index + 1}", content=body, publish_time=time, crawl_time=now_iso(),
            ip_location=["上海", "广东", "浙江", "北京", "未知"][index % 5],
            like_count=(index * 17) % 230, favorite_count=(index * 7) % 80, comment_count=(index * 11) % 70,
            share_count=(index * 3) % 40, url=f"https://www.xiaohongshu.com/explore/{content_id}",
            raw_data={"mock": True, "batch": "demo"},
        ).to_dict()
        posts.append(post)
        if config["crawler"].get("include_comments", True):
            comment_body = ["我也遇到了同样的问题，希望支持旧款。", "已经更新成功，动画很可爱。", "请问照片会保存多久？", "教程有帮助，设置完成了。"][index % 4]
            comments.append(StandardRecord(
                record_id=f"xhs-comment-{content_id}-1", record_type="comment", parent_id=post["record_id"],
                source_platform="xiaohongshu", source_keyword=post["source_keyword"], content_id=f"{content_id}-c1",
                content=comment_body, publish_time=time, crawl_time=now_iso(), like_count=index % 9,
                url=post["url"], raw_data={"mock": True},
            ).to_dict())
    return posts, comments, []


def mediacrawler_records(config: dict[str, Any], paths: ProjectPaths) -> tuple[list[dict], list[dict], list[dict]]:
    persisted = str(config["crawler"].get("mediacrawler_input_path") or "").strip()
    if persisted:
        persisted_path = _input_path(persisted)
        if not persisted_path.exists():
            raise FileNotFoundError(f"crawler.mediacrawler_input_path not found: {persisted_path}")
        return _parse_mediacrawler_output(persisted_path, config)
    configured_path = str(config["crawler"].get("mediacrawler_path") or "").strip()
    if not configured_path:
        raise ValueError("MediaCrawler adapter requires an explicit crawler.mediacrawler_path")
    crawler_path = Path(configured_path).expanduser()
    if not crawler_path.is_absolute():
        crawler_path = (SKILL_ROOT / crawler_path).resolve()
    main = crawler_path / "main.py"
    if not main.exists():
        raise FileNotFoundError(f"MediaCrawler not found: {main}")
    keywords = ",".join(config["crawler"].get("keywords", []))
    if not keywords:
        raise ValueError("MediaCrawler adapter requires crawler.keywords")
    destination = paths.raw / "mediacrawler"
    destination.mkdir(parents=True, exist_ok=True)
    configured_python = str(config["crawler"].get("mediacrawler_python") or "").strip()
    bundled_python = crawler_path / ".venv" / "bin" / "python"
    crawler_python = Path(configured_python).expanduser() if configured_python else bundled_python
    if not crawler_python.is_absolute():
        crawler_python = (SKILL_ROOT / crawler_python).absolute()
    if not crawler_python.exists():
        crawler_python = Path(sys.executable)
    command = [
        str(crawler_python), str(main), "--platform", "xhs", "--lt", "qrcode", "--type", "search",
        "--keywords", keywords, "--get_comment", str(bool(config["crawler"].get("include_comments", True))).lower(),
        "--get_sub_comment", str(bool(config["crawler"].get("include_sub_comments", False))).lower(),
        "--crawler_max_notes_count", str(max(1, int(config["crawler"].get("max_notes_per_keyword", 20)))),
        "--max_comments_count_singlenotes", str(config["crawler"].get("max_comments_per_note", 20)),
        "--max_concurrency_num", str(config["crawler"].get("concurrency", 1)),
        "--save_data_option", "jsonl", "--save_data_path", str(destination),
    ]
    completed = subprocess.run(  # noqa: S603  # nosec B603
        command,
        cwd=crawler_path,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    (paths.logs / "mediacrawler.stdout.log").write_text(_sanitize_crawler_log(completed.stdout[-100000:]), encoding="utf-8")
    (paths.logs / "mediacrawler.stderr.log").write_text(_sanitize_crawler_log(completed.stderr[-100000:]), encoding="utf-8")
    if completed.returncode:
        raise RuntimeError(f"MediaCrawler exited {completed.returncode}; inspect project logs. Login/verification may require the user.")
    return _parse_mediacrawler_output(destination, config)


def _merge_source_records(*sources: tuple[str, list[dict]]) -> tuple[list[dict], int]:
    merged: dict[tuple[str, str, str], dict[str, Any]] = {}
    overlap = 0
    for adapter, records in sources:
        for record in records:
            key = (
                str(record.get("source_platform") or "xiaohongshu"),
                str(record.get("record_type") or "post"),
                str(record.get("content_id") or record.get("record_id") or ""),
            )
            if not key[2]:
                key = (key[0], key[1], _stable_id(json.dumps(record, ensure_ascii=False, sort_keys=True, default=str)))
            if key not in merged:
                candidate = dict(record)
                raw = dict(candidate.get("raw_data") or {})
                raw["source_adapters"] = list(dict.fromkeys([*(raw.get("source_adapters") or []), adapter]))
                candidate["raw_data"] = raw
                merged[key] = candidate
                continue
            overlap += 1
            current = merged[key]
            for field, value in record.items():
                if current.get(field) in (None, "", [], {}) and value not in (None, "", [], {}):
                    current[field] = value
            raw = dict(current.get("raw_data") or {})
            raw["source_adapters"] = list(dict.fromkeys([*(raw.get("source_adapters") or []), adapter]))
            current["raw_data"] = raw
    return list(merged.values()), overlap


def hybrid_records(config: dict[str, Any], paths: ProjectPaths) -> tuple[list[dict], list[dict], list[dict]]:
    browser_posts, browser_comments, browser_failures = browser_records(config)
    media_posts, media_comments, media_failures = mediacrawler_records(config, paths)
    posts, post_overlap = _merge_source_records(("browseract", browser_posts), ("mediacrawler", media_posts))
    comments, comment_overlap = _merge_source_records(("browseract", browser_comments), ("mediacrawler", media_comments))
    failures = [
        *[{**item, "source_adapter": "browseract"} for item in browser_failures],
        *[{**item, "source_adapter": "mediacrawler"} for item in media_failures],
    ]
    limit = max(1, int(config["crawler"].get("max_notes", len(posts) or 1)))
    selected_posts = posts[:limit]
    selected_post_ids = {post["record_id"] for post in selected_posts}
    selected_comments = [comment for comment in comments if comment.get("parent_id") in selected_post_ids or str(comment.get("parent_id", "")).startswith("xhs-comment-")]
    for record in selected_posts:
        record.setdefault("raw_data", {})["hybrid_overlap_total"] = post_overlap
    for record in selected_comments:
        record.setdefault("raw_data", {})["hybrid_overlap_total"] = comment_overlap
    return selected_posts, selected_comments, failures


def collect_records(config: dict[str, Any], paths: ProjectPaths) -> dict[str, Any]:
    adapter = config["crawler"]["adapter"]
    if adapter == "mock":
        posts, comments, failures = mock_records(config)
    elif adapter == "import":
        posts, comments, failures = import_records(config)
    elif adapter in {"browser", "browseract"}:
        posts, comments, failures = browser_records(config)
    elif adapter == "mediacrawler":
        posts, comments, failures = mediacrawler_records(config, paths)
    elif adapter == "hybrid":
        posts, comments, failures = hybrid_records(config, paths)
    else:
        raise ValueError(f"Unsupported crawler adapter: {adapter}")
    write_jsonl(posts, paths.raw / "posts.jsonl")
    write_jsonl(comments, paths.raw / "comments.jsonl")
    write_jsonl(failures, paths.raw / "crawl_failures.jsonl")
    source_counts: dict[str, int] = {}
    overlap_records = 0
    for record in [*posts, *comments]:
        sources = (record.get("raw_data") or {}).get("source_adapters", [adapter])
        if len(sources) > 1:
            overlap_records += 1
        for source in sources:
            source_counts[source] = source_counts.get(source, 0) + 1
    return {"adapter": adapter, "posts": len(posts), "comments": len(comments), "failures": len(failures), "source_counts": source_counts, "overlap_records": overlap_records}
