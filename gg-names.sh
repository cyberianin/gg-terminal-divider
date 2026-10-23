#!/usr/bin/env bash
# Shared name policy; never defines a public command on load.
_gg_valid_name() {
    case $1 in gg|vv|xx|bn|bb|cv) return 0 ;; *) return 1 ;; esac
}

_gg_owned_link() {
    if [[ -L $1 ]]; then
        [[ $(readlink -- "$1") == "$2" ]]
    elif [[ -f $1 ]]; then
        [[ $(cat -- "$1") == "$(_gg_wrapper "$2")" ]]
    else
        return 1
    fi
}

_gg_wrapper() {
    printf '#!/usr/bin/env bash\n# gg-terminal-divider wrapper v1\nexec bash %q "$@"\n' "$1"
}

_gg_probe() {
    local name=$1 owned=${2:-} kind path definition expected
    _gg_valid_name "$name" || { printf 'unsupported name (cc is reserved for C compilers)'; return 1; }
    if alias "$name" >/dev/null 2>&1; then
        alias "$name"
        return 1
    fi
    kind=$(type -t -- "$name" 2>/dev/null) || kind=''
    if [[ $kind == function ]]; then
        definition=$(declare -f "$name")
        expected=$(printf '%s () \n{ \n    _gg_generate "$@"\n}' "$name")
        if [[ $definition != "$expected" ]]; then
            printf 'Bash function'; return 1
        fi
    elif [[ -n $kind && $kind != file ]]; then
        printf 'shell %s' "$kind"; return 1
    fi
    if [[ $kind == file ]]; then
        path=$(command -v -- "$name")
        if [[ -z $owned ]] || ! _gg_owned_link "$path" "$owned"; then
            printf 'resolved executable (PATH or Bash hash): %s' "$path"; return 1
        fi
    fi
    # Inspect every PATH entry, including shadowed executables.
    local -a dirs
    local IFS=:
    read -r -a dirs <<< "${PATH}:"
    for path in "${dirs[@]}"; do
        path=${path:-.}/$name
        if [[ -f $path && -x $path ]]; then
            if [[ -n $owned ]] && _gg_owned_link "$path" "$owned"; then continue; fi
            printf 'PATH executable: %s' "$path"; return 1
        fi
    done
    command -v -- "$name" >/dev/null 2>&1 || :
    type -a -- "$name" >/dev/null 2>&1 || :
    printf 'no conflict detected in this Bash environment'
}

_gg_enable_function() {
    local name=$1 reason target
    target=${2:-}
    if [[ -z $target ]]; then
        target=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)/gg
    fi
    if ! reason=$(_gg_probe "$name" "$target"); then
        printf 'GG: %s: CONFLICT: %s\n' "$name" "$reason" >&2
        return 1
    fi
    eval "function $name { _gg_generate \"\$@\"; }"
}
