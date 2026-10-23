#!/usr/bin/env python3
"""Opt-in, bounded TSV and text-frame renderer. No third-party imports."""
import os
import re
import shutil
import sys
import unicodedata

if sys.version_info < (3, 9):
    print("gg: --box and --table require Python 3.9+", file=sys.stderr)
    sys.exit(2)


class GGError(Exception):
    pass


GEOMETRY = {
    "single": "─│┌┐└┘├┤┬┴┼",
    "double": "═║╔╗╚╝╠╣╦╩╬",
    "heavy": "━┃┏┓┗┛┣┫┳┻╋",
    "ascii": "-|+++++++++",
}
# Dashed and dotted map to a single-line frame with matching horizontal strokes.
GEOMETRY["dashed"] = "╌" + GEOMETRY["single"][1:]
GEOMETRY["dotted"] = "·" + GEOMETRY["single"][1:]
NAMES = {
    "black": 30, "red": 31, "green": 32, "yellow": 33,
    "blue": 34, "magenta": 35, "cyan": 36, "white": 37,
    "gray": 90, "bright-red": 91, "bright-green": 92,
    "bright-yellow": 93, "bright-blue": 94, "bright-magenta": 95,
    "bright-cyan": 96, "bright-white": 97,
}
CSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
OSC = re.compile(r"\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)?")
ESCAPE = re.compile(r"\x1b(?:[ -/]*[@-_])?")


def clean(value):
    """Remove terminal control strings and remaining control code points."""
    value = OSC.sub("", CSI.sub("", value))
    value = ESCAPE.sub("", value)
    return "".join(ch for ch in value if ch not in "\r\n\t" and
                   unicodedata.category(ch) not in ("Cc", "Cf", "Cs"))


def cell_width(value):
    total = 0
    for ch in value:
        if unicodedata.combining(ch) or unicodedata.category(ch) in ("Mn", "Me", "Cf"):
            continue
        total += 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1
    return total


def chunks(value, width):
    if not value:
        return [""]
    result, part, used = [], "", 0
    for ch in value:
        step = cell_width(ch)
        if step > width:
            raise GGError("width is too narrow for a wide character")
        if used + step > width and part:
            result.append(part)
            part, used = "", 0
        part += ch
        used += step
    result.append(part)
    return result


def fit(value, width, overflow):
    size = cell_width(value)
    if size <= width:
        return [value]
    if overflow == "error":
        raise GGError(f"text needs {size} columns, only {width} available")
    if overflow == "wrap":
        return chunks(value, width)
    if width == 1:
        return ["…"]
    part = ""
    for ch in value:
        if cell_width(part) + cell_width(ch) > width - 1:
            break
        part += ch
    return [part + "…"]


def color_code(value):
    if value in ("none", "default"):
        return ""
    if value in NAMES:
        return f"\x1b[{NAMES[value]}m"
    if re.fullmatch(r"#[0-9a-fA-F]{6}", value):
        rgb = [int(value[i:i+2], 16) for i in (1, 3, 5)]
        return f"\x1b[38;2;{rgb[0]};{rgb[1]};{rgb[2]}m"
    if re.fullmatch(r"[0-9]{1,3}", value) and int(value) <= 255:
        return f"\x1b[38;5;{int(value)}m"
    raise GGError(f"invalid color: {value}")


def parse(argv):
    values = {
        "style": os.getenv("GG_STYLE") or "double",
        "color": os.getenv("GG_COLOR") or "magenta",
        "text-color": os.getenv("GG_TEXT_COLOR") or "cyan",
        "width": os.getenv("GG_WIDTH") or "",
        "align": None, "title": "", "header": None, "overflow": None,
        "max-rows": "10000", "max-bytes": "8388608",
    }
    seen, words = set(), []
    modes = []
    flags = {"--box", "--table", "--header-first-row", "--no-color", "--force-color"}
    aliases = {"-s": "style", "-w": "width", "-a": "align"}
    permitted = set(values) | {"char", "layout", "text"}
    i, positional = 0, False
    while i < len(argv):
        arg = argv[i]
        i += 1
        if positional:
            words.append(arg)
            continue
        if arg == "--":
            positional = True
            continue
        if arg in ("-h", "--help"):
            raise GGError("use gg --help for usage")
        if arg in flags:
            seen.add(arg)
            if arg in ("--box", "--table"):
                modes.append(arg[2:])
            continue
        key = None
        if arg.startswith("--") and "=" in arg:
            key, val = arg[2:].split("=", 1)
        elif arg.startswith("--"):
            key = arg[2:]
            if key not in permitted:
                raise GGError(f"unknown option: {arg}")
            if i >= len(argv):
                raise GGError(f"{arg} requires a value")
            val = argv[i]
            i += 1
        elif arg in aliases:
            key = aliases[arg]
            if i >= len(argv):
                raise GGError(f"{arg} requires a value")
            val = argv[i]
            i += 1
        elif arg.startswith("-"):
            raise GGError(f"unknown option: {arg}")
        else:
            words.append(arg)
            continue
        if key not in permitted:
            raise GGError(f"unknown option: --{key}")
        if key in ("char", "layout", "text"):
            raise GGError(f"--{key} cannot be used with --box or --table")
        values[key] = val
        seen.add("--" + key)
    if len(modes) != 1:
        raise GGError("select exactly one of --box and --table")
    mode = modes[0]
    if values["style"] not in GEOMETRY:
        raise GGError(f"invalid style: {values['style']}")
    if values["align"] is None:
        values["align"] = os.getenv("GG_ALIGN") or ("left" if mode == "box" else "left")
    if values["align"] not in ("left", "center", "right"):
        raise GGError(f"invalid align: {values['align']}")
    if values["overflow"] is None:
        values["overflow"] = "wrap" if mode == "box" else "truncate"
    if values["overflow"] not in ("wrap", "truncate", "error"):
        raise GGError(f"invalid overflow: {values['overflow']}")
    for key in ("max-rows", "max-bytes"):
        val = values[key]
        if not re.fullmatch(r"[1-9][0-9]*", val):
            raise GGError(f"--{key} must be a positive integer")
        values[key] = int(val)
    if values["width"]:
        raw = values["width"]
        if not re.fullmatch(r"[0-9]{1,3}", raw) or not 8 <= int(raw) <= 500:
            raise GGError("width must be an integer from 8 to 500")
        values["width"] = int(raw)
    else:
        raw = os.getenv("COLUMNS", "")
        if not raw.isdigit() and sys.stdout.isatty():
            raw = str(shutil.get_terminal_size((80, 24)).columns)
        width = int(raw) if raw.isdigit() else 80
        values["width"] = max(8, min(120, width - 2 if width > 2 else width))
    if mode == "box":
        for key in ("--header", "--header-first-row", "--max-rows"):
            if key in seen:
                raise GGError(f"{key} applies only to --table")
    else:
        if words:
            raise GGError("--table accepts TSV from stdin, not positional text")
        if "--header" in seen and "--header-first-row" in seen:
            raise GGError("--header and --header-first-row are mutually exclusive")
    if os.getenv("GG_LAYOUT") not in (None, "", "box") and "--layout" not in seen:
        raise GGError("GG_LAYOUT does not apply to --box or --table")
    border_code = color_code(values["color"])
    content_code = color_code(values["text-color"])
    color_on = "--no-color" not in seen and (
        "--force-color" in seen or (sys.stdout.isatty() and not os.getenv("NO_COLOR")))
    values["border-color"] = border_code if color_on else ""
    values["content-color"] = content_code if color_on else ""
    return mode, values, seen, words


def paint(value, code):
    return code + value + "\x1b[0m" if code else value


def border(geometry, widths, position, color):
    h, v, tl, tr, bl, br, left, right, top, bottom, cross = geometry
    if position == "top":
        a, join, b = tl, top, tr
    elif position == "bottom":
        a, join, b = bl, bottom, br
    else:
        a, join, b = left, cross, right
    return paint(a + join.join(h * (w + 2) for w in widths) + b, color)


def titled_top(geometry, width, title, border_color, text_color, overflow):
    h, _, tl, tr, *_ = geometry
    capacity = width - 4
    rendered = fit(title, capacity, "truncate" if overflow == "wrap" else overflow)[0]
    text_size = cell_width(rendered)
    remaining = width - text_size - 4
    left = remaining // 2
    right = remaining - left
    return (paint(tl + h * left + " ", border_color) +
            paint(rendered, text_color) +
            paint(" " + h * right + tr, border_color))


def aligned(value, width, alignment):
    free = width - cell_width(value)
    left = free // 2 if alignment == "center" else free if alignment == "right" else 0
    return " " * left + value + " " * (free - left)


def render_box(options, words, data):
    width = options["width"]
    if words:
        if data:
            raise GGError("use positional text or stdin, not both")
        content = " ".join(words)
    else:
        content = data
    lines = content.splitlines() if content else [""]
    if content.endswith(("\n", "\r")):
        # One terminal newline terminates the last line; extra newlines are content.
        pass
    lines = [clean(line) for line in lines]
    title = clean(options["title"])
    interior = width - 4
    if interior < 1:
        raise GGError("width is too narrow for box")
    rendered = []
    for line in lines:
        rendered.extend(fit(line, interior, options["overflow"]))
    g = GEOMETRY[options["style"]]
    bc, tc = options["border-color"], options["content-color"]
    out = [titled_top(g, width, title, bc, tc, options["overflow"]) if title else
           paint(g[2] + g[0] * (width - 2) + g[3], bc)]
    for line in rendered:
        out.append(paint(g[1] + " ", bc) + paint(aligned(line, interior, options["align"]), tc) +
                   paint(" " + g[1], bc))
    out.append(paint(g[4] + g[0] * (width - 2) + g[5], bc))
    return out


def allocate(natural, budget, minimum):
    if budget < sum(minimum):
        raise GGError("width is too narrow for the minimum table structure")
    if sum(natural) <= budget:
        return natural[:]
    low, high = 0, max(natural)
    while low < high:
        middle = (low + high + 1) // 2
        if sum(max(floor, min(n, middle)) for n, floor in zip(natural, minimum)) <= budget:
            low = middle
        else:
            high = middle - 1
    widths = [max(floor, min(n, low)) for n, floor in zip(natural, minimum)]
    extra = budget - sum(widths)
    for i, n in enumerate(natural):
        if extra == 0:
            break
        if widths[i] < n:
            widths[i] += 1
            extra -= 1
    return widths


def render_table(options, seen, data):
    lines = data.split("\n") if data else []
    if lines and lines[-1] == "":
        lines.pop()
    if len(lines) > options["max-rows"]:
        raise GGError(f"input exceeds --max-rows={options['max-rows']}")
    rows = [[clean(cell) for cell in line.removesuffix("\r").split("\t")] for line in lines]
    header = None
    if "--header-first-row" in seen:
        if not rows:
            raise GGError("--header-first-row requires a TSV row")
        header = rows.pop(0)
    elif options["header"] is not None:
        header = [clean(cell) for cell in options["header"].split(",")]
    if not rows and header is None:
        raise GGError("empty TSV input needs --header")
    columns = len(header) if header is not None else len(rows[0])
    if options["header"] is not None and rows and len(header) != len(rows[0]):
        raise GGError(f"header has {len(header)} columns; TSV has {len(rows[0])}")
    for number, row in enumerate(rows, 2 if "--header-first-row" in seen else 1):
        if len(row) != columns:
            raise GGError(f"TSV row {number}: expected {columns} columns, got {len(row)}")
    width = options["width"]
    budget = width - (3 * columns + 1)
    natural = [1] * columns
    for row in ([header] if header is not None else []) + rows:
        for i, cell in enumerate(row):
            natural[i] = max(natural[i], cell_width(cell))
    minimum = [1] * columns
    if options["overflow"] == "wrap":
        for row in ([header] if header is not None else []) + rows:
            for i, cell in enumerate(row):
                if any(cell_width(char) == 2 for char in cell):
                    minimum[i] = 2
    widths = allocate(natural, budget, minimum)
    if options["overflow"] == "error" and widths != natural:
        raise GGError("table content exceeds --width")
    g = GEOMETRY[options["style"]]
    bc, tc = options["border-color"], options["content-color"]
    title = clean(options["title"])
    total = sum(widths) + 3 * columns + 1
    out = [titled_top(g, total, title, bc, tc, options["overflow"]) if title else border(g, widths, "top", bc)]
    def row_lines(row):
        cells = [fit(cell, w, options["overflow"]) for cell, w in zip(row, widths)]
        height = max(len(cell) for cell in cells)
        for line_index in range(height):
            parts = []
            for cell, size in zip(cells, widths):
                value = cell[line_index] if line_index < len(cell) else ""
                parts.append(" " + aligned(value, size, options["align"]) + " ")
            yield paint(g[1], bc) + paint(g[1], bc).join(paint(part, tc) for part in parts) + paint(g[1], bc)
    if header is not None:
        out.extend(row_lines(header))
        if rows:
            out.append(border(g, widths, "middle", bc))
    for index, row in enumerate(rows):
        if index:
            out.append(border(g, widths, "middle", bc))
        out.extend(row_lines(row))
    out.append(border(g, widths, "bottom", bc))
    return out


def main():
    mode, options, seen, words = parse(sys.argv[1:])
    # Read at most one byte past the ceiling. No temporary files or unbounded arrays.
    if sys.stdin.isatty():
        if mode == "table":
            raise GGError("--table requires redirected TSV input")
        raw = b""
    else:
        try:
            raw = sys.stdin.buffer.read(options["max-bytes"] + 1)
        except OSError as exc:
            raise GGError(f"cannot read stdin: {exc}") from exc
    if len(raw) > options["max-bytes"]:
        raise GGError(f"input exceeds --max-bytes={options['max-bytes']}")
    try:
        data = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise GGError(f"input is not valid UTF-8: {exc}") from exc
    if mode == "box":
        output = render_box(options, words, data)
    else:
        output = render_table(options, seen, data)
    sys.stdout.write("\n".join(output) + "\n")
    sys.stdout.flush()


if __name__ == "__main__":
    try:
        main()
    except GGError as exc:
        print(f"gg: {exc}", file=sys.stderr)
        sys.exit(2)
    except BrokenPipeError:
        try:
            fd = os.open(os.devnull, os.O_WRONLY)
            os.dup2(fd, sys.stdout.fileno())
            os.close(fd)
        except OSError:
            pass
        sys.exit(1)
