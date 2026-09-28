"""Сравнение из командной строки.

    python -m app.cli old.docx new.docx
    python -m app.cli old.xlsx new.xlsx --html report.html

Код выхода: 0 — документы совпадают, 1 — есть различия, 2 — ошибка.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .differ import Options, compare_files
from .parsers import UnsupportedFormat

STATIC = Path(__file__).parent / "static"


def build_report(result: dict) -> str:
    """Самодостаточный HTML-отчёт: веб-интерфейс + встроенный результат."""
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    payload = json.dumps(result, ensure_ascii=False).replace("<", "\\u003c")
    return html.replace("</head>", f"<script>window.__PRELOADED__={payload};</script>\n</head>", 1)


def _color(enabled: bool):
    def c(code: str, s: str) -> str:
        return f"\033[{code}m{s}\033[0m" if enabled else s
    return c


def _segs(segs, c) -> str:
    colors = {"=": "0", "-": "41;97", "+": "42;30"}
    return "".join(c(colors[op], s) for op, s in segs)


def print_result(r: dict, color: bool) -> None:
    c = _color(color)
    s = r["stats"]
    print(c("1", f"{r['left']['name']}  →  {r['right']['name']}"))
    print(f"Сходство: {s['similarity'] * 100:.1f}%   "
          f"{c('32', '+' + str(s['insert']))}  {c('31', '-' + str(s['delete']))}  "
          f"{c('33', '~' + str(s['replace']))}")
    if r["mode"] == "text":
        for row in r["rows"]:
            if row["op"] == "equal":
                continue
            if row["a"]:
                print(c("31", f"- {row['l']:>5} "), _segs(row["a"], c), sep="")
            if row["b"]:
                print(c("32", f"+ {row['r']:>5} "), _segs(row["b"], c), sep="")
        return
    for sh in r["sheets"]:
        if sh["status"] == "same":
            continue
        print(c("1;36", f"\n== Лист: {sh['name_a'] or '—'} → {sh['name_b'] or '—'} [{sh['status']}]"))
        for row in sh["rows"]:
            if row["op"] == "equal":
                continue
            if row["op"] == "replace":
                for col, (st, va, vb) in zip(sh["cols"], row["cells"]):
                    if st == "~":
                        print(f"  {col}{row['l']}: {c('31', repr(va))} → {c('32', repr(vb))}")
            else:
                sign, num, idx = ("-", row["l"], 1) if row["op"] == "delete" else ("+", row["r"], 2)
                vals = " | ".join(cell[idx] or "" for cell in row["cells"])
                print(c("31" if sign == "-" else "32", f"{sign} строка {num}: {vals}"))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="docdiff", description="Сравнение документов")
    p.add_argument("old", type=Path, help="исходный файл («было»)")
    p.add_argument("new", type=Path, help="новый файл («стало»)")
    p.add_argument("--html", type=Path, help="сохранить HTML-отчёт")
    p.add_argument("--json", type=Path, help="сохранить результат в JSON")
    p.add_argument("-i", "--ignore-case", action="store_true", help="не учитывать регистр")
    p.add_argument("-w", "--ignore-whitespace", action="store_true", help="не учитывать пробелы")
    p.add_argument("-q", "--quiet", action="store_true", help="не печатать различия")
    args = p.parse_args(argv)

    try:
        r = compare_files(args.old.read_bytes(), args.old.name, args.new.read_bytes(), args.new.name,
                          Options(args.ignore_case, args.ignore_whitespace))
    except (OSError, UnsupportedFormat) as e:
        print(f"Ошибка: {e}", file=sys.stderr)
        return 2

    if not args.quiet:
        print_result(r, sys.stdout.isatty())
    if args.html:
        args.html.write_text(build_report(r), encoding="utf-8")
        print(f"HTML-отчёт: {args.html}")
    if args.json:
        args.json.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"JSON: {args.json}")
    s = r["stats"]
    return 0 if s["insert"] == s["delete"] == s["replace"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
