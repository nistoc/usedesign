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
trap 'chmod -R u+rwx "$scratch" 2>/dev/null; rm -rf "$scratch"' EXIT
mkdir -p "$scratch/empty" "$scratch/bom"
printf '\xef\xbb\xbf' > "$scratch/bom/sample.session.finish.op.md"
cat cards/sample.session.finish.op.md >> "$scratch/bom/sample.session.finish.op.md"
printf '\xff\xfe\x00\x01' > "$scratch/bin.dat"

# Which files both implementations collect (1.4.2): a directory named like a card, names that start
# with a dot, brackets and letter case in a pattern, a card whose YAML does not parse; then, where
# symbolic links hold, a directory reached through a link, a loop of links, links that lead
# nowhere; where permissions hold, a file nobody may read and a directory nobody may list.
# Without links or permissions (Windows without symbolic links, a run as root) those cases are
# skipped and the run says so; in CI they must run.
card=cards/sample.session.finish.op.md
as() { sed "s/^id: sample.session.finish$/id: sample.session.$1/" "$card"; }
mkdir -p "$scratch/dirnamed/y.op.md" "$scratch/real" "$scratch/linked" "$scratch/dangling" "$scratch/denied" \
  "$scratch/dotted/.drafts" "$scratch/brackets" "$scratch/bad" "$scratch/loop/real" "$scratch/twin" \
  "$scratch/formsreal" "$scratch/formsdang" "$scratch/shut/locked"
for d in dirnamed real dangling denied dotted loop/real shut shut/locked; do cp "$card" "$scratch/$d/"; done
as draft > "$scratch/dotted/.drafts/c.op.md"; as dot > "$scratch/dotted/.dot.op.md"
as a > "$scratch/brackets/a.op.md"; as b > "$scratch/brackets/b.op.md"; as ab > "$scratch/brackets/[ab].op.md"
cp broken/badyaml.op.md "$scratch/bad/"
cp forms/session.contract.md "$scratch/formsreal/"; cp form-inventory.json "$scratch/"
cp "$card" "$scratch/denied/z.op.md"; chmod 000 "$scratch/denied/z.op.md"
cp docs/notes.md "$scratch/denied/hidden.md"; chmod 000 "$scratch/denied/hidden.md"
chmod 000 "$scratch/shut/locked"
config() { local name="$1"; shift; { printf 'usedesign_config: 1\n'; printf '%s\n' "$@"; } > "$scratch/$name.config.yaml"; }
config dangling  'checks: [3]' 'cards:' '  - dangling/*.op.md'
config starstar  'checks: [3]' 'cards:' '  - real/**'
config onlydir   'checks: [3]' 'cards:' '  - dirnamed/y.op.md'
config fileunder 'checks: [3]' 'cards:' '  - real/sample.session.finish.op.md/**'
config dotted    'checks: [3]' 'cards:' '  - dotted/**/*.op.md'
config dotdir    'checks: [3]' 'cards:' '  - dotted/.drafts/*.op.md'
config brackets  'checks: [3]' 'cards:' '  - brackets/[ab].op.md'
config upper     'checks: [3]' 'cards:' '  - real/*.OP.MD'
config badyaml   'checks: [3]' 'cards:' '  - bad/*.op.md'
config two       'checks: [3]' 'cards:' '  - real/*.op.md' '  - linked/sub/*.op.md'
config wild      'checks: [3]' 'cards:' '  - linked/*/*.op.md'
config loop      'checks: [3]' 'cards:' '  - loop/**'
config forms2    'checks: [5]' 'forms:' '  - formsreal/*.contract.md' '  - formslinked/*.contract.md' 'form_inventory: form-inventory.json'
config formsdang 'checks: [5]' 'forms:' '  - formsdang/*.contract.md' 'form_inventory: form-inventory.json'
# A symbolic link; on Windows without the right to make one, a junction, which both implementations
# follow as they follow a link.
link() {
  MSYS=winsymlinks:nativestrict ln -s "$1" "$2" 2>/dev/null \
    || { command -v cygpath > /dev/null && cmd //c mklink //J "$(cygpath -w "$2")" "$(cygpath -w "$1")" > /dev/null 2>&1; }
  [ -L "$2" ]
}
links=no
if link "$scratch/real" "$scratch/linked/sub" && link "$scratch/nowhere" "$scratch/dangling/x.op.md" \
   && link "$scratch/nowhere" "$scratch/dotted/.#sample.session.finish.op.md" \
   && link "$scratch/dangling" "$scratch/twin/sub" && link "$scratch/formsreal" "$scratch/formslinked" \
   && link "$scratch/nowhere" "$scratch/formsdang/c.contract.md" \
   && link "$scratch/loop/real" "$scratch/loop/real/up1" && link "$scratch/loop/real" "$scratch/loop/real/up2"; then
  links=yes
fi
perms=no; [ -r "$scratch/denied/z.op.md" ] || perms=yes
# In CI the link and permission cases must run: a test that quietly stopped testing looks like one
# that passes. Only root, which reads everything, may skip the permission cases, and says so.
if [ "${CI:-}" = true ]; then
  [ "$links" = yes ] || { echo "::error::symbolic links do not hold here; CI must run the link cases"; exit 1; }
  [ "$perms" = yes ] || [ "$(id -u)" = 0 ] || { echo "::error::permissions do not hold here; CI must run the permission cases"; exit 1; }
fi

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

  # Both implementations collect the same files (1.4.2). A directory named like a card is not a
  # document — passed over by `validate`, not a match for `check`; `**` at the end matches files,
  # and a file is not a directory for `**` to walk.
  expect 0 "${v[@]}" "$scratch/dirnamed";   says "1 card(s), 0 form contract(s): 0 error(s)"
  expect 1 "${c[@]}" "$scratch/onlydir.config.yaml"; says "no_cards_found"
  expect 0 "${c[@]}" "$scratch/starstar.config.yaml"; says "1 card(s), 0 evidence path(s)"
  expect 1 "${c[@]}" "$scratch/fileunder.config.yaml"; says "no_cards_found"
  # A name that starts with a dot is matched only by a segment that starts with a dot: drafts and
  # an editor's lock beside a card are not cards. Brackets are plain characters; letter case counts.
  expect 0 "${v[@]}" "$scratch/dotted";     says "1 card(s), 0 form contract(s): 0 error(s)"
  expect 0 "${c[@]}" "$scratch/dotted.config.yaml"; says "1 card(s), 0 evidence path(s)"
  expect 0 "${c[@]}" "$scratch/dotdir.config.yaml"; says "1 card(s), 0 evidence path(s)"
  expect 0 "${c[@]}" "$scratch/brackets.config.yaml"; says "1 card(s), 0 evidence path(s)"
  expect 1 "${c[@]}" "$scratch/upper.config.yaml"; says "no_cards_found"
  # Front matter that does not parse stops `check` with exit 2 and the card's name.
  expect 2 "${c[@]}" "$scratch/badyaml.config.yaml"; says "badyaml.op.md\` front matter is not valid YAML"
  if [ "$links" = yes ]; then
    # A directory reached through a link is read, and a card reached two ways is read once — by one
    # pattern, by two patterns, by two paths given to `validate`.
    expect 0 "${v[@]}" "$scratch/linked";   says "1 card(s), 0 form contract(s): 0 error(s)"
    expect 0 "${v[@]}" "$scratch/linked" "$scratch/real"; says "1 card(s), 0 form contract(s): 0 error(s)"
    expect 0 "${c[@]}" "$scratch/two.config.yaml"; says "1 card(s), 0 evidence path(s)"
    expect 0 "${c[@]}" "$scratch/wild.config.yaml"; says "1 card(s), 0 evidence path(s)"
    expect 0 "${c[@]}" "$scratch/forms2.config.yaml"; says "1 contract(s)"
    # A loop of links is walked once, two links to the same directory included (Python's glob took
    # exponential time here).
    expect 0 timeout 60 "${v[@]}" "$scratch/loop"; says "1 card(s), 0 form contract(s): 0 error(s)"
    expect 0 timeout 60 "${c[@]}" "$scratch/loop.config.yaml"; says "1 card(s), 0 evidence path(s)"
    # A link that leads nowhere is a card that cannot be read: `validate` counts and names it, once
    # however it is reached; `check` and `preview` stop with exit 2 and name it — never a traceback,
    # never a silent skip.
    expect 1 "${v[@]}" "$scratch/dangling"; says "2 card(s), 0 form contract(s): 1 error(s)"
    says "cannot be read — it is a link to a path that does not exist"
    expect 1 "${v[@]}" "$scratch/dangling" "$scratch/twin"; says "2 card(s), 0 form contract(s): 1 error(s)"
    expect 2 "${c[@]}" "$scratch/dangling.config.yaml"; says "cannot be read — it is a link to a path that does not exist"
    expect 2 "${c[@]}" "$scratch/formsdang.config.yaml"; says "c.contract.md\` cannot be read"
    if [ "$impl" = ts ]; then
      expect 2 node "$root/impl/typescript/dist/cli.js" preview "$scratch/formsdang.config.yaml" --out "$scratch/p.html"
      says "c.contract.md\` cannot be read"
    fi
  else
    echo "  (no symbolic links here: the link cases are skipped)"
  fi
  if [ "$perms" = yes ]; then
    expect 1 "${v[@]}" "$scratch/denied";   says "2 card(s), 0 form contract(s): 1 error(s)"
    says "cannot be read — permission denied"
    expect 2 "${v[@]}" "$scratch/denied/hidden.md"; says "cannot be read — permission denied"
    # A directory nobody may list stops the run with its name: the cards in it would go unseen.
    expect 2 "${v[@]}" "$scratch/shut";     says "locked\` cannot be listed — permission denied"
  else
    echo "  (read permission does not hold here: the permission cases are skipped)"
  fi
  echo "  ok"
done
