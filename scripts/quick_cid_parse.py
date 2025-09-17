import xml.etree.ElementTree as ET
import os
import unicodedata


def strip_accents(s: str) -> str:
    if not s:
        return ""
    normalized = unicodedata.normalize("NFD", s)
    return "".join(c for c in normalized if not unicodedata.combining(c))


def format_code(raw: str) -> str:
    raw = (raw or "").strip()
    if not raw:
        return ""
    if len(raw) == 4 and raw[0].isalpha() and raw[1:].isdigit():
        return f"{raw[:3]}.{raw[3]}"
    return raw


def main():
    base = os.path.join(os.getcwd(), "app", "atestados")
    path = os.path.join(base, "CID10.xml")
    tree = ET.parse(path)
    root = tree.getroot()
    q = "carie"
    qnorm = strip_accents(q).lower().replace(".", "")
    results = []
    seen = set()
    for tag, attr in (("subcategoria", "codsubcat"), ("categoria", "codcat")):
        for node in root.findall(f".//{tag}"):
            raw_code = node.get(attr) or ""
            codigo = format_code(raw_code)
            descricao = (node.findtext("nome50") or node.findtext("nome") or "").strip()
            descricao_norm = strip_accents(descricao).lower()
            codigo_norm = strip_accents(codigo).lower().replace(".", "")
            if qnorm in codigo_norm or qnorm in descricao_norm:
                key = (codigo, descricao)
                if key in seen:
                    continue
                seen.add(key)
                results.append((codigo, descricao))
                if len(results) >= 50:
                    break
        if len(results) >= 50:
            break

    for c, d in results[:30]:
        print(c, "-", d)


if __name__ == "__main__":
    main()
