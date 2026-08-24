"""Wraps report/index.html (an Artifact-style fragment -- no <!DOCTYPE>/<html>/
<head>/<body>, since Claude's Artifact publisher supplies that skeleton) into a
complete, self-contained standalone HTML document for direct static hosting
(GitHub Pages), where there is no such wrapper.
"""

import pathlib
import re

HERE = pathlib.Path(__file__).resolve().parent
FRAGMENT_PATH = HERE / "index.html"
OUT_PATH = HERE.parent.parent.parent / "public" / "flock-latino-report.html"

fragment = FRAGMENT_PATH.read_text()

title_match = re.search(r"<title>(.*?)</title>", fragment, re.DOTALL)
title = title_match.group(1) if title_match else "Camera Placement and Latino Population Share"

style_match = re.search(r"<style>.*?</style>", fragment, re.DOTALL)
style_block = style_match.group(0) if style_match else ""

# Everything after the </style> tag is the actual page body markup.
body_content = fragment[style_match.end():] if style_match else fragment[title_match.end():]

# Favicon: camera emoji as an inline SVG data URI (same emoji used for the
# Artifact publish), so the standalone page keeps the same tab icon.
favicon = (
    "data:image/svg+xml,"
    "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'>"
    "<text y='.9em' font-size='90'>%F0%9F%93%B7</text></svg>"
)

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<meta name="description" content="A fifteen-city econometric analysis of Flock/ALPR camera siting, race, and class, from a single-city deep dive to a hierarchical Bayesian model.">
<link rel="icon" href="{favicon}">
{style_block}
</head>
<body>
{body_content}
</body>
</html>
"""

OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
OUT_PATH.write_text(html)
print(f"wrote {OUT_PATH} ({len(html):,} bytes)")
