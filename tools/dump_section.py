"""Print sections of the built book with block indices, for translation work.

Usage: python3 tools/dump_section.py <section_id> [<section_id> ...]
"""
import json, os, sys
book = json.load(open(os.path.join(os.path.dirname(__file__), "..", "app", "content", "book.json")))
secs = {s["id"]: s for p in book["parts"] for s in p["sections"]}
for sid in sys.argv[1:]:
    s = secs[sid]
    print(f"=== {sid} | {s['title']} | p.{s['page']} | {len(s['introBlocks'])} intro, {len(s['questions'])} q")
    for i, b in enumerate(s["introBlocks"]):
        print(f"I{i} [{b['t']}] {b['md']}")
    for q in s["questions"]:
        print(f"\n## {q['id']} :: {q['q']}")
        for i, b in enumerate(q["a"]):
            print(f" A{i} [{b['t']}] {b['md']}")
