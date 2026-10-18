#!/usr/bin/env bash
# The same text read alike by both implementations (1.6.0). The Python prototype read YAML with
# PyYAML, a YAML 1.1 scanner, and cut and matched text with Python's strip(), \d and `.`; each case
# below printed other lines in the two implementations in 1.5.2, or one of them refused what the
# other read. Since 1.6.0 Python runs a port of the TypeScript reference's parser
# (impl/python/yaml12.py), both refuse what that parser lets through in the same words, and text is
# cut and matched as JavaScript does it, in both.
# Usage, from the repository root after `npm run build` in impl/typescript:
#   bash tests/fixtures/validate-cli/yaml.sh
# KEEP_GOING=1 runs every case and names each one that fails, instead of stopping at the first;
# ONLY=<case>,<case> runs those cases alone.
set -u
here="$(cd "$(dirname "$0")" && pwd)"
root="$(cd "$here/../../.." && pwd)"
cd "$here"
scratch="$(mktemp -d)"
trap 'rm -rf "$scratch"' EXIT
cases_dir="$root/tests/conformance/cases"
checks_dir="$root/tests/conformance/checks/cases"
base=cards/sample.session.finish.op.md
# A path as both runtimes read it: Git Bash writes /tmp/…, which Node and Python on Windows do not.
abs() { if command -v cygpath > /dev/null; then cygpath -m "$1"; else printf '%s' "$1"; fi; }

total=0
failed=()
fail() {
  echo "::error::$1: $2"
  [ -f "$scratch/last" ] && cat "$scratch/last"
  case " ${failed[*]-} " in *" $1 "*) ;; *) failed+=("$1") ;; esac
  [ "${KEEP_GOING:-}" = 1 ] || exit 1
}
# chosen <name> — whether the case runs: always, or when ONLY names it.
chosen() { case ",${ONLY:-$1}," in *",$1,"*) return 0 ;; esac; return 1; }

# validate_both <name> <exit> — `validate` on $scratch/<name>, with the schema and without: the two
# implementations print the same lines and exit alike, and never with a traceback.
validate_both() {
  local name="$1" want="$2" flag suffix t p
  chosen "$name" || return 0
  total=$((total + 1))
  for flag in "" --no-schema; do
    suffix="${flag:+.ns}"
    node "$root/impl/typescript/dist/cli.js" validate $flag "$scratch/$name" > "$scratch/$name$suffix.ts" 2>&1; t=$?
    python "$root/impl/python/validate.py" $flag "$scratch/$name" > "$scratch/$name$suffix.py" 2>&1; p=$?
    if ! diff --strip-trailing-cr "$scratch/$name$suffix.ts" "$scratch/$name$suffix.py" > "$scratch/last"; then
      fail "$name" "\`validate${flag:+ $flag}\` prints different lines in the two implementations"
    fi
    rm -f "$scratch/last"
    [ "$t" -eq "$p" ] || fail "$name" "\`validate${flag:+ $flag}\` exits $t in TypeScript and $p in Python"
    [ "$t" -eq "$want" ] || { cp "$scratch/$name$suffix.ts" "$scratch/last"; fail "$name" "\`validate${flag:+ $flag}\` exited $t, expected $want"; rm -f "$scratch/last"; }
    grep -q "Traceback" "$scratch/$name$suffix.py" && fail "$name" "Python stopped with a traceback"
  done
  return 0
}

# check_both <name> <exit> — `check` on $scratch/<name>.config.yaml: the same lines on stdout and on
# stderr, past each implementation's prefix, and the same exit.
check_both() {
  local name="$1" want="$2" t p side
  chosen "$name" || return 0
  total=$((total + 1))
  node "$root/impl/typescript/dist/cli.js" check "$scratch/$name.config.yaml" > "$scratch/$name.ts" 2> "$scratch/$name.ts.err"; t=$?
  python "$root/impl/python/check.py" "$scratch/$name.config.yaml" > "$scratch/$name.py" 2> "$scratch/$name.py.err"; p=$?
  sed -i 's/^usedesign: //' "$scratch/$name.ts.err"; sed -i 's/^check\.py: //' "$scratch/$name.py.err"
  for side in "" .err; do
    if ! diff --strip-trailing-cr "$scratch/$name.ts$side" "$scratch/$name.py$side" > "$scratch/last"; then
      fail "$name" "\`check\` prints different lines in the two implementations"
    fi
  done
  rm -f "$scratch/last"
  cat "$scratch/$name.ts.err" >> "$scratch/$name.ts"
  [ "$t" -eq "$p" ] || fail "$name" "\`check\` exits $t in TypeScript and $p in Python"
  [ "$t" -eq "$want" ] || { cp "$scratch/$name.ts" "$scratch/last"; fail "$name" "\`check\` exited $t, expected $want"; rm -f "$scratch/last"; }
  grep -q "Traceback" "$scratch/$name.py.err" && fail "$name" "Python stopped with a traceback"
  return 0
}

# says / lacks <name> <text> — what the TypeScript side printed for <name> (the same lines as Python's).
says() { chosen "$1" || return 0; grep -qF -- "$2" "$scratch/$1.ts" || { cp "$scratch/$1.ts" "$scratch/last"; fail "$1" "expected \`$2\` in the output"; rm -f "$scratch/last"; }; }
lacks() { chosen "$1" || return 0; grep -qF -- "$2" "$scratch/$1.ts" && { cp "$scratch/$1.ts" "$scratch/last"; fail "$1" "\`$2\` in the output"; rm -f "$scratch/last"; }; return 0; }

# titled <name> <printf format> — the sample card with its title line written by printf.
titled() {
  mkdir -p "$scratch/$1"
  { sed -n '1,2p' "$base"; printf "$2"; printf '\n'; sed -n '4,$p' "$base"; } > "$scratch/$1/sample.session.finish.op.md"
}
# edited <name> <file> <sed script> — a card or case file, edited.
edited() { mkdir -p "$scratch/$1"; sed "$3" "$2" > "$scratch/$1/$(basename "$2")"; }
# config <name> <printf format> — a config beside a copy of the sample card.
mkdir -p "$scratch/real"; cp "$base" "$scratch/real/"
config() { { printf 'usedesign_config: 1\n'; printf "$2"; } > "$scratch/$1.config.yaml"; }

echo "— YAML the two scanners read apart"
# PyYAML stopped on a tab after a colon, on U+2028, NEL, DEL or NUL in a plain value and on a tag it
# did not know; it read a CR alone as a line break — so did Python's universal newlines — and a
# line inside double quotes, after an empty one, at the margin, where TypeScript refuses it.
titled tab 'title:\tFinish the session';                   validate_both tab 0; lacks tab "not valid YAML"
titled ls 'title: Finish\342\200\250the session';          validate_both ls 0; lacks ls "not valid YAML"
titled nel 'title: Finish\302\205the session';             validate_both nel 0; lacks nel "not valid YAML"
titled del 'title: Finish\177the session';                 validate_both del 0; lacks del "not valid YAML"
titled nulchar 'title: Finish\000the session';             validate_both nulchar 0; lacks nulchar "not valid YAML"
titled cr 'title: Finish\rthe session';                    validate_both cr 0; lacks cr "not valid YAML"
titled tag 'title: !foo Finish the session';               validate_both tag 0; lacks tag "not valid YAML"
titled quoted 'title: "Finish\n\nthe session"';            validate_both quoted 1
says quoted "front matter is not valid YAML — Missing closing \"quote at line 4, column 1"
mkdir -p "$scratch/cronly"; tr '\n' '\r' < "$base" > "$scratch/cronly/sample.session.finish.op.md"
validate_both cronly 1; says cronly "no front matter"
# A refusal is in the same words, at the same line and column: PyYAML wrote its own.
titled flow 'title: [Finish the session';                  validate_both flow 1
says flow "front matter is not valid YAML — Flow sequence in block collection must be sufficiently indented and end with a ] at line 4, column 1"

echo "— what the parser lets through, refused in both"
# 1.5.2 TypeScript wrote a collection key as YAML text, and returned a value that contains itself
# for an alias inside its own node; Python refused the key in its own words and stopped on the alias
# with a traceback. Past 100 aliases TypeScript refused and Python read, ten times slower per level.
titled ckey 'title: Finish the session\n? [a, b]\n: c';      validate_both ckey 1
says ckey "front matter is not valid YAML — Map keys must be scalars at line 4, column 3"
titled cycle 'title: &a [*a]';                               validate_both cycle 1
says cycle "front matter is not valid YAML — Alias *a is inside the node it refers to at line 3, column 12"
titled bomb "title: Finish the session\nx1: &a [$(printf 'a,%.0s' $(seq 9))a]\nx2: &b [$(printf '*a,%.0s' $(seq 9))*a]\nx3: [$(printf '*b,%.0s' $(seq 9))*b]"
validate_both bomb 1; says bomb "front matter is not valid YAML — Excessive alias count indicates a resource exhaustion attack"
titled lone 'title: "Finish \\ud800"';                       validate_both lone 1
says lone "front matter is not valid YAML — A string holds half of a surrogate pair, which is not a character at line 3, column 8"
# 64 levels are read, 65 are refused alike; before, each runtime stopped where its stack ran out.
# The card itself is a level: `x` holds 63 more, or 64. 1.5.2 TypeScript read 700 levels and
# refused 800; Python read 400 and stopped with a traceback at 500.
nested() { printf 'title: Finish the session\nx: %s%s' "$(printf '[%.0s' $(seq "$1"))" "$(printf ']%.0s' $(seq "$1"))"; }
titled deep64 "$(nested 63)"; validate_both deep64 0; lacks deep64 "not valid YAML"
titled deep65 "$(nested 64)"; validate_both deep65 1
says deep65 "front matter is not valid YAML — Collections are nested deeper than 64 levels"
# A tag outside the core schema leaves the text: 1.5.2 TypeScript made a date of `!!timestamp`
# (a schema violation in a title), and Python stopped with a traceback on a day that is not one.
titled typed 'title: !!timestamp 2026-02-30';               validate_both typed 0

echo "— text cut and matched as JavaScript does"
# An id read from a block scalar ends in a line feed: Python's `$` matched before it.
edited stepid "$base" 's/^  - id: s1-commit$/  - id: |\n      s1-commit/';            validate_both stepid 1; says stepid "malformed_step_id"
edited opid "$base" 's/^id: sample.session.finish$/id: |\n  sample.session.finish/';    validate_both opid 1
# Integer keys come first, ascending, as a JavaScript object keeps them; Python kept the written order.
edited order "$base" 's/^  rest: \(.*\)$/  b: { transport: smoke }\n  2: { transport: smoke }\n  rest: \1/'
validate_both order 1
# trim() is not strip(): NEL is not white space to JavaScript, U+FEFF is not to Python.
same="$cases_dir/valid/outcomes-shown-identically.op.md"
edited trimnel "$same" 's/consent_required: "Something went wrong. Please try again."/consent_required: "Something went wrong. Please try again.\\x85"/'
validate_both trimnel 0; lacks trimnel "outcomes_indistinguishable"
edited trimbom "$same" 's/consent_required: "Something went wrong. Please try again."/consent_required: "Something went wrong. Please try again.\\ufeff"/'
validate_both trimbom 0; says trimbom "outcomes_indistinguishable"
# A line of a pair with no word left is compared trimmed, as JavaScript trims: ` ✗<U+FEFF>` is `✗`.
edited pairglyph "$cases_dir/valid/outcomes-pair-glyph.op.md" 's/shows: " ✗ "/shows: " ✗\\ufeff"/'
validate_both pairglyph 0; says pairglyph "outcomes \`unauthorized\`, \`forbidden\`"
stale="$cases_dir/valid/tested-count-stale.op.md"
edited spacefs "$stale" 's/tested: 3 tests/tested: "\\x1c3 tests"/';  validate_both spacefs 0; lacks spacefs "tested_count_mismatch"
edited spacebom "$stale" 's/tested: 3 tests/tested: "\\ufeff3 tests"/'; validate_both spacebom 0; says spacebom "tested_count_mismatch"
variant="$cases_dir/invalid/variant-shared-not-implemented.op.md"
# `\d` is any digit to Python, 0–9 to JavaScript: `:١٢` is not a line number.
edited digits "$variant" 's|implemented: src/loans/CheckoutOnBehalf.ts|implemented: "src/loans/CheckoutOnBehalf.ts + src/loans/CheckoutHandler.ts:\\u0661\\u0662"|'
validate_both digits 1; says digits "variant_shared_not_implemented"
edited sharednel "$variant" 's|implemented: src/loans/CheckoutOnBehalf.ts|implemented: src/loans/CheckoutOnBehalf.ts + src/loans/CheckoutHandler.ts|; s|shared: src/loans/CheckoutHandler.ts|shared: "src/loans/CheckoutHandler.ts\\x85"|'
validate_both sharednel 1; says sharednel "variant_shared_not_implemented"
edited sharedbom "$variant" 's|implemented: src/loans/CheckoutOnBehalf.ts|implemented: src/loans/CheckoutOnBehalf.ts + src/loans/CheckoutHandler.ts|; s|shared: src/loans/CheckoutHandler.ts|shared: "src/loans/CheckoutHandler.ts\\ufeff"|'
validate_both sharedbom 0; lacks sharedbom "variant_shared_not_implemented"
edited ownbom "$variant" 's|implemented: src/loans/CheckoutOnBehalf.ts|implemented: "src/loans/CheckoutOnBehalf.ts + src/loans/CheckoutHandler.ts\\ufeff"|'
validate_both ownbom 0; lacks ownbom "variant_shared_not_implemented"

echo "— the config, read alike"
# The words after the dash were each parser's own; a tag PyYAML did not know, NUL, a collection key,
# 100 aliases and a CR, NEL or U+2028 where a line ends were read by one and refused by the other.
config cwords 'checks: [3\ncards:\n  - real/*.op.md\n';                         check_both cwords 2
says cwords "config is not valid YAML — Flow sequence in block collection must be sufficiently indented and end with a ] at line 3, column 1"
config ctagged 'checks: [3]\ncards:\n  - real/*.op.md\nevidence_horizon_days: !foo 30\n'; check_both ctagged 2
says ctagged "\`evidence_horizon_days\` in the config must be an integer"
config cnul 'checks: [3]\ncards:\n  - real/*.op.md\n# \000\n';                   check_both cnul 0
config cckey 'checks: [3]\ncards:\n  - real/*.op.md\n? [a, b]\n: c\n';           check_both cckey 2
says cckey "config is not valid YAML — Map keys must be scalars at line 5, column 3"
config cbomb "checks: [3]\ncards:\n  - real/*.op.md\nx1: &a [$(printf 'a,%.0s' $(seq 9))a]\nx2: &b [$(printf '*a,%.0s' $(seq 9))*a]\nx3: [$(printf '*b,%.0s' $(seq 9))*b]\n"
check_both cbomb 2; says cbomb "config is not valid YAML — Excessive alias count indicates a resource exhaustion attack"
config ccr 'checks: [3]\rcards:\n  - real/*.op.md\n';                            check_both ccr 2
config cnel 'checks: [3]\302\205cards:\n  - real/*.op.md\n';                     check_both cnel 2
config cls 'checks: [3]\342\200\250cards:\n  - real/*.op.md\n';                  check_both cls 2

echo "— check: paths, routes, names"
# check 3 reads an evidence path as JavaScript trims it, and `:N` only with digits 0–9.
mkdir -p "$scratch/ev"; cp -r "$checks_dir/evidence-multipath/." "$scratch/ev/"
cp -r "$scratch/ev" "$scratch/evbom"; cp -r "$scratch/ev" "$scratch/evdigits"
sed -i 's|^  implemented: .*|  implemented: "src/api/Endpoint.ts\\ufeff + src/workers/Worker.ts"|' "$scratch/evbom/cards/sample.evidence.spanning.op.md"
sed -i 's|^  implemented: .*|  implemented: "src/api/Endpoint.ts:\\u0661\\u0662 + src/workers/Worker.ts"|' "$scratch/evdigits/cards/sample.evidence.spanning.op.md"
evidence() { config "$1" "checks: [3]\ncards:\n  - $1/cards/*.op.md\ntest_report: $1/test-report.xml\ncode_root: $1/code\n"; }
evidence evbom; evidence evdigits
check_both evbom 0
check_both evdigits 1; says evdigits "src/api/Endpoint.ts:١٢"
# An evidence path is in the repository: `/src/…` starts at `code_root`, as `path.join` reads it.
# Python's `os.path.join` read it from the root of the file system.
cp -r "$scratch/ev" "$scratch/evslash"
sed -i 's|^  implemented: .*|  implemented: /src/api/Endpoint.ts + src/workers/Worker.ts|' "$scratch/evslash/cards/sample.evidence.spanning.op.md"
evidence evslash; check_both evslash 0
# `code_root` must be a directory: 1.5.2 TypeScript took a file and found nothing under it.
config rootfile 'checks: [3]\ncards:\n  - ev/cards/*.op.md\ntest_report: ev/test-report.xml\ncode_root: ev/code/src/api/Endpoint.ts\n'
check_both rootfile 1; says rootfile "code_root_missing"
# An absolute path in the config is that path: 1.5.2 TypeScript joined it under the config's directory.
config absolute "checks: [3]\ncards:\n  - ev/cards/*.op.md\ntest_report: $(abs "$scratch/ev/test-report.xml")\ncode_root: $(abs "$scratch/ev/code")\n"
check_both absolute 0
# So is an absolute `test_report`, which check 2 reads: 1.5.2 TypeScript found no report there.
mkdir -p "$scratch/reportabs/lib"; cp -r "$checks_dir/variant-clean/." "$scratch/reportabs/"; cp "$root"/examples/library/*.op.md "$scratch/reportabs/lib/"
config reportabs "checks: [2]\ncards:\n  - reportabs/lib/*.op.md\n  - reportabs/cards/*.op.md\ntest_report: $(abs "$scratch/reportabs/test-report.xml")\n"
check_both reportabs 0; lacks reportabs "report_missing"
mkdir -p "$scratch/routes"; cp "$base" "$scratch/routes/"
route() { printf '{"usedesign_inventory": 1, "produced_by": "t", "routes": [{"method": "POST", "path": "%s"}]}\n' "$2" > "$scratch/$1.json"; }
route routebom '/session/{id}:finish\ufeff'; config routebom 'checks: [1]\ncards:\n  - routes/*.op.md\ninventory: routebom.json\n'; check_both routebom 0
route routenel '/session/{id}:finish\u0085'; config routenel 'checks: [1]\ncards:\n  - routes/*.op.md\ninventory: routenel.json\n'; check_both routenel 1
# The inventory names a method exactly; the card's is trimmed first, as JavaScript trims.
edited routemethod "$base" 's/method: POST,/method: "POST\\ufeff",/'; route routemethod '/session/{id}:finish'
config routemethod 'checks: [1]\ncards:\n  - routemethod/*.op.md\ninventory: routemethod.json\n'; check_both routemethod 0
route routeabs '/session/{id}:finish'; config routeabs "checks: [1]\ncards:\n  - routes/*.op.md\ninventory: $(abs "$scratch/routeabs.json")\n"; check_both routeabs 0
# A parameter list ends at a line break to JavaScript's `.`: `t(a<U+2028>b)` is no parametrised `t`.
cp -r "$scratch/ev" "$scratch/param"
sed -i 's|name="does_the_thing"|name="does_the_thing(a\&#x2028;b)"|' "$scratch/param/test-report.xml"
config param 'checks: [2]\ncards:\n  - param/cards/*.op.md\ntest_report: param/test-report.xml\n'; check_both param 1
# A family pattern matches no line break either (check 5).
mkdir -p "$scratch/family"; cp -r "$checks_dir/form-family/." "$scratch/family/"
sed -i 's/row-open-2/row-open-\\u2028a/g; s/row-open-3/row-open-\\u2028b/g' "$scratch/family/form-inventory.json"
config family 'checks: [5]\nforms:\n  - family/*.contract.md\nform_inventory: family/form-inventory.json\n'; check_both family 1
config familyabs "checks: [5]\nforms:\n  - family/*.contract.md\nform_inventory: $(abs "$checks_dir/form-family/form-inventory.json")\n"; check_both familyabs 0
mkdir -p "$scratch/storage"; cp -r "$checks_dir/storage-clean/." "$scratch/storage/"
config storageabs "checks: [4]\ncards:\n  - storage/*.op.md\nstorage_inventory: $(abs "$scratch/storage/storage-inventory.json")\n"; check_both storageabs 0
# The preview reads the form inventory where check 5 reads it (TypeScript alone: the prototype has
# no preview); 1.5.2 drew the screens without it.
if chosen previewabs; then
  total=$((total + 1))
  node "$root/impl/typescript/dist/cli.js" preview "$scratch/familyabs.config.yaml" --out "$scratch/previewabs.html" > "$scratch/previewabs.ts" 2>&1
  grep -q "runtime dump" "$scratch/previewabs.html" || fail previewabs "the preview did not read the form inventory at an absolute path"
fi
# Check 2 credits a variant's inherited steps when `shared` is in the original's evidence, both
# trimmed as JavaScript trims: U+FEFF is white space there.
mkdir -p "$scratch/checkvar/lib"; cp -r "$checks_dir/variant-clean/." "$scratch/checkvar/"; cp "$root"/examples/library/*.op.md "$scratch/checkvar/lib/"
sed -i 's|^  shared: .*|  shared: "src/loans/CheckoutHandler.ts\\ufeff"|' "$scratch/checkvar/cards/library.loan.checkout.on-behalf.op.md"
config checkvar 'checks: [2]\ncards:\n  - checkvar/lib/*.op.md\n  - checkvar/cards/*.op.md\ntest_report: checkvar/test-report.xml\n'; check_both checkvar 0
# The test report is read as UTF-8, as cards are, whatever it declares: Python decoded a report
# declared ISO-8859-1 as Latin-1 and refused one with a byte that is not UTF-8.
cp -r "$scratch/ev" "$scratch/latin1"
sed -i 's|encoding="UTF-8"|encoding="ISO-8859-1"|; s|name="does_the_thing"|name="does_the_thing_é"|' "$scratch/latin1/test-report.xml"
sed -i 's|SampleTests.does_the_thing,|SampleTests.does_the_thing_é,|' "$scratch/latin1/cards/sample.evidence.spanning.op.md"
config latin1 'checks: [2]\ncards:\n  - latin1/cards/*.op.md\ntest_report: latin1/test-report.xml\n'; check_both latin1 0
cp -r "$scratch/ev" "$scratch/badbyte"
sed -i 's|name="does_the_thing"|name="does_the_thing\xe9"|' "$scratch/badbyte/test-report.xml"
config badbyte 'checks: [2]\ncards:\n  - badbyte/cards/*.op.md\ntest_report: badbyte/test-report.xml\n'; check_both badbyte 1
lacks badbyte "report_malformed"; says badbyte "test_not_found"

if [ "${#failed[@]}" -gt 0 ]; then
  echo "${#failed[@]} of $total case(s) failed: ${failed[*]}"
  exit 1
fi
echo "  ok — $total case(s)"
