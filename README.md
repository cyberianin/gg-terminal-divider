# GG — Gorgeous Gaps

**Beautiful terminal separators, frames, and TSV tables for Bash and PowerShell.** Version **1.1.0 target**. [Русская версия](README.ru.md).

GG prints a divider or a titled section in a terminal. The ordinary Bash divider retains its shell-only fast path. The new `--box` and `--table` modes use the same Rust binary in Bash and PowerShell; packaged builds require neither Rust nor Python on the user's machine.

```text
════════════════════════════════════════
             SYSTEM HEALTH
════════════════════════════════════════

━━━━━━━  DOCKER STATUS  ━━━━━━━
```

Terminal output can use named ANSI colors, 256 colors, or `#RRGGBB` truecolor. Colors turn off when output is redirected, unless `--force-color` is used.

## Requirements

Bash and a UTF-8 locale on Linux/Git Bash, or PowerShell 7+ on Windows. Windows PowerShell 5.1 is separately tested, including UTF-8 text pipeline input. `tput` is optional for Bash. Automatic width is capped at 120.

The source tree includes `dist/linux-x64/gg-format` (static musl) and `dist/windows-x64/gg-format.exe` (MSVC). To rebuild, use `cargo build --release` for the host target, or `cargo build --release --target x86_64-unknown-linux-musl` with a compatible linker. Releases must package the binary in the appropriate `dist/` directory before installation. Windows ARM64, Linux ARM64, and macOS are **NOT VERIFIED**.

## Frames and tables

```bash
gg --box "WARNING"
printf 'CPU: 12%%\nRAM: 1.2 GiB\n' | gg --box --title "SYSTEM HEALTH"
printf 'NAME\tSTATUS\nnginx\tRUNNING\n' | gg --table --header-first-row
docker ps --format '{{.Names}}\t{{.Status}}' | gg --table --header NAME,STATUS
```

`--box` accepts positional text or multiline stdin. `--table` accepts TSV on stdin only. Empty cells, including trailing fields, are preserved. Use `--header A,B` or `--header-first-row`, never both. A header is optional, and without one the first row is data. Column counts must agree. LF and CRLF are accepted. Structured PowerShell objects are not converted into GG tables; send text.

Both modes accept `--style single|double|heavy|ascii|dashed|dotted`, `--title`, `--width 8..500`, `--align left|center|right`, `--color`, `--text-color`, `--no-color`, `--force-color`, and `--overflow wrap|truncate|error`. Dashed and dotted use single-line corners and vertical sides. Box defaults to wrap; table defaults to truncate. Truncation uses `…`. A width too small for borders and one cell per column returns exit code 2 with no partial frame. `--max-bytes` defaults to 8 MiB; table `--max-rows` defaults to 10000 physical TSV rows, including a first-row header. Input is bounded before decoding and rendering. ANSI and terminal controls in input are removed; output color is generated only by GG. Unicode width follows grapheme clusters and the bundled Unicode width tables; individual terminal emoji and ambiguous-width policies can differ.

The full table is buffered up to these limits to calculate column widths. Output is written after validation. A broken output pipe returns nonzero. Piped output is not automatically colored. `--force-color` enables color even when redirected; `--no-color` wins.

## PowerShell installation and activation

```powershell
& .\install.ps1 -Command gg
$env:PATH = "$HOME\.local\bin;$env:PATH"
gg --box "WARNING"
@('NAME`tSTATUS', 'nginx`tRUNNING') | gg --table --header-first-row
```

PowerShell resolves aliases and functions before external scripts. If direct `gg` does not resolve `gg.ps1` on your PATH, explicitly activate the chosen short name in the current session with `. "$HOME\.local\bin\.gg-divider-ps\activate.ps1" -Name gg`. Use `-Command vv` for the alternative. `-CheckNames` reports conflicts; the installer refuses to overwrite a command, alias, function, or foreign file. The installer never edits the PowerShell profile. Add the PATH or activation line to your own profile only if desired. `-Uninstall -Command gg` removes only its owned launcher. Each invocation pins one `version.*` directory containing `gg-ps.ps1` and `gg-format.exe`; updates atomically switch `current` and retain old releases for existing readers.

PowerShell 5.1 sends text pipeline values through an explicit UTF-8 .NET stream. When starting `pwsh -File gg.ps1` from a non-PowerShell host with raw redirected Unicode bytes, that host's console input encoding may corrupt the data before the script sees it; use a PowerShell text pipeline with UTF-8 host input for this case. This direct raw-byte path is **NOT VERIFIED** across console encodings.

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

Download [gg](gg), [gg-names.sh](gg-names.sh), [gg-launcher.sh](gg-launcher.sh), [install.sh](install.sh), [LICENSE](LICENSE), [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md), and the matching Rust binary under `dist/linux-x64/` or `dist/windows-x64/`. Preserve the `dist/` layout and license notices, review the files, then run the installer as above. This method needs no Git.

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

The legacy divider aligns by character count and can misalign emoji and wide CJK characters. Box/table use grapheme display width, with terminal-dependent ambiguity for some emoji. Custom divider patterns should use narrow characters. Unicode styles need terminal and font support. macOS remains **NOT VERIFIED**.

## Tests and timing

Run `bash tests/test.sh` for installation safety and rendering checks, `bash tests/regression.sh` for 36 independent golden output comparisons, and `python3 tests/linux_edges.py` for Linux PTY, native links, permissions, concurrency, interrupted copies, SIGKILL before/after the release commit, reader consistency during updates, and legacy migration. Golden files were captured from the fixed original commit documented in [tests/golden/README.md](tests/golden/README.md); tests never regenerate them from current HEAD.

`bash tests/ci.sh` runs syntax checks, ShellCheck, legacy tests, and new formatter contracts; it requires Python 3 and ShellCheck for development only. Windows contracts run through `python tests/powershell_contract.py`. The Linux GitHub Actions workflow runs the entrypoint with ShellCheck 0.10.0 in an isolated container. Version 0.11.0 previously crashed internally on the test script in this environment.

Run `bash tests/benchmark.sh 100` for three samples of 100 executable/function calls. Set `GG_BENCH_ENTRY="$HOME/.local/bin/.gg-divider/gg"` to include the installed launcher. The benchmark explicitly launches Bash for the executable, redirects output and uses ASCII, width 80, and title `STATUS`. It reports wall, user and system seconds; timings depend on the host and do not predict interactive terminal latency. See [VALIDATION.md](VALIDATION.md) for measured results and verification limits.

`bash tests/benchmark_compare.sh 200` compares the historical divider with the working tree on the same filesystem. `python3 tests/benchmark_modes.py` measures Rust, the saved Python prototype, and the shell adapter on box and 10/1,000/10,000-row TSV data. These benchmarks discard stdout; they do not measure terminal drawing.

## License

GG is licensed under the standard [MIT License](LICENSE), copyright (c) 2026 cyberianin. The MIT License permits use, modification, distribution, and sale of copies, subject to retaining its copyright and permission notices. This includes use in commercial organizations and production infrastructure. Rust dependencies retain their own licenses; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

Issues and pull requests are welcome. Contact the maintainer through [GitHub Issues](https://github.com/cyberianin/gg-terminal-divider/issues).
