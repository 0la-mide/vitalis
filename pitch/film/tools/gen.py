"""Writes index.html and compositions/*.html for the VITALIS film.

Positions come from the real screens (percent of each capture), so taps and clicks land on the real buttons.
Edit numbers here and re-run:  python3 tools/gen.py
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMP = ROOT / "compositions"
COMP.mkdir(exist_ok=True)

PAPER, MINT, TEAL, GREEN, INK, MUTED = "#F6F8F7", "#EEF6F3", "#134E5E", "#0F5C4A", "#14201C", "#4B5A55"
# Phone: bezel 440x920, screen 412x892 (the captures are 780x1688 = 390x844 css at 2x)
SW, SH = 412, 892

FONTS = "\n".join(
    f"@font-face {{ font-family: 'Plex'; src: url('assets/fonts/ibm-plex-sans-latin-{w}-normal.woff2') format('woff2'); font-weight: {w}; }}"
    for w in (400, 500, 600, 700))

BASE_CSS = f"""
{FONTS}
#root {{ position: absolute; inset: 0; overflow: hidden; font-family: 'Plex', sans-serif; color: {INK}; }}
.bg {{ position: absolute; inset: 0; }}
.phone {{ position: absolute; width: 440px; height: 920px; border-radius: 62px; background: #101614; padding: 14px;
  box-shadow: 0 40px 80px rgba(20,32,28,.18); }}
.screen {{ position: relative; width: {SW}px; height: {SH}px; border-radius: 48px; overflow: hidden; background: {PAPER}; }}
.inner {{ position: absolute; left: 0; top: 0; width: {SW}px; height: {SH}px; }}
.inner img {{ position: absolute; left: 0; top: 0; width: {SW}px; height: {SH}px; }}
.tap {{ position: absolute; width: 58px; height: 58px; margin: -29px 0 0 -29px; border-radius: 50%;
  background: rgba(20,32,28,.30); border: 2px solid rgba(255,255,255,.9); opacity: 0; }}
.t {{ position: absolute; margin: 0; font-weight: 700; letter-spacing: -0.02em; line-height: 1.06; }}
.t span, .sub span {{ display: inline-block; }}
.sub {{ position: absolute; margin: 0; font-weight: 500; font-size: 34px; line-height: 1.3; color: {MUTED}; }}
.win {{ position: absolute; overflow: hidden; border-radius: 20px; background: #fff;
  box-shadow: 0 40px 80px rgba(20,32,28,.16); }}
.pan {{ position: absolute; left: 0; top: 0; }}
.pan img {{ position: absolute; left: 0; top: 0; width: 100%; height: 100%; }}
.cursor {{ position: absolute; width: 48px; height: 64px; left: 0; top: 0; opacity: 0; }}
.dim {{ position: absolute; inset: 0; background: rgba(0,0,0,.38); opacity: 0; }}
.sheet {{ position: absolute; left: 10px; right: 10px; bottom: 10px; border-radius: 30px; background: #fff;
  padding: 24px 22px 20px; box-shadow: 0 -10px 40px rgba(0,0,0,.2); opacity: 0; }}
.sheet .host {{ font-size: 22px; color: {MUTED}; }}
.sheet .ask {{ font-size: 28px; font-weight: 600; margin: 8px 0 20px; display: flex; gap: 10px; align-items: center; }}
.sheet .btns {{ display: flex; gap: 10px; }}
.sheet .b {{ flex: 1; text-align: center; padding: 14px 0; border-radius: 16px; font-size: 24px; font-weight: 600;
  background: #EEF2F0; }}
.sheet .b.allow {{ background: {GREEN}; color: #fff; }}
.note {{ position: absolute; left: 10px; right: 10px; top: 12px; border-radius: 26px; background: rgba(255,255,255,.97);
  padding: 16px 18px; box-shadow: 0 16px 40px rgba(0,0,0,.22); display: flex; gap: 14px; opacity: 0; }}
.note img {{ width: 44px; height: 44px; border-radius: 11px; flex: none; }}
.note .app {{ font-size: 14px; color: {MUTED}; font-weight: 600; letter-spacing: .04em; }}
.note .ttl {{ font-size: 19px; font-weight: 700; margin-top: 2px; }}
.note .body {{ font-size: 16px; line-height: 1.3; margin-top: 2px; }}
"""

CURSOR_SVG = (
    '<svg viewBox="0 0 48 64"><path d="M4 3 L4 52 L16 41 L25 61 L33 57 L24 38 L41 38 Z" '
    f'fill="{INK}" stroke="#fff" stroke-width="3" stroke-linejoin="round"/></svg>')

PIN = ('<svg width="26" height="26" viewBox="0 0 24 24"><path d="M12 22s7-7.6 7-13a7 7 0 0 0-14 0c0 5.4 7 13 7 13z" '
       f'fill="none" stroke="{INK}" stroke-width="2"/><circle cx="12" cy="9" r="2.5" fill="{INK}"/></svg>')
BELL = ('<svg width="26" height="26" viewBox="0 0 24 24"><path d="M6 16V11a6 6 0 0 1 12 0v5l2 2H4z M10 20a2 2 0 0 0 4 0" '
        f'fill="none" stroke="{INK}" stroke-width="2" stroke-linejoin="round"/></svg>')


def words(text: str, pid: str) -> str:
    """Words as spans; a lone "|" is a line break."""
    return " ".join("<br>" if w == "|" else f'<span class="{pid}-w">{w}</span>' for w in text.split())


def title(tid: str, text: str, left: int, top: int, size: int = 84, width: int = 860, color: str = INK, cls="t") -> str:
    return (f'<h2 id="{tid}" class="{cls}" style="left:{left}px; top:{top}px; width:{width}px; font-size:{size}px; '
            f'color:{color};">{words(text, tid)}</h2>')


def sub(tid: str, text: str, left: int, top: int, width: int = 760, size: int = 34, color: str = MUTED) -> str:
    return (f'<p id="{tid}" class="sub" style="left:{left}px; top:{top}px; width:{width}px; font-size:{size}px; '
            f'color:{color};">{words(text, tid)}</p>')


def word_in(tid: str, at: float, step: float = 0.067) -> str:
    return (f'tl.fromTo("#{tid} .{tid}-w", {{opacity: 0, filter: "blur(6px)"}}, '
            f'{{opacity: 1, filter: "blur(0px)", duration: 0.13, stagger: {step}, ease: "power2.out"}}, {at});')


def grey_in(tid: str, at: float) -> str:
    return (f'tl.fromTo("#{tid} .{tid}-w", {{color: "#C9D1CE"}}, '
            f'{{color: "{INK}", duration: 0.12, stagger: 0.08, ease: "none"}}, {at});')


def out(sel: str, at: float, d: float = 0.18) -> str:
    return (f'tl.fromTo("{sel}", {{opacity: 1, filter: "blur(0px)"}}, '
            f'{{opacity: 0, filter: "blur(8px)", duration: {d}, ease: "power3.in"}}, {at});')


def phone(pid: str, left: int, top: int, shots: list[str], extra: str = "") -> str:
    imgs = "\n".join(
        f'<img id="{pid}-{i}" src="assets/screens/{s}.png" alt="" style="opacity:{1 if i == 0 else 0};">'
        for i, s in enumerate(shots))
    return (f'<div id="{pid}" class="phone" style="left:{left}px; top:{top}px;"><div class="screen">'
            f'<div id="{pid}-inner" class="inner">{imgs}</div>{extra}</div></div>')


def baseline(*ids: str) -> str:
    """A stable resting state for elements that get more than one fromTo."""
    return "".join(f'tl.set("#{i}", {{opacity: 0}}, 0);' for i in ids)


def tapdot(tid: str) -> str:
    return f'<div id="{tid}" class="tap"></div>'


def tap(tid: str, x: float, y: float, at: float) -> str:
    """x, y in screen px. A soft touch: appear, press, lift."""
    return (f'tl.set("#{tid}", {{left: {x:.1f}, top: {y:.1f}}}, {at - 0.01});'
            f'tl.fromTo("#{tid}", {{opacity: 0, scale: 1.25}}, {{opacity: 1, scale: 0.86, duration: 0.12, ease: "power2.out"}}, {at});'
            f'tl.to("#{tid}", {{opacity: 0, scale: 1, duration: 0.22, ease: "power2.in"}}, {at + 0.16});')


def swap(a: str, b: str, at: float) -> str:
    return (f'tl.fromTo("#{a}", {{opacity: 1, filter: "blur(0px)"}}, {{opacity: 0, filter: "blur(8px)", duration: 0.15, ease: "power2.in"}}, {at});'
            f'tl.fromTo("#{b}", {{opacity: 0, filter: "blur(8px)"}}, {{opacity: 1, filter: "blur(0px)", duration: 0.15, ease: "power2.out"}}, {at + 0.05});')


def sheet(sid: str, ask: str, icon: str) -> str:
    return (f'<div id="{sid}-dim" class="dim"></div><div id="{sid}" class="sheet">'
            f'<div class="host">vitalis.olamide.cloud wants to</div><div class="ask">{icon}{ask}</div>'
            f'<div class="btns"><div class="b">Block</div><div class="b allow">Allow</div></div></div>')


def sheet_in(sid: str, at: float) -> str:
    return (f'tl.fromTo("#{sid}-dim", {{opacity: 0}}, {{opacity: 1, duration: 0.25}}, {at});'
            f'tl.fromTo("#{sid}", {{opacity: 1, y: 260}}, {{y: 0, duration: 0.4, ease: "expo.out"}}, {at});')


def sheet_out(sid: str, at: float) -> str:
    return (f'tl.to("#{sid}", {{y: 280, duration: 0.25, ease: "power3.in"}}, {at});'
            f'tl.to("#{sid}-dim", {{opacity: 0, duration: 0.2}}, {at + 0.05});')


ALLOW_IN_SHEET = (SW - 10 - 22 - (SW - 20 - 44 - 10) / 4, SH - 10 - 20 - 26)  # centre of the Allow button


def crop(natw: float, nath: float, x0: float, y0: float, x1: float, y1: float, width: float):
    """A region of a capture (percent) shown `width` px wide. Returns scale, x, y and the window height."""
    s = width / ((x1 - x0) * natw)
    return s, -x0 * natw * s, -y0 * nath * s, (y1 - y0) * nath * s


def window(wid: str, img: str, natw: float, nath: float, left: int, top: int, width: int, height: float) -> str:
    return (f'<div id="{wid}" class="win" style="left:{left}px; top:{top}px; width:{width}px; height:{height:.0f}px;">'
            f'<div id="{wid}-pan" class="pan" style="width:{natw}px; height:{nath}px;">'
            f'<img src="assets/screens/{img}.png" alt=""></div></div>')


def pan_set(wid: str, s: float, x: float, y: float, at: float = 0) -> str:
    return f'tl.set("#{wid}-pan", {{transformOrigin: "0 0", scale: {s:.4f}, x: {x:.1f}, y: {y:.1f}}}, {at});'


def cursor(cid: str) -> str:
    return f'<div id="{cid}" class="cursor">{CURSOR_SVG}</div>'


def cursor_click(cid: str, frm: tuple, to: tuple, t_in: float, t_click: float) -> str:
    return (f'tl.fromTo("#{cid}", {{opacity: 1, x: {frm[0]}, y: {frm[1]}}}, {{x: {to[0]:.0f}, y: {to[1]:.0f}, duration: 0.6, ease: "power2.inOut"}}, {t_in});'
            f'tl.to("#{cid}", {{scale: 0.85, duration: 0.08, transformOrigin: "10% 5%"}}, {t_click});'
            f'tl.to("#{cid}", {{scale: 1, duration: 0.12}}, {t_click + 0.08});')


def scene(sid: str, body: str, js: str, dur: float, css: str = "") -> None:
    (COMP / f"{sid}.html").write_text(f"""<template>
  <style>
{BASE_CSS}
{css}
  </style>
  <div id="root" data-composition-id="{sid}" data-width="1920" data-height="1080">
{body}
  </div>
  <script>
    const tl = gsap.timeline({{ paused: true }});
    {js}
    tl.set({{}}, {{}}, {dur});
    window.__timelines["{sid}"] = tl;
  </script>
</template>
""")


SCENES: list[tuple[str, float]] = []

# ---------------- s1 night ----------------
digits = "".join(f'<span class="s1-c">{c}</span>' for c in "2:07")
scene("s1", f"""
<div id="s1-bg" class="bg" style="background:{TEAL};"></div>
<div id="s1-time" class="t" style="left:160px; top:200px; font-size:300px; color:#fff; letter-spacing:-0.04em;">{digits}<span class="s1-c" style="font-size:110px; letter-spacing:0; margin-left:24px;">AM</span></div>
{title("s1-l1", "She is 34 weeks pregnant.", 168, 600, 64, 1500, "rgba(255,255,255,.82)")}
{title("s1-l2", "And she is bleeding.", 168, 690, 64, 1500, "#fff")}
""", "\n".join([
    'tl.fromTo("#s1-time .s1-c", {opacity: 0.25, filter: "blur(6px)"}, {opacity: 1, filter: "blur(0px)", duration: 0.2, stagger: 0.1, ease: "power2.out"}, 0.1);',
    word_in("s1-l1", 1.2), word_in("s1-l2", 2.3, 0.09),
    out("#s1-time, #s1-l1, #s1-l2", 3.95, 0.22),
    f'tl.fromTo("#s1-bg", {{backgroundColor: "{TEAL}"}}, {{backgroundColor: "{PAPER}", duration: 0.4, ease: "power2.inOut"}}, 4.1);',
]), 4.5)
SCENES.append(("s1", 4.5))

# ---------------- s2 the old way ----------------
rows = [("Ibara Family Clinic", "No obstetrician on duty"),
        ("Lafenwa General Hospital", "Obstetrician: unknown"),
        ("Ogun Teaching Hospital", "Updated 12 hours ago")]
rows_html = ""
for i, (name, why) in enumerate(rows):
    top = 400 + i * 165
    rows_html += (f'<div id="s2-r{i}" style="position:absolute; left:160px; top:{top}px;">'
                  f'<div style="position:relative; display:inline-block; font-size:56px; font-weight:600; letter-spacing:-0.01em;">{name}'
                  f'<div id="s2-k{i}" style="position:absolute; left:-6px; right:-6px; top:52%; height:5px; background:{INK};"></div></div>'
                  f'<div style="font-size:34px; color:{MUTED}; margin-top:6px;">{why}</div></div>')
js = [grey_in("s2-h", 0.15)]
for i in range(3):
    js.append(f'tl.fromTo("#s2-r{i}", {{opacity: 0, filter: "blur(8px)"}}, {{opacity: 1, filter: "blur(0px)", duration: 0.18}}, {0.55 + i * 0.25});')
    js.append(f'tl.fromTo("#s2-k{i}", {{scaleX: 0, transformOrigin: "0% 50%"}}, {{scaleX: 1, duration: 0.32, ease: "power3.inOut"}}, {2.75 + i * 0.4});')
    js.append(f'tl.to("#s2-r{i}", {{opacity: 0.32, duration: 0.25}}, {3.0 + i * 0.4});')
js.append(f'tl.fromTo("#s2-flood", {{yPercent: 100}}, {{yPercent: 0, duration: 0.55, ease: "power3.inOut"}}, 4.4);')
scene("s2", f"""
<div class="bg" style="background:{PAPER};"></div>
{title("s2-h", "Which hospital can actually help?", 160, 180, 88, 1600)}
{rows_html}
<div id="s2-flood" class="bg" style="background:{GREEN};"></div>
""", "\n".join(js), 5.0)
SCENES.append(("s2", 5.0))

# ---------------- s3 reveal ----------------
letters = "".join(f'<span class="s3-c">{c}</span>' for c in "VITALIS")
scene("s3", f"""
<div id="s3-bg" class="bg" style="background:{GREEN};"></div>
<img id="s3-icon" src="assets/brand/icon.png" alt="" style="position:absolute; left:860px; top:250px; width:200px; height:200px; border-radius:46px; box-shadow:0 30px 60px rgba(0,0,0,.18);">
<div id="s3-word" class="t" style="left:0; width:1920px; top:500px; text-align:center; font-size:150px; color:#fff; letter-spacing:0.02em;">{letters}</div>
{title("s3-tag", "Get the right hospital, fast", 0, 690, 48, 1920, "rgba(255,255,255,.88)")}
""", "\n".join([
    'tl.fromTo("#s3-icon", {opacity: 0, scale: 0.7}, {opacity: 1, scale: 1, duration: 0.6, ease: "back.out(1.4)"}, 0.05);',
    'tl.fromTo("#s3-word .s3-c", {opacity: 0.2, filter: "blur(6px)"}, {opacity: 1, filter: "blur(0px)", duration: 0.18, stagger: 0.06, ease: "power2.out"}, 0.4);',
    word_in("s3-tag", 1.1),
    out("#s3-icon, #s3-word, #s3-tag", 2.5, 0.2),
    f'tl.fromTo("#s3-bg", {{backgroundColor: "{GREEN}"}}, {{backgroundColor: "{PAPER}", duration: 0.4, ease: "power2.inOut"}}, 2.6);',
]), 3.0, css="#s3-tag { text-align: center; font-weight: 500; }")
SCENES.append(("s3", 3.0))

# ---------------- s4 three taps ----------------
PX, PY = 300, 80  # phone position
def scr(xp, yp):  # percent of the capture -> screen px
    return xp * SW, yp * SH
s4_extra = (tapdot("s4-tap") + sheet("s4-sh", "Know your location", PIN))
digits_html = "".join(f'<div style="height:360px;">{n}</div>' for n in range(4))
ax, ay = ALLOW_IN_SHEET
js = [
    baseline("s4-ph-1", "s4-ph-2", "s4-ph-3", "s4-ph-4"),
    'tl.fromTo("#s4-ph", {opacity: 0, y: 220}, {opacity: 1, y: 0, duration: 0.6, ease: "expo.out"}, 0);',
    'tl.set("#s4-dig", {y: -360}, 0);',
    'tl.fromTo("#s4-count", {opacity: 0, filter: "blur(8px)"}, {opacity: 1, filter: "blur(0px)", duration: 0.2}, 1.35);',
    word_in("s4-sub", 1.8), word_in("s4-cap", 3.55),
    tap("s4-tap", *scr(0.26, 0.79), 1.3),
        sheet_in("s4-sh", 1.5),
    tap("s4-tap", ax, ay, 2.35),
    sheet_out("s4-sh", 2.5),
    swap("s4-ph-0", "s4-ph-1", 2.65),
    tap("s4-tap", *scr(0.22, 0.785), 3.45),
    'tl.to("#s4-dig", {y: -720, duration: 0.35, ease: "expo.out"}, 3.5);',
    swap("s4-ph-1", "s4-ph-2", 3.65),
    tap("s4-tap", *scr(0.74, 0.22), 4.6),
    'tl.to("#s4-dig", {y: -1080, duration: 0.35, ease: "expo.out"}, 4.65);',
    swap("s4-ph-2", "s4-ph-3", 4.8),
    out("#s4-count, #s4-cap, #s4-sub", 5.55, 0.2),
    'tl.fromTo("#s4-ph-inner", {scale: 1, transformOrigin: "50% 52%"}, {scale: 1.45, duration: 0.6, ease: "power2.inOut"}, 5.5);',
    word_in("s4-t2", 5.8), word_in("s4-s2", 6.2, 0.06),
]
sx = SW / 2 + (0.42 * SW - SW / 2) * 1.45
sy = 0.52 * SH + (0.645 * SH - 0.52 * SH) * 1.45
js += [tap("s4-tap", sx, sy, 8.0),
       swap("s4-ph-3", "s4-ph-4", 8.2),
       'tl.to("#s4-ph-inner", {scale: 1, duration: 0.5, ease: "power2.inOut"}, 8.2);',
       'tl.to("#s4-ph, #s4-t2, #s4-s2", {x: -420, opacity: 0, filter: "blur(14px)", duration: 0.32, ease: "power3.in"}, 9.1);']
scene("s4", f"""
<div class="bg" style="background:{PAPER};"></div>
{phone("s4-ph", PX, PY, ["P_home", "P_body", "P_symptoms", "P_emergency", "P_waiting"], s4_extra)}
<div id="s4-count" style="position:absolute; left:960px; top:170px; width:260px; height:360px; overflow:hidden;">
  <div id="s4-dig" style="font-size:300px; font-weight:700; line-height:360px; color:{GREEN}; letter-spacing:-0.04em;">{digits_html}</div>
</div>
{title("s4-cap", "taps to an emergency plan", 968, 520, 64, 860)}
{sub("s4-sub", "No account. No typing.", 970, 610)}
{title("s4-t2", "Only hospitals that can treat her", 960, 300, 84, 820)}
{sub("s4-s2", "Matched to the care she needs", 962, 500, 760)}
""", "\n".join(js), 9.5)
SCENES.append(("s4", 9.5))

# ---------------- s5 the hospital accepts ----------------
s, x, y, h = crop(1440, 900, 0.20, 0.07, 0.58, 0.39, 1100)
WL, WT = 160, 330
acc = (WL + (0.33 - 0.20) * 1440 * s, WT + (0.35 - 0.07) * 900 * s)
note = ('<div id="s5-note" class="note"><img src="assets/brand/icon.png" alt=""><div>'
        '<div class="app">VITALIS · NOW</div><div class="ttl">Hospital is ready</div>'
        '<div class="body">Abeokuta Central Hospital is ready for you.</div>'
        '</div></div>')
js = [
    baseline("s5-ph-1"),
    'tl.fromTo("#s5-desk", {x: 420, opacity: 0, filter: "blur(14px)"}, {x: 0, opacity: 1, filter: "blur(0px)", duration: 0.35, ease: "power3.out"}, 0);',
    pan_set("s5-win", s, x, y),
    word_in("s5-h", 0.35),
    cursor_click("s5-cur", (1760, 1080), (acc[0] - 6, acc[1] - 4), 0.9, 1.95),
    'tl.to("#s5-desk", {opacity: 0, duration: 0.01}, 2.05);',
    'tl.fromTo("#s5-ph", {opacity: 0, scale: 1.04}, {opacity: 1, scale: 1, duration: 0.3, ease: "power2.out"}, 2.05);',
    word_in("s5-t", 2.35),
    sheet_in("s5-sh", 2.6),
    tap("s5-tap", ax, ay, 3.15),
    sheet_out("s5-sh", 3.3),
    swap("s5-ph-0", "s5-ph-1", 3.45),
    'tl.fromTo("#s5-note", {opacity: 0, y: -120}, {opacity: 1, y: 0, duration: 0.45, ease: "expo.out"}, 3.6);',
    word_in("s5-s", 3.9, 0.05),
    'tl.to("#s5-ph", {x: -420, opacity: 0, filter: "blur(14px)", duration: 0.3, ease: "power3.in"}, 6.15);',
    out("#s5-t, #s5-s", 6.1, 0.2),
]
scene("s5", f"""
<div id="s5-desk" style="position:absolute; inset:0; background:{MINT};">
  {title("s5-h", "The hospital sees her coming", WL, 160, 76, 1600)}
  {window("s5-win", "D_incoming", 1440, 900, WL, WT, 1100, h)}
  {cursor("s5-cur")}
</div>
<div id="s5-world" style="position:absolute; inset:0;">
  <div class="bg" style="background:{PAPER};"></div>
  {phone("s5-ph", PX, PY, ["P_waiting", "P_accepted"], tapdot("s5-tap") + sheet("s5-sh", "Show notifications", BELL) + note)}
  {title("s5-t", "Accepted before she arrives", 960, 300, 84, 820)}
  {sub("s5-s", "An alert even when the app is closed", 962, 500, 760)}
</div>
""", "\n".join(js), 6.5, css="#s5-world { z-index: 0; } #s5-desk { z-index: 1; }")
SCENES.append(("s5", 6.5))

# ---------------- s6 chemist, reception, NHIA ----------------
ds, dx, dy, dh = crop(752, 118, 0, 0, 1, 1, 1500)
js = [
    baseline("s6-b"),
    'tl.fromTo("#s6-ph", {opacity: 0, y: 220}, {opacity: 1, y: 0, duration: 0.6, ease: "expo.out"}, 0);',
    word_in("s6-t", 0.3), word_in("s6-s", 1.0, 0.05),
    'tl.to("#s6-a", {x: -480, opacity: 0, filter: "blur(14px)", duration: 0.3, ease: "power3.in"}, 3.0);',
    'tl.fromTo("#s6-b", {x: 480, opacity: 0, filter: "blur(14px)"}, {x: 0, opacity: 1, filter: "blur(0px)", duration: 0.35, ease: "power3.out"}, 3.2);',
    pan_set("s6-win", ds, dx, dy),
    word_in("s6-t2", 3.45),
    f'tl.fromTo("#s6-line", {{scaleX: 0, transformOrigin: "0% 50%"}}, {{scaleX: 1, duration: 0.4, ease: "power3.inOut"}}, 4.2);',
    word_in("s6-s2", 4.4, 0.05), word_in("s6-s3", 4.75, 0.05),
    out("#s6-b", 6.8, 0.18),
]
scene("s6", f"""
<div id="s6-a" style="position:absolute; inset:0; background:{PAPER};">
  {phone("s6-ph", 1180, 80, ["P_worker"])}
  {title("s6-t", "The chemist on the corner can start it too", 160, 300, 84, 900)}
  {sub("s6-s", "Walk-in triage and vital signs", 162, 610, 820)}
</div>
<div id="s6-b" style="position:absolute; inset:0; background:{MINT}; opacity:0;">
  {title("s6-t2", "One VITALIS ID. | Her name. Her NHIA number.", 210, 170, 80, 1500)}
  {window("s6-win", "D_details", 752, 118, 210, 520, 1500, dh)}
  <div id="s6-line" style="position:absolute; left:{210 + 0.66 * 1500:.0f}px; top:{520 + dh * 0.9:.0f}px; width:{0.16 * 1500:.0f}px; height:6px; border-radius:3px; background:{GREEN};"></div>
  {sub("s6-s2", "She adds it. Reception can fix it.", 212, 820, 1500)}
  {sub("s6-s3", "NHIA, formerly the NHIS", 212, 880, 1500, 30)}
</div>
""", "\n".join(js), 7.0)
SCENES.append(("s6", 7.0))

# ---------------- s7 doctor and AI ----------------
s1_, x1_, y1_, h1_ = crop(1440, 900, 0.20, 0.13, 0.88, 0.45, 1600)
# punch-in on the safety alert (x 22-86 %, y 27-43 %)
s2_ = 1600 / ((0.86 - 0.22) * 1440) * 1.0
x2_, y2_ = -0.215 * 1440 * s2_, -0.255 * 900 * s2_
ps, px_, py_, ph_ = crop(752, 324, 0, 0, 1, 1, 1300)
js = [
    baseline("s7-b"),
    'tl.fromTo("#s7-a", {opacity: 0, filter: "blur(12px)", scale: 1.04}, {opacity: 1, filter: "blur(0px)", scale: 1, duration: 0.4, ease: "power3.out"}, 0);',
    pan_set("s7-win", s1_, x1_, y1_),
    word_in("s7-t", 0.3),
    f'tl.to("#s7-win-pan", {{scale: {s2_:.4f}, x: {x2_:.1f}, y: {y2_:.1f}, duration: 0.6, ease: "power2.inOut"}}, 1.8);',
    word_in("s7-s", 1.7, 0.05),
    'tl.to("#s7-a", {opacity: 0, filter: "blur(12px)", duration: 0.2, ease: "power3.in"}, 4.0);',
    'tl.fromTo("#s7-b", {opacity: 0, filter: "blur(12px)"}, {opacity: 1, filter: "blur(0px)", duration: 0.25, ease: "power3.out"}, 4.15);',
    pan_set("s7-win2", ps, px_, py_),
    word_in("s7-t2", 4.4), word_in("s7-s2", 4.9, 0.06),
    out("#s7-b", 7.78, 0.2),
]
scene("s7", f"""
<div id="s7-a" style="position:absolute; inset:0; background:{PAPER};">
  {title("s7-t", "It remembers what another hospital wrote", 160, 140, 76, 1600)}
  {window("s7-win", "D_safety", 1440, 900, 160, 300, 1600, h1_)}
  {sub("s7-s", "Allergy recorded at Ogun Teaching Hospital", 162, 820, 1600)}
</div>
<div id="s7-b" style="position:absolute; inset:0; background:{MINT}; opacity:0;">
  {title("s7-t2", "AI suggests. The doctor decides.", 310, 140, 80, 1300)}
  {window("s7-win2", "D_prescribe", 752, 324, 310, 300, 1300, ph_)}
  {sub("s7-s2", "Overriding it needs a reason", 312, 900, 1300)}
</div>
""", "\n".join(js), 8.0)
SCENES.append(("s7", 8.0))

# ---------------- s8 lab and radiology ----------------
ls, lx, ly, lh = crop(1440, 900, 0.19, 0.06, 0.96, 0.36, 1500)
LL, LT = 210, 400
btn = (LL + (0.89 - 0.19) * 1440 * ls, LT + (0.185 - 0.06) * 900 * ls)
js = [
    'tl.fromTo("#s8-win", {y: 160, opacity: 0}, {y: 0, opacity: 1, duration: 0.5, ease: "expo.out"}, 0);',
    pan_set("s8-win", ls, lx, ly),
    word_in("s8-t", 0.25),
    cursor_click("s8-cur", (1900, 1000), (btn[0] - 6, btn[1] - 4), 0.9, 1.95),
    f'tl.fromTo("#s8-done", {{opacity: 0}}, {{opacity: 1, duration: 0.15}}, 2.05);',
    word_in("s8-s", 1.2, 0.06),
    out("#s8-root", 3.75, 0.2),
]
scene("s8", f"""
<div id="s8-root" style="position:absolute; inset:0; background:{MINT};">
  {title("s8-t", "Lab and radiology, each with its own worklist", LL, 170, 76, 1500)}
  {window("s8-win", "D_lab", 1440, 900, LL, LT, 1500, lh)}
  <div id="s8-done" style="position:absolute; left:{btn[0] - 150:.0f}px; top:{btn[1] - 30:.0f}px; width:300px; height:60px; border-radius:10px; background:{GREEN}; color:#fff; font-size:26px; font-weight:600; display:flex; align-items:center; justify-content:center; opacity:0;">Sample collected ✓</div>
  {sub("s8-s", "Verified results go back to the doctor", LL + 2, 860, 1500)}
  {cursor("s8-cur")}
</div>
""", "\n".join(js), 4.0)
SCENES.append(("s8", 4.0))

# ---------------- s9 consent ----------------
js = [
    baseline("s9-ph-1", "s9-ph-2"),
    'tl.fromTo("#s9-ph", {opacity: 0, y: 220}, {opacity: 1, y: 0, duration: 0.6, ease: "expo.out"}, 0);',
    word_in("s9-t", 0.3),
    tap("s9-tap", *scr(0.74, 0.335), 2.2),
    swap("s9-ph-0", "s9-ph-1", 2.4),
    out("#s9-t", 2.5, 0.18), word_in("s9-t2", 2.6), word_in("s9-s2", 2.75, 0.05),
    swap("s9-ph-1", "s9-ph-2", 4.7),
    out("#s9-t2, #s9-s2", 4.6, 0.18), word_in("s9-t3", 4.75),
    'tl.to("#s9-ph, #s9-t3", {x: -420, opacity: 0, filter: "blur(14px)", duration: 0.3, ease: "power3.in"}, 6.2);',
]
scene("s9", f"""
<div class="bg" style="background:{PAPER};"></div>
{phone("s9-ph", PX, PY, ["P_request", "P_wholooked", "P_share"], tapdot("s9-tap"))}
{title("s9-t", "Her record opens only when she says yes", 960, 300, 84, 820)}
{title("s9-t2", "She sees every hospital that looked", 960, 300, 84, 820)}
{sub("s9-s2", "and can stop it any time", 962, 500, 760)}
{title("s9-t3", "Or shares one QR, once", 960, 300, 84, 820)}
""", "\n".join(js), 6.5)
SCENES.append(("s9", 6.5))

# ---------------- s10 montage, claim, mark ----------------
ad_s, ad_x, ad_y, ad_h = crop(1440, 900, 0.19, 0.02, 0.96, 0.45, 1500)
nw_s, nw_x, nw_y, nw_h = crop(752, 358, 0, 0, 1, 1, 1200)
mark_letters = "".join(f"<span>{c}</span>" for c in "VITALIS")
js = [
    'tl.set("#s10-m1", {opacity: 1}, 0); tl.set("#s10-m1", {opacity: 0}, 0.4);',
    'tl.set("#s10-m2", {opacity: 1}, 0.4); tl.set("#s10-m2", {opacity: 0}, 0.8);',
    'tl.set("#s10-m3", {opacity: 1}, 0.8); tl.set("#s10-m3", {opacity: 0}, 1.2);',
    pan_set("s10-w2", ad_s, ad_x, ad_y), pan_set("s10-w3", nw_s, nw_x, nw_y),
    word_in("s10-c1", 1.3, 0.09), word_in("s10-c2", 1.8, 0.09),
    out("#s10-c1, #s10-c2", 4.4, 0.2),
    f'tl.fromTo("#s10-bg", {{backgroundColor: "{PAPER}"}}, {{backgroundColor: "{GREEN}", duration: 0.4, ease: "power2.inOut"}}, 4.45);',
    'tl.fromTo("#s10-icon", {opacity: 0, y: 300}, {opacity: 1, y: 0, duration: 0.6, ease: "expo.out"}, 4.55);',
    'tl.fromTo("#s10-word", {clipPath: "inset(0 100% 0 0)"}, {clipPath: "inset(0 0% 0 0)", duration: 0.5, ease: "power3.out"}, 4.8);',
    word_in("s10-url", 5.1), word_in("s10-fine", 5.25, 0.05),
]
scene("s10", f"""
<div id="s10-bg" class="bg" style="background:{PAPER};"></div>
<div id="s10-m1" style="position:absolute; inset:0; background:#0B1411; opacity:0;">{phone("s10-ph", 740, 80, ["P_home_dark"])}</div>
<div id="s10-m2" style="position:absolute; inset:0; background:{MINT}; opacity:0;">{window("s10-w2", "D_admin", 1440, 900, 210, 160, 1500, ad_h)}</div>
<div id="s10-m3" style="position:absolute; inset:0; background:{PAPER}; opacity:0;">{window("s10-w3", "D_network", 752, 358, 360, 160, 1200, nw_h)}</div>
{title("s10-c1", "From “something is wrong”", 160, 330, 92, 1600)}
{title("s10-c2", "to “a hospital is ready for you.”", 160, 450, 92, 1600, GREEN)}
<img id="s10-icon" src="assets/brand/icon.png" alt="" style="position:absolute; left:545px; top:360px; width:180px; height:180px; border-radius:42px; box-shadow:0 24px 50px rgba(0,0,0,.18); opacity:0;">
<div id="s10-word" class="t" style="left:765px; top:368px; font-size:150px; color:#fff; letter-spacing:0.02em;">{mark_letters}</div>
{title("s10-url", "vitalis.olamide.cloud", 771, 560, 44, 900, "rgba(255,255,255,.92)")}
{sub("s10-fine", "ITDC 2026 · synthetic demo data", 773, 630, 1000, 28, "rgba(255,255,255,.7)")}
""", "\n".join(js), 8.0, css="#s10-word { clip-path: inset(0 100% 0 0); } #s10-url { font-weight: 500; }")
SCENES.append(("s10", 8.0))

# ---------------- index ----------------
hosts, t = [], 0.0
for sid, dur in SCENES:
    hosts.append(f'      <div id="{sid}" data-composition-id="{sid}" data-composition-src="compositions/{sid}.html" '
                 f'data-start="{t:g}" data-duration="{dur:g}" data-track-index="1" data-track-kind="graphics" '
                 f'data-width="1920" data-height="1080" class="clip"></div>')
    t += dur
TOTAL = t
S = dict(SCENES)
starts = {}
acc_t = 0.0
for sid, dur in SCENES:
    starts[sid] = acc_t
    acc_t += dur
sfx = [  # (file, absolute time, volume)
    ("whoosh-short", starts["s1"] + 4.05, 0.45),
    ("whoosh", starts["s2"] + 4.4, 0.5),
    ("pop", starts["s3"] + 0.1, 0.5),
    ("whoosh-short", starts["s3"] + 2.55, 0.4),
    ("click-soft", starts["s4"] + 1.3, 0.7), ("pop", starts["s4"] + 1.36, 0.45),
    ("click-soft", starts["s4"] + 2.35, 0.7),
    ("click-soft", starts["s4"] + 3.45, 0.7), ("pop", starts["s4"] + 3.51, 0.45),
    ("click-soft", starts["s4"] + 4.6, 0.7), ("pop", starts["s4"] + 4.66, 0.45),
    ("click-soft", starts["s4"] + 8.0, 0.7),
    ("whoosh-short", starts["s4"] + 9.1, 0.45),
    ("click", starts["s5"] + 1.95, 0.7),
    ("whoosh", starts["s5"] + 2.0, 0.35),
    ("click-soft", starts["s5"] + 3.15, 0.7),
    ("notification", starts["s5"] + 3.6, 0.5),
    ("whoosh-short", starts["s5"] + 6.15, 0.45),
    ("whoosh", starts["s6"] + 3.0, 0.4),
    ("whoosh-short", starts["s7"] + 0.0, 0.4),
    ("whoosh", starts["s7"] + 4.0, 0.35),
    ("whoosh-short", starts["s8"] + 0.0, 0.4),
    ("click", starts["s8"] + 1.95, 0.7),
    ("click-soft", starts["s9"] + 2.2, 0.7),
    ("whoosh-short", starts["s9"] + 6.2, 0.4),
    ("whoosh-short", starts["s10"] + 0.4, 0.35), ("whoosh", starts["s10"] + 0.8, 0.3),
    ("impact-bass-2", starts["s10"] + 4.45, 0.6),
]
dur_of = {"whoosh-short": 0.57, "whoosh": 0.57, "pop": 0.72, "click-soft": 0.37, "click": 0.37,
          "notification": 2.46, "impact-bass-2": 2.59}
audio = "\n".join(
    f'      <audio id="sfx-{i}" class="clip" src="assets/sfx/{f}.mp3" data-start="{at:.2f}" '
    f'data-duration="{dur_of[f]}" data-track-index="{10 + i % 3}" data-volume="{v}"></audio>'
    for i, (f, at, v) in enumerate(sfx))
(ROOT / "index.html").write_text(f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1920, height=1080" />
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/gsap.min.js"></script>
    <style>
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{ margin: 0; width: 1920px; height: 1080px; overflow: hidden; background: {PAPER}; }}
      #root {{ position: relative; width: 100%; height: 100%; }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{TOTAL:g}" data-width="1920" data-height="1080">
{chr(10).join(hosts)}
{audio}
    </div>
    <script>
      window.__timelines = window.__timelines || {{}};
      window.__timelines["main"] = gsap.timeline({{ paused: true }});
    </script>
  </body>
</html>
""")
print("total", TOTAL, "s; scenes", [s for s, _ in SCENES])
