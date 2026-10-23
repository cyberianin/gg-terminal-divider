#!/usr/bin/env bash
set -eu
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
entry=${GG_BENCH_ENTRY:-$root/gg}
count=${1:-100}
[[ $count =~ ^[1-9][0-9]*$ ]] || exit 2
# shellcheck source=gg
source "$entry" --function cv
printf 'Bash %s; %s calls per sample; output redirected; width 80, ASCII, STATUS\n' "$BASH_VERSION" "$count"
TIMEFORMAT='total real=%3R user=%3U sys=%3S seconds'
for sample in 1 2 3; do
    printf 'executable sample %s: ' "$sample" >&2
    time { for ((i=0; i<count; i++)); do bash "$entry" --no-color --style ascii --width 80 STATUS >/dev/null; done; }
    printf 'function sample %s: ' "$sample" >&2
    time { for ((i=0; i<count; i++)); do cv --no-color --style ascii --width 80 STATUS >/dev/null; done; }
done
