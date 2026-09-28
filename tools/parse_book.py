"""Parse the BIWS 400 Questions PDF into a structured JSON knowledge tree.

Usage: python3 tools/parse_book.py <book.pdf> <out.json>
"""
import json, os, re, sys, html
import pymupdf

SKIP_RE = re.compile(r"^(Access the Financial Modeling Course|Access the Full IB Interview Guide|https://breakingintowallstreet\.com|Return to Top\.?)\s*$")
PAGENUM_RE = re.compile(r"^\d+\s*of\s*\d+$")
Q_RE = re.compile(r"^(\d+)\.\s*(\S.*)")

PART_IDS = {
    "Why Publish a New Version of This Guide? What’s Different?": "preface",
    "Fit/Behavioral Interview Questions": "fit",
    "Discussing Transaction Experience": "deal",
    "Technical Questions (Generalist)": "tech",
    "Industry and Group-Specific Technical Questions": "industry",
}


def slug(s):
    s = s.lower().replace("&", "and")
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:48]


def line_md(spans):
    """Join spans of one line into lightweight markup: **bold**, *italic*."""
    out = []
    prev = None
    for s in spans:
        t = s["text"]
        if not t:
            continue
        # PDF sometimes encodes the space between spans as a positional gap.
        if prev is not None and out and not out[-1].endswith(" ") and not t.startswith(" ") and s["bbox"][0] - prev["bbox"][2] > 1.0:
            out.append(" ")
        prev = s
        bold = "Bold" in s["font"] or s["flags"] & 16
        ital = "Italic" in s["font"] or s["flags"] & 2
        core = t.strip()
        if not core:
            out.append(t)
            continue
        lead = t[: len(t) - len(t.lstrip())]
        trail = t[len(t.rstrip()):]
        if bold:
            core = "**" + core + "**"
        elif ital:
            core = "_" + core + "_"
        out.append(lead + core + trail)
    txt = "".join(out).replace("\uf0e0", "→")
    txt = re.sub(r"\*\*(\s*)\*\*", r"\1", txt)  # merge adjacent bold runs
    return re.sub(r"\s+", " ", txt).strip()


def extract_lines(doc, fig_dir=None):
    lines = []
    for pno, page in enumerate(doc, start=1):
        figs = [im for im in page.get_image_info() if im["bbox"][1] > 120]
        for k, im in enumerate(figs, start=1):
            name = f"p{pno:03d}-{k}.png"
            if fig_dir:
                page.get_pixmap(clip=pymupdf.Rect(im["bbox"]), dpi=150).save(os.path.join(fig_dir, name))
            lines.append({"page": pno, "block": (pno, "fig", k), "x": round(im["bbox"][0]), "y": im["bbox"][1],
                          "size": 0, "plain": "", "md": "", "bold": False, "firstBold": False, "fig": name})
        for bi, b in enumerate(page.get_text("dict")["blocks"]):
            for l in b.get("lines", []):
                spans = [s for s in l["spans"] if s["text"].strip()]
                if not spans:
                    continue
                plain = re.sub(r"\s+", " ", "".join(s["text"] for s in l["spans"])).strip().replace("\uf0e0", "→")
                if SKIP_RE.match(plain) or PAGENUM_RE.match(plain):
                    continue
                if plain in ("of",) or re.fullmatch(r"\d+", plain) and l["bbox"][1] < 80:
                    continue
                allbold = all(("Bold" in s["font"] or s["flags"] & 16) for s in spans if s["font"] != "SymbolMT")
                lines.append({
                    "page": pno, "block": (pno, bi), "x": round(l["bbox"][0]), "y": l["bbox"][1],
                    "size": round(max(s["size"] for s in spans)), "plain": plain, "md": line_md(spans),
                    "bold": allbold, "firstBold": ("Bold" in spans[0]["font"] or spans[0]["flags"] & 16),
                })
    lines.sort(key=lambda l: (l["page"], l["y"]))
    return lines


def to_blocks(lines):
    """Group answer lines into paragraphs / bullets."""
    blocks = []
    cur = None
    for ln in lines:
        if ln.get("fig"):
            blocks.append({"t": "img", "src": "fig/" + ln["fig"]})
            continue
        md = ln["md"]
        is_bullet = ln["plain"].startswith(("•", "o ", "▪", "-")) or md in ("•", "o", "▪")
        num = re.match(r"^(\d+)\.\s*(.*)", ln["plain"]) and ln["x"] > 80
        if md in ("•", "o", "▪"):
            cur = {"t": "li", "lvl": 1 if ln["x"] < 100 else 2, "md": ""}
            blocks.append(cur)
            continue
        if is_bullet:
            md = re.sub(r"^[•▪o]\s+", "", md)
            cur = {"t": "li", "lvl": 1 if ln["x"] < 100 else 2, "md": md}
            blocks.append(cur)
            continue
        if num:
            cur = {"t": "ol", "lvl": 1, "md": md}
            blocks.append(cur)
            continue
        if cur and ((cur["t"] in ("li", "ol") and ln["x"] >= 90) or (cur["t"] == "p" and ln["block"] == cur["_blk"] and ln["x"] <= cur["_x"] + 4)):
            cur["md"] = (cur["md"] + " " + md).strip()
            if cur["t"] == "p":
                cur["_blk"] = ln["block"]
            continue
        if cur and cur["t"] == "p" and ln["block"] == cur["_blk"]:
            cur["md"] += " " + md
            continue
        cur = {"t": "p", "md": md, "_blk": ln["block"], "_x": ln["x"]}
        blocks.append(cur)
    for b in blocks:
        b.pop("_blk", None); b.pop("_x", None)
        if b["t"] == "img":
            continue
        b["md"] = re.sub(r"^[•▪]\s*", "", b["md"])
        if b["t"] == "ol":
            b["md"] = re.sub(r"^(\d+)\.\s*", r"\1. ", b["md"])
        b["md"] = b["md"].replace("** **", " ").strip()
    blocks = [b for b in blocks if b.get("md") or b["t"] == "img"]
    # Re-join paragraphs split by page breaks or PDF line blocks mid-sentence.
    merged = []
    for b in blocks:
        prev = merged[-1] if merged else None
        if (prev and prev["t"] == b["t"] and b["t"] != "img" and b["t"] in ("p", "li") and prev.get("lvl") == b.get("lvl")
                and not re.search(r"[.?!:;”\"’)]\**_?$", prev["md"])
                and re.match(r"^[_*]*[a-z(]", b["md"])):
            prev["md"] += " " + b["md"]
        else:
            merged.append(b)
    for b in merged:
        if b["t"] == "img":
            continue
        b["md"] = re.sub(r"_\s+_", " ", b["md"])
        b["md"] = re.sub(r"\*\*\s+\*\*", " ", b["md"])
        b["md"] = re.sub(r"(\w)- (?!(?:and|or|to)\b)([a-z])", r"\1-\2", b["md"])  # words hyphenated across lines
    return merged


def split_figs(blocks):
    """Keep text blocks aligned with translations; figures ride alongside with an anchor index."""
    text, figs = [], []
    for b in blocks:
        if b["t"] == "img":
            figs.append({"src": b["src"], "after": len(text)})
        else:
            text.append(b)
    return text, figs


def main(pdf, out):
    doc = pymupdf.open(pdf)
    toc = doc.get_toc()
    fig_dir = os.path.join(os.path.dirname(os.path.abspath(out)), "fig")
    os.makedirs(fig_dir, exist_ok=True)
    lines = extract_lines(doc, fig_dir)

    # Section headings: 14pt bold lines matching a TOC title.
    titles = {t for _, t, _ in toc}
    parts, part, sec = [], None, None
    body = []  # lines for the current section

    def flush():
        if sec is None:
            return
        sec["_lines"] = body[:]

    for ln in lines:
        if ln["size"] >= 14 and ln["bold"] and ln["plain"] in titles:
            lvl = next(l for l, t, _ in toc if t == ln["plain"])
            flush(); body = []
            if lvl == 1:
                pid = PART_IDS.get(ln["plain"])
                part = {"id": pid, "title": ln["plain"], "page": ln["page"], "sections": []} if pid else None
                if part:
                    parts.append(part)
                    sec = {"id": pid + "-intro", "title": ln["plain"], "page": ln["page"], "intro": True}
                    part["sections"].append(sec)
                else:
                    sec = None
            elif part:
                sec = {"id": slug(ln["plain"]), "title": ln["plain"], "page": ln["page"]}
                part["sections"].append(sec)
            else:
                sec = None
            continue
        if sec is not None:
            body.append(ln)
    flush()

    total = 0
    for part in parts:
        for sec in part["sections"]:
            L = sec.pop("_lines", [])
            intro, qs, cur, in_q = [], [], None, False
            for ln in L:
                m = Q_RE.match(ln["plain"])
                if m and ln["x"] <= 75 and ln["firstBold"]:
                    cur = {"n": int(m.group(1)), "page": ln["page"], "q": [re.sub(r"^\*\*\d+\.\s*", "**", ln["md"])], "a": []}
                    qs.append(cur); in_q = True
                    continue
                if cur and in_q and ln["bold"] and ln["x"] <= 75:
                    cur["q"].append(ln["md"]); continue
                in_q = False
                (cur["a"] if cur else intro).append(ln)
            sec["introBlocks"], sec["introFigs"] = split_figs(to_blocks(intro))
            sec["questions"] = []
            for q in qs:
                qtext = " ".join(q["q"]).replace("**", "").strip()
                qtext = re.sub(r"^\d+\.\s*", "", qtext)
                qtext = re.sub(r"(\w)- (?!(?:and|or|to)\b)([a-z])", r"\1-\2", qtext)
                a, figs = split_figs(to_blocks(q["a"]))
                sec["questions"].append({
                    "id": f"{sec['id']}-{q['n']}", "n": q["n"], "page": q["page"],
                    "q": qtext, "a": a, **({"figs": figs} if figs else {}),
                })
            total += len(qs)
            if not sec["introFigs"]:
                del sec["introFigs"]
            if sec.get("intro") and not qs and not sec["introBlocks"]:
                part["sections"].remove(sec)
    # A part with only an intro section keeps it as its single section.
    json.dump({"title": doc.metadata.get("title"), "parts": parts}, open(out, "w"), ensure_ascii=False, indent=1)
    for p in parts:
        print(p["id"], p["title"])
        for s in p["sections"]:
            print("   ", s["id"], len(s["questions"]), "p", s["page"])
    print("TOTAL", total)


if __name__ == "__main__":
    main(*sys.argv[1:])
