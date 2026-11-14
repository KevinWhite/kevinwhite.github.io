#!/usr/bin/env python3
"""Build the generated parts of index.html from now.json.

Usage:
  python3 build.py            rebuild index.html from now.json
  python3 build.py --stamp    set now.json "updated" to today, then rebuild
  python3 build.py --check    validate now.json; exit 1 if index.html is out of date (changes nothing)

The page has two modes, rendered side by side and switched by a class on <html> (js/theme.js, js/site.js):
  "outie" - Kevin's personal self, the green-on-black terminal theme. Shown by default and with no JavaScript.
  "innie" - his work self, GOV.UK-Design-System-flavoured. Hidden unless <html> has class "mode-innie".

now.json:
  {"updated": "YYYY-MM-DD", "outie": MODE, "innie": MODE}
  MODE = {
    "host":     short decorative text in the top bar,
    "notice":   optional one-liner under the banner,
    "prompt":   optional heading prefix (outie uses "$ "),
    "sections": {"about": S, "tunes": S, "make": S, "now": S, "links": S},   (all five, fixed order)
    "entries":  the "Currently" cards,
    "footer":   list of footer lines
  }
  S (section) keys: "heading" (required), "paragraphs" [..], "inset" (quip box), "cta" {"text","url"},
    "note", "cards" [{"title","url"?,"text","placeholder"?}], "links" [{"text","url","note"?}], "placeholder"?,
    "experience" {"label","since": "YYYY-MM-DD"}  -> "<label>: N years", N computed now (js/site.js recomputes on load),
    "figures" [{"src","width","height","alt","caption","credit"}]  (self-hosted /assets images; credit = inline markup),
    "timeline" {"heading","items": [inline text..],"after"?}  (an ordered list under an h3; "after" is a second inset)
  MODE "inset_by": optional attribution shown under every inset in that mode (innie: Kier Eagan).
  Entry keys: {"label", "title", "by"?, "quip"?, "url"?, "placeholder"?}

Text fields accept three bits of inline markup: **bold**, *italic* and [link text](url).
URLs: absolute https:// everywhere; card, CTA and inline links may also be site paths such as /assets/x.mp4.
Anything marked "placeholder": true is listed after each build. Standard library only.
"""
import datetime
import html
import json
import pathlib
import re
import sys
import urllib.parse

HERE = pathlib.Path(__file__).resolve().parent
DATA = HERE / "now.json"
PAGE = HERE / "index.html"
MODES = ("outie", "innie")
SECTIONS = ("about", "tunes", "make", "now", "links")
REGIONS = ("host", "notice", "main", "foot")

MODE_KEYS = {"host", "notice", "prompt", "sections", "entries", "footer", "inset_by"}
SECTION_KEYS = {"heading", "paragraphs", "inset", "cta", "note", "cards", "links", "placeholder",
                "experience", "figures", "timeline"}
FIGURE_KEYS = {"src", "width", "height", "alt", "caption", "credit"}
TODAY = datetime.date.today()
CARD_KEYS = {"title", "url", "text", "placeholder"}
LINK_KEYS = {"text", "url", "note"}
ENTRY_KEYS = {"label", "title", "by", "quip", "url", "placeholder"}

# Innie mode borrows the look of a public-sector service, so it always says what it is not. Not editable.
DISCLAIMER = "Personal site. Not an official West Northamptonshire Council or GOV.UK page."


def fail(msg):
    sys.exit(f"build.py: {msg}")


def esc(s):
    return html.escape(str(s), quote=True)


def check_url(where, url, relative_ok=False):
    """Return url if it is an absolute https:// link (or, if allowed, a /site/path), else stop the build."""
    if not isinstance(url, str) or not url.strip():
        fail(f'{where}: "url" must be a non-empty string')
    if url != url.strip() or any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in url):
        fail(f'{where}: "url" must not contain spaces or control characters')
    if relative_ok and url.startswith("/") and not url.startswith("//") and "\\" not in url:
        return url
    parts = urllib.parse.urlsplit(url)
    if parts.scheme != "https" or not parts.hostname:
        kind = "an absolute https:// link or a /site/path" if relative_ok else "an absolute https:// link"
        fail(f'{where}: "url" must be {kind}, got {url!r}')
    if parts.username or parts.password:
        fail(f'{where}: "url" must not contain credentials')
    return url


def need_str(where, obj, key, optional=False):
    v = obj.get(key)
    if v is None and optional:
        return None
    if not isinstance(v, str) or not v.strip():
        fail(f'{where}: "{key}" must be a non-empty string')
    return v


def only(where, obj, allowed):
    if not isinstance(obj, dict):
        fail(f"{where} must be an object")
    unknown = sorted(set(obj) - allowed)
    if unknown:
        fail(f'{where}: unknown field(s) {", ".join(unknown)}')


LINK_RE = re.compile(r"\[([^\]\n]+)\]\(([^)\s]+)\)")


def _emph(s):
    """**bold** and *italic* on already-escaped text."""
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    return re.sub(r"\*(.+?)\*", r"<em>\1</em>", s)


def inline(where, text):
    """Escape text, then apply the tiny markup. Square brackets without (url) stay literal."""
    if not isinstance(text, str):
        fail(f"{where}: expected text")
    out, pos = [], 0
    for m in LINK_RE.finditer(text):
        out.append(_emph(esc(text[pos:m.start()])))
        href = esc(check_url(where, m.group(2), relative_ok=True))
        out.append(f'<a href="{href}">{_emph(esc(m.group(1)))}</a>')
        pos = m.end()
    out.append(_emph(esc(text[pos:])))
    return "".join(out)


class Out:
    def __init__(self, indent):
        self.lines, self.base = [], indent

    def __call__(self, depth, line):
        self.lines.append(" " * (self.base + 2 * depth) + line)

    def text(self):
        return "\n".join(self.lines)


def heading(mode, prompt, key, sec, where):
    text = esc(need_str(where, sec, "heading"))
    pre = f'<span class="prompt" aria-hidden="true">{esc(prompt)}</span>' if prompt else ""
    return f'<h2 id="{key}-h-{mode}">{pre}{text}</h2>'


def years_since(since, today=None):
    """Whole years from `since` to today; rolls over on the anniversary."""
    today = today or TODAY
    return today.year - since.year - ((today.month, today.day) < (since.month, since.day))


def render_inset(o, d, where, text, by):
    if by:
        o(d, '<figure class="inset">')
        o(d + 1, f'<blockquote><p>{inline(where, text)}</p></blockquote>')
        o(d + 1, f'<figcaption>{esc(by)}</figcaption>')
        o(d, '</figure>')
    else:
        o(d, f'<div class="inset"><p>{inline(where, text)}</p></div>')


def render_now(o, d, mode, entries, updated):
    where = f"{mode}.entries"
    if not isinstance(entries, list) or not entries:
        fail(f'{where} must be a non-empty list')
    o(d, '<dl class="now">')
    for n, e in enumerate(entries, 1):
        if not isinstance(e, dict) or not e.get("label"):
            fail(f"{where}: entry {n} has no label")
        w = f'{where}: entry {n} ({e["label"]})'
        only(w, e, ENTRY_KEYS)
        title = esc(need_str(w, e, "title"))
        if "url" in e:
            title = f'<a href="{esc(check_url(w, e["url"]))}" rel="noopener">{title}</a>'
        o(d + 1, '<div class="now-item">')
        o(d + 2, f'<dt>{esc(e["label"])}</dt>')
        o(d + 2, f'<dd class="now-title">{title}</dd>')
        if e.get("by"):
            o(d + 2, f'<dd class="now-by">{esc(e["by"])}</dd>')
        if e.get("quip"):
            o(d + 2, f'<dd class="now-quip">{esc(e["quip"])}</dd>')
        o(d + 1, '</div>')
    o(d, '</dl>')
    o(d, f'<p class="small now-stamp">Updated <time datetime="{updated.isoformat()}">'
         f'{updated.day} {updated:%B %Y}</time></p>')


def render_section(o, d, mode, prompt, key, sec, m, updated):
    where = f"{mode}.sections.{key}"
    only(where, sec, SECTION_KEYS)
    cls = {"about": "panel about", "tunes": "panel feature"}.get(key, "panel")
    o(d, f'<section class="{cls}" aria-labelledby="{key}-h-{mode}">')
    o(d + 1, heading(mode, prompt, key, sec, where))
    by = m.get("inset_by")
    if "experience" in sec:
        ex = sec["experience"]
        only(f"{where}.experience", ex, {"label", "since"})
        try:
            since = datetime.date.fromisoformat(ex.get("since"))
        except (TypeError, ValueError):
            fail(f'{where}.experience: "since" must be YYYY-MM-DD')
        n = years_since(since)
        o(d + 1, f'<p class="lede experience"><strong>{esc(need_str(where, ex, "label"))}:</strong> '
                 f'<span data-years-since="{since.isoformat()}">{n}</span> years</p>')
    paras = sec.get("paragraphs", [])
    if not isinstance(paras, list):
        fail(f'{where}: "paragraphs" must be a list')
    for i, p in enumerate(paras):
        lede = ' class="lede"' if key == "about" and i == 0 and "experience" not in sec else ""
        o(d + 1, f"<p{lede}>{inline(where, p)}</p>")
    if sec.get("inset"):
        render_inset(o, d + 1, where, sec["inset"], by)
    if "figures" in sec:
        figs = sec["figures"]
        if not isinstance(figs, list) or not figs:
            fail(f'{where}: "figures" must be a non-empty list')
        o(d + 1, '<div class="figures">')
        for n, f in enumerate(figs, 1):
            w = f"{where}.figures[{n}]"
            only(w, f, FIGURE_KEYS)
            src = need_str(w, f, "src")
            if not src.startswith("/assets/") or not (HERE / src.lstrip("/")).is_file():
                fail(f'{w}: "src" must be an existing self-hosted /assets/ file, got {src!r}')
            if not all(isinstance(f.get(k), int) and f[k] > 0 for k in ("width", "height")):
                fail(f'{w}: "width" and "height" must be positive integers')
            o(d + 2, '<figure class="figure">')
            o(d + 3, f'<img src="{esc(src)}" width="{f["width"]}" height="{f["height"]}" loading="lazy" decoding="async" '
                     f'alt="{esc(need_str(w, f, "alt"))}">')
            o(d + 3, f'<figcaption>{inline(w, need_str(w, f, "caption"))} '
                     f'<span class="credit">{inline(w, need_str(w, f, "credit"))}</span></figcaption>')
            o(d + 2, '</figure>')
        o(d + 1, '</div>')
    if "timeline" in sec:
        tl = sec["timeline"]
        only(f"{where}.timeline", tl, {"heading", "items", "after"})
        items = tl.get("items")
        if not isinstance(items, list) or not items:
            fail(f'{where}.timeline: "items" must be a non-empty list')
        o(d + 1, f'<h3 id="{key}-tl-{mode}">{esc(need_str(where, tl, "heading"))}</h3>')
        o(d + 1, f'<ol class="timeline" role="list" aria-labelledby="{key}-tl-{mode}">')
        for n, it in enumerate(items, 1):
            o(d + 2, f"<li>{inline(f'{where}.timeline[{n}]', it)}</li>")
        o(d + 1, '</ol>')
        if tl.get("after"):
            render_inset(o, d + 1, where, tl["after"], by)
    if "cta" in sec:
        cta = sec["cta"]
        only(f"{where}.cta", cta, {"text", "url"})
        words = need_str(f"{where}.cta", cta, "text").rsplit(" ", 2)
        # Keep the last two words and the arrow together so the button never strands the arrow on mobile.
        tail = esc(" ".join(words[-2:]))
        lead = esc(words[0]) + " " if len(words) == 3 else ""
        href = esc(check_url(f"{where}.cta", cta["url"], relative_ok=True))
        o(d + 1, f'<p class="cta-wrap"><a class="cta" href="{href}">{lead}<span>{tail}&nbsp;&rarr;</span></a></p>')
    if "cards" in sec:
        cards = sec["cards"]
        if not isinstance(cards, list) or not cards:
            fail(f'{where}: "cards" must be a non-empty list')
        o(d + 1, '<ul class="cards">')
        for n, c in enumerate(cards, 1):
            w = f"{where}.cards[{n}]"
            only(w, c, CARD_KEYS)
            t = esc(need_str(w, c, "title"))
            if "url" in c:
                t = f'<a href="{esc(check_url(w, c["url"], relative_ok=True))}">{t}</a>'
            o(d + 2, '<li class="card">')
            o(d + 3, f"<h3>{t}</h3>")
            o(d + 3, f"<p>{inline(w, need_str(w, c, 'text'))}</p>")
            o(d + 2, "</li>")
        o(d + 1, "</ul>")
    if key == "now":
        o(d + 1, "<!-- Generated from now.json by build.py. Edit now.json, not this block. -->")
        render_now(o, d + 1, mode, m.get("entries"), updated)
    if "links" in sec:
        links = sec["links"]
        if not isinstance(links, list) or not links:
            fail(f'{where}: "links" must be a non-empty list')
        o(d + 1, '<ul class="links">')
        for n, ln in enumerate(links, 1):
            w = f"{where}.links[{n}]"
            only(w, ln, LINK_KEYS)
            a = f'<a href="{esc(check_url(w, ln.get("url"), relative_ok=True))}">{esc(need_str(w, ln, "text"))}</a>'
            note = f": {inline(w, ln['note'])}" if ln.get("note") else ""
            o(d + 2, f"<li>{a}{note}</li>")
        o(d + 1, "</ul>")
    if sec.get("note"):
        o(d + 1, f'<p class="small">{inline(where, sec["note"])}</p>')
    o(d, "</section>")


def render(data):
    if not isinstance(data, dict):
        fail("now.json must be an object")
    only("now.json", data, {"updated", *MODES})
    try:
        updated = datetime.date.fromisoformat(data["updated"])
    except (KeyError, TypeError, ValueError):
        fail('now.json needs "updated": "YYYY-MM-DD"')
    for mode in MODES:
        if mode not in data:
            fail(f'now.json needs an "{mode}" set')
        only(mode, data[mode], MODE_KEYS)
        secs = data[mode].get("sections")
        only(f"{mode}.sections", secs, set(SECTIONS))
        missing = [k for k in SECTIONS if k not in secs]
        if missing:
            fail(f'{mode}.sections is missing {", ".join(missing)} (both modes keep the same page structure)')
        if not isinstance(data[mode].get("footer"), list) or not data[mode]["footer"]:
            fail(f'{mode}: "footer" must be a non-empty list')

    regions = {}
    o = Out(8)
    for mode in MODES:
        o(0, f'<span data-mode="{mode}">{esc(need_str(mode, data[mode], "host"))}</span>')
    regions["host"] = o.text()

    o = Out(6)
    for mode in MODES:
        m = data[mode]
        o(0, f'<div class="notice" data-mode="{mode}">')
        if mode == "innie":
            o(1, f'<p class="disclaimer">{esc(DISCLAIMER)}</p>')
        if need_str(mode, m, "notice", optional=True):
            o(1, f'<p class="notice-line">{inline(mode, m["notice"])}</p>')
        o(0, "</div>")
    regions["notice"] = o.text()

    o = Out(4)
    for mode in MODES:
        m = data[mode]
        prompt = m.get("prompt", "")
        o(0, f'<div class="mode-block" data-mode="{mode}">')
        for key in SECTIONS:
            render_section(o, 1, mode, prompt, key, m["sections"][key], m, updated)
        o(0, "</div>")
    regions["main"] = o.text()

    o = Out(4)
    for mode in MODES:
        o(0, f'<div data-mode="{mode}">')
        for line in data[mode]["footer"]:
            o(1, f"<p>{inline(mode + '.footer', line)}</p>")
        if mode == "outie":
            o(1, '<p class="cursor-line"><span aria-hidden="true">kevin@clubpit:~$ </span>'
                 '<span class="cursor" aria-hidden="true"></span></p>')
        o(0, "</div>")
    regions["foot"] = o.text()
    return regions


def placeholders(data):
    todo = []
    for mode in MODES:
        m = data[mode]
        todo += [f'{mode}: {e["label"]}' for e in m["entries"] if e.get("placeholder")]
        for key in SECTIONS:
            s = m["sections"][key]
            if s.get("placeholder"):
                todo.append(f"{mode}: {key} section")
            todo += [f'{mode}: {key} card "{c["title"]}"' for c in s.get("cards", []) if c.get("placeholder")]
    return todo


def splice(page, regions):
    for name in REGIONS:
        start, end = f"<!-- build:{name} -->", f"<!-- /build:{name} -->"
        if page.count(start) != 1 or page.count(end) != 1:
            fail(f"index.html must contain exactly one {start} and one {end}")
        head, rest = page.split(start)
        _, tail = rest.split(end)
        indent = head[head.rfind("\n") + 1:]
        page = f"{head}{start}\n{regions[name]}\n{indent}{end}{tail}"
    return page


def main(argv):
    try:
        data = json.loads(DATA.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        fail(f"now.json is not valid JSON: {e}")
    if "--stamp" in argv:
        data["updated"] = datetime.date.today().isoformat()
        DATA.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    page = PAGE.read_text(encoding="utf-8")
    new = splice(page, render(data))

    labels = {m: [e["label"] for e in data[m]["entries"]] for m in MODES}
    if len(labels["outie"]) != len(labels["innie"]):
        print(f'Note: outie has {len(labels["outie"])} "Currently" cards, innie has {len(labels["innie"])}.')

    if "--check" in argv:
        if new != page:
            fail("index.html is out of date - run: python3 build.py")
        print("now.json is valid (outie + innie) and index.html is up to date")
        return
    if new != page:
        PAGE.write_text(new, encoding="utf-8")
        print("index.html rebuilt")
    else:
        print("index.html already up to date")
    todo = placeholders(data)
    if todo:
        print('Still placeholders (delete "placeholder": true once real):\n  ' + "\n  ".join(todo))


if __name__ == "__main__":
    main(sys.argv[1:])
