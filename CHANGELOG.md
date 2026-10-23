# Changelog

All notable changes to GG — Gorgeous Gaps are documented in this file.

This project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html) and the [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) format.

## [Unreleased]

## [1.0.0] - 2026-10-20

### Added

- Initial public release of GG, a lightweight Bash terminal divider utility.
- Configurable border styles, custom characters, widths, title alignment, and layouts.
- Named ANSI colors, 256-color palettes, and 24-bit RGB support.
- Automatic terminal-width detection and color handling for redirected output.
- Configurable defaults through environment variables.
- Short command names with conflict detection and explicit selection.
- Interactive and non-interactive installation modes.
- Optional Bash-function mode for low-overhead execution.
- Safe installation, reinstallation, migration, and selective uninstallation.
- Versioned runtime directories with atomic release-pointer switching.
- Stable launcher protocol with release-consistent generator and policy loading.
- Independent golden regression fixtures and automated Linux CI.
- Documentation in English and Russian.

### Fixed

- Bash command-hash conflicts during installation.
- Unsafe symlink creation when a destination changes type during installation.
- Possible generator corruption after interrupted file copying.
- Mixed-version runtime loading during concurrent updates.
- Release-reader consistency during updates and uninstallation.

### Verified

- 16 core test groups.
- 36 byte-for-byte golden regression comparisons.
- 19 Linux edge-case tests, including SIGKILL and concurrent update scenarios.
- Bash syntax validation and ShellCheck 0.10.0.
- Windows Git Bash/MSYS and WSL2 Linux testing.

### Known Limitations

- Terminal display width is not fully Unicode-cell-aware.
- macOS compatibility is not verified.
- Power-loss durability and hostile modification of private installation directories are not guaranteed.
- ShellCheck 0.11.0 encounters an internal analyzer error in the tested environment.
