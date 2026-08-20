#!/usr/bin/env python3
"""Превращает OpenAPI-документ приложения в перечень маршрутов usedesign.

⚠️ ЧЕСТНАЯ ГРАНИЦА (issue #5, замерено на живом сервисе): OpenAPI показывает только то, что
разработчик РЕШИЛ опубликовать. Маршрут, скрытый из документации (в ASP.NET —
`ExcludeFromDescription()`), в перечень НЕ попадёт, и проверка №1 его не увидит — молча.
На замерившем сервисе так пропала половина поверхности: обе машинные группы маршрутов.

Честный источник по SPEC — собственная ТАБЛИЦА МАРШРУТОВ фреймворка (в ASP.NET —
EndpointDataSource, отдаваемый служебной ручкой только в Development). Этот скрипт — дешёвый
старт для первого часа; перечень подписывает свою границу сам, и сверщик печатает подпись
в каждой сводке.

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
                "produced_by": "the application's OpenAPI document — routes hidden from the docs are ABSENT",
                "routes": routes,
            },
            handle,
            ensure_ascii=False,
            indent=2,
        )
        handle.write("\n")

    print(f"маршрутов в перечне: {len(routes)}")
    print("граница: перечень построен из OpenAPI — маршруты, скрытые из документации, "
          "в нём отсутствуют (честный источник — таблица маршрутов фреймворка)",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    sys.exit(main(sys.argv[1], sys.argv[2]))
