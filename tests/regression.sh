#!/usr/bin/env bash
# Golden files capture the original generator, independently of current HEAD.
set -eu
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
actual=$(mktemp)
trap 'rm -f -- "$actual"' EXIT
count=0
for style in double single heavy dashed dotted ascii; do
    for layout in box inline; do
        for align in left center right; do
            bash "$root/gg" --no-color -w 32 -s "$style" -l "$layout" -a "$align" STATUS > "$actual"
            cmp "$root/tests/golden/$style-$layout-$align.txt" "$actual"
            ((count+=1))
        done
    done
done
printf 'Baseline output comparisons passed: %s\n' "$count"
