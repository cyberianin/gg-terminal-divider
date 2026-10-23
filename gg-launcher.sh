#!/usr/bin/env bash
# Stable v1 launcher: resolve the release once, never follow current twice.
_gg_dispatch() {
    local mode=$1 entry=${BASH_SOURCE[0]} link base version
    shift
    while [[ -L $entry ]]; do
        link=$(readlink -- "$entry") || return
        if [[ $link == /* ]]; then entry=$link; else entry=$(dirname -- "$entry")/$link; fi
    done
    base=$(cd -- "$(dirname -- "$entry")" && pwd -P) || return
    if ! IFS= read -r version < "$base/current"; then
        printf 'GG: cannot read installed release pointer\n' >&2
        return 1
    fi
    if [[ ! $version =~ ^version\.[a-zA-Z0-9]{6}$ ]]; then
        printf 'GG: invalid installed release pointer\n' >&2
        return 1
    fi
    if [[ $mode == execute ]]; then
        exec bash "$base/$version/gg" "$@"
    else
        local _gg_public_target=$base/gg
        # shellcheck source=gg
        source "$base/$version/gg" "$@"
    fi
}

if [[ ${BASH_SOURCE[0]} == "$0" ]]; then
    _gg_dispatch execute "$@"
else
    _gg_dispatch source "$@"
fi
