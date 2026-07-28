---
id: library.staff.issue-api-key
title: Issue an API key to an integrating system
scenario: library.administration.grant-machine-access
actors: [library_admin]

maturity: in_production
maturity_evidence:
  implemented: src/admin/ApiKeyHandler.ts
  tested: 4 tests
  deployed: production

data_transition: { from: nonexistent, to: active }

concurrency:
  mode: idempotency_by_header
  rationale: >
    A retried request must not mint a second key. Optimistic locking does not apply — there is
    no prior revision of a key that does not exist yet.
  on_duplicate: { http: 200, code: existing_key_returned_without_secret }
  source: src/admin/routes.ts:33

steps:
  - id: s1-role
    text: Caller holds the administrator role
    on_violation: { error: role_forbidden, http: 403 }
  - id: s2-scopes
    text: Requested scopes are a subset of what the issuer may delegate
    on_violation: { error: scope_not_delegatable, http: 403 }
    rationale: >
      An administrator cannot mint a key more powerful than themselves. Without this check,
      key issuance becomes a privilege escalation path.
  - id: s3-mint
    text: A secret is generated, hashed and stored; only the hash is persisted
  - id: s4-disclose
    text: The plaintext secret is returned once, in this response only

interfaces:
  rest:
    transport: http_rest
    method: POST
    path: /v1/admin/api-keys
    headers_required: [Idempotency-Key]
    responses: [201, 403]
    source: src/admin/routes.ts:33
  ui:
    transport: ui
    screen: AdminApiKeys
    control: "Issue key"
    covers_steps: [s1-role, s2-scopes, s4-disclose]
    source: web/src/pages/admin/AdminApiKeys.tsx:88

data:
  entities: [api_key]
  fields_touched: [api_key.hash, api_key.scopes, api_key.expires_at, api_key.issued_by]

provenance:
  activity_kind: api_key_issued
  attributed_to: the issuing administrator
  on_failure: no key row is committed

reversibility:
  reversible_via: library.staff.revoke-api-key
  note: >
    Revocation disables the key but never recovers the secret. A lost secret means issuing a
    new key, not recovering the old one.

sensitivity:
  response_contains_secret: true
  disclosure: one_time
  storage: hashed with a memory-hard function plus a server-side pepper
  logging_rule: >
    The response body must not be logged, cached, or echoed into error reports. UI shows the
    secret once behind an explicit reveal and never re-fetches it.

tests:
  - { id: ApiKeyTests.non_admin_is_refused, covers: s1-role, level: integration }
  - { id: ApiKeyTests.cannot_delegate_scopes_it_lacks, covers: s2-scopes, level: integration }
  - { id: ApiKeyTests.only_hash_is_persisted, covers: s3-mint, level: unit }
  - { id: AdminApiKeys.test.tsx:secret_is_shown_once_and_not_refetched, covers: s4-disclose, level: ui }

coverage_gaps:
  - step: s4-disclose
    gap: >
      no contract test asserting that the response body is excluded from request logging —
      today this is enforced by a middleware allowlist that nothing verifies
---

# Issue an API key to an integrating system

This operation exists to demonstrate a field most formats have nowhere to put: `sensitivity`.

The secret is returned exactly once. That single fact is a rule for three different consumers at
the same time — the UI must not offer a "show again" affordance, the gateway must not log the
response body, and tests must not print it into CI output. Written in one place, it is one line;
scattered across three codebases, it is three conventions that drift apart.

The second point worth noticing is `s2-scopes`. Key issuance is an obvious privilege-escalation
surface: an administrator who can mint a key with scopes they do not hold has effectively granted
themselves those scopes through a machine identity. The check belongs in the card because it is
a *security property of the operation*, not an implementation detail of the handler.
