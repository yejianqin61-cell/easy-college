#!/usr/bin/env python
"""easy-review -- check a revision note against the four things that make it a revision note.

1. The map is at the top: an image reference sits above the first knowledge module.
2. Knowledge has no questions in it: no question marker between the first module and the
   self-test column.
3. The mastery checklist is present, covers every module, and cites a page per item.
4. The self-test column is last, stands alone, and every question in it carries a page citation.

It cannot see the courseware, so it cannot prove coverage. What it can prove is that the
document's own structure obeys the contract -- which is the part that silently rots when a note
is edited by hand.

Usage:
    python check-review.py NOTES.md [--json]

Exit codes: 0 clean (warnings allowed) | 1 violations found | 2 input could not be read
"""

import argparse
import json
import os
import re
import sys

# A question marker the skill writes itself. The blockquote markers are deliberate: an
# interleaved question is always a quote of the lecture's own check.
QUESTION_MARKERS = ("❓", "❔")
# Wording that only ever appears next to a question. Matched on a blockquote line, not anywhere
# in the prose: "全部习题集中在文末" is a sentence about the document, not a question in it.
QUESTION_WORDS = ("check yourself", "your turn", "try the following", "try these", "self-test",
                  "pause the video", "随堂练习", "随堂测验", "思考题", "复习题", "自测", "自检",
                  "课堂练习", "小测")
# A `##` section that is the self-test column.
SELFTEST = ("自测", "self-test", "self test", "test yourself", "quiz")
# A `##` section holding the pre-exam mastery checklist: derived from the body, not knowledge
# itself, so it is furniture for the map and the module count but a contract for this checker.
CHECKLIST = ("复习目标", "考前自检", "自检清单", "review goals", "mastery checklist",
             "revision checklist")
# A `##` section that is document furniture rather than knowledge. This list mirrors the map
# script's NON_BODY; keep the two in step when either changes.
NON_BODY = ("自测", "自检", "附录", "报告", "勘误", "纠错", "复习目标", "考前自检",
            "self-test", "self test", "test yourself", "quiz", "question bank",
            "appendix", "errata", "report", "review goals", "mastery checklist")
# The source citation at the end of an item: `(p42)`, `(p42–46)`, `(s03)` for an HTML unit,
# `(slide 3)` / `(第 12 页)` for a hand-written one, `(s02、s11)` for several units at once, and any
# `, rebuilt from markup` provenance suffix.
CITATION = re.compile(r"[（(]\s*(?:[ps]\s*|slide\s*|第\s*)\d+(?:\s*[–~-]\s*\d+)?\s*页?"
                      r"(?:\s*[,，、;；和与及][^）)]*)?\s*[)）]")
ITEM = re.compile(r"^\s*(?:>\s*)?(?:\*{1,2})?\s*(?:\d+\s*[.)、]|[-*]\s|Q\d+|自测\s*\d+)")
# A task-list entry: the checklist's item shape. `- [ ]` / `- [x]`.
TASK = re.compile(r"^\s*[-*]\s+\[[ xX]\]\s*\S")
KNOWLEDGE = re.compile(r"^###\s")
LATIN = re.compile(r"[A-Za-z]")
HAN = re.compile(r"[\u4e00-\u9fff]")
# The marker that introduces a translation of the quote above it, in a Chinese note.
TRANSLATION = "译："


def strip_fences(text):
    """Blank out fenced code blocks so a `#` or a `?` inside a listing is not read as prose."""
    out, fenced = [], False
    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            fenced = not fenced
            out.append("")
            continue
        out.append("" if fenced else line)
    return out


def is_non_body(title):
    low = title.lower()
    return any(key in title or key in low for key in NON_BODY)


def modules_of(lines):
    """[(heading index, heading text)] for every `##` section holding a `###` knowledge point.

    The rule is the map's rule: a section with no knowledge point is document furniture -- a
    summary table, a structure note, an errata list -- and is not a module.
    """
    out = []
    current = None
    for i, line in enumerate(lines):
        if line.startswith("## "):
            if current and not is_non_body(current[1]):
                out.append(current)
            current = (i, line[3:].strip(), False)
        elif line.startswith("### ") and current:
            current = (current[0], current[1], True)
    if current and not is_non_body(current[1]):
        out.append(current)
    return [(i, title) for i, title, has_points in out if has_points]


def selftest_start(lines):
    """(index, title) of the self-test column's `##` heading, or (None, None)."""
    for i, line in enumerate(lines):
        if line.startswith("## "):
            title = line[3:].strip()
            low = title.lower()
            if any(key in title or key in low for key in SELFTEST):
                return i, title
    return None, None


def checklist_start(lines):
    """(index, title) of the mastery checklist's `##` heading, or (None, None)."""
    for i, line in enumerate(lines):
        if line.startswith("## "):
            title = line[3:].strip()
            low = title.lower()
            if any(key in title or key in low for key in CHECKLIST):
                return i, title
    return None, None


def section_end(lines, start, fallback):
    """Index of the `##` that closes the section opened at `start`."""
    for i in range(start + 1, len(lines)):
        if lines[i].startswith("## "):
            return i
    return fallback


def is_english_quote(line):
    """True for a blockquote line that is the lecture's own English wording.

    A quote with Chinese on it is the note's own narration or a translation, a nesting quote is
    the note's own answer rather than the lecture's wording, and a formula-only quote carries no
    wording to translate.
    """
    stripped = line.lstrip()
    if not stripped.startswith(">") or stripped.startswith("> >"):
        return False
    body = stripped.lstrip(">").strip()
    latin, han = len(LATIN.findall(body)), len(HAN.findall(body))
    return latin >= 4 and latin > han * 2


def quote_block_end(lines, start):
    """Index just past the blockquote that starts at `start`."""
    end = start + 1
    while end < len(lines) and lines[end].lstrip().startswith(">"):
        end += 1
    return end


def utf8_when_redirected():
    """Windows redirects stdout through the ANSI code page, so printing a CJK path raises
    UnicodeEncodeError and kills a check that had already finished. A console keeps its own
    encoding; only a redirected stream is switched to UTF-8."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure") and not stream.isatty():
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except (ValueError, OSError):
                pass


def malformed_math(lines):
    """`$E = $` is not math: pandoc prints the dollars literally, so the formula ships as source.

    Display math (`$$...$$`) is skipped, and a space *before* an opening `$` is legitimate.
    """
    out = []
    for i, line in enumerate(lines):
        if "$" not in line:
            continue
        bare = line.replace("$$", "")
        if bare.count("$") % 2:
            out.append(i)
            continue
        parts = bare.split("$")
        if any(parts[n] != parts[n].strip() for n in range(1, len(parts), 2)):
            out.append(i)
    return out


def main():
    utf8_when_redirected()
    ap = argparse.ArgumentParser(description="easy-review revision-note checker")
    ap.add_argument("notes")
    ap.add_argument("--json", action="store_true", help="emit the result as JSON")
    args = ap.parse_args()

    if not os.path.isfile(args.notes):
        sys.stderr.write(f"not found: {args.notes}\n")
        return 2
    lines = strip_fences(open(args.notes, encoding="utf-8-sig").read())
    modules = modules_of(lines)

    violations, warnings = [], []
    summary = {"modules": len(modules), "self_test_groups": 0, "self_test_quotes": 0,
               "checklist_items": 0, "checklist_groups": 0, "knowledge_points": 0,
               "checklist_coverage": 0, "untranslated_quotes": 0}

    if not any(l.startswith("# ") for l in lines):
        violations.append("no `#` title")
    if not modules:
        violations.append("no knowledge module (`##` section holding a `###` knowledge point)")

    # 1. The map is at the top.
    figure = next((i for i, l in enumerate(lines) if re.match(r"^\s*!\[.*\]\(.*\)\s*$", l)), None)
    if figure is None:
        violations.append("no image reference: the note must open with its knowledge map")
    elif modules and figure > modules[0][0]:
        violations.append("the map image appears after the first module")

    # 2. No questions in the knowledge body.
    test_start, _ = selftest_start(lines)
    body_end = test_start if test_start is not None else len(lines)
    for i in range(figure + 1 if figure is not None else 0, body_end):
        line = lines[i]
        if line.startswith("## ") and is_non_body(line[3:].strip()):
            break
        if any(m in line for m in QUESTION_MARKERS):
            violations.append(f"line {i + 1}: a question is inside the knowledge body -> "
                              f"{line.strip()[:70]}")
        elif line.lstrip().startswith(">") and any(w in line.lower() for w in QUESTION_WORDS):
            violations.append(f"line {i + 1}: a question is inside the knowledge body -> "
                              f"{line.strip()[:70]}")

    # 3. The mastery checklist: present, before the self-test column, covering every module, and
    #    citing every item. This is the coverage contract a revision reader actually uses.
    check_start, check_title = checklist_start(lines)
    if check_start is None:
        violations.append("no mastery checklist (`##` heading naming 复习目标 / 考前自检 / "
                          "review goals)")
    else:
        check_end = section_end(lines, check_start, body_end)
        if test_start is not None and test_start < check_start:
            violations.append(f"line {check_start + 1}: the mastery checklist comes after the "
                              "self-test column")
        groups = [i for i in range(check_start, check_end) if lines[i].startswith("### ")]
        tasks = [i for i in range(check_start, check_end) if TASK.match(lines[i])]
        summary["checklist_groups"] = len(groups)
        summary["checklist_items"] = len(tasks)
        if not tasks:
            violations.append("the mastery checklist is empty: no `- [ ]` item found")
        if groups and len(groups) < len(modules):
            violations.append(f"the mastery checklist has {len(groups)} group(s) for "
                              f"{len(modules)} module(s): one `###` per module")
        for i in tasks:
            if not CITATION.search(lines[i]):
                violations.append(f"line {i + 1}: a checklist item carries no page citation -> "
                                  f"{lines[i].strip()[:70]}")
        # A checklist is the coverage proof, so it should not hold meaningfully fewer items than
        # the body holds knowledge points. The floor is 80%, the same tolerance this check uses
        # for citations, because a heading or two is legitimately not a capability: a
        # "Learning Outcomes" slide is a knowledge point but nobody ticks it off.
        body_slice = lines[modules[0][0]:check_start] if modules else []
        points = sum(1 for l in body_slice if l.startswith("### "))
        summary["knowledge_points"] = points
        summary["checklist_coverage"] = round(100 * len(tasks) / points) if points else 100
        if points and len(tasks) < points * 0.8:
            warnings.append(f"the mastery checklist has {len(tasks)} item(s) for {points} "
                            f"knowledge point(s) ({summary['checklist_coverage']}%): a revision "
                            "reader may think they are done")

    # 4. The self-test column is last, stands alone, and cites its pages.
    if test_start is None:
        violations.append("no self-test column (`##` heading naming 自测 / self-test)")
    else:
        for i, title in modules:
            if i > test_start:
                violations.append(f"line {i + 1}: module `{title[:50]}` comes after the "
                                  "self-test column")
        if check_start is not None and test_start < check_start:
            pass  # already reported above
        quotes = [i for i in range(test_start, len(lines))
                  if lines[i].lstrip().startswith(">") and lines[i].strip() not in (">", "")]
        cited = [i for i in quotes if CITATION.search(lines[i])]
        numbered = [i for i in range(test_start, len(lines)) if ITEM.match(lines[i])]
        summary["self_test_quotes"] = len(quotes)
        if not quotes and not numbered:
            warnings.append("the self-test column looks empty: no item and no quote found")
        elif quotes and not cited:
            violations.append(f"the self-test column has {len(quotes)} quoted item(s) and no "
                              "page citation")
        # A question group is a `###` inside the column -- that is the shape the skill writes.
        # `❓` is the first-pass marker, kept as a fallback for a note that arrived from there.
        group_lines = [i for i in range(test_start, len(lines)) if lines[i].startswith("### ")]
        if not group_lines:
            group_lines = [i for i in range(test_start, len(lines)) if "❓" in lines[i]]
        summary["self_test_groups"] = len(group_lines)
        # A citation on *either* line of a question/answer pair is enough, so the unit is the
        # group: its heading plus the quotes that follow it.
        for n, i in enumerate(group_lines):
            end = group_lines[n + 1] if n + 1 < len(group_lines) else len(lines)
            if not CITATION.search("\n".join(lines[i:end])):
                violations.append(f"line {i + 1}: a self-test question group carries no page "
                                  "citation")
        if len(quotes) < len(numbered):
            warnings.append(f"{len(numbered) - len(quotes)} self-test item(s) are not blockquoted: "
                            "quote the stem, so the answer can be covered")

    # 5. In a Chinese note, every quoted English original carries its translation. This is the
    #    one check that is a warning rather than a violation: a formula or a bare symbol in a
    #    quote is recognisably untranslatable, and the note's author is the judge of that.
    is_chinese = any(HAN.search(l) for l in lines if l.startswith("# "))
    if is_chinese:
        # From the first module on: the header's `> source line` quotes a course code and a term,
        # not the lecture, and is not something to translate.
        body_start = modules[0][0] if modules else 0
        untranslated = [i for i, line in enumerate(lines)
                        if i >= body_start and is_english_quote(line)
                        and TRANSLATION not in "\n".join(lines[i:quote_block_end(lines, i)])]
        summary["untranslated_quotes"] = len(untranslated)
        if untranslated:
            warnings.append(f"{len(untranslated)} quoted English line(s) carry no {TRANSLATION} "
                            f"translation (first at line {untranslated[0] + 1})")
    summary.setdefault("untranslated_quotes", 0)

    # 6. Formula hygiene: a `$...$` span that starts or ends with a space is not math to pandoc.
    #    It prints as literal source in the PDF, which the reader cannot tell was a mistake.
    loose = malformed_math(lines)
    summary["malformed_math"] = len(loose)
    if loose:
        warnings.append(f"{len(loose)} formula span(s) start or end with a space inside `$...$` "
                        f"(first at line {loose[0] + 1}): pandoc prints them literally, so write "
                        f"`$E = 5850$` and not `$E = $ 5850`")

    if args.json:
        print(json.dumps({"file": args.notes, "summary": summary, "violations": violations,
                          "warnings": warnings}, ensure_ascii=False, indent=1))
    else:
        print(f"{args.notes}: {summary['modules']} module(s), body ends at line {body_end}, "
              f"checklist at line {check_start + 1 if check_start is not None else '—'} "
              f"({summary['checklist_groups']} group(s), {summary['checklist_items']} item(s) for "
              f"{summary['knowledge_points']} knowledge point(s), "
              f"{summary['checklist_coverage']}% covered), "
              f"self-test at line {test_start + 1 if test_start is not None else '—'} "
              f"({summary['self_test_groups']} question group(s), "
              f"{summary['self_test_quotes']} quoted item(s), "
              f"{summary['untranslated_quotes']} untranslated quote(s))")
        for v in violations:
            print(f"VIOLATION  {v}")
        for w in warnings:
            print(f"warning    {w}")
        if not violations:
            print("OK  map on top, no questions in the body, checklist covers the modules, "
                  "self-test column last")

    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
