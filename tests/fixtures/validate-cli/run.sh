#!/usr/bin/env bash
# What `validate` must do with its paths, run against both implementations (round 29, issues #13 and #14).
# Usage, from the repository root after `npm run build` in impl/typescript:
#   bash tests/fixtures/validate-cli/run.sh
# Exits 1 on the first difference, printing the command and its output.
set -u
here="$(cd "$(dirname "$0")" && pwd)"
root="$(cd "$here/../../.." && pwd)"
cd "$here"

# What git cannot hold is made here and removed on exit: an empty directory, a byte-order mark,
# bytes that are not UTF-8.
scratch="$(mktemp -d)"
out="$scratch/out.txt"
trap 'rm -rf "$scratch"' EXIT
mkdir -p "$scratch/empty" "$scratch/bom"
printf '\xef\xbb\xbf' > "$scratch/bom/sample.session.finish.op.md"
cat cards/sample.session.finish.op.md >> "$scratch/bom/sample.session.finish.op.md"
printf '\xff\xfe\x00\x01' > "$scratch/bin.dat"

fail() { echo "::error::$1"; cat "$out"; exit 1; }
expect() {
  local want="$1"; shift
  "$@" > "$out" 2>&1
  local got=$?
  [ "$got" -eq "$want" ] || fail "\`$*\` exited $got, expected $want"
}
says() { grep -q -- "$1" "$out" || fail "expected \`$1\` in the output"; }

for impl in ts py; do
  if [ "$impl" = ts ]; then
    v=(node "$root/impl/typescript/dist/cli.js" validate); c=(node "$root/impl/typescript/dist/cli.js" check)
  else
    v=(python "$root/impl/python/validate.py"); c=(python "$root/impl/python/check.py")
  fi
  echo "— $impl"

  # A path with nothing to validate is refused, not passed over an empty set (#14).
  expect 2 "${v[@]}" usedesign.config.yaml; says "usedesign check usedesign.config.yaml"
  expect 2 "${v[@]}" closed.config.yaml;    says "usedesign check closed.config.yaml"
  expect 2 "${v[@]}" "$scratch/empty";      says "nothing to validate"
  expect 2 "${v[@]}" docs;                  says "nothing to validate"
  expect 2 "${v[@]}" docs/notes.md;         says "has no front matter"
  expect 2 "${v[@]}" "$scratch/bin.dat";    says "has no front matter"
  # A path that does not exist is refused by name, alone or beside a good one — never read as a card
  # whose front matter is not valid YAML (1.4.0 did that: «1 card(s)», exit 1).
  expect 2 "${v[@]}" nope;                  says "\`nope\`: no such file or directory"
  expect 2 "${v[@]}" cards nope.op.md;      says "\`nope.op.md\`: no such file or directory"
  grep -q "card(s)" "$out" && fail "a missing path must stop the run before any card is counted"

  # A collected card whose front matter cannot be read is an error and is counted, not skipped (#14):
  # a line above the fence, no closing fence, YAML that does not parse, a list where fields belong.
  expect 1 "${v[@]}" broken;                says "4 card(s), 0 form contract(s): 4 error(s)"
  says "close them with a second"; says "not valid YAML"; says "front matter is a list"
  # A byte-order mark decides nothing.
  expect 0 "${v[@]}" "$scratch/bom";        says "1 card(s), 0 form contract(s): 0 error(s)"

  # Contracts validated with cards: `calls` is read against the cards of the same run (#13).
  expect 0 "${v[@]}" cards forms;           says "form_calls_undescribed"
  # Contracts alone: nothing to compare against, nothing said.
  expect 0 "${v[@]}" forms
  grep -q form_calls_undescribed "$out" && fail "contracts alone must not report form_calls_undescribed"

  # `cards: []` is a declared glob that matched nothing, in both implementations.
  expect 0 "${c[@]}" cards-empty.config.yaml; says "no_cards_found"
  echo "  ok"
done
