#!/usr/bin/env python3
"""Windows PowerShell 7 contract checks against the shared fixtures."""
import os
import base64
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
        result = subprocess.run([PWSH, "-NoProfile", "-File", str(ROOT / "install.ps1"),
                                 "-Command", "vv"], env=self.env, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.bin / ".gg-divider-ps" / "current").read_text(), before)
        result = subprocess.run([PWSH, "-NoProfile", "-Command", "vv --box --style ascii --width 12 Hi"],
                                env=self.env, capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(b"Hi", result.stdout)

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

    @unittest.skipUnless(WINDOWS_PS, "Windows PowerShell 5.1 unavailable")
    def test_windows_powershell_51(self):
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
        old_adapter.write_text(old_adapter.read_text(encoding="utf-8").replace(
            "    if (-not (Test-Path -LiteralPath $core -PathType Leaf)) {", gate +
            "    if (-not (Test-Path -LiteralPath $core -PathType Leaf)) {", 1),
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
