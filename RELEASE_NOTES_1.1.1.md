# GG — Gorgeous Gaps 1.1.1

GG 1.1.1 fixes Windows PowerShell 5.1 compatibility and makes the default colors readable across terminal themes. Bash, Windows PowerShell 5.1, and PowerShell 7+ retain the existing divider, frame, and TSV table commands.

`gg version` and `gg --version` report the version of the selected installed formatter.

## Fixes

- PowerShell 5.1 now reads Unicode divider glyphs correctly from the BOM-marked adapter. Interactive Windows stdout and stderr use `WriteConsoleW`; redirected output stays UTF-8.
- Console Host color is used only after VT capability is confirmed through the Console API. Plain output remains readable without VT support. Positional `--box` sends EOF to Rust without a BOM or extra newline.
- Reinstallation and update accept GG's active alias when it resolves to the verified owned launcher. Foreign aliases, functions, commands, and files still block installation.
- Borders and text now default to the terminal foreground (`GG_COLOR=default`, `GG_TEXT_COLOR=default`) in Bash, PowerShell, and the Rust formatter. User colors and `--color`/`--text-color` still take precedence. `--force-color` preserves requested ANSI colors in redirected output; `--no-color` takes priority.

## Artifacts and verification

- Windows x64 MSVC `gg-format.exe`: SHA-256 `5aa9736bf2fea139b3ebd16fc9026a4e3c56aba546e9ca3c3303088ebc77a323`.
- Linux x64 musl `gg-format`: SHA-256 `56adef138dc39505a5ce05684fc2a6264aa308e62786fb21aabba5613e89654f`.
- Windows PowerShell contract suite: 14 tests passed, including 36 golden fixtures on each shell. Rust: 5 tests passed. WSL Bash: 16 groups, 36 golden fixtures, 20 Linux edge checks, and 9 formatter checks passed.

The Windows x64 ZIP includes the PowerShell installer, launcher, adapter, activation script, formatter, README files, and license notices. The Linux x64 tarball includes the Bash installer, launcher, generator, name policy, formatter, README files, and license notices. Both archives were extracted and installed in isolated test directories. Verify downloads with the attached `SHA256SUMS.txt`.

The new `--box` and `--table` features were introduced in the 1.1.0 code, which is committed on `main`; they are not new features of this patch. At preparation time, the latest published GitHub Release was v1.0.0. Additional limits and test details are in [VALIDATION.md](https://github.com/cyberianin/gg-terminal-divider/blob/v1.1.1/VALIDATION.md).
