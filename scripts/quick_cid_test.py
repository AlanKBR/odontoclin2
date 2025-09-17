from app import create_app


def main():
    app = create_app()
    with app.test_client() as c:
        resp = c.get("/atestados/api/buscar_cid?q=carie")
        print("status", resp.status_code)
        try:
            print(resp.get_json())
        except Exception:
            print(resp.data[:400])


if __name__ == "__main__":
    main()
