#!/usr/bin/env python3
"""Build the "Currently" section of index.html from now.json.

Usage:
  python3 build.py            rebuild index.html from now.json
  python3 build.py --stamp    set now.json "updated" to today, then rebuild
  python3 build.py --check    exit 1 if index.html is out of date (changes nothing)

now.json entries: {"label", "title", "by"?, "quip"?, "url"?, "placeholder"?} or
{"label", "rotate": [one-liners]}. A "rotate" entry is rendered with one line
chosen by ISO week, and js/site.js picks a random one on each page load.
An optional "url" (absolute https:// only) turns the title into a link that
opens in the same tab with rel="noopener".
The page is fully readable without JavaScript. Standard library only.
"""
import datetime
import html
import json
import pathlib
import sys
import urllib.parse

HERE = pathlib.Path(__file__).resolve().parent
DATA = HERE / "now.json"
PAGE = HERE / "index.html"
START, END = "<!-- now:start -->", "<!-- now:end -->"
INDENT = "      "


def esc(s):
    return html.escape(str(s), quote=True)


def fail(msg):
    sys.exit(f"build.py: {msg}")


CARD_KEYS = {"label", "title", "by", "quip", "url", "placeholder"}
ROTATE_KEYS = {"label", "rotate"}


def check_url(where, url):
    """Return url if it is a plain absolute https:// link, else stop the build."""
    if not isinstance(url, str) or not url.strip():
        fail(f'{where}: "url" must be a non-empty string')
    if url != url.strip() or any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in url):
        fail(f'{where}: "url" must not contain spaces or control characters')
    parts = urllib.parse.urlsplit(url)
    if parts.scheme != "https" or not parts.hostname:
        fail(f'{where}: "url" must be an absolute https:// link, got {url!r}')
    if parts.username or parts.password:
        fail(f'{where}: "url" must not contain credentials')
    return url


def render(data):
    try:
        updated = datetime.date.fromisoformat(data["updated"])
    except (KeyError, ValueError):
        fail('now.json needs "updated": "YYYY-MM-DD"')
    entries = data.get("entries")
    if not entries:
        fail('now.json needs a non-empty "entries" list')

    week = updated.isocalendar()[1]
    out = ['<dl class="now">']
    for n, e in enumerate(entries, 1):
        if not e.get("label"):
            fail(f"entry {n} has no label")
        where = f'entry {n} ({e["label"]})'
        allowed = ROTATE_KEYS if "rotate" in e else CARD_KEYS
        unknown = sorted(set(e) - allowed)
        if unknown:
            fail(f'{where}: unknown field(s) {", ".join(unknown)}')
        out.append('  <div class="now-item">')
        out.append(f'    <dt>{esc(e["label"])}</dt>')
        if "rotate" in e:
            lines = [str(x) for x in e["rotate"] if str(x).strip()]
            if not lines:
                fail(f'entry {n} ({e["label"]}): "rotate" is empty')
            pick = lines[week % len(lines)]
            data_attr = esc(json.dumps(lines, ensure_ascii=False))
            out.append(f'    <dd class="now-title"><q class="rotate" data-rotate="{data_attr}">{esc(pick)}</q></dd>')
        else:
            if not e.get("title"):
                fail(f'entry {n} ({e["label"]}) has no title')
            title = esc(e["title"])
            if "url" in e:
                href = esc(check_url(where, e["url"]))
                title = f'<a href="{href}" rel="noopener">{title}</a>'
            out.append(f'    <dd class="now-title">{title}</dd>')
            if e.get("by"):
                out.append(f'    <dd class="now-by">{esc(e["by"])}</dd>')
            if e.get("quip"):
                out.append(f'    <dd class="now-quip">{esc(e["quip"])}</dd>')
        out.append('  </div>')
    out.append('</dl>')
    long_date = f"{updated.day} {updated:%B %Y}"
    out.append(f'<p class="small now-stamp">Updated <time datetime="{updated.isoformat()}">{long_date}</time></p>')
    return "\n".join(INDENT + line for line in out)


def main(argv):
    data = json.loads(DATA.read_text(encoding="utf-8"))
    if "--stamp" in argv:
        data["updated"] = datetime.date.today().isoformat()
        DATA.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    page = PAGE.read_text(encoding="utf-8")
    if page.count(START) != 1 or page.count(END) != 1:
        fail(f"index.html must contain exactly one {START} and one {END}")
    head, rest = page.split(START)
    _, tail = rest.split(END)
    new = f"{head}{START}\n{render(data)}\n{INDENT}{END}{tail}"

    if "--check" in argv:
        if new != page:
            fail("index.html is out of date - run: python3 build.py")
        print("index.html is up to date")
        return
    if new != page:
        PAGE.write_text(new, encoding="utf-8")
        print("index.html rebuilt")
    else:
        print("index.html already up to date")
    todo = [e["label"] for e in data["entries"] if e.get("placeholder")]
    if todo:
        print("Still placeholders (set \"placeholder\": false or delete it once real):", ", ".join(todo))


if __name__ == "__main__":
    main(sys.argv[1:])
