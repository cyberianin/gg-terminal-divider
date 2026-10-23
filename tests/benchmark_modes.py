#!/usr/bin/env python3
"""Measure process invocation and peak RSS; output goes to a null sink."""
import os
from pathlib import Path
import statistics
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent.parent
WINDOWS = sys.platform == "win32"
CORE = ROOT / ("dist/windows-x64/gg-format.exe" if WINDOWS else "dist/linux-x64/gg-format")
PROTOTYPE = ROOT / "prototype/gg-format.py"
try:
    import psutil
except ImportError:
    psutil = None


def memory_kib(command, data):
    if not WINDOWS:
        result = subprocess.run(["/usr/bin/time", "-f", "%M", *command], input=data,
                                stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=60)
        if result.returncode:
            raise RuntimeError(result.stderr.decode(errors="replace"))
        return int(result.stderr.decode().strip().splitlines()[-1])
    if psutil is None:
        return None
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                               stderr=subprocess.PIPE)
    peak = 0
    child = psutil.Process(process.pid)
    try:
        process.stdin.write(data)
        process.stdin.close()
        while process.poll() is None:
            try:
                peak = max(peak, child.memory_info().peak_wset)
            except psutil.NoSuchProcess:
                break
            time.sleep(0.001)
        stderr = process.stderr.read()
        if process.returncode:
            raise RuntimeError(stderr.decode(errors="replace"))
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
    return peak // 1024


def measure(label, command, data):
    durations = []
    for _ in range(6):
        start = time.perf_counter()
        result = subprocess.run(command, input=data, stdout=subprocess.DEVNULL,
                                stderr=subprocess.PIPE, timeout=60)
        durations.append((time.perf_counter() - start) * 1000)
        if result.returncode:
            raise RuntimeError(f"{label}: {result.stderr.decode(errors='replace')}")
    peak = memory_kib(command, data)
    print(f"{label:22} first={durations[0]:9.3f} ms repeat_median={statistics.median(durations[1:]):9.3f} ms peak_rss={peak} KiB")


def main():
    env_bash = os.environ.get("GG_TEST_BASH")
    print(f"platform={sys.platform} Python={sys.version.split()[0]} Rust_binary={CORE.stat().st_size} bytes prototype={PROTOTYPE.stat().st_size} bytes")
    for rows in (0, 10, 1000, 10000):
        if rows:
            data = "".join(f"service-{i}\tRUNNING\t{i * 7} MiB\n" for i in range(rows)).encode()
            args = ["--table", "--header", "NAME,STATUS,SIZE", "--style", "ascii", "--width", "80"]
            name = f"table {rows} rows"
        else:
            data = b"CPU: 12%\nRAM: 1.2 GiB\n"
            args = ["--box", "--style", "ascii", "--width", "80"]
            name = "box 2 lines"
        print(f"{name}: input={len(data)} bytes; output discarded (not terminal rendering)")
        measure("Rust core", [str(CORE), *args], data)
        measure("Python prototype", [sys.executable, str(PROTOTYPE), *args], data)
        if WINDOWS:
            measure("PowerShell 7 adapter", ["pwsh", "-NoProfile", "-File", str(ROOT / "gg.ps1"), *args], data)
        else:
            measure("Bash adapter", ["bash", str(ROOT / "gg"), *args], data)


if __name__ == "__main__":
    main()
