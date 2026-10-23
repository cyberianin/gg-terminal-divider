# Validation

## GG 1.1.0 Rust formatter validation (2026-10-24)

The shared `gg-format` library and CLI are built with Rust 1.98.0, `unicode-width`, and `unicode-segmentation`. The distributed binaries in this working tree are Windows x64 MSVC (200,192 bytes) and Linux x64 musl (466,432 bytes). The uncompressed platform payloads, including shell scripts and the binary, are 219,916 and 485,495 bytes respectively. The Python prototype (15,022 bytes of source) is retained only for comparison.

| Environment | Confirmed checks |
| --- | --- |
| WSL2 Ubuntu 26.04, Bash 5.3.9 | Rust binary ran; complete `bash tests/ci.sh` passed with ShellCheck 0.10.0: Bash syntax, 16 Bash groups, all 36 unchanged v1 golden fixtures, 20/20 Linux edge tests, 9/9 new formatter contracts. |
| Windows Git Bash/MSYS, Bash 5.2.37 | 16 Bash groups, 36 v1 golden fixtures, 6/9 new contracts (Linux PTY, closed-pipe, and infinite-input tests skipped), direct Windows Rust box/table dispatch passed. |
| Windows PowerShell 7.6.5 and Windows PowerShell 5.1.19041.7802 | 6/6 Windows contract groups passed, including shared ASCII/Unicode golden fixtures, PS 5.1 UTF-8/TSV/blank lines/exit code, large input early rejection, and a reader paused across release update. |
| Rust 1.98.0 | `cargo fmt --check`, `cargo test --locked` (5 tests), `cargo clippy --locked --all-targets -- -D warnings`, both release builds passed. |

The PowerShell 5.1 adapter uses a .NET `Process` for pipeline input. It writes UTF-8 incrementally, while stdout and stderr start independent asynchronous drains before stdin writing. Tests passed for trailing blank lines and a 10 MB generated pipeline rejected by the 1 KiB Rust input limit. An additional 10 MB versus 100 MB generated-input probe returned exit code 2 in 1.48 versus 6.99 seconds, with PowerShell process peak working set 119.17 versus 134.59 MiB; the difference did not track the additional 90 MB of logical input. This is evidence for streaming in the tested path, not a universal memory ceiling. On Linux, an infinite input producer was stopped by `--max-bytes=1024` without waiting for EOF. A direct `pwsh -File gg.ps1` launched from a host with a non-UTF-8 console input encoding did not preserve Unicode redirected stdin; use a PowerShell text pipeline with UTF-8 host input for this case. PowerShell-native text pipelines and Unicode positional arguments passed.

The Windows update test starts a launcher reader, pauses it after the old release was selected, publishes a new release containing a byte-distinct but runnable binary, and then resumes the reader. Its recorded binary hash matches the old release; a new invocation selects the new one. The Linux test likewise confirms old and new releases hold distinct runnable binaries. `File.Replace` publishes the `current` pointer atomically on the tested Windows filesystem, and readers retain their selected `version.*`. Power-loss durability, hostile mutation of private install folders, and behavior on other filesystems are **NOT VERIFIED**.

### Benchmarks

Wall times are Python `perf_counter` around separate processes: first invocation and median of five later invocations. RSS comes from a separate `/usr/bin/time` run on WSL and `psutil` process peak working set on Windows. Output was discarded, so these are **not** terminal-rendering measurements. Each row used the same input and options for Rust and the Python prototype. Shell-adapter costs include shell startup and are listed separately.

| Platform and input | Rust first / repeat ms | Rust peak KiB | Python first / repeat ms | Python peak KiB | Shell adapter first / repeat ms |
| --- | ---: | ---: | ---: | ---: | ---: |
| WSL box, 2 lines | 11.64 / 18.11 | 392 | 146.53 / 129.43 | 13,844 | Bash 54.30 / 49.37 |
| WSL table, 10 rows | 17.00 / 17.35 | 392 | 150.48 / 130.62 | 13,976 | Bash 46.19 / 50.10 |
| WSL table, 1,000 rows | 38.58 / 33.12 | 392 | 189.76 / 191.41 | 14,392 | Bash 59.06 / 61.20 |
| WSL table, 10,000 rows | 163.15 / 176.26 | 2,316 | 730.63 / 715.51 | 20,076 | Bash 209.98 / 253.64 |
| Windows box, 2 lines | 19.14 / 10.82 | 3,716 | 155.08 / 160.28 | 21,592 | PS7 1057.90 / 943.63 |
| Windows table, 10 rows | 16.33 / 11.59 | 3,564 | 168.91 / 172.81 | 21,644 | PS7 1075.89 / 1032.21 |
| Windows table, 1,000 rows | 30.67 / 29.43 | 3,872 | 206.23 / 211.08 | 21,824 | PS7 1290.83 / 1032.75 |
| Windows table, 10,000 rows | 208.00 / 199.91 | 7,132 | 960.87 / 802.04 | 21,736 | PS7 2383.06 / 2374.78 |

The ordinary Bash divider comparison was rerun with both scripts on the same WSL-mounted filesystem, 200 calls in each of three samples. Median per call: old executable 16.10 ms, changed executable 16.07 ms; old function 0.885 ms, changed function 0.855 ms. The earlier comparison placed the baseline in native Linux `/tmp` and the changed script on `/mnt/c`, causing a misleading apparent executable regression. No Rust process is started for the ordinary Bash divider.

The full local Linux CI entrypoint passed using ShellCheck 0.10.0 from the pinned cached image. Hosted GitHub Actions jobs and an interactive Windows Terminal PTY have not run in this working tree: **NOT VERIFIED**. The workflow is configured to build/test both targets. Windows ARM64, Linux ARM64, and macOS: **NOT VERIFIED**. No commit, tag, push, or release was created.

Measured on 2026-10-20, Windows with Git Bash 5.2.37(1)-release.

`bash tests/benchmark.sh 100`: three samples, 100 calls each, output redirected
to `/dev/null`, ASCII style, width 80, title `STATUS`. The executable path is
launched explicitly with `bash`; shell startup and process creation are included.
Function loading is outside the timed loop. Installation and conflict checks are
outside both loops. These are per-call invocation measurements, not terminal
rendering latency measurements.

| Sample | Executable wall seconds | Function wall seconds |
| --- | ---: | ---: |
| 1 | 8.214 | 0.119 |
| 2 | 7.756 | 0.120 |
| 3 | 7.742 | 0.125 |

Median per call: executable 77.56 ms; function 1.20 ms. The function was faster
in this environment. These measurements do not establish performance on Linux,
macOS, or other hosts. The script also reports user and system CPU time.

Automated coverage is in `tests/test.sh`: free names, shared output, reinstall,
alias/function/PATH conflicts, non-interactive failure, reserved `cc`, explicit
function activation and reload, alias expansion safety, availability reports,
shadowed executables, foreign destinations, safe removal, and rendering options.

Results: all 15 test groups passed. `bash -n` passed for the generator,
name policy, installer and all three test/benchmark scripts. `git diff --check`
passed. The initial comparison against original Git history passed all 36
style/layout/alignment cases. These expectations are now independent golden
files captured from commit `4c20cc36b7692137d727169e76574a023976cd8d`.

No pre-existing test suite was present. The initial Windows run had no
ShellCheck. Windows/MSYS wrapper behavior is covered. Checks describe only the
Bash process running them, not unloaded shell configuration files.

## Linux follow-up, 2026-10-20

WSL2, Ubuntu 26.04, Bash 5.3.9(1)-release, unprivileged user. Temporary installer
destinations were on the Linux filesystem, exercising real Unix symlinks.

`bash tests/ci.sh` passed locally in WSL with a ShellCheck 0.10.0 container:

- Bash syntax checks for every shell script.
- ShellCheck `-x` with no findings and no disabled diagnostics.
- All 15 original test groups.
- All 36 byte-for-byte golden output comparisons, including trailing newlines.
- All 13 Linux edge tests: native shared links and selective removal, widths
  8/500 and exact title fit, dangling foreign link, check-only side effects,
  permission denial, Bash hash conflicts, file/directory races at link creation,
  interrupted copy, concurrent installations, and three real PTY interactions
  (checked alternative, both names occupied, cancellation).

The new tests exposed and verified fixes for ignored Bash hash entries,
`ln` treating a newly appearing directory as a destination directory, and
overwriting the installed generator during a failed copy. The first fix staged
both files before replacing them separately. The transactional release update
described below supersedes that implementation.

The Linux workflow is saved in `.github/workflows/linux.yml` and its entrypoint
was run locally. A hosted GitHub Actions run is **NOT VERIFIED**: these changes
have not been pushed. No repository refs were changed.

ShellCheck 0.11.0 crashed internally with `Non-exhaustive patterns in function
checkCmd` on `tests/test.sh`. Version 0.10.0 successfully checked every script.
Official Docker images were downloaded; no system packages were installed.

Same benchmark parameters as above, WSL samples:

| Sample | Executable wall seconds | Function wall seconds |
| --- | ---: | ---: |
| 1 | 1.359 | 0.091 |
| 2 | 1.354 | 0.087 |
| 3 | 1.379 | 0.083 |

Median per call: executable 13.59 ms; function 0.87 ms. Sources were read from
the mounted Windows project directory; these results are environment-specific.

## Transactional release update, 2026-10-20

The stable `gg-launcher.sh` is installed at `.gg-divider/gg`. The installer first
prepares both runtime files in a fresh `version.*` directory. It commits the
release with a single same-filesystem rename of a regular `current` pointer
file. A regular pointer file also works with MSYS's emulated public symlinks.
The launcher reads the pointer once, then uses that exact version directory for
both files. Old directories remain available to in-flight readers; interrupted
updates may leave unused directories. Identical reinstalls reuse the current
version. Legacy migration leaves its original policy file unchanged and replaces
the old entrypoint only after a complete version has been published.

Verification adds an installed-launcher function-mode check (16 core groups
total) and four Linux edge checks (17 total): actual SIGKILL immediately before
and after the pointer rename, source paused between generator and policy loading
while another process updates, and migration from the previous layout. Both
SIGKILL cases also verify that a subsequent reinstall succeeds. The versioned
test generator and policy reject mismatched release markers.

Linux atomic visibility and reader consistency are verified. Power-loss
durability, filesystem corruption, and hostile concurrent modification of the
private directory are **NOT VERIFIED**. The stable launcher protocol itself is
not version-switched; changing that protocol requires a separate migration.

Final results: the full local Linux CI passed (Bash syntax, ShellCheck 0.10.0,
16 core groups, 36 golden comparisons, 17 Linux edge tests). Git Bash/MSYS also
passed the 16 core groups and 36 golden comparisons. `git diff --check` passed.

Installed-launcher benchmark, same parameters, 100 calls per sample; function
activation is outside the timed loop:

| Sample | Installed executable wall seconds | Function wall seconds |
| --- | ---: | ---: |
| 1 | 2.120 | 0.086 |
| 2 | 2.084 | 0.074 |
| 3 | 2.076 | 0.104 |

Median per call: installed executable 20.84 ms; function 0.86 ms. This includes
the stable launcher and its exec of the pinned generator on the executable
path; it is distinct from the earlier direct-generator measurement.

Maintenance contract follow-up: README now explicitly prohibits pruning old
releases without reader coordination and documents the independent v1 launcher
contract. Two added Linux tests pause a reader after release selection but before
its first file open across update/uninstall, and verify that updating both runtime
files preserves the installed launcher's contents and inode while CLI and source
mode use the new generator. Full local CI passed: ShellCheck 0.10.0, Bash syntax,
16 core groups, 36 golden comparisons and all 19 Linux edges. `git diff --check`
also passed. Hosted GitHub Actions remains unrun.
