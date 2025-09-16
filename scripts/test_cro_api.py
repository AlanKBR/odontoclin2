import os
import sys
import json
import argparse
import requests

# Simple CLI to probe consultacro-style APIs.
# Usage: python scripts/test_cro_api.py --api cro --q "Joao" --uf SP --key 123


def call_api(api: str, q: str, uf: str | None, key: str, timeout: float = 10.0):
    url = f"https://www.consulta{api.lower()}.com.br/api/index.php"
    headers = {"Accept": "application/json"}
    params = {"tipo": api, "q": q, "chave": key, "destino": "json"}
    if uf and uf.lower() != "todos":
        params["uf"] = uf
    r = requests.get(url, headers=headers, params=params, timeout=timeout)
    r.raise_for_status()
    return r.json()


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", default="cro", help="cro|crm|oab|crp|crea|cau|crn")
    parser.add_argument("--q", required=True, help="search term, e.g. 'Joao'")
    parser.add_argument("--uf", default="todos", help="UF or 'todos'")
    parser.add_argument("--key", default=os.getenv("CRO_API_KEY", ""), help="API key")
    args = parser.parse_args(argv)

    if not args.key:
        print("Missing --key (or set CRO_API_KEY)", file=sys.stderr)
        return 2
    data = call_api(args.api, args.q, args.uf, args.key)
    print(json.dumps(data, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
