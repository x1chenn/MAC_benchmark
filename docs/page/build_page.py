#!/usr/bin/env python
"""Build the shareable page from the three Markdown sources.

    python build_page.py        # writes index.html next to this script

Sources: ../DESIGN.md, ../SCENARIOS.md, ../APPENDIX_tools.md, template.html, figs/*.html.
No third-party packages. The converter covers only the Markdown subset those files use:
headings, paragraphs, one-level lists, pipe tables, fenced code, block quotes,
inline code, bold, italic, links and bare URLs.
"""
import html
import pathlib
import re

HERE = pathlib.Path(__file__).resolve().parent
SRC = HERE.parent
INTERNAL = {"DESIGN.md": "#design", "SCENARIOS.md": "#scenarios", "APPENDIX_tools.md": "#tools"}
PART_NAME = {"#design": "第一部分", "#scenarios": "第二部分", "#tools": "第三部分"}

# The Markdown addresses the project owner as "you"; the page is read by others.
VOICE = [
    ("和你说的三个模块的对应关系：", "和最初划分的三个模块的对应关系："),
    ("| 你的模块 |", "| 最初的模块 |"),
    ('你说的"sandbox 环境"就是内核加领域包', '最初说的"sandbox 环境"就是内核加领域包'),
    ('所以你说的"5 到 10 个工具"', '所以最初设想的"5 到 10 个工具"'),
    ("## 10. 需要你定的事", "## 10. 待定事项"),
    ("要不要做由你定。", "要不要做待定。"),
]


def short_url(url):
    text = re.sub(r"^https?://(www\.)?", "", url).rstrip("/")
    return text if len(text) <= 44 else text[:41] + "…"


def inline(s):
    codes, links = [], []

    def keep_code(m):
        codes.append(m.group(1))
        return f"\x00{len(codes) - 1}\x00"

    def keep_link(m):
        links.append((m.group(1), m.group(2)))
        return f"\x01{len(links) - 1}\x01"

    def keep_bare(m):
        url, tail = m.group(0), ""
        while url and url[-1] in ".,;:":
            tail, url = url[-1] + tail, url[:-1]
        links.append((None, url))
        return f"\x01{len(links) - 1}\x01{tail}"

    def put_link(m):
        text, url = links[int(m.group(1))]
        url = html.unescape(url)
        if url in INTERNAL:
            return f'<a href="{INTERNAL[url]}">{PART_NAME[INTERNAL[url]]}</a>'
        label = text if text is not None else html.escape(short_url(url))
        return f'<a href="{html.escape(url, quote=True)}" target="_blank" rel="noopener">{label}</a>'

    s = re.sub(r"`([^`]+)`", keep_code, s)
    s = html.escape(s, quote=False)
    s = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", keep_link, s)
    s = re.sub(r"https?://[^\s\x00\x01，。；、）】]+", keep_bare, s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<![*\w])\*([^*]+)\*(?![*\w])", r"<em>\1</em>", s)
    s = re.sub(r"\x01(\d+)\x01", put_link, s)
    s = re.sub(r"\x00(\d+)\x00", lambda m: "<code>" + html.escape(codes[int(m.group(1))], quote=False) + "</code>", s)
    return s


def split_row(line):
    codes = []

    def keep(m):
        codes.append(m.group(0))
        return f"\x02{len(codes) - 1}\x02"

    tmp = re.sub(r"`[^`]+`", keep, line.strip())
    if tmp.startswith("|"):
        tmp = tmp[1:]
    if tmp.endswith("|"):
        tmp = tmp[:-1]
    return [re.sub(r"\x02(\d+)\x02", lambda m: codes[int(m.group(1))], c.strip()) for c in tmp.split("|")]


def heading_id(prefix, text, counter):
    m = re.match(r"^(\d+(?:\.\d+)*)\.?\s+(.*)$", text)
    if m:
        return f"{prefix}-{m.group(1).replace('.', '-')}", m.group(1), m.group(2)
    if text == "来源":
        return f"{prefix}-src", "", text
    counter[0] += 1
    return f"{prefix}-x{counter[0]}", "", text


def convert(md, prefix, subnav_for=()):
    """Return (html, heads). heads = [(level, id, number, label)], level 2 or 3."""
    lines = md.split("\n")
    out, heads, para, counter = [], [], [], [0]
    started = False  # everything before the first level-2 heading is the file's own header
    i = 0

    def flush():
        if para:
            out.append("<p>" + inline(" ".join(para)) + "</p>")
            para.clear()

    while i < len(lines):
        ln = lines[i]
        m = re.match(r"^(#{1,3}) (.+)$", ln)
        if m:
            flush()
            level, text = len(m.group(1)), m.group(2).strip()
            i += 1
            if level == 1:
                continue
            started = True
            hid, num, label = heading_id(prefix, text, counter)
            heads.append((level, hid, num, label))
            tag = "h3" if level == 2 else "h4"
            numhtml = f'<span class="hn">{num}</span>' if num else ""
            out.append(f'<{tag} id="{hid}">{numhtml}{inline(label)}</{tag}>')
            if level == 2 and num in subnav_for:
                out.append(f"<!--SUBNAV {hid}-->")
            continue
        if not started:
            i += 1
            continue
        if ln.startswith("```"):
            flush()
            buf = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                buf.append(lines[i])
                i += 1
            i += 1
            out.append("<pre><code>" + html.escape("\n".join(buf), quote=False) + "</code></pre>")
            continue
        if re.match(r"^@@[A-Z_]+@@$", ln.strip()):
            flush()
            out.append(ln.strip())
            i += 1
            continue
        if ln.startswith("|") and i + 1 < len(lines) and re.match(r"^\|[\s:|-]+\|\s*$", lines[i + 1]):
            flush()
            header = split_row(ln)
            i += 2
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append(split_row(lines[i]))
                i += 1
            n = len(header)
            cls = f"c{min(n, 6)}"
            t = [f'<div class="tw"><table class="{cls}"><thead><tr>']
            t += [f"<th>{inline(c)}</th>" for c in header]
            t.append("</tr></thead><tbody>")
            for r in rows:
                r = (r + [""] * n)[:n]
                t.append("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>")
            t.append("</tbody></table></div>")
            out.append("".join(t))
            continue
        if ln.startswith(">"):
            flush()
            buf = []
            while i < len(lines) and lines[i].startswith(">"):
                buf.append(lines[i][1:].strip())
                i += 1
            out.append("<blockquote><p>" + inline(" ".join(buf)) + "</p></blockquote>")
            continue
        if ln.startswith("- "):
            flush()
            items = []
            while i < len(lines) and lines[i].startswith("- "):
                items.append(lines[i][2:])
                i += 1
            out.append("<ul>" + "".join(f"<li>{inline(x)}</li>" for x in items) + "</ul>")
            continue
        if re.match(r"^\d+\. ", ln):
            flush()
            items = []
            while i < len(lines) and re.match(r"^\d+\. ", lines[i]):
                items.append(re.sub(r"^\d+\. ", "", lines[i]))
                i += 1
            out.append("<ol>" + "".join(f"<li>{inline(x)}</li>" for x in items) + "</ol>")
            continue
        if ln.strip() in ("", "---"):
            flush()
            i += 1
            continue
        para.append(ln.strip())
        i += 1
    flush()

    body = "\n".join(out)
    # per-scenario section links
    for k, (level, hid, num, label) in enumerate(heads):
        mark = f"<!--SUBNAV {hid}-->"
        if mark not in body:
            continue
        subs = []
        for level2, hid2, num2, label2 in heads[k + 1:]:
            if level2 == 2:
                break
            subs.append(f'<a href="#{hid2}">{num2} {html.escape(label2)}</a>')
        body = body.replace(mark, '<nav class="subnav" aria-label="本节内容">' + "".join(subs) + "</nav>")
    return body, heads


def swap_fence_after(md, heading, marker):
    i = md.index(heading)
    a = md.index("```", i)
    b = md.index("```", a + 3)
    return md[:a] + marker + md[b + 3:]


def insert_after_line(md, line_start, marker):
    i = md.index(line_start)
    end = md.index("\n", i)
    return md[:end + 1] + "\n" + marker + "\n" + md[end + 1:]


def insert_before_line(md, line_start, marker):
    i = md.index(line_start)
    return md[:i] + marker + "\n\n" + md[i:]


def toc_block(title, anchor, heads):
    items = "".join(
        f'<li><a href="#{hid}"><span class="n">{num}</span>{html.escape(label)}</a></li>'
        for level, hid, num, label in heads if level == 2
    )
    return f'<div><h2><a href="#{anchor}">{title}</a></h2><ol>{items}</ol></div>'


def main():
    design = (SRC / "DESIGN.md").read_text(encoding="utf-8")
    scen = (SRC / "SCENARIOS.md").read_text(encoding="utf-8")
    tools = (SRC / "APPENDIX_tools.md").read_text(encoding="utf-8")

    for old, new in VOICE:
        assert old in design, old
        design = design.replace(old, new)
    design = swap_fence_after(design, "### 3.1 六层", "@@FIG_LAYERS@@")
    design = swap_fence_after(design, "### 3.4 一次试验的容器拓扑", "@@FIG_RUNTIME@@")
    design = insert_after_line(design, "### 3.5 两种运行模式", "@@FIG_MODES@@")
    scen = insert_before_line(scen, "三个场景共用四个机制", "@@FIG_SEATS@@")

    d_html, d_heads = convert(design, "d")
    s_html, s_heads = convert(scen, "s", subnav_for=("1", "2", "3"))
    t_html, t_heads = convert(tools, "t")

    figs = {
        "@@FIG_LAYERS@@": "fig_layers.html",
        "@@FIG_RUNTIME@@": "fig_runtime.html",
        "@@FIG_MODES@@": "fig_modes.html",
        "@@FIG_SEATS@@": "fig_seats.html",
    }
    parts = {"d": d_html, "s": s_html, "t": t_html}
    for marker, name in figs.items():
        fig = (HERE / "figs" / name).read_text(encoding="utf-8").strip()
        hit = [k for k in parts if marker in parts[k]]
        assert len(hit) == 1, (marker, hit)
        parts[hit[0]] = parts[hit[0]].replace(marker, fig)

    toc = "\n".join([
        toc_block("顶层设计", "design", d_heads),
        toc_block("三个场景", "scenarios", s_heads),
        toc_block("工具调研附录", "tools", t_heads),
    ])
    page = (HERE / "template.html").read_text(encoding="utf-8")
    for key, val in (("<!--TOC-->", toc), ("<!--PART_DESIGN-->", parts["d"]),
                     ("<!--PART_SCENARIOS-->", parts["s"]), ("<!--PART_TOOLS-->", parts["t"])):
        assert key in page, key
        page = page.replace(key, val)

    for bad in ("@@", "\x00", "\x01", "\x02", "<!--SUBNAV"):
        assert bad not in page, repr(bad)
    ids = re.findall(r'\sid="([^"]+)"', page)
    assert len(ids) == len(set(ids)), [x for x in ids if ids.count(x) > 1]
    for target in re.findall(r'href="#([^"]+)"', page):
        assert target in ids, target

    (HERE / "index.html").write_text(page, encoding="utf-8")
    print("index.html", len(page.encode("utf-8")), "bytes;",
          page.count("<table"), "tables;", page.count("<figure"), "figures;",
          len(d_heads) + len(s_heads) + len(t_heads), "headings")


if __name__ == "__main__":
    main()
