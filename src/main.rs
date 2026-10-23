use gg_format::{render_box, render_table, Align, Options, Overflow, Style};
use std::env;
use std::io::{self, IsTerminal, Read, Write};

struct Cli {
    mode: String,
    options: Options,
    header: Option<Vec<String>>,
    first_row_header: bool,
    max_rows: usize,
    max_bytes: usize,
    words: Vec<String>,
}
fn env_default(name: &str, fallback: &str) -> String {
    env::var(name)
        .ok()
        .filter(|s| !s.is_empty())
        .unwrap_or_else(|| fallback.into())
}
fn parse_positive(value: &str, name: &str) -> Result<usize, String> {
    if value.is_empty() || !value.bytes().all(|b| b.is_ascii_digit()) || value.starts_with('0') {
        return Err(format!("--{name} must be a positive integer"));
    }
    value
        .parse::<usize>()
        .map_err(|_| format!("--{name} is too large"))
}
fn color(value: &str) -> Result<String, String> {
    let code = match value {
        "none" | "default" => return Ok(String::new()),
        "black" => 30,
        "red" => 31,
        "green" => 32,
        "yellow" => 33,
        "blue" => 34,
        "magenta" => 35,
        "cyan" => 36,
        "white" => 37,
        "gray" => 90,
        "bright-red" => 91,
        "bright-green" => 92,
        "bright-yellow" => 93,
        "bright-blue" => 94,
        "bright-magenta" => 95,
        "bright-cyan" => 96,
        "bright-white" => 97,
        _ => {
            if value.len() == 7
                && value.starts_with('#')
                && value[1..].bytes().all(|b| b.is_ascii_hexdigit())
            {
                let r = u8::from_str_radix(&value[1..3], 16).unwrap();
                let g = u8::from_str_radix(&value[3..5], 16).unwrap();
                let b = u8::from_str_radix(&value[5..7], 16).unwrap();
                return Ok(format!("\x1b[38;2;{r};{g};{b}m"));
            }
            if value.len() <= 3 && !value.is_empty() && value.bytes().all(|b| b.is_ascii_digit()) {
                if let Ok(n) = value.parse::<u8>() {
                    return Ok(format!("\x1b[38;5;{n}m"));
                }
            }
            return Err(format!("invalid color: {value}"));
        }
    };
    Ok(format!("\x1b[{code}m"))
}
fn parse(args: &[String]) -> Result<Cli, String> {
    let mut mode = String::new();
    let mut style = env_default("GG_STYLE", "double");
    let mut border_color = env_default("GG_COLOR", "magenta");
    let mut text_color = env_default("GG_TEXT_COLOR", "cyan");
    let mut width_raw = env_default("GG_WIDTH", "");
    let mut align_raw = env_default("GG_ALIGN", "left");
    let mut title = String::new();
    let mut header: Option<Vec<String>> = None;
    let mut first = false;
    let mut overflow_raw = String::new();
    let mut max_rows = 10000;
    let mut max_bytes = 8 * 1024 * 1024;
    let mut rows_explicit = false;
    let mut no_color = false;
    let mut force_color = false;
    let mut words = Vec::new();
    let mut positional = false;
    let mut index = 0;
    while index < args.len() {
        let arg = &args[index];
        index += 1;
        if positional {
            words.push(arg.clone());
            continue;
        }
        if arg == "--" {
            positional = true;
            continue;
        }
        match arg.as_str() {
            "--box" | "--table" => {
                if !mode.is_empty() {
                    return Err("select exactly one of --box and --table".into());
                }
                mode = arg[2..].into();
                continue;
            }
            "--header-first-row" => {
                first = true;
                continue;
            }
            "--no-color" => {
                no_color = true;
                continue;
            }
            "--force-color" => {
                force_color = true;
                continue;
            }
            "-h" | "--help" => {
                return Err("use gg --help for usage".into());
            }
            _ => {}
        }
        let (key, value) = if let Some(stripped) = arg.strip_prefix("--") {
            if let Some((key, value)) = stripped.split_once('=') {
                (key.to_owned(), value.to_owned())
            } else {
                let valid = matches!(
                    stripped,
                    "style"
                        | "color"
                        | "text-color"
                        | "width"
                        | "align"
                        | "title"
                        | "header"
                        | "overflow"
                        | "max-rows"
                        | "max-bytes"
                        | "char"
                        | "layout"
                        | "text"
                );
                if !valid {
                    return Err(format!("unknown option: {arg}"));
                }
                if index >= args.len() {
                    return Err(format!("{arg} requires a value"));
                }
                let value = args[index].clone();
                index += 1;
                (stripped.to_owned(), value)
            }
        } else if matches!(arg.as_str(), "-s" | "-w" | "-a" | "-t" | "-c" | "-l") {
            if index >= args.len() {
                return Err(format!("{arg} requires a value"));
            }
            let key = match arg.as_str() {
                "-s" => "style",
                "-w" => "width",
                "-a" => "align",
                "-t" => "text",
                "-c" => "char",
                _ => "layout",
            };
            let value = args[index].clone();
            index += 1;
            (key.into(), value)
        } else if arg.starts_with('-') {
            return Err(format!("unknown option: {arg}"));
        } else {
            words.push(arg.clone());
            continue;
        };
        match key.as_str() {
            "style" => style = value,
            "color" => border_color = value,
            "text-color" => text_color = value,
            "width" => width_raw = value,
            "align" => {
                align_raw = value;
            }
            "title" => title = value,
            "header" => header = Some(value.split(',').map(str::to_owned).collect()),
            "overflow" => overflow_raw = value,
            "max-rows" => {
                max_rows = parse_positive(&value, "max-rows")?;
                rows_explicit = true;
            }
            "max-bytes" => max_bytes = parse_positive(&value, "max-bytes")?,
            "char" | "layout" | "text" => {
                return Err(format!("--{key} cannot be used with --box or --table"))
            }
            _ => return Err(format!("unknown option: --{key}")),
        }
    }
    if mode.is_empty() {
        return Err("select --box or --table".into());
    }
    let style = match style.as_str() {
        "single" => Style::Single,
        "double" => Style::Double,
        "heavy" => Style::Heavy,
        "ascii" => Style::Ascii,
        "dashed" => Style::Dashed,
        "dotted" => Style::Dotted,
        _ => return Err(format!("invalid style: {style}")),
    };
    let align = match align_raw.as_str() {
        "left" => Align::Left,
        "center" => Align::Center,
        "right" => Align::Right,
        _ => return Err(format!("invalid align: {align_raw}")),
    };
    let overflow = match overflow_raw.as_str() {
        "" if mode == "box" => Overflow::Wrap,
        "" => Overflow::Truncate,
        "wrap" => Overflow::Wrap,
        "truncate" => Overflow::Truncate,
        "error" => Overflow::Error,
        _ => return Err(format!("invalid overflow: {overflow_raw}")),
    };
    let width = if width_raw.is_empty() {
        let terminal = env::var("COLUMNS")
            .ok()
            .and_then(|n| n.parse::<usize>().ok())
            .unwrap_or(80);
        terminal.saturating_sub(2).clamp(8, 120)
    } else {
        if width_raw.len() > 3 || !width_raw.bytes().all(|b| b.is_ascii_digit()) {
            return Err("width must be an integer from 8 to 500".into());
        }
        let size = width_raw
            .parse::<usize>()
            .map_err(|_| "width must be an integer from 8 to 500")?;
        if !(8..=500).contains(&size) {
            return Err("width must be an integer from 8 to 500".into());
        }
        size
    };
    if env::var("GG_LAYOUT")
        .ok()
        .filter(|v| !v.is_empty() && v != "box")
        .is_some()
    {
        return Err("GG_LAYOUT does not apply to --box or --table".into());
    }
    if mode == "box" && (header.is_some() || first || rows_explicit) {
        return Err("--header, --header-first-row and --max-rows apply only to --table".into());
    }
    if mode == "table" {
        if !words.is_empty() {
            return Err("--table accepts TSV from stdin, not positional text".into());
        }
        if header.is_some() && first {
            return Err("--header and --header-first-row are mutually exclusive".into());
        }
    }
    let border_code = color(&border_color)?;
    let text_code = color(&text_color)?;
    let colored = !no_color
        && (force_color
            || ((io::stdout().is_terminal()
                || env::var("GG_OUTPUT_IS_TTY").as_deref() == Ok("1"))
                && env::var("NO_COLOR")
                    .ok()
                    .is_none_or(|value| value.is_empty())));
    Ok(Cli {
        mode,
        options: Options {
            width,
            style,
            align,
            overflow,
            title,
            border_color: if colored { border_code } else { String::new() },
            text_color: if colored { text_code } else { String::new() },
        },
        header,
        first_row_header: first,
        max_rows,
        max_bytes,
        words,
    })
}
fn run() -> Result<(), String> {
    let cli = parse(&env::args().skip(1).collect::<Vec<_>>())?;
    let mut bytes = Vec::new();
    if io::stdin().is_terminal() {
        if cli.mode == "table" {
            return Err("--table requires redirected TSV input".into());
        }
    } else {
        (&mut io::stdin())
            .take((cli.max_bytes as u64).saturating_add(1))
            .read_to_end(&mut bytes)
            .map_err(|e| format!("cannot read stdin: {e}"))?;
    }
    if bytes.len() > cli.max_bytes {
        return Err(format!("input exceeds --max-bytes={}", cli.max_bytes));
    }
    let input = String::from_utf8(bytes).map_err(|e| format!("input is not valid UTF-8: {e}"))?;
    let output = if cli.mode == "box" {
        if !cli.words.is_empty() && !input.is_empty() {
            return Err("use positional text or stdin, not both".into());
        }
        let content = if cli.words.is_empty() {
            input.as_str()
        } else {
            ""
        };
        if cli.words.is_empty() {
            render_box(content, &cli.options)?
        } else {
            render_box(&cli.words.join(" "), &cli.options)?
        }
    } else {
        render_table(
            &input,
            cli.header,
            cli.first_row_header,
            cli.max_rows,
            &cli.options,
        )?
    };
    let mut stdout = io::stdout().lock();
    stdout
        .write_all(output.as_bytes())
        .map_err(|e| format!("cannot write stdout: {e}"))?;
    Ok(())
}
fn main() {
    if let Err(error) = run() {
        eprintln!("gg: {error}");
        std::process::exit(2);
    }
}
