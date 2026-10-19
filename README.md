# GG — Gorgeous Gaps

**Beautiful, customizable terminal separators for Bash.** Version **1.0.0**. [Русская версия](README.ru.md).

GG prints a divider or a titled section in a terminal. It is one Bash file with no mandatory third-party dependencies. Run it as a CLI, or source it as a function so repeated calls in an interactive SSH session do not start a new Bash process.

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
mkdir -p "$HOME/.local/bin"
cp gg "$HOME/.local/bin/gg"
chmod +x "$HOME/.local/bin/gg"
```

Without an SSH key, use `git clone https://github.com/cyberianin/gg-terminal-divider.git` instead. If needed, add `export PATH="$HOME/.local/bin:$PATH"` to `~/.bashrc` for CLI use. To use GG as a Bash function, add the source line once:

```bash
grep -Fqx 'source "$HOME/.local/bin/gg"' "$HOME/.bashrc" || printf '\nsource "$HOME/.local/bin/gg"\n' >> "$HOME/.bashrc"
source "$HOME/.bashrc"
gg --help
```

If you already have a `gg` function, sourcing this file replaces its definition in the current shell. To update, run `git pull` in the clone and copy `gg` again.

## Install by copying code

Open [gg](gg), copy its entire contents, and save them as `~/.local/bin/gg` after `mkdir -p "$HOME/.local/bin"`. Then run `chmod +x "$HOME/.local/bin/gg"`. Add the PATH or source line from the GitHub installation steps above. This method needs no Git. Review the script before running it.

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

There are no additional command aliases. Short flags are aliases for the long options shown here. `--` ends option parsing.

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
source "$HOME/.local/bin/gg"
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

## Contributing and license

Issues and pull requests are welcome. See [LICENSE](LICENSE). Contact: `211379639+cyberianin@users.noreply.github.com`.
