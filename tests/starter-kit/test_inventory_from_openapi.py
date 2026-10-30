"""Tests of starter-kit/tools/inventory-from-openapi.py — the script a team copies into its repository.

They live here, not beside the script: the starter kit is copied whole, and a test there would be
copied with it. Run from anywhere: python tests/starter-kit/test_inventory_from_openapi.py

What they hold (card #333): a route the document gives but the inventory does not take — a
`trace`, a `query`, a method in `additionalOperations` — and a path item given by `$ref` that is not
read are each named on stderr with the route, where up to 1.7.4 they fell out of the count with
nothing said. And the script counts the routes `usedesign scaffold` counts on the same document: the
scaffold goldens say how many routes each fixture serves, and the script must say the same.
"""
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
SCRIPT = REPO / "starter-kit" / "tools" / "inventory-from-openapi.py"
SCAFFOLD = REPO / "impl" / "typescript" / "test"


def run(document):
    with tempfile.TemporaryDirectory() as out:
        target = Path(out) / "route-inventory.json"
        done = subprocess.run(
            [sys.executable, str(SCRIPT), str(document), str(target)],
            capture_output=True, encoding="utf-8",
        )
        routes = json.loads(target.read_text(encoding="utf-8"))["routes"] if target.exists() else None
    return done, routes


class LeftOut(unittest.TestCase):
    def test_every_route_left_out_is_named_with_its_route(self):
        done, routes = run(HERE / "openapi-left-out.json")
        self.assertEqual(done.returncode, 0, done.stderr)
        lines = done.stderr.splitlines()
        named = [line for line in lines if line.startswith(("пропущен: ", "не прочитан: "))]
        self.assertEqual(
            [line[: line.index(" — ")] for line in named],
            [
                "пропущен: TRACE /v1/echo",
                "пропущен: QUERY /v1/search",
                "пропущен: COPY /v1/files/{id}",
                "пропущен: LINK /v1/files/{id}",
                "не прочитан: POST /v1/dup",
                "не прочитан: post /v1/dup-missing",
                "не прочитан: /v1/bad-map",
                "не прочитан: /v1/elsewhere",
                "не прочитан: /v1/missing",
                "не прочитан: /v1/chained",
                "не прочитан: /v1/schema",
                "не прочитан: /v1/superscript",
                "не прочитан: /v1/leading-zero",
                "не прочитан: /v1/nothing",
                "не прочитан: /v1/empty",
                "не прочитан: /v1/not-an-object",
            ],
        )
        said = dict((line[: line.index(" — ")], line[line.index(" — ") + 3:]) for line in named)
        seven = "перечень маршрутов и check берут семь: GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS; маршрут в перечень не попал"
        self.assertTrue(said["пропущен: TRACE /v1/echo"].endswith(seven))
        self.assertTrue(said["пропущен: QUERY /v1/search"].endswith(seven))
        self.assertTrue(said["пропущен: COPY /v1/files/{id}"].startswith("метод из additionalOperations (OpenAPI 3.2)"))
        self.assertTrue(said["не прочитан: POST /v1/dup"].endswith("а OpenAPI 3.2 такого здесь не допускает; маршрут взят из поля post"))
        self.assertTrue(said["не прочитан: post /v1/dup-missing"].endswith("маршрут в перечень не попал, его место — поле post"))
        # `POST` the text forbids; `post` differs from it only in case, and the line says so (finding 4).
        self.assertIn("отличается от POST только регистром", said["не прочитан: post /v1/dup-missing"])
        self.assertIn("не словарь", said["не прочитан: /v1/bad-map"])
        for path, why in [
            ("/v1/elsewhere", "это адрес не внутри документа"),
            ("/v1/missing", "по этому адресу ничего нет"),
            ("/v1/chained", "там снова $ref, а читается один уровень"),
            ("/v1/schema", "там не path item"),
            # A list index is "0" or ASCII digits with no leading zero: "²" passed `isdigit()` and
            # broke `int()` (DOMES's finding 3 in note #1218).
            ("/v1/superscript", "по этому адресу ничего нет"),
            ("/v1/leading-zero", "по этому адресу ничего нет"),
            ("/v1/nothing", "там нет ни одной операции"),
            ("/v1/empty", "там нет ни одной операции"),
        ]:
            self.assertIn(f": {why}; маршруты по этому адресу в перечень не попали", said[f"не прочитан: {path}"], path)
        self.assertIn("не прочитано или пропущено: 16 — каждое названо выше", lines)

        # What gets in: the seven methods, a path item given by `$ref` inside the document followed
        # one level (a pointer with `~1` too), and a field written beside the `$ref` with it.
        self.assertEqual(
            [(r["method"], r["path"]) for r in routes],
            [
                ("GET", "/v1/bad-map"),
                ("POST", "/v1/dup"),
                ("GET", "/v1/echo"),
                ("PUT", "/v1/escaped"),
                ("GET", "/v1/files/{id}"),
                ("DELETE", "/v1/read"),
                ("GET", "/v1/read"),
                ("PATCH", "/v1/read"),
            ],
        )
        self.assertIn("маршрутов в перечне: 8", done.stdout)

    def test_a_document_with_nothing_left_out_says_nothing_more(self):
        done, routes = run(SCAFFOLD / "fixtures" / "scaffold" / "openapi.json")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual([line for line in done.stderr.splitlines() if not line.startswith("граница: ")], [])
        self.assertEqual(len(routes), 7)


class SameCountAsScaffold(unittest.TestCase):
    def test_every_scaffold_fixture_counts_alike(self):
        counted = set()
        for golden in sorted(SCAFFOLD.glob("golden/*/stdout.txt")):
            for line in golden.read_text(encoding="utf-8").splitlines():
                found = re.fullmatch(r"routes:\s+(\d+) served, read from (\S+)", line)
                if found:
                    counted.add((found.group(2), int(found.group(1))))
        self.assertGreaterEqual(len(counted), 9, counted)
        for name, served in sorted(counted):
            with self.subTest(document=name):
                done, routes = run(SCAFFOLD / "fixtures" / "scaffold" / name)
                if served == 0:
                    self.assertEqual(done.returncode, 1, done.stderr)
                    self.assertIn("ОШИБКА: в документе нет ни одного маршрута", done.stderr)
                else:
                    self.assertEqual(done.returncode, 0, done.stderr)
                    self.assertEqual(len(routes), served, f"scaffold counts {served} routes in {name}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
