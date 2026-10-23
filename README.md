# GG — Gorgeous Gaps

**Beautiful, customizable terminal separators for Bash.** Version **1.0.0**. [Русская версия](README.ru.md).

GG prints a divider or a titled section in a terminal with no mandatory third-party dependencies. The default installation uses one executable and a short symlink (a thin wrapper on MSYS systems that emulate symlinks). An explicitly enabled Bash function avoids starting a Bash process on each call.

```text
════════════════════════════════════════
             SYSTEM HEALTH
════════════════════════════════════════

━━━━━━━  DOCKER STATUS  ━━━━━━━
```

Terminal output can use named ANSI colors, 256 colors, or `#RRGGBB` truecolor. Colors turn off when output is redirected, unless `--force-color` is used.

## Requirements

Bash and a UTF-8 locale for Unicode styles. `tput` is optional. The default width uses `COLUMNS`, then `tput cols` on a terminal, then 80; it reserves two columns and caps automatic width at 120.

## Install from GitHub

```bash
git clone git@github.com:cyberianin/gg-terminal-divider.git
cd gg-terminal-divider
source ./install.sh
```

Without an SSH key, use `git clone https://github.com/cyberianin/gg-terminal-divider.git` instead. The installer never edits `.bashrc`. If needed, add `export PATH="$HOME/.local/bin:$PATH"` yourself. Sourcing the installer lets it inspect aliases and functions in the calling Bash; installation runs in a subshell. Executing `bash install.sh` sees only definitions available to that child process.

### Short command names and conflicts

The brand remains **GG — Gorgeous Gaps**, and the repository remains `gg-terminal-divider`. The primary command is `gg`; the recommended alternative is `vv` (Visual Divider). No two-character name is universally free:

| Name | Known conflicts |
| --- | --- |
| `gg` | Oh My Zsh git plugin |
| `vv` | Terminal image viewers |
| `xx` | xxcmd |
| `bn` | Binary Ninja CLI, Bonsai |
| `bb` | Babashka |
| `cv` | CiviCRM CLI and other projects |
| `cc` | C compiler interface; rejected by GG |

The installer checks `gg` first. On an interactive conflict it suggests `vv` only after checking it, then asks for an explicit name. If both are occupied, choose another supported name manually. It never silently selects an alternative or overwrites a foreign command. Checks include aliases, functions, builtins, shell keywords and executables throughout PATH, using Bash `type`, `command -v` and `alias`.

```bash
source ./install.sh --check-names
source ./install.sh --command vv
vv "STATUS"
# CI: never prompts, returns nonzero on conflict
bash install.sh --command vv --non-interactive
```

`--check-names` prints `AVAILABLE` or `CONFLICT` with a reason for each supported name, without installing. `AVAILABLE` means no conflict was detected in the current Bash environment. It cannot guarantee availability in another shell or in configuration files not loaded into that process (including Zsh plugins). Recheck from the Bash session where you will use GG. Non-terminal input/output also disables prompts.

`GG_BIN_DIR` overrides `$HOME/.local/bin`. Each selected name points to a stable launcher at `.gg-divider/gg`. The launcher reads `.gg-divider/current` once and uses the selected immutable `version.*` directory. Reinstalling identical files reuses the current release. After `git pull`, rerun the installer with the same name to update. Multiple selected names can coexist. Remove one with:

```bash
source ./install.sh --command vv --uninstall
```

Removal accepts only GG's exact symlink or wrapper; it leaves foreign objects and the shared files intact so other selected names keep working. Installation expects a user-owned directory; do not run it against a directory concurrently modified by untrusted users.

On Linux, link creation refuses a destination that appears after the availability check, including a directory. Updates prepare both files in a new version directory, then atomically rename one small `current` pointer file on the same filesystem. The pointer is a regular file so MSYS does not need native symlink support for version selection. Readers pin one version for both the generator and its policy; a concurrent update cannot mix them. Old versions and releases left by interrupted updates are retained so existing readers remain valid. Legacy installations migrate without changing their old policy file. The installer uses GNU-compatible `ln -T` and `mv -T`; macOS installation is not verified. This provides atomic visibility on Linux, not a guarantee of durable writes after power loss.

Maintenance rules: never prune `version.*` directories merely because they are not current; a reader may have selected one without opening its files yet. Future cleanup must coordinate with all readers. The v1 launcher protocol is maintained separately: `current` contains one `version.XXXXXX` basename, the release contains `gg` and `gg-names.sh`, and source mode passes the stable command path as `_gg_public_target`. Generator updates must remain compatible with the installed launcher; changing this contract requires an explicit protocol migration.

### Optional Bash function mode

Enable this mode explicitly in each desired shell, or add this line to your own Bash configuration:

```bash
source "$HOME/.local/bin/.gg-divider/gg" --function gg
gg --help
```

For the alternative use `source "$HOME/.local/bin/.gg-divider/gg" --function vv`, then `vv "STATUS"`. Public functions are created only after checking for conflicts, including aliases even when alias expansion is enabled. A foreign alias or function causes a nonzero return and is preserved. GG's own function can be reloaded. Sourcing without `--function NAME` fails; it never implicitly installs `gg`. Remove a function from the current session with `unset -f gg` (or the selected name). The executable and function call the same internal generator.

## Install by copying code

Download [gg](gg), [gg-names.sh](gg-names.sh), [gg-launcher.sh](gg-launcher.sh) and [install.sh](install.sh) into one directory, review them, then run the installer as above. This method needs no Git.

## Usage

```bash
gg
gg "DOCKER STATUS"
gg --char '*' "SYSTEM"
gg --char '=-' --color red "WARNING"
gg --style heavy --color '#A855F7' "SERVER HEALTH"
gg --layout inline --text-color yellow "DATABASE"
gg --width 100 --align right "FINISHED"
gg --no-color "PLAIN OUTPUT"
gg --help
```

Positional words are joined with spaces. `--text` is an alternative to positional text; do not use both. Use `--` before text beginning with `-`. Long value options also accept `--option=value`.

### Options and short aliases

| Long option | Short alias | Value or effect |
| --- | --- | --- |
| `--text` | `-t` | Title text |
| `--style` | `-s` | `double`, `single`, `heavy`, `dashed`, `dotted`, `ascii` |
| `--char` | `-c` | Repeating pattern, 1–16 narrow printable characters; overrides style glyph |
| `--color` | — | Separator color |
| `--text-color` | — | Title color |
| `--width` | `-w` | 8–500 columns |
| `--align` | `-a` | `left`, `center`, `right` |
| `--layout` | `-l` | `box` or `inline` |
| `--no-color` | — | Disable ANSI colors |
| `--force-color` | — | Keep colors when stdout is redirected; `--no-color` still wins |
| `--help` | `-h` | Show help |

Short flags are aliases for the long options shown here. The installed command name does not change these options. `--` ends option parsing.

Colors: `black`, `red`, `green`, `yellow`, `blue`, `magenta`, `cyan`, `white`, `gray`, `bright-red`, `bright-green`, `bright-yellow`, `bright-blue`, `bright-magenta`, `bright-cyan`, `bright-white`, `#RRGGBB`, or an index `0`–`255`. `none` and `default` disable one color.

### Defaults

| Variable | Default | Matching option |
| --- | --- | --- |
| `GG_STYLE` | `double` | `--style` |
| `GG_COLOR` | `magenta` | `--color` |
| `GG_TEXT_COLOR` | `cyan` | `--text-color` |
| `GG_WIDTH` | Automatic | `--width` |
| `GG_ALIGN` | `center` | `--align` |
| `GG_LAYOUT` | `box` | `--layout` |

Set variables before sourcing the file, for example:

```bash
export GG_STYLE=heavy GG_COLOR='#A855F7' GG_TEXT_COLOR=white
export GG_LAYOUT=inline GG_ALIGN=center GG_WIDTH=80
source "$HOME/.local/bin/.gg-divider/gg" --function gg
```

Command options override environment defaults. `NO_COLOR` disables colors unless `--force-color` is used.

## Example script

```bash
gg "SYSTEM HEALTH"
uptime
free -h
gg -l inline -s heavy "DOCKER CONTAINERS"
docker ps
gg "DONE"
```

## Limits

Alignment counts characters rather than terminal display cells. Emoji and wide CJK characters can misalign. Custom patterns should use narrow characters. Unicode styles need terminal and font support. Compatibility with macOS Bash and other terminal setups has not been verified.

## Tests and timing

Run `bash tests/test.sh` for installation safety and rendering checks, `bash tests/regression.sh` for 36 independent golden output comparisons, and `python3 tests/linux_edges.py` for Linux PTY, native links, permissions, concurrency, interrupted copies, SIGKILL before/after the release commit, reader consistency during updates, and legacy migration. Golden files were captured from the fixed original commit documented in [tests/golden/README.md](tests/golden/README.md); tests never regenerate them from current HEAD.

`bash tests/ci.sh` runs syntax checks, ShellCheck and all tests; it requires Python 3 and ShellCheck for development only. The Linux GitHub Actions workflow runs this entrypoint with ShellCheck 0.10.0 in an isolated container. Version 0.11.0 currently crashes internally on the test script in this environment.

Run `bash tests/benchmark.sh 100` for three samples of 100 executable/function calls. Set `GG_BENCH_ENTRY="$HOME/.local/bin/.gg-divider/gg"` to include the installed launcher. The benchmark explicitly launches Bash for the executable, redirects output and uses ASCII, width 80, and title `STATUS`. It reports wall, user and system seconds; timings depend on the host and do not predict interactive terminal latency. See [VALIDATION.md](VALIDATION.md) for measured results and verification limits.

## Contributing and license

Issues and pull requests are welcome. See [LICENSE](LICENSE). Contact the maintainer through [GitHub Issues](https://github.com/cyberianin/gg-terminal-divider/issues).
