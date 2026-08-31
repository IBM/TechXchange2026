#!/usr/bin/env python3
"""
Render selected Lab-2950 markdown docs to standalone, styled HTML.

Usage:
  python tools/md_to_html.py

Outputs (next to the source docs, in docs/html/):
  docs/html/INSTRUCTOR_GUIDE.html
  docs/html/SHARED_ENV_PLAN.html

Self-contained HTML (inline CSS), no external assets or internet needed.
"""
import html as _html
from pathlib import Path

import markdown

REPO = Path(__file__).resolve().parent.parent
DOCS = REPO / "docs"
OUT = DOCS / "html"

# (source markdown, output html, page title)
JOBS = [
    ("INSTRUCTOR_GUIDE.md", "INSTRUCTOR_GUIDE.html",
     "Lab-2950 — Instructor / Setup Guide"),
    ("SHARED_ENV_PLAN.md", "SHARED_ENV_PLAN.html",
     "Lab-2950 — Shared-Environment Plan"),
]

CSS = """
:root { --ibm-blue:#0f62fe; --ink:#161616; --muted:#525252; --line:#e0e0e0;
        --code-bg:#f4f4f4; --accent:#edf5ff; }
* { box-sizing: border-box; }
body { font-family: 'IBM Plex Sans','Segoe UI',Arial,sans-serif; color:var(--ink);
       line-height:1.55; max-width:960px; margin:0 auto; padding:2.5rem 1.5rem 4rem; }
h1,h2,h3,h4 { line-height:1.25; margin-top:1.8em; }
h1 { font-size:1.9rem; border-bottom:3px solid var(--ibm-blue); padding-bottom:.3em; }
h2 { font-size:1.4rem; border-bottom:1px solid var(--line); padding-bottom:.2em; }
h3 { font-size:1.15rem; color:var(--muted); }
a { color:var(--ibm-blue); }
code { background:var(--code-bg); padding:.12em .35em; border-radius:3px;
       font-family:'IBM Plex Mono',Consolas,monospace; font-size:.9em; }
pre { background:var(--code-bg); padding:1rem; border-radius:6px; overflow:auto;
      border-left:3px solid var(--ibm-blue); }
pre code { background:none; padding:0; }
table { border-collapse:collapse; width:100%; margin:1.2em 0; font-size:.94rem; }
th,td { border:1px solid var(--line); padding:.5em .7em; text-align:left; vertical-align:top; }
th { background:var(--accent); }
tr:nth-child(even) td { background:#fafafa; }
blockquote { border-left:4px solid var(--ibm-blue); background:var(--accent);
             margin:1em 0; padding:.6em 1em; color:#0043ce; }
ul,ol { padding-left:1.4rem; }
.header-note { color:var(--muted); font-size:.85rem; margin-top:.2rem; }
hr { border:0; border-top:1px solid var(--line); margin:2rem 0; }
"""

TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>{css}</style>
</head>
<body>
<p class="header-note">IBM TechXchange 2026 · Lab-2950 — generated from {src}</p>
{body}
</body>
</html>
"""


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    md = markdown.Markdown(extensions=["tables", "fenced_code", "toc", "sane_lists"])
    for src_name, out_name, title in JOBS:
        src = DOCS / src_name
        if not src.exists():
            print(f"SKIP (missing): {src}")
            continue
        md.reset()
        body = md.convert(src.read_text(encoding="utf-8"))
        page = TEMPLATE.format(title=_html.escape(title), css=CSS, body=body,
                               src=_html.escape(src_name))
        (OUT / out_name).write_text(page, encoding="utf-8")
        print(f"Wrote {OUT / out_name}")


if __name__ == "__main__":
    main()
