"""Tiny stdlib HTML/CSS helpers for the site tests."""
import os
import re
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VOID = {"meta", "link", "img", "br", "input", "source", "hr", "area", "base",
        "col", "embed", "track", "wbr"}
# SVG self-closing shapes are handled by handle_startendtag.


def _matches(el, tag, attrs):
    if tag is not None and el.tag != tag:
        return False
    for key, want in attrs.items():
        if key == "class_":
            if want not in el.attrs.get("class", "").split():
                return False
            continue
        name = key.replace("_", "-")
        if name not in el.attrs:
            return False
        if want is not True and el.attrs[name] != want:
            return False
    return True


class El:
    def __init__(self, tag, attrs, parent=None):
        self.tag = tag
        self.attrs = attrs
        self.parent = parent
        self.children = []
        self._text = []

    @property
    def text(self):
        parts = []
        self._collect(parts)
        return " ".join(" ".join(parts).split())

    def _collect(self, parts):
        for item in self._text:
            if isinstance(item, El):
                item._collect(parts)
            else:
                parts.append(item)

    def iter(self):
        for child in self.children:
            yield child
            yield from child.iter()

    def find_all(self, tag=None, **attrs):
        """attrs: exact match; True = present; underscores become hyphens; class_ = class token."""
        return [el for el in self.iter() if _matches(el, tag, attrs)]


class _Builder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = El("#root", {})
        self.stack = [self.root]
        self.extra_text = []

    def _open(self, tag, attrs):
        attrs = {k: (v if v is not None else "") for k, v in attrs}
        parent = self.stack[-1]
        el = El(tag, attrs, parent)
        parent.children.append(el)
        parent._text.append(el)
        for key in ("alt", "aria-label"):
            if attrs.get(key):
                self.extra_text.append(attrs[key])
        return el

    def handle_starttag(self, tag, attrs):
        el = self._open(tag, attrs)
        if tag not in VOID:
            self.stack.append(el)

    def handle_startendtag(self, tag, attrs):
        self._open(tag, attrs)

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                return

    def handle_data(self, data):
        if self.stack[-1].tag not in ("script", "style"):
            self.stack[-1]._text.append(data)


class Page:
    def __init__(self, raw):
        self.raw = raw
        b = _Builder()
        b.feed(raw)
        b.close()
        self.root = b.root
        self.text = " ".join((self.root.text + " " + " ".join(b.extra_text)).split())

    @classmethod
    def load(cls, path):
        return cls((ROOT / path).read_text(encoding="utf-8"))

    def find_all(self, tag=None, **attrs):
        return self.root.find_all(tag, **attrs)

    def by_id(self, el_id):
        found = self.root.find_all(id=el_id)
        return found[0] if found else None


def read_css():
    return (ROOT / "styles.css").read_text(encoding="utf-8")


def read_js():
    return (ROOT / "script.js").read_text(encoding="utf-8")


def css_rules(css):
    """Yield (selectors, body) for every innermost rule, including those inside @media."""
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    for match in re.finditer(r"([^{}]+)\{([^{}]*)\}", css):
        selectors = [s.strip() for s in match.group(1).split(",") if s.strip()]
        yield selectors, match.group(2)


def exists_exact(rel):
    """True if `rel` (relative to the repo root) is a file whose name matches exactly,
    capitals included. macOS ignores case; GitHub Pages does not."""
    path = ROOT
    for part in Path(rel).parts:
        if part not in os.listdir(path):
            return False
        path = path / part
    return path.is_file()
