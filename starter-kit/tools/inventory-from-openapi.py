#!/usr/bin/env python3
"""Превращает OpenAPI-документ работающего приложения в перечень маршрутов usedesign.

Приложение спрашивают о нём самом — исходники не разбираются. Маршруты, порождённые циклом
или расширением, в тексте не видны, а в таблице маршрутов видны все, и именно они чаще всего
оказываются не описанными никем.

    <старт вашего приложения> &
    curl -fsS http://localhost:8080/openapi/v1.json -o openapi.json
    python3 usedesign/tools/inventory-from-openapi.py openapi.json usedesign/route-inventory.json
"""
import json
import sys

VERBS = ("get", "post", "put", "patch", "delete", "head", "options")


def main(source: str, target: str) -> int:
    with open(source, encoding="utf-8") as handle:
        doc = json.load(handle)

    routes = [
        {"method": method.upper(), "path": path, "source": "openapi/v1.json"}
        for path, operations in doc.get("paths", {}).items()
        for method in operations
        if method.lower() in VERBS
    ]
    routes.sort(key=lambda r: (r["path"], r["method"]))

    if not routes:
        # Пустой перечень почти всегда означает неудавшийся снимок, а не приложение без
        # маршрутов. Промолчать здесь — значит выдать сломанный сбор за чистую проверку.
        print("ОШИБКА: в документе нет ни одного маршрута", file=sys.stderr)
        return 1

    with open(target, "w", encoding="utf-8") as handle:
        json.dump(
            {
                "usedesign_inventory": 1,
                "produced_by": "runtime dump — the application's own OpenAPI document",
                "routes": routes,
            },
            handle,
            ensure_ascii=False,
            indent=2,
        )
        handle.write("\n")

    print(f"маршрутов в перечне: {len(routes)}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    sys.exit(main(sys.argv[1], sys.argv[2]))
