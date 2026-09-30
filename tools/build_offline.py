"""Bundle the study page, book content and figures into one self-contained HTML file.

Usage: python3 tools/build_offline.py <out.html>
The file works from disk (file://) with no network: data is kept in the browser's
localStorage and moved to the online version through exported JSON files.
"""
import base64, json, os, re, sys

root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "app")
page = open(os.path.join(root, "index.html"), encoding="utf-8").read()
book = open(os.path.join(root, "content", "book.json"), encoding="utf-8").read()
fig_dir = os.path.join(root, "content", "fig")
figs = {f"fig/{f}": "data:image/png;base64," + base64.b64encode(open(os.path.join(fig_dir, f), "rb").read()).decode()
        for f in sorted(os.listdir(fig_dir))}

# Web fonts are unreachable offline; the CSS already falls back to system fonts.
page = re.sub(r'<link rel="(?:preconnect|stylesheet)"[^>]*>\n', "", page)
page = page.replace("<title>IB 400 学习台</title>", "<title>IB 400 学习台（离线版）</title>")

safe = lambda s: s.replace("</", "<\\/")
data = ("<script>window.IB400_OFFLINE=true;\nwindow.IB400_BOOK=" + safe(book) +
        ";\nwindow.IB400_FIGS=" + safe(json.dumps(figs)) + ";</script>\n")
page = page.replace("<script>\n(() => {", data + "<script>\n(() => {", 1)
assert "IB400_BOOK=" in page

html = ('<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
        '<style>:root{color-scheme:light}body{margin:0}img{max-width:100%}[hidden]{display:none!important}</style>'
        '</head><body>' + page + '</body></html>')
open(sys.argv[1], "w", encoding="utf-8").write(html)
print(f"wrote {sys.argv[1]} ({len(html.encode()) / 1e6:.1f} MB)")
