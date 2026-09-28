"""Движок сравнения на базе стандартного difflib.

Результат — JSON-совместимый dict, который рендерит фронтенд (app/static/index.html)
и CLI (app/cli.py). Сегменты внутристрочной разницы: [op, text], где op:
"=" — без изменений, "-" — удалено, "+" — добавлено.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher

from .parsers import TableDoc, TextDoc, parse

TOKEN_RE = re.compile(r"\w+|\s+|[^\w\s]", re.UNICODE)
PAIR_THRESHOLD = 0.5      # насколько строки должны быть похожи, чтобы считаться «изменённой», а не удалённой+добавленной
PAIR_MAX_CELLS = 40_000   # лимит на попарное сопоставление в одном блоке замен


@dataclass
class Options:
    ignore_case: bool = False
    ignore_whitespace: bool = False

    def key(self, s: str) -> str:
        if self.ignore_whitespace:
            s = " ".join(s.split())
        if self.ignore_case:
            s = s.casefold()
        return s


# ---------------------------------------------------------------- inline diff

def _merge(segs: list[list[str]]) -> list[list[str]]:
    out: list[list[str]] = []
    for op, s in segs:
        if not s:
            continue
        if out and out[-1][0] == op:
            out[-1][1] += s
        else:
            out.append([op, s])
    return out


def inline_diff(a: str, b: str, opts: Options) -> tuple[list, list]:
    """Пословная разница между двумя строками."""
    ta, tb = TOKEN_RE.findall(a), TOKEN_RE.findall(b)
    sm = SequenceMatcher(None, [opts.key(t) for t in ta], [opts.key(t) for t in tb], autojunk=False)
    sa, sb = [], []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            sa.append(["=", "".join(ta[i1:i2])])
            sb.append(["=", "".join(tb[j1:j2])])
        else:
            sa.append(["-", "".join(ta[i1:i2])])
            sb.append(["+", "".join(tb[j1:j2])])
    return _merge(sa), _merge(sb)


def _pair(a: list[str], b: list[str]) -> list[tuple[str, int | None, int | None]]:
    """Сопоставляет строки внутри блока замен: какие изменены, какие удалены/добавлены."""
    if len(a) * len(b) > PAIR_MAX_CELLS:
        n = min(len(a), len(b))
        return ([("replace", i, i) for i in range(n)]
                + [("delete", i, None) for i in range(n, len(a))]
                + [("insert", None, j) for j in range(n, len(b))])
    out: list[tuple[str, int | None, int | None]] = []
    j = 0
    for i, la in enumerate(a):
        best, bj = 0.0, -1
        for k in range(j, len(b)):
            sm = SequenceMatcher(None, la, b[k], autojunk=False)
            if sm.real_quick_ratio() <= best or sm.quick_ratio() <= best:
                continue
            r = sm.ratio()
            if r > best:
                best, bj = r, k
        if bj >= 0 and best >= PAIR_THRESHOLD:
            out += [("insert", None, k) for k in range(j, bj)]
            out.append(("replace", i, bj))
            j = bj + 1
        else:
            out.append(("delete", i, None))
    out += [("insert", None, k) for k in range(j, len(b))]
    return out


def _align(ka: list, kb: list, a_text: list[str], b_text: list[str]):
    """Общий алгоритм выравнивания: yield (op, i, j) по индексам строк."""
    sm = SequenceMatcher(None, ka, kb, autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                yield "equal", i1 + k, j1 + k
        elif tag == "delete":
            for i in range(i1, i2):
                yield "delete", i, None
        elif tag == "insert":
            for j in range(j1, j2):
                yield "insert", None, j
        else:
            for op, i, j in _pair(a_text[i1:i2], b_text[j1:j2]):
                yield op, None if i is None else i1 + i, None if j is None else j1 + j


def _similarity(stats: dict, total: int) -> float:
    if total == 0:
        return 1.0
    return round(stats["equal"] / total, 4)


# ---------------------------------------------------------------- text

def diff_text(a: list[str], b: list[str], opts: Options) -> dict:
    ka, kb = [opts.key(x) for x in a], [opts.key(x) for x in b]
    rows = []
    stats = {"equal": 0, "insert": 0, "delete": 0, "replace": 0}
    for op, i, j in _align(ka, kb, ka, kb):
        if op == "equal":
            row = {"op": op, "l": i + 1, "r": j + 1, "a": [["=", a[i]]], "b": [["=", b[j]]]}
        elif op == "delete":
            row = {"op": op, "l": i + 1, "r": None, "a": [["-", a[i]]], "b": None}
        elif op == "insert":
            row = {"op": op, "l": None, "r": j + 1, "a": None, "b": [["+", b[j]]]}
        else:
            sa, sb = inline_diff(a[i], b[j], opts)
            row = {"op": op, "l": i + 1, "r": j + 1, "a": sa, "b": sb}
        stats[op] += 1
        rows.append(row)
    stats["similarity"] = _similarity(stats, max(len(a), len(b)))
    return {"mode": "text", "stats": stats, "rows": rows}


# ---------------------------------------------------------------- tables

def col_letter(n: int) -> str:
    s = ""
    n += 1
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def _diff_sheet(a: list[list[str]], b: list[list[str]], opts: Options) -> dict:
    ka = [tuple(opts.key(c) for c in r) for r in a]
    kb = [tuple(opts.key(c) for c in r) for r in b]
    ta, tb = [" | ".join(r) for r in ka], [" | ".join(r) for r in kb]
    rows = []
    stats = {"equal": 0, "insert": 0, "delete": 0, "replace": 0, "cells_changed": 0}
    for op, i, j in _align(ka, kb, ta, tb):
        if op == "equal":
            cells = [["=", v, None] for v in a[i]]
        elif op == "delete":
            cells = [["-", v, None] for v in a[i]]
        elif op == "insert":
            cells = [["+", None, v] for v in b[j]]
        else:
            ra, rb = a[i], b[j]
            cells = []
            for c in range(max(len(ra), len(rb))):
                va = ra[c] if c < len(ra) else ""
                vb = rb[c] if c < len(rb) else ""
                if opts.key(va) == opts.key(vb):
                    cells.append(["=", va, None])
                else:
                    cells.append(["~", va, vb])
                    stats["cells_changed"] += 1
        stats[op] += 1
        rows.append({"op": op, "l": None if i is None else i + 1,
                     "r": None if j is None else j + 1, "cells": cells})
    stats["similarity"] = _similarity(stats, max(len(a), len(b)))
    ncols = max((len(r["cells"]) for r in rows), default=0)
    return {"stats": stats, "cols": [col_letter(c) for c in range(ncols)], "rows": rows}


def diff_tables(a: TableDoc, b: TableDoc, opts: Options) -> dict:
    names_a, names_b = list(a.sheets), list(b.sheets)
    pairs: list[tuple[str | None, str | None]] = []
    if len(names_a) == 1 and len(names_b) == 1:
        pairs = [(names_a[0], names_b[0])]  # один лист — сравниваем даже при разных именах
    else:
        for n in names_a:
            pairs.append((n, n if n in b.sheets else None))
        pairs += [(None, n) for n in names_b if n not in a.sheets]

    sheets = []
    total = {"equal": 0, "insert": 0, "delete": 0, "replace": 0, "cells_changed": 0}
    for na, nb in pairs:
        ra = a.sheets.get(na, []) if na else []
        rb = b.sheets.get(nb, []) if nb else []
        d = _diff_sheet(ra, rb, opts)
        if na is None:
            status = "added"
        elif nb is None:
            status = "removed"
        elif d["stats"]["similarity"] == 1.0 and len(ra) == len(rb):
            status = "same"
        else:
            status = "changed"
        for k in total:
            total[k] += d["stats"][k]
        sheets.append({"name_a": na, "name_b": nb, "status": status, **d})
    rows_total = sum(max(len(a.sheets.get(s["name_a"], []) if s["name_a"] else []),
                         len(b.sheets.get(s["name_b"], []) if s["name_b"] else [])) for s in sheets)
    total["similarity"] = _similarity(total, rows_total)
    total["sheets_added"] = sum(s["status"] == "added" for s in sheets)
    total["sheets_removed"] = sum(s["status"] == "removed" for s in sheets)
    return {"mode": "table", "stats": total, "sheets": sheets}


# ---------------------------------------------------------------- entry point

def compare_docs(a: TextDoc | TableDoc, b: TextDoc | TableDoc, opts: Options | None = None) -> dict:
    opts = opts or Options()
    if isinstance(a, TableDoc) and isinstance(b, TableDoc):
        return diff_tables(a, b, opts)
    ta = a.to_text() if isinstance(a, TableDoc) else a
    tb = b.to_text() if isinstance(b, TableDoc) else b
    return diff_text(ta.lines, tb.lines, opts)


def compare_files(data_a: bytes, name_a: str, data_b: bytes, name_b: str,
                  opts: Options | None = None) -> dict:
    result = compare_docs(parse(data_a, name_a), parse(data_b, name_b), opts)
    result["left"] = {"name": name_a, "size": len(data_a)}
    result["right"] = {"name": name_b, "size": len(data_b)}
    return result
