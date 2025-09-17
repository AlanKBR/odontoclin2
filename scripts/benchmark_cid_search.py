"""Simple benchmark for CID search performance.

Compares:
- JSON in-memory search (using the precomputed `app/atestados/cid10_filtered.json`)
- A naive XML text scan using regex (baseline, slower)

Run: python scripts/benchmark_cid_search.py
"""

import json
import os
import re
import time
import unicodedata

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
CID_JSON = os.path.join(ROOT, "app", "atestados", "cid10_filtered.json")
CID_XML = os.path.join(ROOT, "app", "atestados", "CID10.xml")


def strip_norm(s: str) -> str:
    s = unicodedata.normalize("NFD", s)
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


def search_json(q: str, entries: list):
    qn = strip_norm(q).replace(".", "")
    out = []
    for e in entries:
        if qn in e.get("_search_code", "") or qn in e.get("_search_desc", ""):
            out.append(e)
            if len(out) >= 50:
                break
    return out


def search_xml_naive(q: str, xml_text: str):
    qn = strip_norm(q).replace(".", "")
    sub_re = re.compile(
        r'<subcategoria[^>]*codsubcat="([^"]+)"[^>]*>' r"(.*?)</subcategoria>",
        re.DOTALL,
    )
    cat_re = re.compile(r'<categoria[^>]*codcat="([^"]+)"[^>]*>(.*?)</categoria>', re.DOTALL)
    nome50_re = re.compile(r"<nome50>(.*?)</nome50>", re.DOTALL)
    nome_re = re.compile(r"<nome>(.*?)</nome>", re.DOTALL)
    results = []

    def desc_from_block(block):
        m = nome50_re.search(block)
        if m:
            return m.group(1).strip()
        m2 = nome_re.search(block)
        return (m2.group(1).strip() if m2 else "").strip()

    for code_raw, block in sub_re.findall(xml_text):
        codigo = code_raw.strip().upper()
        if len(codigo) == 4 and codigo[0].isalpha() and codigo[1:].isdigit():
            codigo = f"{codigo[:3]}.{codigo[3]}"
        desc = desc_from_block(block)
        if qn in strip_norm(codigo) or qn in strip_norm(desc):
            results.append((codigo, desc))
            if len(results) >= 50:
                return results

    for code_raw, block in cat_re.findall(xml_text):
        codigo = code_raw.strip().upper()
        desc = desc_from_block(block)
        if qn in strip_norm(codigo) or qn in strip_norm(desc):
            results.append((codigo, desc))
            if len(results) >= 50:
                return results

    return results


def main():
    queries = ["carie", "cancro", "Cólera", "K02", "A00"]

    # load JSON
    with open(CID_JSON, "r", encoding="utf-8") as fh:
        entries = json.load(fh)

    # ensure precomputed search fields exist
    for e in entries:
        if "_search_desc" not in e:
            desc = e.get("descricao", "") or ""
            code = e.get("codigo", "") or ""
            e["_search_desc"] = strip_norm(desc)
            e["_search_code"] = strip_norm(code).replace(".", "")

    # load XML (for baseline)
    with open(CID_XML, "r", encoding="latin-1", errors="ignore") as fh:
        xml_text = fh.read()

    print("Benchmarking CID search (JSON in-memory vs naive XML scan)")
    for q in queries:
        iters = 200
        t0 = time.time()
        for _ in range(iters):
            search_json(q, entries)
        t_json = (time.time() - t0) / iters

        t0 = time.time()
        for _ in range(20):
            search_xml_naive(q, xml_text)
        t_xml = (time.time() - t0) / 20

        print(f"query={q!r}: json avg {t_json*1000:.3f} ms | xml avg {t_xml*1000:.3f} ms")


if __name__ == "__main__":
    main()
