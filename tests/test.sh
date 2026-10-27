#!/usr/bin/env bash
set -eu
test_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
tmp=$(mktemp -d)
trap 'rm -rf -- "$tmp"' EXIT
export GG_BIN_DIR=$tmp/bin
mkdir -p "$GG_BIN_DIR"
export PATH=$GG_BIN_DIR:$PATH
source "$test_root/gg-names.sh"
pass() { printf 'PASS %s\n' "$1"; }
fail() { printf 'FAIL %s\n' "$1" >&2; exit 1; }
_gg_probe vv >/dev/null || fail free
bash "$test_root/install.sh" --command vv --non-interactive >/dev/null
_gg_owned_link "$GG_BIN_DIR/vv" "$GG_BIN_DIR/.gg-divider/gg" || fail link
expected=$(bash "$test_root/gg" --no-color --width 24 STATUS)
[[ $(vv --no-color --width 24 STATUS) == "$expected" ]] || fail output
installed_release=$(cat "$GG_BIN_DIR/.gg-divider/current")
case $(uname -s) in MINGW*|MSYS*|CYGWIN*) formatter=gg-format.exe ;; *) formatter=gg-format ;; esac
installed_version=$("$GG_BIN_DIR/.gg-divider/$installed_release/$formatter" --version)
[[ $installed_version == 'gg 1.1.1' && $(vv version) == "$installed_version" &&
   $(vv --version) == "$installed_version" ]] || fail version
pass 'free name and shared output'
bash "$test_root/install.sh" --command vv --non-interactive >/dev/null
release_before=$(cat "$GG_BIN_DIR/.gg-divider/current")
bash "$test_root/install.sh" --command vv --non-interactive >/dev/null
[[ $(cat "$GG_BIN_DIR/.gg-divider/current") == "$release_before" ]] || fail release-idempotency
pass 'idempotent installation'
# shellcheck source=gg-launcher.sh
source "$GG_BIN_DIR/.gg-divider/gg" --function vv
[[ $(vv --no-color --width 24 STATUS) == "$expected" ]] || fail installed-source
unset -f vv
pass 'installed launcher function mode'
alias xx='printf foreign'
if source "$test_root/install.sh" --command xx --non-interactive >/dev/null 2>&1; then fail alias; fi
[[ $(alias xx) == *foreign* ]] || fail alias-preservation
pass 'alias conflict'
bn() { printf foreign; }
if source "$test_root/install.sh" --command bn --non-interactive >/dev/null 2>&1; then fail function; fi
[[ $(bn) == foreign ]] || fail function-preservation
pass 'function conflict'
printf '#!/usr/bin/env bash\nprintf foreign\n' > "$GG_BIN_DIR/bb"
chmod +x "$GG_BIN_DIR/bb"
if bash "$test_root/install.sh" --command bb --non-interactive </dev/null >/dev/null 2>&1; then fail executable; fi
[[ $(bb) == foreign ]] || fail executable-preservation
pass 'non-interactive executable conflict'
if bash "$test_root/install.sh" --command cc --non-interactive >/dev/null 2>&1; then fail cc; fi
pass 'reserved cc'
if source "$test_root/gg" >/dev/null 2>&1; then fail implicit-source; fi
source "$test_root/gg" --function cv
[[ $(cv --no-color --width 24 STATUS) == "$expected" ]] || fail source-output
source "$test_root/gg" --function cv
pass 'explicit function mode and reload'
shopt -s expand_aliases
alias xx='echo FOREIGN'
if source "$test_root/gg" --function xx >/dev/null 2>&1; then fail source-alias; fi
[[ $(alias xx) == *FOREIGN* ]] || fail source-alias-preservation
pass 'source alias safety with alias expansion enabled'
if source "$test_root/gg" --function bn >/dev/null 2>&1; then fail source-function; fi
pass 'source function conflict'
bash "$test_root/install.sh" --command vv --uninstall >/dev/null
[[ ! -e $GG_BIN_DIR/vv && -f $GG_BIN_DIR/.gg-divider/gg ]] || fail uninstall
if bash "$test_root/install.sh" --command bb --uninstall >/dev/null 2>&1; then fail foreign-uninstall; fi
[[ $(bb) == foreign ]] || fail foreign-uninstall-preservation
pass 'safe removal of own links only'
report=$(source "$test_root/install.sh" --check-names)
[[ $report == *'xx CONFLICT'* && $report == *'vv AVAILABLE'* ]] || fail report
pass 'availability report'
mkdir -p "$tmp/shadow"
printf '#!/usr/bin/env bash\nexit 0\n' > "$tmp/shadow/vv"
chmod +x "$tmp/shadow/vv"
bash "$test_root/install.sh" --command vv --non-interactive >/dev/null
if PATH="$PATH:$tmp/shadow" bash "$test_root/install.sh" --command vv --non-interactive >/dev/null 2>&1; then fail shadowed; fi
pass 'shadowed PATH executable conflict'
mkdir "$GG_BIN_DIR/xx"
unalias xx
if bash "$test_root/install.sh" --command xx --non-interactive >/dev/null 2>&1; then fail directory; fi
[[ -d $GG_BIN_DIR/xx ]] || fail directory-preservation
pass 'foreign destination preserved'
rm "$GG_BIN_DIR/vv"
printf 'foreign\n' > "$tmp/foreign-target"
ln -s "$tmp/foreign-target" "$GG_BIN_DIR/vv"
if bash "$test_root/install.sh" --command vv --uninstall >/dev/null 2>&1; then fail foreign-link; fi
pass 'foreign link removal rejected'
# Regression coverage for rendering and option validation.
for style in double single heavy dashed dotted ascii; do
    for layout in box inline; do
        for align in left center right; do
            result=$(bash "$test_root/gg" -w 24 -s "$style" -l "$layout" -a "$align" --no-color STATUS)
            [[ $result == *STATUS* ]] || fail rendering
            while IFS= read -r line; do
                [[ -z $line || ${#line} == 24 ]] || fail width
            done <<< "$result"
        done
    done
done
for args in '--width 7' '--width 501' '--style bad' '--align bad' '--layout bad' '--color bad' '--text'; do
    read -r -a bad_args <<< "$args"
    if bash "$test_root/gg" "${bad_args[@]}" >/dev/null 2>&1; then fail validation; fi
done
[[ $(bash "$test_root/gg" --width 8 --char ab --no-color) == $'\nabababab' ]] || fail pattern
[[ $(bash "$test_root/gg" --width 24 --color red --force-color STATUS) == *$'\033[31m'* ]] || fail color
default_output=$(env -u GG_COLOR -u GG_TEXT_COLOR bash "$test_root/gg" --width 24 --force-color STATUS)
[[ $default_output != *$'\033['* ]] || fail default-foreground
explicit_output=$(GG_COLOR=red GG_TEXT_COLOR=green bash "$test_root/gg" --width 24 --force-color STATUS)
[[ $explicit_output == *$'\033[31m'* && $explicit_output == *$'\033[32m'* ]] || fail environment-colors
override_output=$(GG_COLOR=red GG_TEXT_COLOR=green bash "$test_root/gg" --width 24 --force-color --color blue --text-color yellow STATUS)
[[ $override_output == *$'\033[34m'* && $override_output == *$'\033[33m'* ]] || fail explicit-colors
pass 'rendering, colors, patterns and invalid options'
