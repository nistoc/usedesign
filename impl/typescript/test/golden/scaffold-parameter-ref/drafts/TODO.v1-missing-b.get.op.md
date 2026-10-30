---
# ЗАГОТОВКА, а не карточка. Машина записала только то, что прочитала в OpenAPI;
# всё остальное — FILL_ME, и пока они здесь, файл НЕ проходит `usedesign validate`.
# Это сделано намеренно: заготовка, прошедшая проверку, выглядела бы описанием, не будучи им.
#
# Дозаполнив, ПЕРЕНЕСИТЕ файл в cards/ — переезд и есть слово «я за это отвечаю».
id: TODO.v1-missing-b.get
title: FILL_ME
scenario: FILL_ME          # либо serves_step, если операция служит шагу другой
actors: [FILL_ME]

maturity: FILL_ME          # conceived | designed | implemented | tested | in_production

steps:
  - id: s1-FILL-ME
    text: FILL_ME

concurrency:
  mode: FILL_ME            # etag_required | idempotency_by_header | idempotency_by_formula | none_by_design
  rationale: FILL_ME
  source: FILL_ME

interfaces:
  rest:
    transport: http_rest
    method: GET
    path: /v1/missing/{x}/b/{y}
    responses: [200]

data:
  entities: [FILL_ME]
provenance: FILL_ME        # none для чтения, либо объект с activity_kind
reversibility: FILL_ME     # reversible | irreversible | not_applicable | {reversible_via: …}
---

Заготовка для маршрута `GET /v1/missing/{x}/b/{y}`, снятого из `openapi-parameter-ref.json`.

Документ говорит о себе: параметры пути: x, y.

Машина не знает, зачем эта операция существует, какие проверки она делает и чем доказана её
зрелость. Эти поля ждут человека, и до него описание не является описанием.
