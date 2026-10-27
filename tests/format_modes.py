#!/usr/bin/env python3
"""Independent byte fixtures and behavior checks for the opt-in modes."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
GOLDEN = ROOT / "tests" / "golden"
GG = ROOT / "gg"
BASH = os.environ.get("GG_TEST_BASH", "bash")


def bash_path(path):
    if sys.platform == "win32":
        return subprocess.check_output(["cygpath", "-u", str(path)], text=True).strip()
    return str(path)


def invoke(*args, data=b"", env=None, executable=GG):
    merged = os.environ.copy()
    merged["NO_COLOR"] = "1"
    if env:
        merged.update(env)
    return subprocess.run([BASH, bash_path(executable), *args], input=data,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          env=merged, timeout=15)


class FormatModes(unittest.TestCase):
    def test_golden(self):
        cases = [
            ("new-box-ascii.txt", ("--box", "--style", "ascii", "--width", "12", "Hi"), b""),
            ("new-box-double.txt", ("--box", "--style", "double", "--width", "12"),
             "a\n\n界é\n".encode()),
            ("new-table-ascii.txt", ("--table", "--style", "ascii", "--header", "A,B,C"),
             b"x\t\t\n"),
        ]
        for fixture, args, data in cases:
            with self.subTest(fixture=fixture):
                result = invoke(*args, data=data)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, (GOLDEN / fixture).read_bytes())

    def test_styles_and_width(self):
        for style in ("single", "double", "heavy", "ascii", "dashed", "dotted"):
            for mode, data in (("--box", b"one\ntwo\n"), ("--table", b"a\tb\n1\t2\n")):
                with self.subTest(style=style, mode=mode):
                    result = invoke(mode, "--style", style, "--width", "20", data=data)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertNotIn(b"\x1b", result.stdout)
                    self.assertTrue(result.stdout.endswith(b"\n"))
                    for line in result.stdout.decode().splitlines():
                        self.assertLessEqual(len(line), 20)

    def test_box_sources_and_overflow(self):
        result = invoke("--box", "--width", "8", "--overflow", "wrap", "abcdefgh")
        self.assertEqual(result.returncode, 0)
        self.assertIn("abcd".encode(), result.stdout)
        self.assertIn("efgh".encode(), result.stdout)
        result = invoke("--box", "--width", "8", "--overflow", "truncate", "abcdefgh")
        self.assertIn("abc…".encode(), result.stdout)
        result = invoke("--box", "--width", "8", "--overflow", "error", "abcdefgh")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, b"")
        result = invoke("--box", "text", data=b"pipe\n")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b"positional text or stdin", result.stderr)
        self.assertEqual(result.stdout, b"")

    def test_table_input_and_limits(self):
        result = invoke("--table", "--header-first-row", data=b"A\tB\r\nx\t\r\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn(b"\r", result.stdout)
        for args, data, diagnostic in [
            (("--table",), b"a\tb\nx\n", b"row 2"),
            (("--table", "--header", "A"), b"x\ty\n", b"header"),
            (("--table", "--header", "A", "--header-first-row"), b"x\n", b"mutually"),
            (("--table", "--max-rows", "1"), b"x\ny\n", b"max-rows"),
            (("--table", "--max-bytes", "3"), b"long", b"max-bytes"),
            (("--table", "--width", "8"), b"a\tb\tc\n", b"minimum"),
        ]:
            with self.subTest(args=args):
                result = invoke(*args, data=data)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, b"")
                self.assertIn(diagnostic, result.stderr)

    def test_unicode_and_controls(self):
        result = invoke("--table", "--style", "ascii", "--width", "16",
                        "--overflow", "wrap", data="界\té\n".encode())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("界".encode(), result.stdout)
        self.assertIn("é".encode(), result.stdout)
        result = invoke("--table", "--style", "ascii",
                        data=b"\x1b]0;changed\x07x\t\x1b[2Jdanger\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn(b"\x1b", result.stdout)
        self.assertNotIn(b"changed", result.stdout)
        self.assertIn(b"danger", result.stdout)
        result = invoke("--box", "--force-color", "--color", "red", "hi")
        self.assertIn(b"\x1b[31m", result.stdout)
        clean = {"GG_COLOR": "", "GG_TEXT_COLOR": ""}
        result = invoke("--box", "--force-color", "hi", env=clean)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn(b"\x1b[", result.stdout)
        result = invoke("--table", "--force-color", "--header", "A", data=b"x\n", env=clean)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn(b"\x1b[", result.stdout)
        result = invoke("--box", "--force-color", "--color", "blue", "--text-color", "yellow",
                        "hi", env={"GG_COLOR": "red", "GG_TEXT_COLOR": "green"})
        self.assertIn(b"\x1b[34m", result.stdout)
        self.assertIn(b"\x1b[33m", result.stdout)
        self.assertNotIn(b"\x1b[31m", result.stdout)
        result = invoke("--box", "--force-color", "--no-color", "hi")
        self.assertNotIn(b"\x1b", result.stdout)

    def test_installed_executable_and_function(self):
        with tempfile.TemporaryDirectory() as directory:
            env = os.environ.copy()
            bin_dir = Path(directory) / "bin"
            env["GG_BIN_DIR"] = bash_path(bin_dir)
            env["PATH"] = str(bin_dir) + os.pathsep + env["PATH"]
            bin_dir.mkdir()
            install = subprocess.run([BASH, bash_path(ROOT / "install.sh"), "--command", "vv",
                                      "--non-interactive"], env=env, capture_output=True)
            self.assertEqual(install.returncode, 0, install.stderr)
            result = invoke("--box", "--style", "ascii", "Hi",
                            env={"PATH": env["PATH"]}, executable=bin_dir / "vv")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(b"Hi", result.stdout)
            script = 'source "$GG_BIN_DIR/.gg-divider/gg" --function vv; vv --table --header A,B --style ascii'
            result = subprocess.run([BASH, "-c", script], input=b"x\ty\n", env=env,
                                    capture_output=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(b"x", result.stdout)

    @unittest.skipUnless(sys.platform.startswith("linux"), "Linux PTY only")
    def test_pty_does_not_wait_for_box_stdin(self):
        import pty
        import select
        import time
        master, slave = pty.openpty()
        try:
            proc = subprocess.Popen([BASH, str(GG), "--box", "--no-color", "Hi"],
                                    stdin=slave, stdout=slave, stderr=slave)
            os.close(slave)
            deadline = time.monotonic() + 5
            while proc.poll() is None and time.monotonic() < deadline:
                time.sleep(0.02)
            self.assertEqual(proc.poll(), 0)
            ready, _, _ = select.select([master], [], [], 1)
            self.assertTrue(ready)
            self.assertIn(b"Hi", os.read(master, 4096))
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait()
            os.close(master)

    @unittest.skipUnless(sys.platform.startswith("linux"), "Linux pipe only")
    def test_closed_output_pipe(self):
        process = subprocess.Popen([BASH, str(GG), "--box", "--style", "ascii",
                                    "--width", "120"], stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        process.stdin.write(("x" * 100 + "\n").encode() * 10000)
        process.stdin.close()
        process.stdout.close()
        diagnostic = process.stderr.read()
        process.stderr.close()
        self.assertEqual(process.wait(timeout=15), 2)
        self.assertIn(b"cannot write stdout", diagnostic)

    @unittest.skipUnless(sys.platform.startswith("linux"), "Linux pipe only")
    def test_max_bytes_stops_infinite_input(self):
        producer = subprocess.Popen(["yes", "x"], stdout=subprocess.PIPE)
        try:
            process = subprocess.Popen([BASH, str(GG), "--table", "--max-bytes", "1024"],
                                       stdin=producer.stdout, stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE)
            producer.stdout.close()
            output, diagnostic = process.communicate(timeout=5)
            self.assertEqual(process.returncode, 2)
            self.assertEqual(output, b"")
            self.assertIn(b"max-bytes", diagnostic)
        finally:
            if producer.poll() is None:
                producer.kill()
            producer.wait(timeout=5)


if __name__ == "__main__":
    unittest.main()
