"""Generate a static JSON with ICD-10 categories and subcategories
filtered by specified ranges relevant to dentistry (and adjacent).

Input:  app/atestados/CID10.xml (ISO-8859-1)
Output: app/atestados/cid10_filtered.json (UTF-8, ensure_ascii=False)

Ranges included (inclusive):
- A00-B99, C00-D48, E00-E90, F00-F99, G00-G99,
  I00-I99, J00-J99, K00-K14, L00-L99, M00-M99,
  Q00-Q99, R00-R99, S00-T98, V01-Y98, Z00-Z99

The JSON includes absolutely all categories within those ranges and includes
all their subcategories. Each entry has: codigo, descricao, tipo.
"""

from __future__ import annotations

import json
import os
import re
import sys
import unicodedata
from typing import Iterable, List, Tuple


THIS_DIR = os.path.dirname(__file__)
ROOT = os.path.abspath(os.path.join(THIS_DIR, os.pardir))
CID_XML = os.path.join(ROOT, "app", "atestados", "CID10.xml")
OUT_JSON = os.path.join(ROOT, "app", "atestados", "cid10_filtered.json")


RANGES: List[Tuple[str, str]] = [
    ("A00", "B99"),
    ("C00", "D48"),
    ("E00", "E90"),
    ("F00", "F99"),
    ("G00", "G99"),
    ("I00", "I99"),
    ("J00", "J99"),
    ("K00", "K14"),
    ("L00", "L99"),
    ("M00", "M99"),
    ("Q00", "Q99"),
    ("R00", "R99"),
    ("S00", "T98"),
    ("V01", "Y98"),
    ("Z00", "Z99"),
]


def strip_accents(s: str) -> str:
    if not s:
        return ""
    normalized = unicodedata.normalize("NFD", s)
    return "".join(c for c in normalized if not unicodedata.combining(c))


def nfc(s: str) -> str:
    # normalize to composed form (avoid odd display issues)
    return unicodedata.normalize("NFC", s)


def code_key(code_cat: str) -> Tuple[int, int]:
    """Return sortable key (letter_index, number) for category-like code e.g. 'K02'."""
    code_cat = code_cat.strip().upper()
    if not code_cat or len(code_cat) < 3:
        return (0, -1)
    letter = code_cat[0]
    try:
        num = int(code_cat[1:3])
    except ValueError:
        num = -1
    return (ord(letter) - ord("A"), num)


def in_any_range(code_cat: str) -> bool:
    k = code_key(code_cat)
    for start, end in RANGES:
        if code_key(start) <= k <= code_key(end):
            return True
    return False


def format_code(raw: str) -> str:
    raw = (raw or "").strip().upper()
    if not raw:
        return ""
    # subcategory like K020 -> K02.0
    if len(raw) == 4 and raw[0].isalpha() and raw[1:].isdigit():
        return f"{raw[:3]}.{raw[3]}"
    return raw


def parse_entries(text: str) -> Iterable[dict]:
    """Yield dict entries from XML text: categories and subcategories with names.

    We avoid full XML parsing due to DTD/entities; use regex for specific nodes.
    """
    sub_re = re.compile(
        r'<subcategoria[^>]*codsubcat="([^"]+)"[^>]*>(.*?)</subcategoria>',
        re.DOTALL,
    )
    cat_re = re.compile(
        r'<categoria[^>]*codcat="([^"]+)"[^>]*>(.*?)</categoria>',
        re.DOTALL,
    )
    nome50_re = re.compile(r"<nome50>(.*?)</nome50>", re.DOTALL)
    nome_re = re.compile(r"<nome>(.*?)</nome>", re.DOTALL)

    # subcategories
    for code_raw, block in sub_re.findall(text):
        codigo = format_code(code_raw)
        base = code_raw[:3]  # e.g., K020 -> base category K02
        # prefer <nome> over <nome50> for description
        m = nome_re.search(block)
        if m:
            desc = m.group(1).strip()
        else:
            m2 = nome50_re.search(block)
            desc = m2.group(1).strip() if m2 else ""
        desc = nfc(" ".join(desc.split()))
        if in_any_range(base):
            yield {"codigo": codigo, "descricao": desc}

    # categories
    for code_raw, block in cat_re.findall(text):
        codigo = code_raw.strip().upper()
        base = codigo[:3]
        # prefer <nome> over <nome50> for description
        m = nome_re.search(block)
        if m:
            desc = m.group(1).strip()
        else:
            m2 = nome50_re.search(block)
            desc = m2.group(1).strip() if m2 else ""
        desc = nfc(" ".join(desc.split()))
        if in_any_range(base):
            yield {"codigo": codigo, "descricao": desc}


def main() -> int:
    if not os.path.exists(CID_XML):
        print(f"CID XML not found at {CID_XML}", file=sys.stderr)
        return 2
    with open(CID_XML, "r", encoding="latin-1") as fh:
        text = fh.read()

    # Parse and collect; dedupe by codigo only (we dropped the 'tipo' field)
    seen = set()
    entries = []
    for e in parse_entries(text):
        key = e["codigo"]
        if key in seen:
            continue
        seen.add(key)
        entries.append(e)

    # Sort lexicographically by letter, 2-digit number, and for subcategory include decimal digit
    def sort_key(e: dict):
        code = e["codigo"]
        letter = code[0]
        num = int(code[1:3]) if code[1:3].isdigit() else -1
        sub = code[4] if len(code) == 5 and code[3] == "." and code[4].isdigit() else ""
        return (letter, num, sub)

    entries.sort(key=sort_key)

    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as fh:
        json.dump(entries, fh, ensure_ascii=False, indent=2)

    print(f"Wrote {len(entries)} entries to {OUT_JSON}")
    # print a couple of samples
    for e in entries[:5]:
        print(" ", e)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
