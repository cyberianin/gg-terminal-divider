# Validation

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
