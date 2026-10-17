#!/usr/bin/env python3
"""拆文、扫榜产物与下游读取方之间的交接契约。

产出方以模板或脚本为准，读取方以它在文档里点名的小节、字段、列名和取值为准，
逐条断言：读取方点名的东西在产出方模板里真实存在。覆盖：

- 长篇拆文报告：各读取方用 `拆文报告.md`「小节」点名的小节；文风生成引用的小节；
  快速预览与拆文报告同名的两节；story-explorer 从黄金三章深度拆解读的字段。
- 情绪模块卡：门禁字段以 inspiration_index.py 的 EM_REQUIRED_FIELDS 为准，
  Stage 3 模板卡要能被同一个解析器读出全部门禁字段；长篇写前召回、作者报告、
  story-explorer 点名的字段要对得上。
- 节奏索引：长篇写前召回的 rhythm_reference 和 story-explorer 点名的列/表要在 节奏.md 模板里。
- 短篇拆文：情节节点模板要有写作端点名的节点字段；genre_detected 的每个取值在写作端题材映射表里；
  导入短篇读的拆文报告小节存在；写作端和导入读的 `_meta.json` 键在 output-contract 的 schema 里。
- 短篇扫榜：选题匹配推荐的目标平台要被写作端的设计模板和 check-phase2-contract.js 接受，
  扫榜支持的每个平台都在对照表里。

最后用几组改坏的输入确认断言真的会报错。
"""

from __future__ import annotations

import re
import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

LONG_ANALYZE = "skills/story-long-analyze"
AUTHOR_FACING = f"{LONG_ANALYZE}/references/author-facing.md"
STAGE1 = f"{LONG_ANALYZE}/references/stage1-golden-chapters.md"
STAGE3 = f"{LONG_ANALYZE}/references/stage3-plot-rhythm.md"
STAGE5 = f"{LONG_ANALYZE}/references/stage5-report.md"
STYLE_GENERATOR = f"{LONG_ANALYZE}/references/style-profile-generator.md"
INSPIRATION_INDEX = f"{LONG_ANALYZE}/scripts/inspiration_index.py"
LONG_RECALL = "skills/story-long-write/references/benchmark-recall.md"
EXPLORER_LOAD = "skills/story-setup/references/agent-references/benchmark-style-load.md"
IMPORT_LONG = "skills/story-import/references/structure-mapping-long.md"
IMPORT_SHORT = "skills/story-import/references/structure-mapping-short.md"

SHORT_ANALYZE_SKILL = "skills/story-short-analyze/SKILL.md"
SHORT_GENRES = "skills/story-short-analyze/references/analysis-short-genres.md"
SHORT_STAGE23 = "skills/story-short-analyze/references/stage2-3-structure-emotion.md"
SHORT_STAGE46 = "skills/story-short-analyze/references/stage4-6-reversal-summary.md"
SHORT_CONTRACT = "skills/story-short-analyze/references/output-contract.md"
IMPORT_DEEP = "skills/story-import/references/deep-analysis.md"
SHORT_RECALL = "skills/story-short-write/references/benchmark-recall.md"
SHORT_DESIGN = "skills/story-short-write/references/workflow-design.md"
PHASE2_CHECK = "skills/story-short-write/scripts/check-phase2-contract.js"
SHORT_SCAN_SKILL = "skills/story-short-scan/SKILL.md"
TOPIC_MATCH = "skills/story-short-scan/references/topic-match.md"

# 读长篇拆文报告的文件：长篇写作、长篇扫榜、导入长篇、story-setup 部署给 agent 的资料。
LONG_REPORT_CONSUMER_GLOBS = (
    "skills/story-long-write/**/*.md",
    "skills/story-long-scan/**/*.md",
    "skills/story-setup/references/agent-references/*.md",
    "skills/story-setup/references/templates/agents/*.md",
    "skills/story-review/**/*.md",
    "skills/story-import/SKILL.md",
    IMPORT_LONG,
    STYLE_GENERATOR,
    STAGE5,
)
# 读短篇拆文报告的文件。
SHORT_REPORT_CONSUMER_GLOBS = (
    "skills/story-short-write/**/*.md",
    IMPORT_SHORT,
)

# `拆文报告.md`「小节」「小节」，可带「小节」的「字段」。
REPORT_REF_RE = re.compile(
    r"拆文报告(?:\.md)?`?((?:「[^」]+」[、与和及]?)+)(?:的「([^」]+)」)?"
)
QUOTED_RE = re.compile(r"「([^」]+)」")
# 「拆文报告·核心发现第 N 条」这类回填依据写法。
REPORT_CITE_RE = re.compile(r"拆文报告·([\u4e00-\u9fff]+?)第")
# Stage 3 模板标题：「### Stage 3 节奏.md」或「## 5. 节奏.md」都认。
EM_TEMPLATE_HEADING = r"^#{2,3}\s+(?:Stage 3\s+|\d+\.\s*)?情绪模块\.md"
RHYTHM_TEMPLATE_HEADING = r"^#{2,3}\s+(?:Stage 3\s+|\d+\.\s*)?节奏\.md"


class Repo:
    """读仓库文件；负例测试用 overrides 换掉个别文件的内容。"""

    def __init__(self, overrides: dict[str, str] | None = None) -> None:
        self.overrides = overrides or {}

    def text(self, rel: str) -> str:
        if rel in self.overrides:
            return self.overrides[rel]
        path = ROOT / rel
        if not path.is_file():
            return ""
        return path.read_text(encoding="utf-8")

    def glob(self, patterns: tuple[str, ...]) -> list[str]:
        found: set[str] = set()
        for pattern in patterns:
            for path in ROOT.glob(pattern):
                if path.is_file():
                    found.add(path.relative_to(ROOT).as_posix())
        found.update(rel for rel in self.overrides if any(Path(rel).match(p) for p in patterns))
        return sorted(found)


# ---------- 通用解析 ----------


def fenced_block_after(text: str, heading_re: str) -> str:
    """返回 heading_re 所在行之后第一个代码围栏里的内容；找不到返回空串。"""
    match = re.search(heading_re, text, re.M)
    if not match:
        return ""
    rest = text[match.end():]
    opening = re.search(r"^```[^\n]*\n", rest, re.M)
    if not opening:
        return ""
    body = rest[opening.end():]
    closing = re.search(r"^```\s*$", body, re.M)
    return body[: closing.start()] if closing else body


def headings(text: str) -> list[str]:
    return [m.group(2).strip() for m in re.finditer(r"^(#{1,6})\s+(.+?)\s*$", text, re.M)]


def table_header_cells(text: str) -> list[str]:
    """Markdown 表头行（下一行是分隔行）里的所有单元格。"""
    lines = text.splitlines()
    cells: list[str] = []
    for i, line in enumerate(lines[:-1]):
        if line.strip().startswith("|") and re.match(r"^\s*\|?\s*:?-{3,}", lines[i + 1]):
            cells.extend(c.strip() for c in line.strip().strip("|").split("|") if c.strip())
    return cells


def tables(text: str) -> list[tuple[list[str], list[list[str]]]]:
    """返回 [(表头, 行列表)]。"""
    lines = text.splitlines()
    result: list[tuple[list[str], list[list[str]]]] = []
    i = 0
    while i < len(lines) - 1:
        line = lines[i].strip()
        if line.startswith("|") and re.match(r"^\s*\|?\s*:?-{3,}", lines[i + 1]):
            header = [c.strip() for c in line.strip("|").split("|")]
            rows: list[list[str]] = []
            j = i + 2
            while j < len(lines) and lines[j].strip().startswith("|"):
                rows.append([c.strip() for c in lines[j].strip().strip("|").split("|")])
                j += 1
            result.append((header, rows))
            i = j
        else:
            i += 1
    return result


def section_body(text: str, title: str) -> str:
    """标题为 title 的小节正文，到下一个同级或更高级标题为止。"""
    match = re.search(rf"^(#{{1,6}})\s+{re.escape(title)}\s*$", text, re.M)
    if not match:
        return ""
    level = len(match.group(1))
    rest = text[match.end():]
    nxt = re.search(rf"^#{{1,{level}}}\s", rest, re.M)
    return rest[: nxt.start()] if nxt else rest


def split_terms(raw: str, seps: str) -> list[str]:
    return [t.strip() for t in re.split(f"[{seps}]", raw) if t.strip()]


def line_no(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1


# ---------- 长篇拆文报告 ----------


def long_report_template(repo: Repo) -> tuple[str, str]:
    text = repo.text(AUTHOR_FACING)
    return (
        fenced_block_after(text, r"^## 拆文报告\.md\s*$"),
        fenced_block_after(text, r"^## 快速预览\.md\s*$"),
    )


def check_long_report(repo: Repo) -> list[str]:
    failures: list[str] = []
    report, preview = long_report_template(repo)
    if not report:
        return [f"{AUTHOR_FACING}: 找不到「## 拆文报告.md」下的报告模板代码块"]
    report_headings = set(headings(report))
    read_sections: dict[str, str] = {}

    for rel in repo.glob(LONG_REPORT_CONSUMER_GLOBS):
        text = repo.text(rel)
        for match in REPORT_REF_RE.finditer(text):
            where = f"{rel}:{line_no(text, match.start())}"
            sections = QUOTED_RE.findall(match.group(1))
            for section in sections:
                read_sections.setdefault(section, where)
            field = match.group(2)
            if field and sections:
                owner = sections[-1]
                body = section_body(report, owner)
                if owner in report_headings and not re.search(rf"(^|[|\s]){re.escape(field)}\s*[：:|]", body, re.M):
                    failures.append(f"{where}: 读拆文报告「{owner}」里的「{field}」，模板该节没写这一项")
        for match in REPORT_CITE_RE.finditer(text):
            read_sections.setdefault(match.group(1), f"{rel}:{line_no(text, match.start())}")
    if not read_sections:
        failures.append("长篇读取方里一处 `拆文报告.md`「小节」引用都没找到，检查正则或读取方清单")

    # 文风生成：报告「文风一句话」回填；「写法技巧 Top 5」「可借鉴套路 Top 3」摘入文风。
    style = repo.text(STYLE_GENERATOR)
    style_refs = re.findall(r"报告「([^」]+)」", style) + re.findall(r"([\u4e00-\u9fff]+) Top \d+", style)
    if not style_refs:
        failures.append(f"{STYLE_GENERATOR}: 没找到它引用的拆文报告小节，确认读取写法后更新本测试")
    for section in style_refs:
        read_sections.setdefault(section, STYLE_GENERATOR)

    for section, where in sorted(read_sections.items(), key=lambda kv: kv[1]):
        if section not in report_headings:
            failures.append(f"{where}: 读拆文报告「{section}」，报告模板没有这一节")

    # 报告模板写明「有下游在读、保留原名」的小节，要覆盖所有被读的小节。
    note = re.search(r"有下游在读[^：\n]*：([^\n]+)", repo.text(AUTHOR_FACING))
    if not note:
        failures.append(f"{AUTHOR_FACING}: 拆文报告模板前缺「有下游在读、保留原名」的小节清单")
    else:
        protected = set(QUOTED_RE.findall(note.group(1)))
        for section in protected - report_headings:
            failures.append(f"{AUTHOR_FACING}: 保留清单里的「{section}」在报告模板里不存在")
        for section, where in sorted(read_sections.items(), key=lambda kv: kv[1]):
            if section in report_headings and section not in protected:
                failures.append(f"{AUTHOR_FACING}: 「{section}」被 {where} 读取，没写进「有下游在读、保留原名」清单")

    # 快速预览说明里约定与拆文报告同名的小节，两边模板都要有。
    shared = re.search(r"沿用((?:「[^」]+」)+)两节的同名同结构", repo.text(AUTHOR_FACING))
    if not shared:
        failures.append(f"{AUTHOR_FACING}: 「快速预览.md」说明里没找到与拆文报告同名的小节约定，确认写法后更新本测试")
    else:
        preview_headings = set(headings(preview))
        for section in QUOTED_RE.findall(shared.group(1)):
            if section not in report_headings or section not in preview_headings:
                failures.append(f"{AUTHOR_FACING}: 约定与拆文报告同名的「{section}」，快速预览和报告模板没有都写")

    # story-explorer 从黄金三章深度拆解读的字段要在 Stage 1 模板里。
    explorer = repo.text(EXPLORER_LOAD)
    match = re.search(r"深度拆解\.md` 存在，再读取并提取((?:「[^」]+」)+)", explorer)
    if not match:
        failures.append(f"{EXPLORER_LOAD}: 没找到从深度拆解读取的字段，确认读取写法后更新本测试")
    else:
        stage1 = repo.text(STAGE1)
        for field in QUOTED_RE.findall(match.group(1)):
            if not re.search(rf"\*\*{re.escape(field)}\*\*", stage1):
                failures.append(f"{EXPLORER_LOAD}: 从深度拆解读「{field}」，Stage 1 深度拆解模板没有这一项")
    return failures


# ---------- 情绪模块卡 ----------


def check_em_cards(repo: Repo) -> list[str]:
    failures: list[str] = []
    module = runpy.run_path(str(ROOT / INSPIRATION_INDEX), run_name="handoff_contracts")
    required = tuple(module["EM_REQUIRED_FIELDS"])
    template = fenced_block_after(repo.text(STAGE3), EM_TEMPLATE_HEADING)
    if not template:
        return [f"{STAGE3}: 找不到「情绪模块.md」模板标题下的模板代码块"]

    cards, _index, problems = module["parse_em_module"](template)
    if not cards:
        failures.append(f"{STAGE3}: inspiration_index 从情绪模块模板里解析不出 EM 卡")
    for card in cards:
        missing = [f for f in required if not card.get(f, "").strip()]
        if missing:
            failures.append(f"{STAGE3}: 模板卡 {card.get('em_id')} 缺门禁字段 {'、'.join(missing)}")
    for problem in problems:
        failures.append(f"{STAGE3}: inspiration_index 解析模板报问题 {problem}")

    vocabulary = set(required) | set(headings(template)) | set(table_header_cells(template))
    for card in cards:
        vocabulary.update(k for k in card if k not in ("em_id", "title"))

    def exact(rel: str, pattern: str, label: str) -> None:
        text = repo.text(rel)
        match = re.search(pattern, text)
        if not match:
            failures.append(f"{rel}: 没找到{label}的字段清单，确认读取写法后更新本测试")
            return
        named = split_terms(match.group(1), "、，,")
        where = f"{rel}:{line_no(text, match.start())}"
        extra = [n for n in named if n not in required]
        absent = [f for f in required if f not in named]
        if extra or absent:
            failures.append(
                f"{where}: {label}字段应与 EM_REQUIRED_FIELDS（{'、'.join(required)}）一致；"
                f"多出 {'、'.join(extra) or '无'}，缺 {'、'.join(absent) or '无'}"
            )

    exact(LONG_RECALL, r"`selected_emotion_module`（([^）]+)）", "写前召回 selected_emotion_module ")

    def known(rel: str, pattern: str, label: str, seps: str) -> None:
        text = repo.text(rel)
        match = re.search(pattern, text)
        if not match:
            failures.append(f"{rel}: 没找到{label}，确认读取写法后更新本测试")
            return
        where = f"{rel}:{line_no(text, match.start())}"
        for term in split_terms(match.group(1), seps):
            if not any(term in v for v in vocabulary):
                failures.append(f"{where}: {label}点名「{term}」，情绪模块.md 模板里没有这个字段或小节")

    known(EXPLORER_LOAD, r"从([^。\n]+?)中选择 1 条 `selected_emotion_module`", "情绪模块取材范围", "、或")
    known(EXPLORER_LOAD, r'"selected_emotion_module": "<从 剧情/情绪模块\.md 选出的([^；>"]+)', "selected_emotion_module 字段说明", "/、")
    return failures


# ---------- 节奏索引 ----------


def check_rhythm(repo: Repo) -> list[str]:
    failures: list[str] = []
    template = fenced_block_after(repo.text(STAGE3), RHYTHM_TEMPLATE_HEADING)
    if not template:
        return [f"{STAGE3}: 找不到「节奏.md」模板标题下的模板代码块"]
    columns = set(table_header_cells(template))
    titles = set(headings(template))

    text = repo.text(LONG_RECALL)
    match = re.search(r"`rhythm_reference`（([^）]+)）", text)
    if not match:
        failures.append(f"{LONG_RECALL}: 没找到 rhythm_reference 的组成说明，确认读取写法后更新本测试")
    else:
        where = f"{LONG_RECALL}:{line_no(text, match.start())}"
        for step in split_terms(match.group(1), "→"):
            if step not in columns and not any(step in t for t in titles):
                failures.append(f"{where}: rhythm_reference 点名「{step}」，节奏.md 模板里没有这一列或这张表")

    explorer = repo.text(EXPLORER_LOAD)
    match = re.search(r"从([^。\n]+?)中选择 1 条 `rhythm_reference`", explorer)
    if not match:
        failures.append(f"{EXPLORER_LOAD}: 没找到节奏取材范围，确认读取写法后更新本测试")
    else:
        where = f"{EXPLORER_LOAD}:{line_no(explorer, match.start())}"
        vocabulary = columns | titles
        for term in split_terms(match.group(1), "、/"):
            if not any(term in v for v in vocabulary):
                failures.append(f"{where}: 节奏取材点名「{term}」，节奏.md 模板里没有对应的列或表")

    # 导入写题材定位时按编号引用节奏与情绪模块的条目。
    importer = repo.text(IMPORT_LONG)
    em_template = fenced_block_after(repo.text(STAGE3), EM_TEMPLATE_HEADING)
    for prefix_group, source, label in (
        (r"\{(RH/TR) 编号\}", template, "节奏.md"),
        (r"\{(EM)-001 等\}", em_template, "情绪模块.md"),
    ):
        match = re.search(prefix_group, importer)
        if not match:
            failures.append(f"{IMPORT_LONG}: 没找到按编号引用{label}的列，确认读取写法后更新本测试")
            continue
        for prefix in match.group(1).split("/"):
            if not re.search(rf"\b{prefix}-\d{{3}}", source):
                failures.append(f"{IMPORT_LONG}: 引用 {prefix} 编号，{label} 模板里没有 {prefix}-xxx 条目")
    return failures


# ---------- 短篇拆文 ----------


def check_short_analyze(repo: Repo) -> list[str]:
    failures: list[str] = []

    # 情节节点：写作端点名的节点字段要在节点模板里。
    node_template = fenced_block_after(repo.text(SHORT_STAGE23), r"^### 节点模板")
    if not node_template:
        failures.append(f"{SHORT_STAGE23}: 找不到「### 节点模板」下的模板代码块")
    else:
        labels = set(re.findall(r"([一-鿿]{2,4})\{", node_template))
        text = repo.text(SHORT_RECALL)
        match = re.search(r"`情节节点\.md` 看每个节点的([^，。\n]+)", text)
        if not match:
            failures.append(f"{SHORT_RECALL}: 没找到读情节节点的字段说明，确认读取写法后更新本测试")
        else:
            where = f"{SHORT_RECALL}:{line_no(text, match.start())}"
            for term in split_terms(match.group(1), "、和"):
                if term in node_template or any(label in term for label in labels):
                    continue
                failures.append(
                    f"{where}: 读情节节点的「{term}」，节点模板里没有这一项（模板字段：{'、'.join(sorted(labels))}）"
                )

    # genre_detected：拆文能写出的每个题材值，写作端映射表都要认得。
    # 取值来源：analysis-short-genres.md「题材路由」表第一列，加 SKILL.md 规定的兜底值。
    skill = repo.text(SHORT_ANALYZE_SKILL)
    produced: list[str] = []
    routing = section_body(repo.text(SHORT_GENRES), "题材路由")
    for header, rows in tables(routing):
        if header and header[0] == "类型":
            produced += [row[0] for row in rows if row and row[0]]
    produced += re.findall(r'扫不到(?:则 genre_detected = |写)[「"]([^」"]+)[」"]', skill)
    if not produced:
        failures.append(f"{SHORT_GENRES}: 没从「题材路由」表解析出 genre_detected 的取值，确认写法后更新本测试")
    recall = repo.text(SHORT_RECALL)
    mapping = next((rows for header, rows in tables(recall) if header and "genre_detected" in header[0]), None)
    if mapping is None:
        failures.append(f"{SHORT_RECALL}: 没找到 genre_detected → 题材包 映射表")
    else:
        accepted: set[str] = set()
        for row in mapping:
            accepted.update(split_terms(re.sub(r"[`]", "", row[0]), "/、（）() "))
        for genre in produced:
            if genre not in accepted:
                failures.append(f"{SHORT_RECALL}: genre_detected 可能取「{genre}」，题材包映射表里没有")

    # 导入短篇读的拆文报告小节。
    short_titles: set[str] = set()
    for rel in (SHORT_STAGE23, SHORT_STAGE46):
        source = repo.text(rel)
        marker = source.find("## 输出模板")
        short_titles.update(headings(source[marker:] if marker >= 0 else source))
    for rel in repo.glob(SHORT_REPORT_CONSUMER_GLOBS):
        text = repo.text(rel)
        for match in REPORT_REF_RE.finditer(text):
            where = f"{rel}:{line_no(text, match.start())}"
            for section in QUOTED_RE.findall(match.group(1)):
                for part in split_terms(section, "/"):
                    if not any(part in title for title in short_titles):
                        failures.append(f"{where}: 读短篇拆文报告「{section}」，Stage 2-6 输出模板里没有「{part}」这一节")

    # 写作端与导入读的 `_meta.json` 键要在 output-contract 的 schema 模板里。
    schema = fenced_block_after(repo.text(SHORT_CONTRACT), r"^## `_meta\.json` schema")
    keys = set(re.findall(r'"([A-Za-z_]+)"\s*:', schema))
    if not keys:
        failures.append(f"{SHORT_CONTRACT}: 没解析出 `_meta.json` schema 模板的键，确认写法后更新本测试")
    else:
        named = 0
        for rel in (SHORT_RECALL, IMPORT_DEEP):
            text = repo.text(rel)
            for line_match in re.finditer(r"^.*_meta\.json.*$", text, re.M):
                for token in re.findall(r"`([A-Za-z_][A-Za-z0-9_.]*)`", line_match.group(0)):
                    token = (token[len("_meta.json"):] if token.startswith("_meta.json") else token).lstrip(".")
                    if not token or token.endswith(".json"):
                        continue
                    named += 1
                    for part in token.split("."):
                        if part not in keys:
                            where = f"{rel}:{line_no(text, line_match.start())}"
                            failures.append(f"{where}: 读 `_meta.json` 的「{part}」，output-contract 的 schema 里没有这个键")
        if not named:
            failures.append(f"{SHORT_RECALL}: 没找到读取 `_meta.json` 键的写法，确认读取写法后更新本测试")
    return failures


# ---------- 短篇扫榜 → 写作平台 ----------


def phase2_platform_regex(repo: Repo) -> re.Pattern[str] | None:
    source = repo.text(PHASE2_CHECK)
    match = re.search(r"settings\.match\(/目标平台\\s\*\[：:\]\\s\*\((.+?)\)/\)", source)
    if not match:
        return None
    return re.compile(rf"^(?:{match.group(1)})$")


def check_short_platforms(repo: Repo) -> list[str]:
    failures: list[str] = []
    accepted = phase2_platform_regex(repo)
    if accepted is None:
        return [f"{PHASE2_CHECK}: 没解析出目标平台正则，确认写法后更新本测试"]

    design = repo.text(SHORT_DESIGN)
    match = re.search(r"- 目标平台：\{([^}]+)\}", design)
    if not match:
        return failures + [f"{SHORT_DESIGN}: 没找到设定模板的「目标平台」取值，确认写法后更新本测试"]
    choices = split_terms(match.group(1), "/")
    for choice in choices:
        if not accepted.match(choice):
            failures.append(f"{SHORT_DESIGN}: 目标平台可选「{choice}」，check-phase2-contract.js 不认")

    topic = repo.text(TOPIC_MATCH)
    mapping = None
    for header, rows in tables(topic):
        target_cols = [i for i, cell in enumerate(header) if "目标平台" in cell and i > 0]
        if target_cols:
            mapping = (header, rows, target_cols[0])
            break
    if mapping is None:
        failures.append(f"{TOPIC_MATCH}: 缺少「扫榜平台 → 写作目标平台」对照表（表头含「目标平台」的一列）")
        return failures
    header, rows, col = mapping
    covered: set[str] = set()
    for row in rows:
        if len(row) <= col:
            continue
        covered.update(split_terms(row[0], "/、 "))
        for target in split_terms(row[col], "/、"):
            target = re.sub(r"[（(].*$", "", target).strip()
            if target not in choices:
                failures.append(
                    f"{TOPIC_MATCH}: 对照表把「{row[0]}」推荐到「{target}」，写作端设定模板只认 {' / '.join(choices)}"
                )
            elif not accepted.match(target):
                failures.append(f"{TOPIC_MATCH}: 对照表目标平台「{target}」过不了 check-phase2-contract.js")

    described = re.search(r"分析(.+?)等平台", repo.text(SHORT_SCAN_SKILL))
    if not described:
        failures.append(f"{SHORT_SCAN_SKILL}: 没从 description 解析出扫榜平台，确认写法后更新本测试")
    else:
        for platform in split_terms(described.group(1), "、"):
            if not any(platform in name or name in platform for name in covered):
                failures.append(f"{TOPIC_MATCH}: 扫榜支持「{platform}」，对照表里没有这一行")
    return failures


CHECKS = (check_long_report, check_em_cards, check_rhythm, check_short_analyze, check_short_platforms)


def run_all(repo: Repo) -> list[str]:
    failures: list[str] = []
    for check in CHECKS:
        failures.extend(check(repo))
    return failures


# ---------- 负例：改坏输入后断言必须报错 ----------


def mutated(rel: str, old: str, new: str) -> Repo | None:
    """把 rel 里最后一处 old 换成 new（报告模板在快速预览之后，取最后一处才改到报告）。"""
    text = Repo().text(rel)
    if old not in text:
        return None
    head, _, tail = text.rpartition(old)
    return Repo({rel: head + new + tail})


NEGATIVE_CASES = (
    ("报告删掉「读者在追什么」", AUTHOR_FACING, "## 读者在追什么", "## 读者追读点", "读者在追什么"),
    ("报告「基本信息」不再写题材", AUTHOR_FACING, "题材：{题材}\n", "", "「题材」"),
    ("报告「基本信息」不再写目标平台", AUTHOR_FACING, "目标平台：{原书所在平台，看不出来就留空}\n", "", "「目标平台」"),
    ("快速预览改了「黄金三章评分」标题", AUTHOR_FACING, "## 黄金三章评分\n\n| 维度", "## 开篇评分\n\n| 维度", "黄金三章评分"),
    ("深度拆解模板改了「可借鉴要素」", STAGE1, "**可借鉴要素**", "**可学的**", "可借鉴要素"),
    ("短篇报告改了「人物分析」标题", SHORT_STAGE46, "### A. 人物分析", "### A. 人物", "人物分析"),
    ("短篇 schema 改了 reversal_type", SHORT_CONTRACT, '"reversal_type"', '"reversal_kind"', "reversal_type"),
    ("短篇 schema 改了 genre_detected", SHORT_CONTRACT, '"genre_detected"', '"genre"', "genre_detected"),
    ("情节节点模板丢掉位置", SHORT_STAGE23, "位置{第N节，约X字} | ", "", "位置"),
    ("写前召回把「可替换项」写成别名", LONG_RECALL, "可替换项、不可照搬）", "可替换要素、不可照搬）", "可替换要素"),
    ("rhythm_reference 点名不存在的列", LONG_RECALL, "扩写方式 →", "扩写技法 →", "扩写技法"),
    ("情绪模块模板丢掉门禁字段", STAGE3, "| 情绪链 | {缺口", "| 情绪曲线 | {缺口", "情绪链"),
    ("写作端校验不再认黑岩", PHASE2_CHECK, "|黑岩|", "|", "黑岩"),
)


def run_negative_cases() -> list[str]:
    failures: list[str] = []
    for label, rel, old, new, expect in NEGATIVE_CASES:
        repo = mutated(rel, old, new)
        if repo is None:
            failures.append(f"负例「{label}」：{rel} 里找不到要改的原文「{old}」，更新负例")
            continue
        if not any(expect in f for f in run_all(repo)):
            failures.append(f"负例「{label}」：改坏后没有报出含「{expect}」的问题")
    return failures


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    failures = run_all(Repo())
    failures += run_negative_cases()
    if failures:
        print("交接契约检查失败：")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("交接契约检查通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
