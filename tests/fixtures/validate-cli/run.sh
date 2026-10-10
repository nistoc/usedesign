#!/usr/bin/env bash
# What `validate` must do with its paths, run against both implementations (round 29, issues #13 and #14).
# Usage, from the repository root after `npm run build` in impl/typescript:
#   bash tests/fixtures/validate-cli/run.sh
# Exits 1 on the first difference, printing the command and its output.
set -u
here="$(cd "$(dirname "$0")" && pwd)"
root="$(cd "$here/../../.." && pwd)"
cd "$here"
mkdir -p empty

fail() { echo "::error::$1"; cat /tmp/usedesign-validate-cli.txt; exit 1; }
expect() {
  local want="$1"; shift
  "$@" > /tmp/usedesign-validate-cli.txt 2>&1
  local got=$?
  [ "$got" -eq "$want" ] || fail "\`$*\` exited $got, expected $want"
}
says() { grep -q -- "$1" /tmp/usedesign-validate-cli.txt || fail "expected \`$1\` in the output"; }

for impl in ts py; do
  if [ "$impl" = ts ]; then v=(node "$root/impl/typescript/dist/cli.js" validate); else v=(python "$root/impl/python/validate.py"); fi
  echo "— $impl"

  # A path with nothing to validate is refused, not passed over an empty set (#14).
  expect 2 "${v[@]}" usedesign.config.yaml; says "usedesign check usedesign.config.yaml"
  expect 2 "${v[@]}" empty;                 says "nothing to validate"
  expect 2 "${v[@]}" docs;                  says "nothing to validate"
  expect 2 "${v[@]}" docs/notes.md;         says "has no front matter"

  # A collected card whose front matter does not open the file is an error, not a silent skip (#14).
  expect 1 "${v[@]}" broken;                says "missing_required_field"

  # Contracts validated with cards: `calls` is read against the cards of the same run (#13).
  expect 0 "${v[@]}" cards forms;           says "form_calls_undescribed"
  # Contracts alone: nothing to compare against, nothing said.
  expect 0 "${v[@]}" forms
  grep -q form_calls_undescribed /tmp/usedesign-validate-cli.txt && fail "contracts alone must not report form_calls_undescribed"
  echo "  ok"
done
