#!/usr/bin/env python
"""easy-review -- check a revision note against the three things that make it a revision note.

1. The map is at the top: an image reference sits above the first knowledge module.
2. Knowledge has no questions in it: no question marker between the first module and the
   self-test column.
3. The self-test column is last, stands alone, and every question in it carries a page citation.

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
# A `##` section that is document furniture rather than knowledge. This list mirrors the map
# script's NON_BODY; keep the two in step when either changes.
NON_BODY = ("自测", "自检", "附录", "报告", "勘误", "纠错",
            "self-test", "self test", "test yourself", "quiz", "question bank",
            "appendix", "errata", "report")
CITATION = re.compile(r"[（(]\s*p\s*\d+(?:\s*[–~-]\s*\d+)?(?:\s*[,，][^）)]*)?\s*[)）]")
ITEM = re.compile(r"^\s*(?:>\s*)?(?:\*{1,2})?\s*(?:\d+\s*[.)、]|[-*]\s|Q\d+|自测\s*\d+)")
KNOWLEDGE = re.compile(r"^###\s")


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


def main():
    ap = argparse.ArgumentParser(description="easy-review revision-note checker")
    ap.add_argument("notes")
    ap.add_argument("--json", action="store_true", help="emit the result as JSON")
    args = ap.parse_args()

    if not os.path.isfile(args.notes):
        sys.stderr.write(f"not found: {args.notes}\n")
        return 2
    lines = strip_fences(open(args.notes, encoding="utf-8").read())
    modules = modules_of(lines)

    violations, warnings = [], []
    summary = {"modules": len(modules), "self_test_groups": 0, "self_test_quotes": 0}

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

    # 3. The self-test column is last, stands alone, and cites its pages.
    if test_start is None:
        violations.append("no self-test column (`##` heading naming 自测 / self-test)")
    else:
        for i, title in modules:
            if i > test_start:
                violations.append(f"line {i + 1}: module `{title[:50]}` comes after the "
                                  "self-test column")
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
        # A citation on *either* line of a question/answer pair is enough, so the unit is the
        # group, not the quote: one marker plus the two quotes under it.
        groups = sum(1 for i in range(test_start, len(lines)) if "❓" in lines[i])
        for i in range(test_start, len(lines)):
            if "❓" in lines[i] and not CITATION.search("\n".join(lines[i:i + 4])):
                violations.append(f"line {i + 1}: a self-test question group carries no page "
                                  "citation")
        if len(quotes) < len(numbered):
            warnings.append(f"{len(numbered) - len(quotes)} self-test item(s) are not blockquoted: "
                            "quote the stem, so the answer can be covered")
        summary["self_test_groups"] = groups

    if args.json:
        print(json.dumps({"file": args.notes, "summary": summary, "violations": violations,
                          "warnings": warnings}, ensure_ascii=False, indent=1))
    else:
        print(f"{args.notes}: {summary['modules']} module(s), body ends at line {body_end}, "
              f"self-test at line {test_start + 1 if test_start is not None else '—'} "
              f"({summary['self_test_groups']} question group(s), "
              f"{summary['self_test_quotes']} quoted item(s))")
        for v in violations:
            print(f"VIOLATION  {v}")
        for w in warnings:
            print(f"warning    {w}")
        if not violations:
            print("OK  map on top, no questions in the body, self-test column last")

    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
