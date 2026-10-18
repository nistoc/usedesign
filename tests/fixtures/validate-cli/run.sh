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
# One id, one document (1.4.3): two cards with one id, two contracts with one id; two cards with
# no id at all are not twins. A name of one character outside the BMP — two UTF-16 code units —
# matched by `?`; ids that sort apart by code point and by UTF-16 code unit (U+FF5E, U+1F600).
mkdir -p "$scratch/sameid" "$scratch/sameform" "$scratch/noid" "$scratch/astral" "$scratch/order"
cp "$card" "$scratch/sameid/a.op.md"; cp "$card" "$scratch/sameid/b.op.md"
cp forms/session.contract.md "$scratch/sameform/a.contract.md"; cp forms/session.contract.md "$scratch/sameform/b.contract.md"
sed '/^id: /d' "$card" > "$scratch/noid/a.op.md"; sed '/^id: /d' "$card" > "$scratch/noid/b.op.md"
# An id that is not text (1.4.4): 1.4.3 read it as absent, and without the schema nothing was said.
mkdir -p "$scratch/wrongid"
sed 's/^id: .*/id: 1/' "$card" > "$scratch/wrongid/a.op.md"; sed 's/^id: .*/id: {a: 1}/' "$card" > "$scratch/wrongid/b.op.md"
sed 's/^id: .*/id: true/' forms/session.contract.md > "$scratch/wrongid/c.contract.md"
# The line and its place (1.5.0): pairs that group, a pair with a misspelt key, a status code where
# the line belongs — read alike with the schema and without it.
mkdir -p "$scratch/pairs"
cases="$root/tests/conformance/cases"
sed 's/^id: .*/id: sample.item.listed/' "$cases/valid/outcomes-pair-list.op.md" > "$scratch/pairs/a.op.md"
sed 's/^id: .*/id: sample.item.misspelt/' "$cases/invalid/outcome-pair-unknown-key.op.md" > "$scratch/pairs/b.op.md"
sed 's/^id: .*/id: sample.item.number/' "$cases/invalid/outcome-shown-as-a-number.op.md" > "$scratch/pairs/c.op.md"
grin="$(printf '\360\237\230\200')"; tilde="$(printf '\357\275\236')"
cp "$card" "$scratch/astral/$grin.op.md"
as "$grin" > "$scratch/order/a.op.md"; as "$tilde" > "$scratch/order/b.op.md"
config astral    'checks: [3]' 'cards:' '  - astral/?.op.md'
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
  # Two documents with one id stop the run with both names (1.4.3): kept by id, one of them left
  # the run without a word. Two cards with no id are two cards, each refused for it.
  expect 2 "${v[@]}" "$scratch/sameid";     says "carry the same id \`sample.session.finish\`"
  says "a.op.md\` and \`"; says "b.op.md\` carry"
  grep -q "card(s)" "$out" && fail "two cards with one id must stop the run before any card is counted"
  expect 2 "${v[@]}" "$scratch/sameform";   says "carry the same id \`sample.session.panel\`"
  expect 1 "${v[@]}" "$scratch/noid";       says "2 card(s), 0 form contract(s)"
  # An id that is not text is a malformed id, with the schema and without it (1.4.4).
  for flag in "" --no-schema; do
    expect 1 "${v[@]}" $flag "$scratch/wrongid"; says "2 card(s), 1 form contract(s)"
    [ "$(grep -c "malformed_operation_id: \`id\` is not text" "$out")" -eq 2 ] || fail "both cards must be named malformed${flag:+ under $flag}"
    says "malformed_form_id: \`id\` is not text"
  done
  # A pair is read alike with the schema and without it (1.5.0): 1.4 had no pair, and without the
  # schema it passed a status code over in silence.
  for flag in "" --no-schema; do
    expect 1 "${v[@]}" $flag "$scratch/pairs"; says "3 card(s), 0 form contract(s)"
    says "outcomes \`unauthorized\`, \`not_found\` are shown identically"
    [ "$(grep -c "malformed_outcome_pair" "$out")" -eq 2 ] || fail "both malformed values must be named${flag:+ under $flag}"
  done
  # `?` is one character, one outside the BMP too (1.4.3); the reference took one UTF-16 code unit.
  expect 0 "${c[@]}" "$scratch/astral.config.yaml"; says "1 card(s), 0 evidence path(s)"
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

# Both implementations order documents as JavaScript compares text, by UTF-16 code unit (1.4.3):
# U+1F600 before U+FF5E. Python compared code points and printed the two cards the other way round.
echo "— order, line for line"
node "$root/impl/typescript/dist/cli.js" validate "$scratch/order" > "$scratch/order.ts.txt" 2>&1
python "$root/impl/python/validate.py" "$scratch/order" > "$scratch/order.py.txt" 2>&1
if ! diff --strip-trailing-cr "$scratch/order.ts.txt" "$scratch/order.py.txt"; then
  echo "::error::validate orders the cards differently in the two implementations"; exit 1
fi
[ "$(grep -m1 -o "^  [A-Za-z]* *[ab]\.op\.md" "$scratch/order.ts.txt" | grep -o "[ab]\.op\.md")" = a.op.md ] \
  || { echo "::error::the card with U+1F600 must come first"; cat "$scratch/order.ts.txt"; exit 1; }
echo "  ok"

# Both implementations count «N days ago» in UTC (1.4.3); Python counted from the local date, a day
# apart near midnight east or west of UTC. At any hour the local date of one of these two zones
# differs from UTC's: UTC+13 from 11:00 UTC on, UTC−11 before it.
echo "— days in UTC"
stale="$root/tests/conformance/checks/cases/evidence-stale/usedesign.config.yaml"
days() { "$@" "$stale" 2>&1 | grep -o "affirmed [0-9]* days ago"; }
want="$(TZ=UTC days node "$root/impl/typescript/dist/cli.js" check)"
[ -n "$want" ] || { echo "::error::the stale case printed no «affirmed N days ago»"; exit 1; }
for tz in XXX-13 XXX+11; do
  for impl in ts py; do
    if [ "$impl" = ts ]; then got="$(TZ=$tz days node "$root/impl/typescript/dist/cli.js" check)"
    else got="$(TZ=$tz days python "$root/impl/python/check.py")"; fi
    [ "$got" = "$want" ] || { echo "::error::$impl in TZ=$tz says «$got», UTC says «$want»"; exit 1; }
  done
done
echo "  ok"

# Both implementations validate against schema/ (1.4.3); the Python prototype had no schema layer,
# and a card only the schema refuses passed there. `schema/` breaks thirteen of the keywords the
# schemas use; both must print the same lines — messages, their order, their count — with the schema
# and without, whatever the hash seed: step ids kept in a set came out in an order the seed chose.
echo "— the schema, line for line"
for flag in "" --no-schema; do
  node "$root/impl/typescript/dist/cli.js" validate $flag schema > "$scratch/schema.ts.txt" 2>&1
  for seed in 0 1 2 3 4 5 6 7; do
    PYTHONHASHSEED=$seed python "$root/impl/python/validate.py" $flag schema > "$scratch/schema.py.txt" 2>&1
    if ! diff --strip-trailing-cr "$scratch/schema.ts.txt" "$scratch/schema.py.txt"; then
      echo "::error::validate ${flag:-with the schema} with PYTHONHASHSEED=$seed prints different lines in the two implementations"; exit 1
    fi
  done
done
grep -q "schema_violation" "$scratch/schema.ts.txt" && { echo "::error::--no-schema still reports schema_violation"; exit 1; }
node "$root/impl/typescript/dist/cli.js" validate schema > "$out" 2>&1
# Two empty outputs are the same too: the schema must have spoken (74 lines at 1.4.3).
[ "$(grep -c "schema_violation" "$out")" -ge 20 ] || { echo "::error::schema/ drew too few schema_violation lines"; cat "$out"; exit 1; }
echo "  ok"

# `check` reads as `validate` reads since 1.4.3 (1.5.1): every field in its type, one id one
# document, the glob of `cards:` for an exclusion and a store name, the config as YAML 1.2, lines in
# one order. Each case runs both implementations; the exit codes and every line must agree, and a
# run must never end in a traceback or in the runtime's own words.
agree() {
  local want="$1" name="$2"; shift 2
  node "$root/impl/typescript/dist/cli.js" check "$@" > "$scratch/$name.ts.out" 2> "$scratch/$name.ts.err"; local t=$?
  python "$root/impl/python/check.py" "$@" > "$scratch/$name.py.out" 2> "$scratch/$name.py.err"; local p=$?
  sed -i 's/^usedesign: //' "$scratch/$name.ts.err"; sed -i 's/^check\.py: //' "$scratch/$name.py.err"
  cat "$scratch/$name.ts.out" "$scratch/$name.ts.err" > "$out"
  for side in out err; do
    if ! diff --strip-trailing-cr "$scratch/$name.ts.$side" "$scratch/$name.py.$side" > "$scratch/$name.diff"; then
      echo "::error::$name: \`check\` prints different lines in the two implementations"
      cat "$scratch/$name.diff"; exit 1
    fi
  done
  [ "$t" -eq "$p" ] || fail "$name: \`check\` exits $t in TypeScript and $p in Python"
  [ "$t" -eq "$want" ] || fail "$name: \`check\` exited $t, expected $want"
  grep -q "Traceback\|is not a function\|is not iterable\|Cannot read properties" "$out" "$scratch/$name.py.err" \
    && fail "$name: \`check\` stopped in the runtime's words"
  return 0
}
echo "— check, line for line"
# Fields of another type are absent to the rules: the typed fixtures stopped 1.5.0 here (TypeScript:
# `path.trim is not a function`, Python: a traceback).
mkdir -p "$scratch/typed"
cp schema/sample.thing.typed.op.md schema/sample.thing.typed-whole.op.md schema/sample.thing.shapes.op.md \
  schema/sample.thing.nulls.op.md schema/sample.session.shapes.contract.md "$scratch/typed/"
printf '%s\n' '{"usedesign_form_inventory": 1, "produced_by": "t", "forms": [{"screen": "ShapesPanel",' \
  '"states": [{"state": "idle", "fields": ["a", "b"], "controls": ["c"], "within": {"a": ["g"]}}]}]}' > "$scratch/typed/forms.json"
config typedall 'cards:' '  - typed/*.op.md' 'forms:' '  - typed/*.contract.md' 'form_inventory: typed/forms.json' \
  'code_root: typed' 'test_report: typed/report.xml' 'storage_inventory: typed/storage.json' 'inventory: typed/routes.json'
printf '<testsuite><testcase classname="c" name="t1"/></testsuite>\n' > "$scratch/typed/report.xml"
printf '{"usedesign_storage_inventory": 1, "produced_by": "t", "stores": [{"name": "things", "keyed_by": ["id"]}]}\n' > "$scratch/typed/storage.json"
printf '{"usedesign_inventory": 1, "produced_by": "t", "routes": [{"method": "POST", "path": "/things"}]}\n' > "$scratch/typed/routes.json"
agree 1 typed "$scratch/typedall.config.yaml"
# One id, one document: two cards or two contracts with one id stop `check` with both names; kept by
# id, 1.5.0 judged one of the two without a word.
config samecards 'checks: [3]' 'cards:' '  - sameid/*.op.md'
config sameforms 'checks: [5]' 'forms:' '  - sameform/*.contract.md' 'form_inventory: form-inventory.json'
agree 2 samecards "$scratch/samecards.config.yaml"; says "carry the same id \`sample.session.finish\`"
agree 2 sameforms "$scratch/sameforms.config.yaml"; says "carry the same id \`sample.session.panel\`"
# Cards and contracts keep two spaces of ids, as in `validate`: a card and a contract that share one
# id, both matched by `cards:`, are not twins.
mkdir -p "$scratch/cardform"
printf '%s\n' '---' 'id: sample.both.thing' 'maturity: designed' '---' > "$scratch/cardform/x.op.md"
printf '%s\n' '---' 'usedesign_form: 1' 'id: sample.both.thing' 'screen: BothPanel' 'maturity: designed' \
  'presents:' '  - field: a' '---' > "$scratch/cardform/x.contract.md"
config cardform 'checks: [3]' 'cards:' '  - cardform/*.md'
agree 0 cardform "$scratch/cardform.config.yaml"
# `gen openapi` reads the cards as `check` does; 1.5.0 merged the two into one route in silence.
node "$root/impl/typescript/dist/cli.js" gen openapi "$scratch/samecards.config.yaml" --out "$scratch/twins.json" > "$out" 2>&1
[ $? -eq 2 ] || fail "gen openapi took two cards with one id"; says "carry the same id \`sample.session.finish\`"
# An exclusion and a store name are matched by the glob of `cards:`: `*` stays inside one part of a
# route, `?` is one character, brackets are plain, letter case counts. 1.5.0 matched them with
# fnmatch in Python (`*` crossed `/`, `[1]` was a set, case went on Windows) and by UTF-16 unit here.
mkdir -p "$scratch/glob/cards"
printf '%s\n' '{"usedesign_inventory": 1, "produced_by": "t", "routes": [' \
  '{"method": "GET", "path": "/health/deep/x"}, {"method": "GET", "path": "/a/'"$grin"'"},' \
  '{"method": "GET", "path": "/Docs"}, {"method": "GET", "path": "/x[1]"}, {"method": "GET", "path": "/b\\c"}]}' > "$scratch/glob/routes.json"
printf '%s\n' '{"usedesign_storage_inventory": 1, "produced_by": "t", "stores": [' \
  '{"name": "sessions[1]", "keyed_by": ["id"]}, {"name": "'"$grin"'log", "keyed_by": ["id"]}]}' > "$scratch/glob/storage.json"
printf '%s\n' '---' 'id: sample.store.read' 'data:' '  storage:' '    - store: "sessions[1]"' '    - store: "?log"' '---' > "$scratch/glob/cards/a.op.md"
config glob 'checks: [1, 4]' 'cards:' '  - glob/cards/*.op.md' 'inventory: glob/routes.json' 'storage_inventory: glob/storage.json' \
  'exclude:' '  - { path: "/health/*", reason: r }' '  - { path: "/a/?", reason: r }' '  - { path: /docs, reason: r }' '  - { path: "/x[1]", reason: r }' \
  '  - { path: "/b*", reason: r }'
agree 1 glob "$scratch/glob.config.yaml"
says "excluded:   2 route(s)"; says "wild_endpoint: GET /health/deep/x"; says "wild_endpoint: GET /Docs"
says "wild_endpoint: GET /b\\\\c"
grep -q "unknown_store" "$out" && fail "glob: a store name matched by the glob of \`cards:\` is a store the storage has"
# The config is read as YAML 1.2, and a value of another type stops the run with the key's name.
# 1.5.0 read `030` as 24 in Python, took the last of two keys there, and stopped on `cards: 5` with a
# traceback and with `patterns is not iterable`.
config octal 'checks: [3]' 'cards:' '  - real/*.op.md' 'evidence_horizon_days: 030'
config twice 'checks: [3]' 'checks: [3]' 'cards:' '  - real/*.op.md'
config number 'cards: 5'
config noscope 'checks: []' 'cards:' '  - real/*.op.md'
agree 0 octal "$scratch/octal.config.yaml"; says "horizon:    30 days"
agree 2 twice "$scratch/twice.config.yaml"; says "config is not valid YAML"
agree 2 number "$scratch/number.config.yaml"; says "\`cards\` in the config must be a list of strings"
agree 2 noscope "$scratch/noscope.config.yaml"; says "\`checks\` in the config must be a list of check numbers"
config horizon 'checks: [3]' 'cards:' '  - real/*.op.md' 'evidence_horizon_days: "30"'
config six 'checks: [6]' 'cards:' '  - real/*.op.md'
config rules 'checks: [1]' 'cards:' '  - real/*.op.md' 'exclude:' '  - { path: 5, reason: r }'
config typo 'chceks: [1]' 'cards:' '  - real/*.op.md'
agree 2 horizon "$scratch/horizon.config.yaml"; says "\`evidence_horizon_days\` in the config must be an integer"
agree 2 six "$scratch/six.config.yaml"; says "\`checks\` in the config must be a list of check numbers"
agree 2 rules "$scratch/rules.config.yaml"; says "\`exclude\` in the config must be a list of rules"
agree 2 typo "$scratch/typo.config.yaml"; says "\`chceks\` is not a config key"
# Past Python's 4 300 digits an integer is Infinity, as JavaScript holds it, and nesting deeper than
# 64 levels is not valid YAML: 1.5.0 Python ended both in a traceback with exit 1, and 1.5.1–1.5.2
# refused the nesting only where each runtime's stack ran out (1.6.0 in the same words in both).
config huge 'checks: [3]' 'cards:' '  - real/*.op.md' "evidence_horizon_days: 1$(printf '0%.0s' $(seq 1 5000))"
agree 2 huge "$scratch/huge.config.yaml"; says "\`evidence_horizon_days\` in the config must be an integer"
config deep 'checks: [3]' 'cards:' '  - real/*.op.md' "x: $(printf '[%.0s' $(seq 1 3000))$(printf ']%.0s' $(seq 1 3000))"
node "$root/impl/typescript/dist/cli.js" check "$scratch/deep.config.yaml" > "$out" 2>&1; t=$?
python "$root/impl/python/check.py" "$scratch/deep.config.yaml" >> "$out" 2>&1; p=$?
[ "$t" -eq 2 ] && [ "$p" -eq 2 ] || fail "deep: \`check\` exits $t in TypeScript and $p in Python, expected 2"
[ "$(grep -c "config is not valid YAML — Collections are nested deeper than 64 levels" "$out")" -eq 2 ] || fail "deep: not refused as YAML in both"
grep -q "Traceback" "$out" && fail "deep: \`check\` stopped in the runtime's words"
# Routes come in the order of their `METHOD shape` (`/a` before `/a b` and `/a+b`) by UTF-16 code
# unit (`/b😀` before `/b～`), and names that look like array indices in the order JavaScript gives
# them — interfaces `b`, `2`, `a`, `10` as 2, 10, b, a, exclusions `/z`, `10`, `9` as 9, 10, /z; an
# `at_least` past 2^53 is written as the reference writes it. 1.5.0 printed each of these in another
# order or form in one of the two.
mkdir -p "$scratch/routes"
printf '%s\n' '---' 'id: sample.order.read' 'maturity: implemented' 'interfaces:' \
  '  b: { transport: http_rest }' '  2: { transport: http_rest }' '  a: { transport: http_rest }' '  10: { transport: http_rest }' \
  '  long: { transport: http_rest, method: GET, path: "/a+b" }' '  short: { transport: http_rest, method: GET, path: /a }' \
  '  space: { transport: http_rest, method: GET, path: "/a b" }' \
  "  astral: { transport: http_rest, method: GET, path: \"/b$grin\" }" "  high: { transport: http_rest, method: GET, path: \"/b$tilde\" }" \
  '---' > "$scratch/routes/p.op.md"
printf '%s\n' '{"usedesign_inventory": 1, "produced_by": "t", "routes": [' \
  '{"method": "GET", "path": "/z"}, {"method": "GET", "path": "10"}, {"method": "GET", "path": "9"}, {"method": "GET", "path": "/w"}]}' \
  > "$scratch/routes/routes.json"
config routes 'checks: [1]' 'cards:' '  - routes/*.op.md' 'inventory: routes/routes.json' \
  'exclude:' '  - { path: /z, reason: r }' '  - { path: "10", reason: r }' '  - { path: "9", reason: r }'
agree 1 routes "$scratch/routes.config.yaml"; says "interface \`2\` declares http_rest"
[ "$(grep "phantom_route" "$out" | sed 's/.*GET \(.*\) is declared.*/\1/' | tr '\n' '|')" = "/a|/a b|/a+b|/b$grin|/b$tilde|" ] \
  || fail "routes: declared routes not in the order of their \`METHOD shape\` by UTF-16 code unit"
printf '%s\n' '---' 'usedesign_form: 1' 'id: sample.big.panel' 'screen: BigPanel' 'maturity: implemented' \
  'presents:' '  - field_pattern: "row-*"' '    at_least: 20000000000000000000' \
  'controls:' '  - control_pattern: "act-*"' '    at_least: 123456789012345678' '    shown_when: [idle]' '---' > "$scratch/routes/big.contract.md"
printf '%s\n' '{"usedesign_form_inventory": 1, "produced_by": "t", "forms": [{"screen": "BigPanel", "states": [{"state": "idle",' \
  '"fields": ["row-1"], "controls": ["act-1"]}]}]}' > "$scratch/routes/forms.json"
config big 'checks: [5]' 'forms:' '  - routes/*.contract.md' 'form_inventory: routes/forms.json'
agree 1 big "$scratch/big.config.yaml"; says "at least 20000000000000000000 element(s)"; says "at least 123456789012345680 control(s)"
# Lines come in one order whatever the hash seed: 1.5.0 Python kept the names a screen renders in
# sets, and the elements no contract line accounts for came out in an order PYTHONHASHSEED chose.
mkdir -p "$scratch/seed"
printf '%s\n' '---' 'usedesign_form: 1' 'id: sample.seed.panel' 'screen: SeedPanel' 'maturity: implemented' \
  'presents:' '  - field: a' '---' > "$scratch/seed/seed.contract.md"
printf '%s\n' '{"usedesign_form_inventory": 1, "produced_by": "t", "forms": [{"screen": "SeedPanel", "states": [{"state": "idle",' \
  '"fields": ["a", "zeta", "alpha", "mid", "beta", "omega", "delta", "kappa", "gamma"], "controls": ["z1", "y2", "x3", "w4"]}]}]}' \
  > "$scratch/seed/forms.json"
config seed 'checks: [5]' 'forms:' '  - seed/*.contract.md' 'form_inventory: seed/forms.json'
for seed in 0 1 2 3; do
  export PYTHONHASHSEED=$seed; agree 0 "seed-$seed" "$scratch/seed.config.yaml"
done
unset PYTHONHASHSEED
says "SeedPanel: \`zeta\` is rendered but no contract line accounts for it"
# Cards are read in the order of their paths by UTF-16 code unit, as the reference sorts them: the
# card at `😀` before the card at `～`, whose ids sort the other way. Sorted by code point, Python
# would print the two the other way round.
mkdir -p "$scratch/pathorder"
for name in "$grin" "$tilde"; do
  id=a; [ "$name" = "$grin" ] && id=z
  printf '%s\n' '---' "id: sample.path.$id" 'maturity: tested' 'steps:' '  - { id: s1, text: Read }' \
    'tests:' '  - { id: T.t1, covers: s1, level: unit }' '---' > "$scratch/pathorder/$name.op.md"
done
config pathorder 'checks: [3]' 'cards:' '  - pathorder/*.op.md'
agree 0 pathorder "$scratch/pathorder.config.yaml"
[ "$(grep -m1 -o "sample\.path\.[az]" "$out")" = sample.path.z ] \
  || fail "pathorder: the card at U+1F600 must be read before the card at U+FF5E"
# A deployment date is a calendar day written `YYYY-MM-DD`, year 1 or later: the basic form
# `20260101` and the week form `2026-W01-1`, which Python's `fromisoformat` reads, and year 0, which
# JavaScript's Date reads, are no date in either implementation.
mkdir -p "$scratch/since"
cp -r "$root/tests/conformance/checks/cases/evidence-impossible-day/code" "$root/tests/conformance/checks/cases/evidence-impossible-day/test-report.xml" "$scratch/since/"
impossible="$root/tests/conformance/checks/cases/evidence-impossible-day/cards/sample.evidence.impossible-day.op.md"
for pair in basic:20260101 week:2026-W01-1 zero:0000-01-01; do
  sed -e "s/^id: .*/id: sample.since.${pair%%:*}/" -e "s/since: 2026-02-30/since: \"${pair#*:}\"/" "$impossible" > "$scratch/since/${pair%%:*}.op.md"
done
config since 'checks: [3]' 'cards:' '  - since/*.op.md' 'code_root: since/code' 'test_report: since/test-report.xml'
agree 1 since "$scratch/since.config.yaml"
[ "$(grep -c "evidence_undated" "$out")" -eq 3 ] || fail "since: each of the three dates must be no date"
# `usedesign_form: true` is not `usedesign_form: 1`: the reference reads such a file as a card, and
# so must Python, where `True == 1`.
mkdir -p "$scratch/formtrue"
sed '1a usedesign_form: true' "$card" > "$scratch/formtrue/t.op.md"
for flag in "" --no-schema; do
  node "$root/impl/typescript/dist/cli.js" validate $flag "$scratch/formtrue" > "$scratch/formtrue.ts.txt" 2>&1
  python "$root/impl/python/validate.py" $flag "$scratch/formtrue" > "$scratch/formtrue.py.txt" 2>&1
  diff --strip-trailing-cr "$scratch/formtrue.ts.txt" "$scratch/formtrue.py.txt" > "$scratch/formtrue.diff" \
    || { echo "::error::formtrue: validate ${flag:-with the schema} prints different lines in the two implementations"; cat "$scratch/formtrue.diff"; exit 1; }
  grep -q "1 card(s), 0 form contract(s)" "$scratch/formtrue.ts.txt" \
    || { echo "::error::formtrue: a file with \`usedesign_form: true\` is a card"; cat "$scratch/formtrue.ts.txt"; exit 1; }
done
echo "  ok"

# Every case of the checks corpus prints the same lines in both implementations, whatever the hash
# seed (the case `seed` above is the one whose order the seed changed in 1.5.0); 1.5.0 Python left
# the routes designed ahead out of its summary line.
echo "— the checks corpus, line for line"
for config_path in "$root"/tests/conformance/checks/cases/*/usedesign.config.yaml; do
  name="corpus-$(basename "$(dirname "$config_path")")"
  node "$root/impl/typescript/dist/cli.js" check "$config_path" > "$scratch/$name.ts.out" 2> /dev/null
  for seed in 0 1 2 3; do
    PYTHONHASHSEED=$seed python "$root/impl/python/check.py" "$config_path" > "$scratch/$name.py.out" 2> /dev/null
    if ! diff --strip-trailing-cr "$scratch/$name.ts.out" "$scratch/$name.py.out" > "$scratch/$name.diff"; then
      echo "::error::$name with PYTHONHASHSEED=$seed: \`check\` prints different lines in the two implementations"
      cat "$scratch/$name.diff"; exit 1
    fi
  done
done
echo "  ok"

# The test report is read as XML reads it (1.5.2). 1.5.1 TypeScript refused a report past 1 000
# escaped characters — 300 test names with four `&quot;` each, as a suite of parametrised tests
# writes them — and named a directory as malformed XML, where Python stopped with a traceback. The
# corpus holds the report cut while it was written and the one with a DOCTYPE.
echo "— the test report, as XML"
mkdir -p "$scratch/xml/cards" "$scratch/xml/report.xml.d"
printf '%s\n' '---' 'id: sample.report.read' 'maturity: designed' 'steps:' '  - { id: s1, text: Read }' \
  'tests:' '  - { id: T.t1, covers: s1, level: unit }' '---' > "$scratch/xml/cards/a.op.md"
{
  printf '<?xml version="1.0" encoding="UTF-8"?>\n<testsuites><testsuite name="s">\n'
  printf '<testcase classname="T" name="t1"><system-out>'
  head -c 100000 /dev/zero | tr '\0' 'q' | sed 's/q/\&quot;/g'
  printf '</system-out></testcase>\n'
  for i in $(seq 300); do printf '<testcase classname="T" name="t%s(&quot;&quot;&#x41;&#65;)"/>\n' "$i"; done
  printf '</testsuite></testsuites>\n'
} > "$scratch/xml/report.xml"
config escapes 'checks: [2]' 'cards:' '  - xml/cards/*.op.md' 'test_report: xml/report.xml'
agree 0 escapes "$scratch/escapes.config.yaml"; says "report:     301 test case(s)"
config reportdir 'checks: [2]' 'cards:' '  - xml/cards/*.op.md' 'test_report: xml/report.xml.d'
agree 1 reportdir "$scratch/reportdir.config.yaml"; says "report_missing: xml/report.xml.d cannot be read: it is a directory"
echo "  ok"
