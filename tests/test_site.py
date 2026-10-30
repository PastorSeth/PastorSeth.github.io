import re
import unittest

from sitecheck import ROOT, Page, css_rules, exists_exact, read_css, read_js


def _hex_to_rgb(value):
    value = value.lstrip("#")
    if len(value) == 3:
        value = "".join(c * 2 for c in value)
    return tuple(int(value[i:i + 2], 16) / 255 for i in (0, 2, 4))


def _luminance(rgb):
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contrast(a, b):
    la, lb = sorted((_luminance(_hex_to_rgb(a)), _luminance(_hex_to_rgb(b))), reverse=True)
    return (la + 0.05) / (lb + 0.05)

_page = None


def page():
    global _page
    if _page is None:
        _page = Page.load("index.html")
    return _page


class TestScaffold(unittest.TestCase):
    def test_meta(self):
        p = page()
        viewport = p.find_all("meta", name="viewport")
        self.assertEqual(len(viewport), 1)
        self.assertEqual(viewport[0].attrs["content"], "width=device-width, initial-scale=1")
        self.assertEqual(p.find_all("title")[0].text, "Seth Peacock · Student Pastor")
        html = p.find_all("html")[0]
        self.assertEqual(html.attrs.get("lang"), "en")
        self.assertEqual(html.attrs.get("class"), "no-js")

    def test_sections_exist(self):
        for section_id in ["top", "about", "experience", "portfolio", "contact"]:
            self.assertIsNotNone(page().by_id(section_id), section_id)

    def test_nav_anchors_resolve(self):
        p = page()
        for a in p.find_all("a"):
            href = a.attrs.get("href", "")
            if href.startswith("#") and href != "#":
                self.assertIsNotNone(p.by_id(href[1:]), href)

    def test_tokens(self):
        css = read_css()
        for decl in ["--night:#120A26", "--deep:#05020C", "--plum:#1C1238", "--gold:#FFD23F",
                     "--ruby:#FF4D6D", "--sapphire:#3D7BFF", "--emerald:#2BD9A4",
                     "--violet:#9B5CFF", "--cream:#FFF6E5"]:
            self.assertIn(decl, css.replace(" ", ""))

    def test_reveal_hidden_only_with_js(self):
        hiding = 0
        for selectors, body in css_rules(read_css()):
            if re.search(r"opacity:\s*0(?![.\d])", body):
                for sel in selectors:
                    if "[data-reveal" in sel:
                        hiding += 1
                        self.assertTrue(sel.startswith(".js "), sel)
        self.assertGreater(hiding, 0, "expected at least one hidden reveal state")

    def test_no_phone_numbers(self):
        p = page()
        self.assertIsNone(re.search(r"\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}", p.text))

    def test_nav_does_not_trap_fixed_menu(self):
        # filter/backdrop-filter/transform on .nav would make the "fixed" mobile menu
        # size itself to the header instead of the whole screen.
        for selectors, body in css_rules(read_css()):
            if ".nav" in selectors:
                self.assertNotRegex(body, r"(^|[;\s])(-webkit-)?(backdrop-)?filter\s*:|(^|[;\s])transform\s*:")

    def test_main_clips_horizontal_overflow(self):
        # Reveal start states slide content sideways (translateX(±60px)). Without clipping,
        # mobile browsers widen the layout viewport and zoom the whole page out.
        body = None
        for selectors, rule in css_rules(read_css()):
            if "main" in selectors:
                body = rule
        self.assertIsNotNone(body, "expected a `main` rule")
        self.assertRegex(body, r"overflow-x:\s*clip")

    def test_js_failure_fallback(self):
        # If script.js is blocked, 404s, or throws, the page must not stay hidden.
        inline = " ".join(sc for sc in re.findall(r"<script>(.*?)</script>", page().raw, re.S))
        self.assertIn("setTimeout", inline)
        self.assertIn("siteReady", inline)
        js = read_js()
        boot = js[js.index("document.addEventListener('DOMContentLoaded'"):]
        self.assertLess(boot.index("initReveal()"), boot.index("window.siteReady = true"))
        self.assertLess(boot.index("window.siteReady = true"), boot.index("initNav"))
        self.assertIn("try {", boot)

    def test_text_contrast(self):
        # Any rule that sets both a background and a text color must meet WCAG AA (4.5:1).
        css = read_css()
        tokens = dict(re.findall(r"(--[a-z]+):\s*(#[0-9A-Fa-f]{3,6})", css))
        large_or_decorative = {".welcome__label", ".welcome__icon"}

        def resolve(value):
            value = value.strip()
            m = re.fullmatch(r"var\((--[a-z]+)\)", value)
            if m:
                return tokens.get(m.group(1))
            return value if re.fullmatch(r"#[0-9A-Fa-f]{3,6}", value) else None

        checked = 0
        for selectors, body in css_rules(css):
            bg = re.search(r"(?:^|;|\s)background(?:-color)?:\s*([^;]+);", body)
            fg = re.search(r"(?:^|;|\s)color:\s*([^;]+);", body)
            if not (bg and fg) or set(selectors) & large_or_decorative:
                continue
            b, f = resolve(bg.group(1)), resolve(fg.group(1))
            if not (b and f):
                continue
            checked += 1
            self.assertGreaterEqual(round(contrast(b, f), 2), 4.5, f"{selectors}: {f} on {b}")
        self.assertGreater(checked, 10)

    def test_overflow_fallback_for_older_safari(self):
        # `clip` needs Safari 16+; `hidden` first keeps older iPhones from zooming out.
        for selectors, body in css_rules(read_css()):
            if "main" in selectors:
                self.assertRegex(" ".join(body.split()), r"overflow-x:\s*hidden;.*overflow-x:\s*clip")
                return
        self.fail("no main rule")

    def test_print_shows_everything(self):
        block = _block_after(read_css(), "@media print")
        rules = {s: " ".join(b.split()) for sels, b in css_rules(block) for s in sels}
        self.assertRegex(rules.get(".js [data-reveal]", ""), r"opacity:\s*1")
        self.assertRegex(rules.get(".nav", ""), r"display:\s*none")

    def test_video_modal_fits_short_screens(self):
        # Landscape phones: the 16:9 player must be limited by height too.
        for selectors, body in css_rules(read_css()):
            if ".video-modal" in selectors and "width" in body:
                self.assertRegex(body, r"width:[^;]*vh")
                return
        self.fail("no .video-modal width rule")

    def test_exists_exact_is_case_sensitive(self):
        # macOS ignores filename case; GitHub Pages does not.
        self.assertTrue(exists_exact("images/seth.jpg"))
        self.assertFalse(exists_exact("images/SETH.JPG"))

    def test_external_links_safe(self):
        for a in page().find_all("a"):
            if a.attrs.get("href", "").startswith("http"):
                self.assertEqual(a.attrs.get("target"), "_blank", a.attrs["href"])
                self.assertIn("noopener", a.attrs.get("rel", ""), a.attrs["href"])


class TestCathedralNight(unittest.TestCase):
    """The A1 "Cathedral Night" look: stained glass, pixel crosses, CRT scanlines."""

    def test_gothic_pixel_font(self):
        css = read_css()
        self.assertRegex(css, r"@font-face\s*\{[^}]*font-family:\s*['\"]GothicPixel['\"][^}]*"
                              r"url\(['\"]?fonts/old-english-gothic-pixel\.ttf")
        self.assertTrue(exists_exact("fonts/old-english-gothic-pixel.ttf"))
        # SIL Open Font License: the license must ship with the font
        self.assertTrue(exists_exact("fonts/OFL.txt"))

    def test_no_video_game_copy(self):
        text = page().text.lower()
        for phrase in ["1p", "stage:", "unlocked", "level 2", "press start", "player 1", "player one"]:
            self.assertNotIn(phrase, text)

    def test_hero_strip_with_crosses(self):
        strips = page().by_id("top").find_all(class_="hero__strip")
        self.assertEqual(len(strips), 1)
        self.assertIn("Student pastor", strips[0].text)
        self.assertIn("Birmingham, AL", strips[0].text)
        self.assertEqual(len(strips[0].find_all("svg", class_="cross")), 3)

    def test_hero_window_eyebrow_and_rec_tag(self):
        hero = page().by_id("top")
        window = hero.find_all(class_="hero__window")
        self.assertEqual(len(window), 1)
        self.assertEqual(window[0].attrs.get("aria-hidden"), "true")
        rec = hero.find_all(class_="welcome__rec")
        self.assertEqual(len(rec), 1)
        self.assertEqual(rec[0].text, "● HELLO.MP4")
        self.assertIn("Resume & Portfolio", hero.text)

    def test_crt_overlay(self):
        crt = page().find_all(class_="crt")
        self.assertEqual(len(crt), 1)
        self.assertEqual(crt[0].attrs.get("aria-hidden"), "true")
        body = _rule(read_css(), ".crt")
        self.assertIsNotNone(body)
        self.assertIn("repeating-linear-gradient", body)
        self.assertRegex(body, r"pointer-events:\s*none")
        self.assertRegex(body, r"position:\s*fixed")


class TestHero(unittest.TestCase):
    def setUp(self):
        self.hero = page().by_id("top")

    def test_hero_name(self):
        h1 = self.hero.find_all("h1")
        self.assertEqual(len(h1), 1)
        self.assertEqual(h1[0].text, "Seth Peacock")

    def test_hero_ctas(self):
        work = [a for a in self.hero.find_all("a", href="#portfolio") if "See my work" in a.text]
        resume = [a for a in self.hero.find_all("a", href="resume.pdf", download=True)
                  if "Grab my resume" in a.text]
        self.assertEqual(len(work), 1)
        self.assertEqual(len(resume), 1)

    def test_app_pill(self):
        pills = [a for a in self.hero.find_all("a", href="#app") if "Check out this curriculum I wrote" in a.text]
        self.assertEqual(len(pills), 1)

    def test_welcome_card(self):
        buttons = [b for b in self.hero.find_all("button", data_video_id=True) if "Welcome Video" in b.text]
        self.assertEqual(len(buttons), 1)
        videos = self.hero.find_all("video")
        self.assertEqual(len(videos), 1)
        v = videos[0]
        for attr in ("muted", "loop", "playsinline", "autoplay"):
            self.assertIn(attr, v.attrs, attr)
        self.assertEqual(v.attrs.get("poster"), "images/hero-poster.jpg")
        self.assertEqual(len(v.find_all("source", src="videos/hero-preview.mp4", type="video/mp4")), 1)

    def test_modal_markup(self):
        dialogs = page().find_all("dialog", id="video-modal")
        self.assertEqual(len(dialogs), 1)
        d = dialogs[0]
        self.assertTrue(d.attrs.get("aria-label"))
        self.assertEqual(len(d.find_all(class_="video-frame")), 1)
        self.assertEqual(len(d.find_all("button", class_="video-close", aria_label="Close video")), 1)


    def test_newsletter_modal(self):
        trigger = page().by_id("portfolio").find_all("a", class_="social-card--newsletter")[0]
        self.assertEqual(trigger.attrs.get("data-modal"), "newsletter-modal")
        dialogs = page().find_all("dialog", id="newsletter-modal")
        self.assertEqual(len(dialogs), 1)
        imgs = dialogs[0].find_all("img")
        self.assertEqual(len(imgs), 1)
        self.assertTrue(imgs[0].attrs.get("alt"))
        self.assertTrue(exists_exact(imgs[0].attrs["src"]))

    def test_cards_modal(self):
        trigger = page().by_id("portfolio").find_all("a", class_="social-card--print")[0]
        self.assertEqual(trigger.attrs.get("data-modal"), "cards-modal")
        dialogs = page().find_all("dialog", id="cards-modal")
        self.assertEqual(len(dialogs), 1)
        d = dialogs[0]
        self.assertTrue(d.attrs.get("aria-label"))
        self.assertEqual(len(d.find_all("button", class_="video-close")), 1)
        imgs = d.find_all("img")
        self.assertEqual(len(imgs), 2)
        for img in imgs:
            self.assertTrue(img.attrs.get("alt"))
            self.assertTrue(exists_exact(img.attrs["src"]), img.attrs["src"])

class TestAbout(unittest.TestCase):
    def setUp(self):
        self.about = page().by_id("about")

    def test_heart_cards(self):
        cards = self.about.find_all(class_="heart-card")
        self.assertEqual(len(cards), 4)
        titles = [c.find_all("h3")[0].text for c in cards]
        self.assertEqual(titles, [
            "Students who love God and live on mission",
            "Parents as primary disciplers",
            "Volunteers empowered to invest in students",
            "Pray Pray Pray",
        ])

    def test_bio_facts(self):
        self.assertIn("Birmingham", self.about.text)
        imgs = self.about.find_all("img")
        self.assertGreaterEqual(len(imgs), 1)
        for img in imgs:
            self.assertTrue(img.attrs.get("alt"))

    def test_prayer_card_is_fourth_card_full_width(self):
        self.assertEqual(self.about.find_all(class_="stat"), [])
        cards = self.about.find_all(class_="heart-card")
        prayer = cards[-1]
        self.assertIn("heart-card--prayer", prayer.attrs["class"].split())
        self.assertIn("Prayer is the glue that holds the ministry together.", prayer.text)
        self.assertEqual(len(prayer.find_all(class_="heart-card__icon")), 1)
        # The icon is the pixel dove (Holy Spirit), not a cross
        icon_svg = prayer.find_all(class_="heart-card__icon")[0].find_all("svg")[0]
        self.assertEqual(icon_svg.attrs.get("viewbox"), "0 0 17 13")
        rule = " ".join(_rule(read_css(), ".heart-card--prayer").split())
        self.assertRegex(rule, r"grid-column:\s*1\s*/\s*-1")

    def test_marquee_a11y(self):
        marquees = page().find_all(class_="marquee")
        self.assertEqual(len(marquees), 1)
        m = marquees[0]
        self.assertEqual(m.attrs.get("aria-hidden"), "true")
        # The verse scrolls twice for a seamless loop...
        self.assertEqual(m.text.count("to equip the saints for the work of ministry"), 2)
        # ...and screen readers get it once, read normally
        hidden = [p for p in self.about.find_all(class_="visually-hidden") if "Ephesians 4:11" in p.text]
        self.assertEqual(len(hidden), 1)


class TestExperience(unittest.TestCase):
    def setUp(self):
        self.cards = page().by_id("experience").find_all(class_="timeline-card")

    def test_ministry_roles(self):
        self.assertEqual([c.find_all("h3")[0].text for c in self.cards], [
            "Student Pastor", "Ministry Resident",
            "Full Time Seminary Student", "Director of Worship Media",
        ])
        self.assertEqual([c.find_all(class_="dates")[0].text for c in self.cards], [
            "Feb 2024 – Aug 2025", "Aug 2023 – Feb 2024",
            "Jan 2020 – May 2024", "Jul 2017 – Oct 2019",
        ])
        places = ["Parkway Baptist Church", "Warren Baptist Church",
                  "Southern Baptist Theological Seminary", "Cottage Hill Baptist Church"]
        for card, place in zip(self.cards, places):
            self.assertIn(place, card.text)
            self.assertIn(len(card.find_all("li")), (2, 3), place)

    def test_parkway_highlights(self):
        self.assertIn("Parenting with Purpose", self.cards[0].text)
        self.assertIn("Encounter WKND", self.cards[0].text)

    def test_work_cards(self):
        work = page().by_id("experience").find_all(class_="work-card")
        expected = [("Peacock Insurance", "Jan 2025 – Present"),
                    ("All American Chimney Service", "Jan 2022 – May 2023"),
                    ("Chick-fil-A", "May 2021 – Jan 2022"),
                    ("UPS", "Oct 2019 – May 2021")]
        self.assertEqual(len(work), len(expected))
        for card, (company, dates) in zip(work, expected):
            self.assertIn(company, card.text)
            self.assertIn(dates, card.text)

    def test_education(self):
        edu = [c.text for c in page().by_id("experience").find_all(class_="edu-card")]
        self.assertEqual(len(edu), 2)
        self.assertIn("M.A. Church Leadership", edu[0])
        self.assertIn("Rice-Judson Scholarship Award", edu[0])
        self.assertIn("B.S. Worship Leadership", edu[1])
        self.assertIn("Summa Cum Laude", edu[1])
        self.assertNotIn("Suma ", page().raw)

    def test_alternating_reveal(self):
        self.assertEqual([c.attrs.get("data-reveal") for c in self.cards],
                         ["left", "right", "left", "right"])


class TestPortfolio(unittest.TestCase):
    def setUp(self):
        self.portfolio = page().by_id("portfolio")
        self.app = page().by_id("app")

    def test_app_first_and_highlighted(self):
        kids = self.portfolio.children
        self.assertTrue(kids[0].find_all("h2"), "portfolio should open with its heading")
        self.assertEqual(kids[1].attrs.get("id"), "app")
        self.assertIn("Written by me", self.app.text)

    def test_app_link(self):
        links = self.app.find_all("a", class_="btn--app")
        self.assertEqual(len(links), 1)
        a = links[0]
        self.assertIn("Open the app", a.text)
        self.assertIn("↗", a.text)
        self.assertEqual(a.attrs.get("target"), "_blank")
        self.assertIn("noopener", a.attrs.get("rel", ""))
        self.assertTrue(a.attrs.get("href", "").startswith("http"))

    def test_sermon_cards(self):
        tracks = self.portfolio.find_all(class_="sermon-track")
        self.assertEqual(len(tracks), 1)
        cards = tracks[0].find_all(class_="sermon-card")
        self.assertGreaterEqual(len(cards), 3)
        for card in cards:
            if card.tag == "a":
                # Videos hosted elsewhere (Subsplash) open in a new tab
                self.assertEqual(card.attrs.get("target"), "_blank")
                self.assertIn("noopener", card.attrs.get("rel", ""))
                self.assertTrue(card.attrs.get("href", "").startswith("https://"))
            else:
                self.assertTrue(card.attrs.get("data-video-id") and card.attrs.get("data-video-title"))
            imgs = card.find_all("img")
            self.assertEqual(len(imgs), 1)
            self.assertTrue(imgs[0].attrs.get("alt"))

    def test_video_ids_valid(self):
        ids = [el.attrs["data-video-id"] for el in page().find_all(data_video_id=True)]
        self.assertGreaterEqual(len(ids), 3)
        for vid in ids:
            self.assertTrue(vid == "REPLACE_ME" or re.fullmatch(r"[A-Za-z0-9_-]{11}", vid), vid)

    def test_real_sermons(self):
        ids = [b.attrs["data-video-id"] for b in self.portfolio.find_all("button", class_="sermon-card")]
        self.assertEqual(ids, ["ANSNAaILUqs", "a2X-9_vmeU8"])

    def test_social_cards(self):
        cards = self.portfolio.find_all("a", class_="social-card")
        self.assertEqual(len(cards), 4)
        for card in cards:
            self.assertIn(card.attrs.get("data-platform"), {"instagram", "facebook", "newsletter", "print"})
            self.assertEqual(card.attrs.get("target"), "_blank")
            self.assertIn("noopener", card.attrs.get("rel", ""))
            href = card.attrs["href"]
            if card.attrs["data-platform"] in {"newsletter", "print"}:
                self.assertTrue(exists_exact(href), href)
                continue
            self.assertTrue(href.startswith("https://www.instagram.com/reel/") or
                            href.startswith("https://www.facebook.com/share/v/"), href)
            # Share links are kept free of tracking codes
            self.assertNotIn("igsh", href)
            self.assertNotIn("mibextid", href)


def _block_after(css, marker):
    """Return the text inside the braces that follow `marker`."""
    start = css.index(marker)
    open_at = css.index("{", start)
    depth = 0
    for i in range(open_at, len(css)):
        if css[i] == "{":
            depth += 1
        elif css[i] == "}":
            depth -= 1
            if depth == 0:
                return css[open_at + 1:i]
    raise AssertionError("unbalanced braces after " + marker)


def _rule(css, selector):
    for selectors, body in css_rules(css):
        if selector in selectors:
            return " ".join(body.split())
    return None


class TestMotion(unittest.TestCase):
    def test_reduced_motion_block(self):
        css = read_css()
        block = _block_after(css, "@media (prefers-reduced-motion: reduce)")
        self.assertRegex(block, r"animation:\s*none")
        reveal_rules = [" ".join(body.split()) for sels, body in css_rules(block)
                        if any("[data-reveal]" in s for s in sels)]
        self.assertTrue(any(re.search(r"opacity:\s*1", b) and re.search(r"transform:\s*none", b)
                            for b in reveal_rules), reveal_rules)

    def test_js_guards(self):
        js = read_js()
        self.assertIn("matchMedia('(prefers-reduced-motion: reduce)')", js)
        self.assertIn("IntersectionObserver", js)
        self.assertIn("'IntersectionObserver' in window", js)

    def test_reveal_variants(self):
        css = read_css()
        expected = {
            '.js [data-reveal="pop"]': r"scale\(\.6\).*rotate\(",
            '.js [data-reveal="left"]': r"translateX\(-60px\)",
            '.js [data-reveal="right"]': r"translateX\(60px\)",
            '.js [data-reveal="rise"]': r"translateY\(60px\)",
        }
        for selector, pattern in expected.items():
            body = _rule(css, selector)
            self.assertIsNotNone(body, selector)
            self.assertRegex(body, pattern, selector)
        visible = _rule(css, ".js [data-reveal].is-visible")
        self.assertRegex(visible, r"opacity:\s*1")
        self.assertRegex(visible, r"transform:\s*none")
        base = _rule(css, ".js [data-reveal]")
        self.assertRegex(base, r"transition:.*var\(--bounce\)")
        self.assertIn("--bounce: cubic-bezier(.34,1.56,.64,1)", css)


class TestScrollEffects(unittest.TestCase):
    """Each section gets its own entrance instead of the same pop/slide everywhere."""

    def setUp(self):
        self.used = [el.attrs["data-reveal"] for el in page().find_all(data_reveal=True)]

    def test_variety(self):
        self.assertGreaterEqual(len(set(self.used)), 10, sorted(set(self.used)))
        most = max(self.used.count(v) for v in set(self.used))
        self.assertLessEqual(most / len(self.used), 0.25)

    def test_every_effect_is_styled(self):
        css = read_css()
        for effect in set(self.used):
            self.assertIn('[data-reveal="%s"]' % effect, css, effect)

    def test_effect_overlays_off_for_reduced_motion(self):
        block = _block_after(read_css(), "@media (prefers-reduced-motion: reduce)")
        for overlay in ('[data-reveal="crt"]::after', '[data-reveal="beam"]::before',
                        '[data-reveal="channel"] .sermon-card__thumb::after'):
            self.assertIn(overlay, block)

    def test_waits_until_partly_on_screen(self):
        self.assertIn("intersectionRatio", read_js())


class TestContact(unittest.TestCase):
    def test_contact(self):
        contact = page().by_id("contact")
        self.assertEqual(len(contact.find_all("a", href="mailto:sethlp114@gmail.com")), 1)
        self.assertEqual(len(contact.find_all("a", href="resume.pdf", download=True)), 1)
        self.assertIn("References available on request", contact.text)
        self.assertIn("Let's do ministry together", contact.text)

    def test_no_tiktok_profile_link(self):
        links = page().by_id("contact").find_all("a", aria_label="TikTok")
        self.assertEqual(links, [])

    def test_assets_exist(self):
        optional = {"videos/hero-preview.mp4"}
        for el in page().find_all():
            for attr in ("src", "poster", "href"):
                ref = el.attrs.get(attr)
                if not ref or ref.startswith(("#", "http", "mailto:")) or ref in optional:
                    continue
                self.assertTrue(exists_exact(ref), f"{el.tag} {attr}={ref} (check capitals too)")

    def test_edit_markers(self):
        self.assertGreaterEqual(page().raw.count("<!-- EDIT:"), 12)

    def test_lazy_images(self):
        hero = page().by_id("top")
        hero_imgs = set(map(id, hero.find_all("img")))
        for img in page().find_all("img"):
            if id(img) not in hero_imgs:
                self.assertEqual(img.attrs.get("loading"), "lazy", img.attrs.get("src"))


if __name__ == "__main__":
    unittest.main()
