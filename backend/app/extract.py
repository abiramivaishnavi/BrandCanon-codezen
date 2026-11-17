"""Turns uploaded files into plain text (+ colours for images) and splits
guideline documents into individual rules."""
import re
from collections import Counter

import pymupdf
import docx
from PIL import Image


def extract_pdf(path: str):
    doc = pymupdf.open(path)
    pages = [page.get_text("text") for page in doc]
    images = sum(len(page.get_images()) for page in doc)
    return "\n".join(pages).strip(), {"pages": len(pages), "images": images}


def extract_docx(path: str):
    d = docx.Document(path)
    parts = [p.text for p in d.paragraphs if p.text.strip()]
    for table in d.tables:
        for row in table.rows:
            parts.append(" | ".join(c.text.strip() for c in row.cells))
    # accessibility: count images that have no alt text (the docPr 'descr' attribute)
    no_alt = total = 0
    for el in d.element.body.iter():
        if el.tag.endswith("}docPr"):
            total += 1
            if not (el.get("descr") or "").strip():
                no_alt += 1
    return "\n".join(parts).strip(), {"images": total, "images_without_alt": no_alt}


def extract_text_file(path: str):
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read().strip(), {}


def image_colors(path: str, k: int = 6):
    """Dominant colours of an image as [{hex, share}] using Pillow's quantiser."""
    img = Image.open(path).convert("RGB")
    img.thumbnail((160, 160))
    q = img.quantize(colors=k, method=Image.Quantize.MEDIANCUT)
    palette = q.getpalette()
    counts = Counter(q.getdata())
    total = sum(counts.values())
    out = []
    for idx, n in counts.most_common():
        r, g, b = palette[idx * 3: idx * 3 + 3]
        out.append({"hex": "#%02X%02X%02X" % (r, g, b), "share": round(n / total, 3)})
    return out


# ---------- guideline document -> rules ----------
CATEGORY_HINTS = [
    ("tone", ["tone", "voice", "language", "writing style"]),
    ("claim", ["claim", "promot", "superlative", "fact", "offer"]),
    ("term", ["terminolog", "naming", "brand name", "product name", "spelling"]),
    ("visual", ["visual", "logo", "colour", "color", "palette", "font", "typograph", "imagery"]),
    ("accessibility", ["accessib", "alt text", "contrast", "readab", "inclusive"]),
    ("messaging", ["messag", "audience", "values", "positioning", "sustainab"]),
]


def guess_category(text: str, default: str = "messaging") -> str:
    low = text.lower()
    for cat, hints in CATEGORY_HINTS:
        if any(h in low for h in hints):
            return cat
    return default


def split_rules(text: str):
    """Headings set the category; each bullet / sentence under it becomes one rule."""
    rules, category = [], "messaging"
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        clean = re.sub(r"^\s*(?:[-*•–]|\d+[.)])\s*", "", line).strip()
        words = clean.split()
        is_heading = len(words) <= 6 and not clean.endswith(".") and not re.match(r"^\s*(?:[-*•–]|\d+[.)])", raw.strip())
        if is_heading:
            category = guess_category(clean, category)
            continue
        if len(words) < 5:
            continue
        # a long paragraph may hold several rules -> split into sentences
        sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z])", clean)
        for s in sentences:
            if len(s.split()) >= 5:
                rules.append({"category": category, "text": s.strip()})
    return rules
