#!/usr/bin/env bash
# Source this installer to include the calling Bash's aliases and functions.
_gg_install() (
    local root bin name=gg explicit=0 interactive=1 check=0 remove=0 reason candidate formatter dist
    root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P) || return
    case $(uname -s) in
        MINGW*|MSYS*|CYGWIN*) formatter=gg-format.exe; dist=windows-x64 ;;
        *) formatter=gg-format; dist=linux-x64 ;;
    esac
    source "$root/gg-names.sh" || return
    bin=${GG_BIN_DIR:-$HOME/.local/bin}
    while (($#)); do
        case $1 in
            --command) (($# >= 2)) || { printf 'Missing command name\n' >&2; return 2; }; name=$2; explicit=1; shift 2 ;;
            --check-names) check=1; shift ;;
            --non-interactive) interactive=0; shift ;;
            --uninstall) remove=1; shift ;;
            *) printf 'Unknown installer option: %s\n' "$1" >&2; return 2 ;;
        esac
    done
    [[ -t 0 && -t 1 ]] || interactive=0
    # Normalize without creating anything during a check or conflict.
    [[ $bin == /* ]] || bin=$PWD/$bin
    local target=$bin/.gg-divider/gg
    if ((check)); then
        for candidate in gg vv xx bn bb cv; do
            if reason=$(_gg_probe "$candidate" "$target"); then
                printf '%s AVAILABLE: %s\n' "$candidate" "$reason"
            else
                printf '%s CONFLICT: %s\n' "$candidate" "$reason"
            fi
        done
        printf 'Scope: current Bash only; other shell configurations may differ.\n'
        return 0
    fi
    _gg_valid_name "$name" || { printf 'Unsupported command: %s (cc is reserved)\n' "$name" >&2; return 2; }
    if ((remove)); then
        if _gg_owned_link "$bin/$name" "$target"; then
            rm -- "$bin/$name"
        else
            printf 'Refusing to remove a foreign object: %s\n' "$bin/$name" >&2; return 1
        fi
        return
    fi
    while ! reason=$(_gg_probe "$name" "$target"); do
        printf '%s CONFLICT: %s\n' "$name" "$reason" >&2
        ((interactive)) || return 1
        if ((!explicit)) && reason=$(_gg_probe vv "$target"); then
            printf 'vv AVAILABLE: %s\n' "$reason"
            printf 'Choose a name (gg vv xx bn bb cv), or Enter to cancel [suggested: vv]: '
        else
            printf 'Choose a name (gg vv xx bn bb cv), or Enter to cancel: '
        fi
        IFS= read -r name || return 1
        _gg_valid_name "$name" || { printf 'Cancelled or unsupported name\n' >&2; return 1; }
        explicit=1
    done
    if [[ -e $bin/$name || -L $bin/$name ]]; then
        _gg_owned_link "$bin/$name" "$target" || { printf 'Foreign destination: %s\n' "$bin/$name" >&2; return 1; }
    fi
    # A private directory is owned only when its marker and regular files match policy.
    if [[ -e $bin/.gg-divider || -L $bin/.gg-divider ]]; then
        [[ ! -L $bin/.gg-divider && -f $bin/.gg-divider/owner && ! -L $bin/.gg-divider/owner && $(cat "$bin/.gg-divider/owner") == gg-terminal-divider-v1 ]] || return 1
        for candidate in gg gg-names.sh gg-format gg-format.exe; do
            [[ ! -L $bin/.gg-divider/$candidate && ! -d $bin/.gg-divider/$candidate ]] || return 1
        done
    fi
    mkdir -p -- "$bin/.gg-divider" || return
    printf 'gg-terminal-divider-v1\n' > "$bin/.gg-divider/owner" || return
    local stage release current='' home=$bin/.gg-divider
    if [[ -e $home/current || -L $home/current ]]; then
        [[ -f $home/current && ! -L $home/current ]] || return 1
        IFS= read -r current < "$home/current" || return
        [[ $current =~ ^version\.[a-zA-Z0-9]{6}$ && -d $home/$current && ! -L $home/$current ]] || return 1
        for candidate in gg gg-names.sh; do
            [[ -f $home/$current/$candidate && ! -L $home/$current/$candidate ]] || return 1
        done
        # The launcher is a stable protocol, not part of an update transaction.
        if [[ -f $target ]] && ! cmp -s -- "$root/gg-launcher.sh" "$target"; then
            # A legacy installation may have been interrupted after publishing
            # current but before replacing the old main file. Its policy stays
            # untouched until the launcher is installed below.
            [[ -f $home/gg-names.sh ]] || return 1
        fi
    fi
    stage=$(mktemp -d "$bin/.gg-divider/.update.XXXXXX") || return
    trap 'rm -rf -- "$stage"' EXIT
    cp -- "$root/gg" "$stage/gg" || return
    cp -- "$root/gg-names.sh" "$stage/gg-names.sh" || return
    cp -- "$root/dist/$dist/$formatter" "$stage/$formatter" || return
    chmod +x -- "$stage/gg" || return
    chmod +x -- "$stage/$formatter" || return
    if [[ -z $current ]] || ! cmp -s -- "$stage/gg" "$home/$current/gg" ||
       ! cmp -s -- "$stage/gg-names.sh" "$home/$current/gg-names.sh" ||
       ! cmp -s -- "$stage/$formatter" "$home/$current/$formatter"; then
        # Publish an immutable directory first. A crash here leaves an unused
        # release, while the old pointer remains fully usable.
        release=$(mktemp -d "$home/version.XXXXXX") || return
        mv -- "$stage/gg" "$stage/gg-names.sh" "$stage/$formatter" "$release/" || return
        printf '%s\n' "${release##*/}" > "$stage/current" || return
        # One same-filesystem rename commits BOTH versioned files together.
        mv -fT -- "$stage/current" "$home/current" || return
    fi
    if ! cmp -s -- "$root/gg-launcher.sh" "$target"; then
        cp -- "$root/gg-launcher.sh" "$stage/launcher" || return
        chmod +x -- "$stage/launcher" || return
        mv -fT -- "$stage/launcher" "$target" || return
    fi
    if ! _gg_owned_link "$bin/$name" "$target"; then
        ln -sT -- "$target" "$bin/$name" || return
        # MSYS may emulate symlinks with a copy. Replace only that exact copy
        # with a thin wrapper so future updates still use the shared generator.
        if [[ ! -L $bin/$name ]]; then
            cmp -s -- "$target" "$bin/$name" || return 1
            rm -- "$bin/$name" || return
            (set -o noclobber; _gg_wrapper "$target" > "$bin/$name") || return
            chmod +x -- "$bin/$name" || return
        fi
    fi
    printf 'Installed %s -> %s\nEnsure %s is in PATH. Shell startup files were not changed.\n' "$name" "$target" "$bin"
)

_gg_install "$@"
