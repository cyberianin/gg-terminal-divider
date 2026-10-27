#!/usr/bin/env python3
"""Byte-level Windows PowerShell 5.1 and 7 contract checks."""
import os
import base64
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "golden"
PWSH = shutil.which("pwsh")
WINDOWS_PS = shutil.which("powershell.exe")


def encoded_command(command):
    return ["-EncodedCommand", base64.b64encode(command.encode("utf-16le")).decode("ascii")]


@unittest.skipUnless(sys.platform == "win32" and PWSH, "Windows PowerShell 7 only")
class PowerShellContract(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / "tests")
        self.addCleanup(self.temp.cleanup)
        self.bin = Path(self.temp.name) / "bin"
        self.env = os.environ.copy()
        self.env["GG_BIN_DIR"] = str(self.bin)
        self.env["NO_COLOR"] = "1"
        self.env["PATH"] = str(self.bin) + os.pathsep + self.env["PATH"]
        result = subprocess.run([PWSH, "-NoProfile", "-File", str(ROOT / "install.ps1"),
                                 "-Command", "vv"], env=self.env, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.launcher = self.bin / "vv.ps1"

    def run_gg(self, *arguments, input_bytes=b""):
        return subprocess.run([PWSH, "-NoProfile", "-File", str(self.launcher), *arguments],
                              input=input_bytes, capture_output=True, env=self.env,
                              timeout=15)

    def test_box_fixture(self):
        result = self.run_gg("--box", "--style", "ascii", "--width", "12", "Hi")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.replace(b"\r\n", b"\n"),
                         (FIXTURES / "new-box-ascii.txt").read_bytes())
        expression = ("[Console]::InputEncoding = [Text.UTF8Encoding]::new($false); "
                      "[Console]::In.ReadToEnd() | & '" + str(self.launcher).replace("'", "''") +
                      "' --box --style double --width 12")
        result = subprocess.run([PWSH, "-NoProfile", "-Command", expression],
                                input="a\n\n界é\n".encode(), capture_output=True,
                                env=self.env, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.replace(b"\r\n", b"\n"),
                         (FIXTURES / "new-box-double.txt").read_bytes())

    def test_table_fixture_via_pipeline(self):
        expression = ("[Console]::In.ReadToEnd() | & '" + str(self.launcher).replace("'", "''") +
                      "' --table --style ascii --header A,B,C")
        result = subprocess.run([PWSH, "-NoProfile", "-Command", expression],
                                input=b"x\t\t\n", capture_output=True, env=self.env,
                                timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.replace(b"\r\n", b"\n"),
                         (FIXTURES / "new-table-ascii.txt").read_bytes())
        error = self.run_gg("--table", "--style", "ascii", "--width", "12",
                            "--header", "A,B,C", input_bytes=b"x\t\t\n")
        self.assertEqual(error.returncode, 2)
        self.assertEqual(error.stdout, b"")
        self.assertIn(b"minimum table structure", error.stderr)

    def test_divider_and_reinstall(self):
        result = self.run_gg("--no-color", "--style", "ascii", "--width", "12", "Hi")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.replace(b"\r\n", b"\n"),
                         b"\n============\n     Hi     \n============\n\n")
        before = (self.bin / ".gg-divider-ps" / "current").read_text()
        installed_adapter = self.bin / ".gg-divider-ps" / before.strip() / "gg-ps.ps1"
        self.assertEqual(installed_adapter.read_bytes(), (ROOT / "gg-ps.ps1").read_bytes())
        self.assertTrue(installed_adapter.read_bytes().startswith(b"\xef\xbb\xbf"))
        result = subprocess.run([PWSH, "-NoProfile", "-File", str(ROOT / "install.ps1"),
                                 "-Command", "vv"], env=self.env, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.bin / ".gg-divider-ps" / "current").read_text(), before)
        result = subprocess.run([PWSH, "-NoProfile", "-Command", "vv --box --style ascii --width 12 Hi"],
                                env=self.env, capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(b"Hi", result.stdout)

    def test_divider_needs_no_rust_process(self):
        adapter = Path(self.temp.name) / "gg-ps.ps1"
        shutil.copy2(ROOT / "gg-ps.ps1", adapter)
        self.assertFalse((Path(self.temp.name) / "gg-format.exe").exists())
        for shell in (PWSH, WINDOWS_PS):
            if not shell:
                continue
            command = [shell, "-NoProfile"]
            if shell == WINDOWS_PS:
                command += ["-ExecutionPolicy", "Bypass"]
            result = subprocess.run(command + ["-File", str(adapter), "--no-color",
                                               "--width", "8", "Тест"],
                                    env=self.env, capture_output=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("═".encode(), result.stdout)

    def test_version_reports_installed_formatter(self):
        release = (self.bin / ".gg-divider-ps" / "current").read_text().strip()
        core = self.bin / ".gg-divider-ps" / release / "gg-format.exe"
        direct = subprocess.run([str(core), "--version"], capture_output=True, timeout=15)
        self.assertEqual(direct.returncode, 0, direct.stderr)
        self.assertEqual(direct.stdout, b"gg 1.1.1\n")
        for shell in (PWSH, WINDOWS_PS):
            if not shell:
                continue
            prefix = [shell, "-NoProfile"]
            if shell == WINDOWS_PS:
                prefix += ["-ExecutionPolicy", "Bypass"]
            for argument in ("version", "--version"):
                version = subprocess.run(prefix + ["-File", str(self.launcher), argument],
                                         env=self.env, capture_output=True, timeout=15)
                self.assertEqual(version.returncode, 0, version.stderr)
                self.assertEqual(version.stdout.replace(b"\r\n", b"\n"), direct.stdout)

    def test_default_foreground_and_explicit_colors(self):
        for shell in (PWSH, WINDOWS_PS):
            if not shell:
                continue
            prefix = [shell, "-NoProfile"]
            if shell == WINDOWS_PS:
                prefix += ["-ExecutionPolicy", "Bypass"]
            clean_env = self.env.copy()
            clean_env.pop("GG_COLOR", None)
            clean_env.pop("GG_TEXT_COLOR", None)
            for options, overrides, expected in (
                (["--width", "12", "CAT", "--force-color"], {}, b""),
                (["--box", "--width", "12", "BOX", "--force-color"], {}, b""),
                (["--width", "12", "CAT", "--force-color", "--color", "magenta",
                  "--text-color", "cyan"], {}, b"\x1b[35m"),
                (["--box", "--width", "12", "BOX", "--force-color",
                  "--color", "magenta", "--text-color", "cyan"], {}, b"\x1b[35m"),
                (["--width", "12", "CAT", "--force-color"],
                 {"GG_COLOR": "red", "GG_TEXT_COLOR": "green"}, b"\x1b[31m"),
            ):
                with self.subTest(shell=shell, options=options):
                    env = clean_env | overrides
                    result = subprocess.run(prefix + ["-File", str(self.launcher), *options],
                                            input=b"", env=env, capture_output=True,
                                            timeout=15)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    if expected:
                        self.assertIn(expected, result.stdout)
                        self.assertIn(b"\x1b[36m" if expected == b"\x1b[35m" else
                                      b"\x1b[32m", result.stdout)
                    else:
                        self.assertNotIn(b"\x1b[", result.stdout)

    def test_original_divider_golden_files(self):
        for shell in (PWSH, WINDOWS_PS):
            if not shell:
                continue
            prefix = [shell, "-NoProfile"]
            if shell == WINDOWS_PS:
                prefix += ["-ExecutionPolicy", "Bypass"]
            for style in ("double", "single", "heavy", "dashed", "dotted", "ascii"):
                for layout in ("box", "inline"):
                    for align in ("left", "center", "right"):
                        with self.subTest(shell=shell, style=style, layout=layout, align=align):
                            result = subprocess.run(prefix + ["-File", str(self.launcher),
                                                    "--no-color", "-w", "32", "-s", style,
                                                    "-l", layout, "-a", align, "STATUS"],
                                                    env=self.env, capture_output=True, timeout=15)
                            self.assertEqual(result.returncode, 0, result.stderr)
                            expected = (FIXTURES / f"{style}-{layout}-{align}.txt").read_bytes()
                            self.assertEqual(result.stdout.replace(b"\r\n", b"\n"), expected)

    @unittest.skipUnless(shutil.which("rustc"), "rustc needed for raw stdin probe")
    def test_formatter_stdin_exact_bytes(self):
        adapter = Path(self.temp.name) / "gg-ps.ps1"
        shutil.copy2(ROOT / "gg-ps.ps1", adapter)
        core = Path(self.temp.name) / "gg-format.exe"
        subprocess.run([shutil.which("rustc"), str(ROOT / "tests" / "support" / "stdin_probe.rs"),
                        "-o", str(core)], check=True, capture_output=True, timeout=30)
        for shell in (PWSH, WINDOWS_PS):
            if not shell:
                continue
            prefix = [shell, "-NoProfile"]
            if shell == WINDOWS_PS:
                prefix += ["-ExecutionPolicy", "Bypass"]
            call = "& '" + str(adapter).replace("'", "''") + "' --box X"
            for expression, expected in ((call, b"\n"),
                                         ("'Ж' | " + call, b"d0960d0a\n")):
                with self.subTest(shell=shell, expression=expression):
                    setup = "[Console]::InputEncoding = [Text.UTF8Encoding]::new($true); "
                    result = subprocess.run(prefix + encoded_command(setup + expression),
                                            input=b"", env=self.env, capture_output=True, timeout=15)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(result.stdout.replace(b"\r\n", b"\n"), expected)

    def test_unicode_and_color_bytes_across_shells(self):
        for shell in (PWSH, WINDOWS_PS):
            if not shell:
                continue
            prefix = [shell, "-NoProfile"]
            if shell == WINDOWS_PS:
                prefix += ["-ExecutionPolicy", "Bypass"]
            for style, glyph in (("double", "═"), ("heavy", "━"), ("single", "─")):
                with self.subTest(shell=shell, style=style):
                    result = subprocess.run(prefix + ["-File", str(self.launcher),
                                            "--no-color", "--style", style, "--width", "8",
                                            "Тест"], env=self.env, capture_output=True, timeout=15)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    expected = ("\n" + glyph * 8 + "\n  Тест  \n" + glyph * 8 + "\n\n").encode()
                    self.assertEqual(result.stdout.replace(b"\r\n", b"\n"), expected)
                    self.assertNotIn(b"\x1b[", result.stdout)
            for arguments, colored in (([], False), (["--no-color"], False),
                                       (["--force-color"], False),
                                       (["--force-color", "--color", "red"], True),
                                       (["--force-color", "--color", "red", "--no-color"], False)):
                with self.subTest(shell=shell, arguments=arguments):
                    result = subprocess.run(prefix + ["-File", str(self.launcher),
                                            "--box", "--width", "20",
                                            *arguments], input=b"", env=self.env, capture_output=True,
                                            timeout=15)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertIn("╔".encode(), result.stdout)
                    self.assertEqual(b"\x1b[" in result.stdout, colored)
            for arguments, colored in (([], False), (["--force-color"], False),
                                       (["--force-color", "--color", "red"], True),
                                       (["--force-color", "--color", "red", "--no-color"], False)):
                with self.subTest(shell=shell, divider=arguments):
                    result = subprocess.run(prefix + ["-File", str(self.launcher),
                                            "--width", "8", "Тест", *arguments],
                                            env=self.env, capture_output=True, timeout=15)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertIn("═".encode(), result.stdout)
                    self.assertEqual(b"\x1b[" in result.stdout, colored)
            with (Path(self.temp.name) / (Path(shell).stem + ".out")).open("wb") as output:
                result = subprocess.run(prefix + ["-File", str(self.launcher),
                                        "--width", "8", "Тест"], env=self.env,
                                        stdout=output, stderr=subprocess.PIPE, timeout=15)
            self.assertEqual(result.returncode, 0, result.stderr)
            saved = (Path(self.temp.name) / (Path(shell).stem + ".out")).read_bytes()
            self.assertIn("═".encode(), saved)
            self.assertNotIn(b"\x1b[", saved)
            expression = ("[Console]::InputEncoding = New-Object Text.UTF8Encoding -ArgumentList $false; "
                          "[Console]::In.ReadToEnd() | & '" +
                          str(self.launcher).replace("'", "''") +
                          "' --table --style double --header A,B --width 20")
            result = subprocess.run(prefix + encoded_command(expression),
                                    input="Ж\t界\n".encode(), capture_output=True,
                                    env=self.env, timeout=15)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Ж".encode(), result.stdout)
            self.assertIn("界".encode(), result.stdout)
            self.assertIn("╔".encode(), result.stdout)
            self.assertNotIn(b"\x1b[", result.stdout)

    def test_real_console_host_vt_and_restoration(self):
        for shell in (PWSH, WINDOWS_PS):
            if not shell:
                continue
            with self.subTest(shell=shell):
                report = Path(self.temp.name) / ("console-" + Path(shell).stem + ".json")
                startup = subprocess.STARTUPINFO()
                startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startup.wShowWindow = 0
                command = [shell, "-NoProfile"]
                if shell == WINDOWS_PS:
                    command += ["-ExecutionPolicy", "Bypass"]
                command += ["-File", str(ROOT / "tests" / "console_host.ps1"),
                            "-Launcher", str(self.launcher), "-Result", str(report)]
                process = subprocess.run(command, env=self.env, timeout=20,
                                         creationflags=subprocess.CREATE_NEW_CONSOLE,
                                         startupinfo=startup)
                self.assertEqual(process.returncode, 0)
                data = json.loads(report.read_text(encoding="utf-8"))
                self.assertEqual(data["after"], data["initial"])
                self.assertTrue(data["divider"])
                self.assertTrue(data["box"])
                self.assertFalse(data["rawEscape"])
                self.assertFalse(data["fileHasConsoleMode"])
                self.assertTrue(data["defaultDividerForeground"])
                self.assertTrue(data["defaultBoxForeground"])

    def test_conflict_and_activation(self):
        expression = ("Set-Alias vv Get-Date; & '" + str(ROOT / "install.ps1").replace("'", "''") +
                      "' -Command vv")
        result = subprocess.run([PWSH, "-NoProfile", "-Command", expression],
                                capture_output=True, env=self.env, timeout=15)
        self.assertNotEqual(result.returncode, 0)
        expression = (". '" + str(self.bin / ".gg-divider-ps" / "activate.ps1").replace("'", "''") +
                      "' -Name vv; vv --box --style ascii --width 12 Hi")
        result = subprocess.run([PWSH, "-NoProfile", "-Command", expression],
                                capture_output=True, env=self.env, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(b"Hi", result.stdout)

    def test_owned_alias_allows_update_but_foreign_alias_blocks_it(self):
        activate = self.bin / ".gg-divider-ps" / "activate.ps1"
        installer = ROOT / "install.ps1"
        pointer = self.bin / ".gg-divider-ps" / "current"
        source = Path(self.temp.name) / "update-source"
        source.mkdir()
        for name in ("install.ps1", "gg.ps1", "gg-ps.ps1", "gg-activate.ps1"):
            shutil.copy2(ROOT / name, source / name)
        updated_core = source / "dist" / "windows-x64" / "gg-format.exe"
        updated_core.parent.mkdir(parents=True)
        updated_core.write_bytes((ROOT / "dist" / "windows-x64" / "gg-format.exe").read_bytes()
                                 + b"GG 1.1.1 alias update test")
        for shell in (PWSH, WINDOWS_PS):
            if not shell:
                continue
            prefix = [shell, "-NoProfile"]
            if shell == WINDOWS_PS:
                prefix += ["-ExecutionPolicy", "Bypass"]
            expression = ("& '" + str(installer).replace("'", "''") +
                          "' -Command gg; . '" + str(activate).replace("'", "''") +
                          "' -Name gg; $before = [IO.File]::ReadAllText('" +
                          str(pointer).replace("'", "''") +
                          "').Trim(); & '" + str(installer).replace("'", "''") +
                          "' -Command gg; if ([IO.File]::ReadAllText('" +
                          str(pointer).replace("'", "''") +
                          "').Trim() -cne $before) { throw 'reinstall changed release' }; & '" +
                          str(source / "install.ps1").replace("'", "''") +
                          "' -Command gg; if ([IO.File]::ReadAllText('" +
                          str(pointer).replace("'", "''") +
                          "').Trim() -ceq $before) { throw 'update did not switch release' }; " +
                          "gg --box --style ascii --width 12 Hi; & '" +
                          str(installer).replace("'", "''") +
                          "' -CheckNames")
            result = subprocess.run(prefix + encoded_command(expression), env=self.env,
                                    capture_output=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(b"Installed gg", result.stdout)
            self.assertIn(b"gg AVAILABLE", result.stdout)
            self.assertIn(b"Hi", result.stdout)
            release = pointer.read_text().strip()
            self.assertEqual((pointer.parent / release / "gg-format.exe").read_bytes(),
                             updated_core.read_bytes())
            expression = ("Set-Alias gg Get-Date; & '" +
                          str(installer).replace("'", "''") + "' -Command gg")
            result = subprocess.run(prefix + encoded_command(expression), env=self.env,
                                    capture_output=True, timeout=15)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(b"Alias", result.stderr)
        launcher = self.bin / "gg.ps1"
        launcher.write_bytes(b"foreign launcher\n")
        for shell in (PWSH, WINDOWS_PS):
            if not shell:
                continue
            prefix = [shell, "-NoProfile"]
            if shell == WINDOWS_PS:
                prefix += ["-ExecutionPolicy", "Bypass"]
            expression = ("Set-Alias gg '" + str(launcher).replace("'", "''") +
                          "'; & '" + str(installer).replace("'", "''") + "' -Command gg")
            result = subprocess.run(prefix + encoded_command(expression), env=self.env,
                                    capture_output=True, timeout=15)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(b"foreign destination", result.stderr)

    @unittest.skipUnless(WINDOWS_PS, "Windows PowerShell 5.1 unavailable")
    def test_windows_powershell_51(self):
        install = subprocess.run([WINDOWS_PS, "-NoProfile", "-ExecutionPolicy", "Bypass",
                                  "-File", str(ROOT / "install.ps1"), "-Command", "vv"],
                                 env=self.env, capture_output=True, timeout=15)
        self.assertEqual(install.returncode, 0, install.stderr)
        release = (self.bin / ".gg-divider-ps" / "current").read_text().strip()
        self.assertEqual((self.bin / ".gg-divider-ps" / release / "gg-ps.ps1").read_bytes(),
                         (ROOT / "gg-ps.ps1").read_bytes())
        result = subprocess.run([WINDOWS_PS, "-NoProfile", "-ExecutionPolicy", "Bypass",
                                 "-File", str(self.launcher), "--box", "--style", "double",
                                 "--width", "12", "界"], env=self.env, capture_output=True,
                                timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("界".encode(), result.stdout)
        expression = ("'x'+[char]9+'y' | & '" + str(self.launcher).replace("'", "''") +
                      "' --table --style ascii --header A,B")
        result = subprocess.run([WINDOWS_PS, "-NoProfile", "-ExecutionPolicy", "Bypass",
                                 *encoded_command(expression)], env=self.env, capture_output=True,
                                timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(b"| x | y |", result.stdout)
        expression = ("@('界\té\t', '', 'x\t\t') "
                      "| & '" + str(self.launcher).replace("'", "''") +
                      "' --table --style ascii --header A,B,C --width 20; exit $LASTEXITCODE")
        result = subprocess.run([WINDOWS_PS, "-NoProfile", "-ExecutionPolicy", "Bypass",
                                 *encoded_command(expression)], env=self.env, capture_output=True,
                                timeout=15)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(result.stdout, b"")
        self.assertIn(b"columns", result.stderr)
        expression = ("@('界\té\t', 'x\t\t') "
                      "| & '" + str(self.launcher).replace("'", "''") +
                      "' --table --style ascii --header A,B,C --width 20; exit $LASTEXITCODE")
        result = subprocess.run([WINDOWS_PS, "-NoProfile", "-ExecutionPolicy", "Bypass",
                                 *encoded_command(expression)], env=self.env, capture_output=True,
                                timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("界".encode(), result.stdout)
        self.assertIn("e\u0301".encode(), result.stdout)
        self.assertIn(b"| x", result.stdout)
        expression = ("'four' | & '" + str(self.launcher).replace("'", "''") +
                      "' --box --max-bytes 3; exit $LASTEXITCODE")
        result = subprocess.run([WINDOWS_PS, "-NoProfile", "-ExecutionPolicy", "Bypass",
                                 *encoded_command(expression)], env=self.env, capture_output=True,
                                timeout=15)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(result.stdout, b"")
        self.assertIn(b"max-bytes", result.stderr)
        expression = ("@('top', '', '') | & '" + str(self.launcher).replace("'", "''") +
                      "' --box --style ascii --width 8; exit $LASTEXITCODE")
        result = subprocess.run([WINDOWS_PS, "-NoProfile", "-ExecutionPolicy", "Bypass",
                                 *encoded_command(expression)], env=self.env, capture_output=True,
                                timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.replace(b"\r\n", b"\n"),
                         b"+------+\n| top  |\n|      |\n|      |\n+------+\n")
        expression = ("1..10000 | ForEach-Object { 'x' * 1000 } | & '" +
                      str(self.launcher).replace("'", "''") +
                      "' --table --max-bytes 1024; exit $LASTEXITCODE")
        result = subprocess.run([WINDOWS_PS, "-NoProfile", "-ExecutionPolicy", "Bypass",
                                 *encoded_command(expression)], env=self.env, capture_output=True,
                                timeout=30)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(result.stdout, b"")
        self.assertIn(b"max-bytes", result.stderr)

    def test_release_pins_formatter(self):
        home = self.bin / ".gg-divider-ps"
        before = (home / "current").read_text().strip()
        original = home / before / "gg-format.exe"
        self.assertEqual(original.read_bytes(), (ROOT / "dist/windows-x64/gg-format.exe").read_bytes())
        ready = Path(self.temp.name) / "reader.ready"
        go = Path(self.temp.name) / "reader.go"
        observed = Path(self.temp.name) / "reader.hash"
        old_adapter = home / before / "gg-ps.ps1"
        gate = ("    [IO.File]::WriteAllText('" + str(ready).replace("'", "''") + "', '')\n"
                "    while (-not (Test-Path -LiteralPath '" + str(go).replace("'", "''") +
                "')) { Start-Sleep -Milliseconds 10 }\n"
                "    [IO.File]::WriteAllText('" + str(observed).replace("'", "''") +
                "', (Get-FileHash -LiteralPath $core -Algorithm SHA256).Hash)\n")
        prefix, mode = old_adapter.read_text(encoding="utf-8").split("if ($mode) {", 1)
        marker = "    if (-not (Test-Path -LiteralPath $core -PathType Leaf)) {"
        old_adapter.write_text(prefix + "if ($mode) {" + mode.replace(marker, gate + marker, 1),
                               encoding="utf-8")
        reader = subprocess.Popen([PWSH, "-NoProfile", "-File", str(self.launcher),
                                   "--box", "--style", "ascii", "Hi"], env=self.env,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.addCleanup(lambda: reader.kill() if reader.poll() is None else None)
        deadline = time.monotonic() + 10
        while not ready.exists() and time.monotonic() < deadline:
            time.sleep(0.01)
        self.assertTrue(ready.exists(), "reader did not pin the old release")
        with tempfile.TemporaryDirectory(dir=ROOT / "tests") as source_dir:
            source = Path(source_dir)
            shutil.copy2(ROOT / "install.ps1", source / "install.ps1")
            shutil.copy2(ROOT / "gg.ps1", source / "gg.ps1")
            shutil.copy2(ROOT / "gg-ps.ps1", source / "gg-ps.ps1")
            shutil.copy2(ROOT / "gg-activate.ps1", source / "gg-activate.ps1")
            binary = source / "dist/windows-x64/gg-format.exe"
            binary.parent.mkdir(parents=True)
            binary.write_bytes(original.read_bytes() + b"GG release test marker")
            result = subprocess.run([PWSH, "-NoProfile", "-File", str(source / "install.ps1"),
                                     "-Command", "vv"], env=self.env, capture_output=True,
                                    timeout=15)
            self.assertEqual(result.returncode, 0, result.stderr)
            after = (home / "current").read_text().strip()
            self.assertNotEqual(before, after)
            self.assertEqual(original.read_bytes(), (ROOT / "dist/windows-x64/gg-format.exe").read_bytes())
            self.assertEqual((home / after / "gg-format.exe").read_bytes(), binary.read_bytes())
            go.touch()
            output, error = reader.communicate(timeout=15)
            self.assertEqual(reader.returncode, 0, error)
            self.assertIn(b"Hi", output)
            self.assertEqual(observed.read_text().strip(),
                             __import__("hashlib").sha256(original.read_bytes()).hexdigest().upper())
            for release in (before, after):
                result = subprocess.run([PWSH, "-NoProfile", "-File",
                                         str(home / release / "gg-ps.ps1"),
                                         "--box", "--style", "ascii", "Hi"],
                                        env=self.env, capture_output=True, timeout=15)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(b"Hi", result.stdout)


if __name__ == "__main__":
    unittest.main()
