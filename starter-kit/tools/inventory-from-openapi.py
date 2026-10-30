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

То, что есть в документе, но в перечень не попало, скрипт называет строкой в stderr с
маршрутом: метод `trace` и `query` (OpenAPI 3.2) и каждый метод из `additionalOperations`
(OpenAPI 3.2) — перечень и `check` берут семь методов; path item через `$ref`, который не
удалось прочитать. Path item через `$ref` внутри документа читается на один уровень, как его
читает `usedesign scaffold`.

    <старт вашего приложения> &
    curl -fsS http://localhost:8080/openapi/v1.json -o openapi.json
    python3 usedesign/tools/inventory-from-openapi.py openapi.json usedesign/route-inventory.json
"""
import json
import sys
from urllib.parse import unquote

VERBS = ("get", "post", "put", "patch", "delete", "head", "options")
# Методы, у которых в path item есть своё поле, но которых нет в перечне: trace (OpenAPI 3.0–3.2),
# query (3.2). Любой другой метод в 3.2 лежит в additionalOperations.
NOT_IN_INVENTORY = ("trace", "query")
FIELD_METHODS = VERBS + NOT_IN_INVENTORY
SEVEN = ", ".join(verb.upper() for verb in VERBS)


def follow_local_ref(doc, ref):
    """Цель `$ref` внутри документа (`#` или JSON Pointer `#/a/b`) — (цель, None) или (None, причина)."""
    if not isinstance(ref, str) or not (ref == "#" or ref.startswith("#/")):
        return None, "это адрес не внутри документа"
    target = doc
    for token in [] if ref == "#" else ref[2:].split("/"):
        try:
            key = unquote(token, errors="strict").replace("~1", "/").replace("~0", "~")
        except UnicodeDecodeError:
            return None, "адрес записан с ошибкой"
        if isinstance(target, dict) and key in target:
            target = target[key]
        elif isinstance(target, list) and key.isdigit() and str(int(key)) == key and int(key) < len(target):
            target = target[int(key)]
        else:
            return None, "по этому адресу ничего нет"
    return target, None


def holds_operation(key, value):
    if key == "additionalOperations":
        return not isinstance(value, dict) or len(value) > 0
    return key.lower() in FIELD_METHODS


def resolve_path_item(doc, path, item, said):
    """Path item через `$ref` внутри документа — на один уровень; поля рядом с `$ref` главнее."""
    if not isinstance(item, dict) or "$ref" not in item:
        return item
    ref = item["$ref"]
    own = {key: value for key, value in item.items() if key != "$ref"}
    target, why = follow_local_ref(doc, ref)
    if why is None and not isinstance(target, dict):
        why = "там не path item"
    elif why is None and "$ref" in target:
        why = "там снова $ref, а читается один уровень"
    elif why is None and not any(holds_operation(key, value) for key, value in target.items()):
        why = "там нет ни одной операции"
    if why is not None:
        said(f"не прочитан: {path} — path item задан через $ref {json.dumps(ref, ensure_ascii=False)}: {why}; "
             "маршруты по этому адресу в перечень не попали")
        return own
    return {**target, **own}


def additional_operations(path, item, given, said):
    if not isinstance(given, dict):
        said(f"не прочитан: {path} — additionalOperations не словарь «метод → операция»; "
             "маршруты в нём в перечень не попали")
        return
    for key in given:
        field = key.lower()
        if field not in FIELD_METHODS:
            said(f"пропущен: {key} {path} — метод из additionalOperations (OpenAPI 3.2), а перечень маршрутов "
                 f"и check берут семь: {SEVEN}; маршрут в перечень не попал")
        elif any(own.lower() == field for own in item):
            said(f"не прочитан: {key} {path} — ключ additionalOperations называет метод со своим полем, "
                 f"а OpenAPI 3.2 такого здесь не допускает; маршрут взят из поля {field}")
        else:
            said(f"не прочитан: {key} {path} — ключ additionalOperations называет метод со своим полем, "
                 f"а OpenAPI 3.2 такого здесь не допускает; маршрут в перечень не попал, его место — поле {field}")


def main(source: str, target: str) -> int:
    with open(source, encoding="utf-8") as handle:
        doc = json.load(handle)

    left_out = []

    def said(line):
        left_out.append(line)
        print(line, file=sys.stderr)

    routes = []
    for path, given in doc.get("paths", {}).items():
        item = resolve_path_item(doc, path, given, said)
        if not isinstance(item, dict):
            said(f"не прочитан: {path} — path item не объект; маршруты по этому адресу в перечень не попали")
            continue
        for method, operation in item.items():
            if method == "additionalOperations":
                additional_operations(path, item, operation, said)
            elif method.lower() in NOT_IN_INVENTORY:
                said(f"пропущен: {method.upper()} {path} — OpenAPI такой метод допускает, а перечень маршрутов "
                     f"и check берут семь: {SEVEN}; маршрут в перечень не попал")
            elif method.lower() in VERBS:
                routes.append({"method": method.upper(), "path": path, "source": "openapi/v1.json"})
    routes.sort(key=lambda r: (r["path"], r["method"]))

    if left_out:
        print(f"не прочитано или пропущено: {len(left_out)} — каждое названо выше", file=sys.stderr)

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
