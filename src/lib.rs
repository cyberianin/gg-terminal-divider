//! Pure formatting rules shared by the Bash and PowerShell adapters.
use unicode_segmentation::UnicodeSegmentation;
use unicode_width::UnicodeWidthStr;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Overflow {
    Wrap,
    Truncate,
    Error,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Align {
    Left,
    Center,
    Right,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Style {
    Single,
    Double,
    Heavy,
    Ascii,
    Dashed,
    Dotted,
}

#[derive(Clone, Debug)]
pub struct Options {
    pub width: usize,
    pub style: Style,
    pub align: Align,
    pub overflow: Overflow,
    pub title: String,
    pub border_color: String,
    pub text_color: String,
}

struct Glyphs {
    h: char,
    v: char,
    tl: char,
    tr: char,
    bl: char,
    br: char,
    l: char,
    r: char,
    t: char,
    b: char,
    x: char,
}
fn glyphs(style: Style) -> Glyphs {
    let set = match style {
        Style::Single => "─│┌┐└┘├┤┬┴┼",
        Style::Double => "═║╔╗╚╝╠╣╦╩╬",
        Style::Heavy => "━┃┏┓┗┛┣┫┳┻╋",
        Style::Ascii => "-|+++++++++",
        Style::Dashed => "╌│┌┐└┘├┤┬┴┼",
        Style::Dotted => "·│┌┐└┘├┤┬┴┼",
    };
    let mut c = set.chars();
    Glyphs {
        h: c.next().unwrap(),
        v: c.next().unwrap(),
        tl: c.next().unwrap(),
        tr: c.next().unwrap(),
        bl: c.next().unwrap(),
        br: c.next().unwrap(),
        l: c.next().unwrap(),
        r: c.next().unwrap(),
        t: c.next().unwrap(),
        b: c.next().unwrap(),
        x: c.next().unwrap(),
    }
}

/// Remove untrusted terminal controls, including CSI, OSC, DCS and C0/C1.
pub fn sanitize(input: &str) -> String {
    let mut result = String::with_capacity(input.len());
    let mut chars = input.chars().peekable();
    while let Some(ch) = chars.next() {
        if ch == '\x1b' {
            match chars.next() {
                Some('[') => {
                    for part in chars.by_ref() {
                        if ('@'..='~').contains(&part) {
                            break;
                        }
                    }
                }
                Some(']') => {
                    while let Some(part) = chars.next() {
                        if part == '\x07' {
                            break;
                        }
                        if part == '\x1b' && chars.peek() == Some(&'\\') {
                            chars.next();
                            break;
                        }
                    }
                }
                Some('P' | 'X' | '^' | '_') => {
                    while let Some(part) = chars.next() {
                        if part == '\x1b' && chars.peek() == Some(&'\\') {
                            chars.next();
                            break;
                        }
                    }
                }
                _ => {}
            }
            continue;
        }
        if ch.is_control()
            || matches!(ch, '\u{200e}'..='\u{200f}' |
            '\u{202a}'..='\u{202e}' | '\u{2066}'..='\u{2069}')
        {
            continue;
        }
        result.push(ch);
    }
    result
}

fn grapheme_width(grapheme: &str) -> usize {
    let measured = UnicodeWidthStr::width(grapheme);
    if grapheme.contains('\u{200d}') {
        measured.min(2).max(
            grapheme
                .chars()
                .map(|c| UnicodeWidthStr::width(c.encode_utf8(&mut [0; 4])))
                .max()
                .unwrap_or(0),
        )
    } else {
        measured
    }
}
pub fn display_width(value: &str) -> usize {
    value.graphemes(true).map(grapheme_width).sum()
}
fn fit(value: &str, width: usize, policy: Overflow) -> Result<Vec<String>, String> {
    let actual = display_width(value);
    if actual <= width {
        return Ok(vec![value.to_owned()]);
    }
    match policy {
        Overflow::Error => Err(format!(
            "text needs {actual} columns, only {width} available"
        )),
        Overflow::Truncate => {
            if width == 0 {
                return Err("width is too narrow".into());
            }
            if width == 1 {
                return Ok(vec!["…".into()]);
            }
            let mut out = String::new();
            let mut used = 0;
            for cluster in value.graphemes(true) {
                let step = grapheme_width(cluster);
                if used + step > width - 1 {
                    break;
                }
                out.push_str(cluster);
                used += step;
            }
            out.push('…');
            Ok(vec![out])
        }
        Overflow::Wrap => {
            if width == 0 {
                return Err("width is too narrow".into());
            }
            let mut out = Vec::new();
            let mut line = String::new();
            let mut used = 0;
            for cluster in value.graphemes(true) {
                let step = grapheme_width(cluster);
                if step > width {
                    return Err("width is too narrow for a wide character".into());
                }
                if used + step > width && !line.is_empty() {
                    out.push(std::mem::take(&mut line));
                    used = 0;
                }
                line.push_str(cluster);
                used += step;
            }
            out.push(line);
            Ok(out)
        }
    }
}
fn aligned(value: &str, width: usize, align: Align) -> String {
    let spare = width - display_width(value);
    let left = match align {
        Align::Left => 0,
        Align::Center => spare / 2,
        Align::Right => spare,
    };
    format!("{}{}{}", " ".repeat(left), value, " ".repeat(spare - left))
}
fn paint(value: &str, color: &str) -> String {
    if color.is_empty() {
        value.to_owned()
    } else {
        format!("{color}{value}\x1b[0m")
    }
}
fn rule(g: &Glyphs, widths: &[usize], kind: &str, color: &str) -> String {
    let (first, joint, last) = match kind {
        "top" => (g.tl, g.t, g.tr),
        "bottom" => (g.bl, g.b, g.br),
        _ => (g.l, g.x, g.r),
    };
    let segments: Vec<String> = widths
        .iter()
        .map(|w| g.h.to_string().repeat(w + 2))
        .collect();
    paint(
        &format!("{first}{}{last}", segments.join(&joint.to_string())),
        color,
    )
}
fn top_title(g: &Glyphs, width: usize, title: &str, options: &Options) -> Result<String, String> {
    let clean = sanitize(title);
    let title_policy = if options.overflow == Overflow::Wrap {
        Overflow::Truncate
    } else {
        options.overflow
    };
    let shown = fit(&clean, width - 4, title_policy)?.remove(0);
    let free = width - display_width(&shown) - 4;
    let left = free / 2;
    Ok(format!(
        "{}{}{}",
        paint(
            &format!("{}{} ", g.tl, g.h.to_string().repeat(left)),
            &options.border_color
        ),
        paint(&shown, &options.text_color),
        paint(
            &format!(" {}{}", g.h.to_string().repeat(free - left), g.tr),
            &options.border_color
        )
    ))
}

pub fn render_box(content: &str, options: &Options) -> Result<String, String> {
    if options.width < 8 || options.width > 500 {
        return Err("width must be 8..500".into());
    }
    let g = glyphs(options.style);
    let inner = options.width - 4;
    let mut rows = Vec::new();
    let mut source: Vec<&str> = content.split('\n').collect();
    if source.len() > 1 && source.last() == Some(&"") {
        source.pop();
    }
    for line in source {
        let cleaned = sanitize(line.trim_end_matches('\r'));
        rows.extend(fit(&cleaned, inner, options.overflow)?);
    }
    let mut output = String::new();
    if options.title.is_empty() {
        output.push_str(&paint(
            &format!(
                "{}{}{}",
                g.tl,
                g.h.to_string().repeat(options.width - 2),
                g.tr
            ),
            &options.border_color,
        ));
    } else {
        output.push_str(&top_title(&g, options.width, &options.title, options)?);
    }
    output.push('\n');
    for row in rows {
        output.push_str(&paint(&format!("{} ", g.v), &options.border_color));
        output.push_str(&paint(
            &aligned(&row, inner, options.align),
            &options.text_color,
        ));
        output.push_str(&paint(&format!(" {}", g.v), &options.border_color));
        output.push('\n');
    }
    output.push_str(&paint(
        &format!(
            "{}{}{}",
            g.bl,
            g.h.to_string().repeat(options.width - 2),
            g.br
        ),
        &options.border_color,
    ));
    output.push('\n');
    Ok(output)
}

fn allocate(natural: &[usize], minimum: &[usize], budget: usize) -> Result<Vec<usize>, String> {
    if budget < minimum.iter().sum() {
        return Err("width is too narrow for the minimum table structure".into());
    }
    if natural.iter().sum::<usize>() <= budget {
        return Ok(natural.to_vec());
    }
    let mut low = 0;
    let mut high = *natural.iter().max().unwrap_or(&0);
    while low < high {
        let middle = low + (high - low).div_ceil(2);
        let sum: usize = natural
            .iter()
            .zip(minimum)
            .map(|(&n, &m)| n.min(middle).max(m))
            .sum();
        if sum <= budget {
            low = middle;
        } else {
            high = middle - 1;
        }
    }
    let mut result: Vec<usize> = natural
        .iter()
        .zip(minimum)
        .map(|(&n, &m)| n.min(low).max(m))
        .collect();
    let mut extra = budget - result.iter().sum::<usize>();
    for (size, &need) in result.iter_mut().zip(natural) {
        if extra == 0 {
            break;
        }
        if *size < need {
            *size += 1;
            extra -= 1;
        }
    }
    Ok(result)
}
fn row_text(
    row: &[&str],
    widths: &[usize],
    g: &Glyphs,
    options: &Options,
) -> Result<String, String> {
    let cells: Vec<Vec<String>> = row
        .iter()
        .zip(widths)
        .map(|(v, &w)| fit(&sanitize(v), w, options.overflow))
        .collect::<Result<_, _>>()?;
    let height = cells.iter().map(Vec::len).max().unwrap_or(1);
    let mut output = String::new();
    for line in 0..height {
        output.push_str(&paint(&g.v.to_string(), &options.border_color));
        for (cell, &size) in cells.iter().zip(widths) {
            let value = cell.get(line).map(String::as_str).unwrap_or("");
            output.push_str(&paint(
                &format!(" {} ", aligned(value, size, options.align)),
                &options.text_color,
            ));
            output.push_str(&paint(&g.v.to_string(), &options.border_color));
        }
        output.push('\n');
    }
    Ok(output)
}
pub fn render_table(
    input: &str,
    header: Option<Vec<String>>,
    first_row_header: bool,
    max_rows: usize,
    options: &Options,
) -> Result<String, String> {
    if options.width < 8 || options.width > 500 {
        return Err("width must be 8..500".into());
    }
    let mut rows: Vec<Vec<&str>> = Vec::new();
    if !input.is_empty() {
        for line in input.split_terminator('\n') {
            if rows.len() == max_rows {
                return Err(format!("input exceeds --max-rows={max_rows}"));
            }
            rows.push(line.trim_end_matches('\r').split('\t').collect());
        }
    }
    let titles: Option<Vec<String>> = if first_row_header {
        if rows.is_empty() {
            return Err("--header-first-row requires a TSV row".into());
        }
        Some(rows.remove(0).into_iter().map(sanitize).collect())
    } else {
        header.map(|h| h.into_iter().map(|v| sanitize(&v)).collect())
    };
    if rows.is_empty() && titles.is_none() {
        return Err("empty TSV input needs --header".into());
    }
    let columns = titles
        .as_ref()
        .map(Vec::len)
        .unwrap_or_else(|| rows[0].len());
    if let (Some(h), Some(row)) = (&titles, rows.first()) {
        if h.len() != row.len() {
            return Err(format!(
                "header has {} columns; TSV has {}",
                h.len(),
                row.len()
            ));
        }
    }
    for (index, row) in rows.iter().enumerate() {
        if row.len() != columns {
            return Err(format!(
                "TSV row {}: expected {columns} columns, got {}",
                index + if first_row_header { 2 } else { 1 },
                row.len()
            ));
        }
    }
    let minimum_border = columns
        .checked_mul(3)
        .and_then(|n| n.checked_add(1))
        .ok_or("too many columns")?;
    if options.width < minimum_border + columns {
        return Err("width is too narrow for the minimum table structure".into());
    }
    let budget = options.width - minimum_border;
    let mut natural = vec![1; columns];
    let mut minimum = vec![1; columns];
    if let Some(h) = &titles {
        for (index, cell) in h.iter().enumerate() {
            natural[index] = natural[index].max(display_width(cell));
            if options.overflow == Overflow::Wrap
                && cell.graphemes(true).any(|g| grapheme_width(g) > 1)
            {
                minimum[index] = 2;
            }
        }
    }
    for row in &rows {
        for (index, cell) in row.iter().enumerate() {
            let cleaned = sanitize(cell);
            natural[index] = natural[index].max(display_width(&cleaned));
            if options.overflow == Overflow::Wrap
                && cleaned.graphemes(true).any(|g| grapheme_width(g) > 1)
            {
                minimum[index] = 2;
            }
        }
    }
    let widths = allocate(&natural, &minimum, budget)?;
    if options.overflow == Overflow::Error && widths != natural {
        return Err("table content exceeds --width".into());
    }
    let g = glyphs(options.style);
    let total = widths.iter().sum::<usize>() + minimum_border;
    let mut output = if options.title.is_empty() {
        rule(&g, &widths, "top", &options.border_color)
    } else {
        top_title(&g, total, &options.title, options)?
    };
    output.push('\n');
    if let Some(h) = &titles {
        let refs: Vec<&str> = h.iter().map(String::as_str).collect();
        output.push_str(&row_text(&refs, &widths, &g, options)?);
        if !rows.is_empty() {
            output.push_str(&rule(&g, &widths, "middle", &options.border_color));
            output.push('\n');
        }
    }
    for (index, row) in rows.iter().enumerate() {
        if index > 0 {
            output.push_str(&rule(&g, &widths, "middle", &options.border_color));
            output.push('\n');
        }
        output.push_str(&row_text(row, &widths, &g, options)?);
    }
    output.push_str(&rule(&g, &widths, "bottom", &options.border_color));
    output.push('\n');
    Ok(output)
}

#[cfg(test)]
mod tests {
    use super::*;
    fn options() -> Options {
        Options {
            width: 12,
            style: Style::Ascii,
            align: Align::Left,
            overflow: Overflow::Wrap,
            title: String::new(),
            border_color: String::new(),
            text_color: String::new(),
        }
    }
    #[test]
    fn box_fixture() {
        assert_eq!(
            render_box("Hi", &options()).unwrap(),
            "+----------+\n| Hi       |\n+----------+\n"
        );
    }
    #[test]
    fn empty_tsv_cells() {
        let mut settings = options();
        settings.width = 13;
        let result = render_table(
            "x\t\t\n",
            Some(vec!["A".into(), "B".into(), "C".into()]),
            false,
            100,
            &settings,
        )
        .unwrap();
        assert!(result.contains("| x |   |   |"));
        assert!(result.ends_with("+---+---+---+\n"));
    }
    #[test]
    fn impossible_table_width_has_no_partial_result() {
        let settings = options(); // width 12; three columns need at least 13.
        let result = render_table(
            "x\t\t\n",
            Some(vec!["A".into(), "B".into(), "C".into()]),
            false,
            100,
            &settings,
        );
        assert_eq!(
            result.unwrap_err(),
            "width is too narrow for the minimum table structure"
        );
    }
    #[test]
    fn escape_safety() {
        assert_eq!(sanitize("\x1b]0;bad\x07hi\x1b[2J"), "hi");
    }
    #[test]
    fn width_examples() {
        assert_eq!(display_width("界e\u{301}"), 3);
    }
}
