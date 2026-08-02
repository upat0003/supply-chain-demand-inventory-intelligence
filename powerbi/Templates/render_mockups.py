"""Render reproducible portfolio screenshots and annotated wireframes from page metadata.

Pure Python + Pillow, no external chart engine - the same reproducible-build
pattern used across this portfolio's other Power BI mockups, recoloured and
re-laid-out for a graphite/rust/steel supply-chain visual identity so it
reads as a distinct product rather than a reskinned template.
"""
from __future__ import annotations
import json, math, textwrap
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
SPEC = json.loads((Path(__file__).with_name("pages.json")).read_text())
W, H = 1600, 900

# Graphite navigation rail with warm rust/amber and steel-blue accents - a
# warehouse/logistics palette distinct from this portfolio's other builds.
COL = {
    "nav": "#2E3238", "bg": "#F5F3EF", "card": "#FFFFFF", "ink": "#23262B", "muted": "#6E7178",
    "grid": "#E2DED5",
    "rust": "#C1622D", "steel": "#3E6E8E", "moss": "#4C8B6E", "amber": "#D9A227",
    "crimson": "#A23A3A", "slate": "#6E6491",
    "tooltip": "#22252A", "tooltip_text": "#F5F1EA", "chip": "#EFE9E1", "chip_border": "#D8CFC2",
}


def font(size: int, bold: bool = False):
    paths = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
    for p in paths:
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            pass
    return ImageFont.load_default()


def txt(d, xy, s, size=18, fill=None, bold=False, anchor=None):
    d.text(xy, str(s), font=font(size, bold), fill=fill or COL["ink"], anchor=anchor)


def text_w(d, s, size=13, bold=False):
    return d.textlength(str(s), font=font(size, bold))


def card(d, box, title=None):
    d.rounded_rectangle(box, 14, fill=COL["card"], outline=COL["grid"], width=2)
    if title:
        txt(d, (box[0] + 22, box[1] + 18), title, 17, COL["ink"], True)


def legend(d, xy, entries):
    """Row of colour-swatch + label legend entries starting at xy."""
    x, y = xy
    for label, colour in entries:
        c = COL.get(colour, colour)
        d.ellipse((x, y + 3, x + 12, y + 15), fill=c)
        txt(d, (x + 18, y), label, 12, COL["muted"])
        x += 18 + text_w(d, label, 12) + 22


def axis_labels(d, box, labels, ylabel=None):
    x1, y1, x2, y2 = box
    if labels:
        n = len(labels)
        for i, lab in enumerate(labels):
            cx = x1 + (i + 0.5) * (x2 - x1) / n
            txt(d, (cx, y2 + 8), lab, 11, COL["muted"], anchor="ma")
    if ylabel:
        txt(d, (x1 - 4, y1 - 18), ylabel, 11, COL["muted"])


def tooltip_bubble(d, anchor_xy, label, value, bound_left=14, bound_right=W - 14,
                    bound_top=104, bound_bottom=H - 14):
    """Power-BI-style hover tooltip near a data point, with a pointer cursor.

    Centred vertically on the anchor rather than placed only above it, then
    clamped into [bound_top, bound_bottom]. Centring (instead of an
    above-first rule with a single flip-to-below fallback) is what keeps the
    bubble off a neighbouring row in a tightly-packed horizontal bar chart
    *and* off the card title when the anchor sits near the top of a chart -
    one rule handles both cases instead of two special-cased ones.
    """
    ax, ay = anchor_xy
    w = max(130, int(text_w(d, value, 13, True)) + 28)
    bh = 44
    by = ay - bh / 2
    by = max(bound_top, min(by, bound_bottom - bh))
    bx = ax + 16
    if bx + w > bound_right:
        bx = ax - w - 16
    if bx < bound_left:
        bx = bound_left
    d.rounded_rectangle((bx, by, bx + w, by + bh), 8, fill=COL["tooltip"])
    txt(d, (bx + 12, by + 6), label, 11, "#B7ABA0", True)
    txt(d, (bx + 12, by + 22), value, 13, COL["tooltip_text"], True)
    lx = bx + 10 if bx > ax else bx + w - 10
    ly = min(max(ay, by), by + bh)
    d.line((ax, ay, lx, ly), fill=COL["tooltip"], width=2)
    d.ellipse((ax - 5, ay - 5, ax + 5, ay + 5), outline=COL["tooltip"], width=2, fill="white")


def filter_chips(d, right_x, y, chips):
    """Right-aligned row of removable filter-chip pills ending at right_x."""
    widths = [int(text_w(d, label, 13)) + 46 for label in chips]
    x = right_x - sum(widths) - 10 * (len(chips) - 1)
    for label, w in zip(chips, widths):
        d.rounded_rectangle((x, y, x + w, y + 30), 15, fill=COL["chip"], outline=COL["chip_border"], width=1)
        txt(d, (x + 14, y + 7), label, 13, COL["nav"])
        txt(d, (x + w - 20, y + 7), "x", 13, COL["muted"], True)
        x += w + 10


def line_chart(d, box, accent, points, highlight_idx=None):
    x1, y1, x2, y2 = box
    d.line((x1, y2, x2, y2), fill=COL["grid"], width=2)
    d.line((x1, y1, x1, y2), fill=COL["grid"], width=2)
    coords = []
    for i, p in enumerate(points):
        coords.append((x1 + i * (x2 - x1) / (len(points) - 1), y2 - p * (y2 - y1)))
    d.line(coords, fill=accent, width=5, joint="curve")
    for i, (x, y) in enumerate(coords):
        r = 7 if i == highlight_idx else 4
        d.ellipse((x - r, y - r, x + r, y + r), fill=accent, outline="white" if i == highlight_idx else None,
                   width=3 if i == highlight_idx else 0)
    return coords[highlight_idx if highlight_idx is not None else -1]


def bars(d, box, values, colors=None, horizontal=False, highlight_idx=None, labels=None, show_values=False):
    """Vertical or horizontal bars, optionally with a value label per bar.

    A bar narrower (vertical) or shallower (horizontal) than ~90px is never
    given centred text - that overflows a thin bar. Instead it gets a small
    colour swatch plus the value printed beside the bar, outside its bounds.
    """
    x1, y1, x2, y2 = box
    colors = colors or [COL["steel"]] * len(values)
    anchor = (x1, y1)
    if horizontal:
        gap = (y2 - y1) / len(values)
        bar_h = gap - 10
        for i, v in enumerate(values):
            b = (x1, y1 + i * gap + 5, x1 + v * (x2 - x1), y1 + (i + 1) * gap - 5)
            outline = COL["ink"] if i == highlight_idx else None
            d.rounded_rectangle(b, 5, fill=colors[i % len(colors)], outline=outline, width=3 if outline else 0)
            # category label sits in the reserved left margin (before x1), so it
            # never competes with the value label at the bar's own end
            if labels:
                txt(d, (x1 - 12, (b[1] + b[3]) / 2), labels[i], 11, COL["ink"], anchor="rm")
            if show_values:
                val_text = f"{int(round(v * 100))}%"
                if bar_h >= 22 and (b[2] - b[0]) >= 46:
                    txt(d, ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2), val_text, 12, "white", True, anchor="mm")
                else:
                    d.ellipse((b[2] + 8, (b[1] + b[3]) / 2 - 5, b[2] + 18, (b[1] + b[3]) / 2 + 5),
                              fill=colors[i % len(colors)])
                    txt(d, (b[2] + 24, (b[1] + b[3]) / 2), val_text, 11, COL["ink"], anchor="lm")
            if i == highlight_idx:
                anchor = (b[2], (b[1] + b[3]) / 2)
    else:
        gap = (x2 - x1) / len(values)
        bar_w = gap - 16
        for i, v in enumerate(values):
            b = (x1 + i * gap + 8, y2 - v * (y2 - y1), x1 + (i + 1) * gap - 8, y2)
            outline = COL["ink"] if i == highlight_idx else None
            d.rounded_rectangle(b, 6, fill=colors[i % len(colors)], outline=outline, width=3 if outline else 0)
            if show_values:
                val_text = f"{int(round(v * 100))}%"
                if bar_w >= 34 and (b[3] - b[1]) >= 30:
                    txt(d, ((b[0] + b[2]) / 2, b[1] + 15), val_text, 12, "white", True, anchor="mm")
                else:
                    # narrow bar: small colour swatch + value printed above the
                    # bar rather than centred text, which would overflow it
                    sw_x = (b[0] + b[2]) / 2 - 4
                    d.ellipse((sw_x, b[1] - 20, sw_x + 8, b[1] - 12), fill=colors[i % len(colors)])
                    txt(d, ((b[0] + b[2]) / 2, b[1] - 24), val_text, 11, COL["ink"], anchor="mb")
            if i == highlight_idx:
                anchor = ((b[0] + b[2]) / 2, b[1])
    return anchor


def donut(d, box, parts, highlight_idx=None):
    total = sum(parts)
    start = -90
    colors = [COL["rust"], COL["steel"], COL["moss"], COL["amber"], COL["slate"]]
    anchor = None
    for i, v in enumerate(parts):
        end = start + 360 * v / total
        width = 34 if i == highlight_idx else 28
        d.arc(box, start, end, fill=colors[i % len(colors)], width=width)
        if i == highlight_idx:
            mid = math.radians((start + end) / 2)
            cx = (box[0] + box[2]) / 2
            cy = (box[1] + box[3]) / 2
            r = (box[2] - box[0]) / 2
            anchor = (cx + (r + 24) * math.cos(mid), cy + (r + 24) * math.sin(mid))
        start = end
    return anchor or ((box[0] + box[2]) / 2, box[1])


def heatmap(d, box, rows=5, cols=7, highlight=(1, 2)):
    x1, y1, x2, y2 = box
    cw = (x2 - x1) / cols
    ch = (y2 - y1) / rows
    palette = ["#F3E7DA", "#E3C29A", "#D19B60", "#C1622D", "#8C4520"]
    anchor = (x1, y1)
    for r in range(rows):
        for c in range(cols):
            cell = (x1 + c * cw, y1 + r * ch, x1 + (c + 1) * cw - 3, y1 + (r + 1) * ch - 3)
            d.rectangle(cell, fill=palette[(r * 3 + c * 2) % 5])
            if (r, c) == highlight:
                d.rectangle(cell, outline=COL["ink"], width=3)
                anchor = (cell[2], cell[1])
    return anchor


def table(d, box, rows, columns=None, highlight_row=0):
    x1, y1, x2, y2 = box
    h = (y2 - y1) / (rows + 1)
    d.rectangle((x1, y1, x2, y1 + h), fill="#EDE7DE")
    columns = columns or ["Item", "Status", "Age", "Owner"]
    ncols = len(columns)
    colw = (x2 - x1 - 42) / max(ncols - 1, 1)
    txt(d, (x1 + 42, y1 + h / 2), columns[0], 12, COL["nav"], True, anchor="lm")
    for ci, cname in enumerate(columns[1:]):
        txt(d, (x1 + 42 + ci * colw + (x2 - x1 - 42) * 0.55, y1 + h / 2), cname, 12, COL["nav"], True, anchor="lm")
    anchor = (x1, y1 + h)
    for r in range(rows):
        y = y1 + (r + 1) * h
        d.line((x1, y, x2, y), fill=COL["grid"], width=1)
        row_box = (x1, y, x2, y + h)
        if r == highlight_row:
            d.rectangle(row_box, fill="#F7F2EA")
        d.ellipse((x1 + 14, y + 12, x1 + 26, y + 24), fill=[COL["crimson"], COL["amber"], COL["moss"]][r % 3])
        d.rounded_rectangle((x1 + 42, y + 12, x1 + 230 + (r % 3) * 60, y + 21), 4, fill="#C9BFAF")
        d.rounded_rectangle((x2 - 180, y + 12, x2 - 35, y + 21), 4, fill="#DAD2C2")
        if r == highlight_row:
            d.rectangle(row_box, outline=COL["ink"], width=2)
            anchor = (x1 + 230 + (r % 3) * 60, y + 16)
    return anchor


def _shape(n, peak_at=None):
    """Deterministic illustrative values of length n with one clear peak, so
    every chart's bar/heatmap count can be sized to match however many axis
    labels a given page actually needs, instead of a hardcoded count that
    only happens to fit some pages."""
    if n <= 0:
        return [0.5]
    peak = peak_at if peak_at is not None else max(n - 2, 0)
    return [max(0.16, 0.90 - abs(i - peak) * 0.15 + (0.04 if i % 2 == 0 else 0)) for i in range(n)]


def _highlight_index(labels, tip, default=None):
    if labels and tip:
        label = str(tip.get("label", "")).lower()
        for i, l in enumerate(labels):
            l = str(l).lower()
            if l and (l in label or label in l):
                return i
    if default is not None:
        return default
    return max(len(labels) - 2, 0) if labels else 0


def _legend_colors(legend_entries, fallback=None):
    """Resolve a page's own chart legend entries to actual fill colours, so a
    chart's bars are always drawn in exactly the colours its legend names -
    never a hardcoded palette that happens to drift out of sync with it."""
    fallback = fallback or [COL["steel"], COL["rust"], COL["amber"], COL["moss"], COL["crimson"]]
    resolved = [COL.get(c[1], c[1]) for c in legend_entries if len(c) > 1]
    return resolved or fallback


def _risk_colors(values):
    return [COL["crimson"] if v >= 0.8 else COL["amber"] if v >= 0.55 else COL["moss"] for v in values]


def render(page, idx, annotated=False):
    im = Image.new("RGB", (W, H), COL["bg"])
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, 238, H), fill=COL["nav"])
    txt(d, (30, 30), SPEC["short_title"], 23, "white", True)
    for i, p in enumerate(SPEC["pages"]):
        y = 104 + i * 58
        if i == idx:
            d.rounded_rectangle((18, y - 10,220, y + 34), 10, fill="#454B53")
        txt(d, (34, y), f"{i + 1:02d}  {p['nav']}", 15, "white" if i == idx else "#B7BCC2", i == idx)
    txt(d, (278, 30), page["title"], 30, COL["ink"], True)
    txt(d, (278, 72), page["question"], 16, COL["muted"])
    filter_chips(d, 1565, 26, ["Period: Latest 13 weeks", "Model: demand_gbm v1.0.0", "Region: All"])
    for i, k in enumerate(page["kpis"]):
        x = 278 + i * 310
        card(d, (x, 112, x + 285, 220))
        txt(d, (x + 20, 132), k[0], 14, COL["muted"], True)
        txt(d, (x + 20, 164), k[1], 28, k[3], True)
        txt(d, (x + 20, 198), k[2], 13, COL["muted"])
    layout = page["layout"]
    # Row-1 chart cards all share the same vertical band (246-565). The
    # tooltip's top/bottom clamp is scoped to that band - specifically below
    # this card's own title - so a highlighted mark near the top of a chart
    # can never push its callout up into that card's title text.
    ROW1_TOP, ROW1_BOTTOM = 296, 555
    tips = []  # (anchor, tooltip_meta, bound_left, bound_right, bound_top, bound_bottom)
    if layout == "trend":
        card(d, (278, 246, 1010, 565), page["visuals"][0])
        a1 = line_chart(d, (322, 320, 966, 495), COL["rust"],
                         [.28, .34, .31, .43, .48, .45, .57, .61, .67, .63, .74, .80, .855], highlight_idx=12)
        axis_labels(d, (322, 320, 966, 495), page.get("chart1_xlabels"), page.get("chart1_ylabel"))
        legend(d, (322, 529), page.get("chart1_legend", []))
        tips.append((a1, page.get("tooltip1"), 300, 1000, ROW1_TOP, ROW1_BOTTOM))
        card(d, (1034, 246, 1565, 565), page["visuals"][1])
        labels2 = page.get("chart2_xlabels") or ["A", "B", "C", "D", "E"]
        hi2 = _highlight_index(labels2, page.get("tooltip2"))
        vals2 = _shape(len(labels2), peak_at=hi2)
        # bar colours are read straight from this page's own legend definition
        # (cycled if there are more bars than legend entries) so the legend
        # is never wrong about what a bar's colour means.
        colors2 = _legend_colors(page.get("chart2_legend", []))
        a2 = bars(d, (1155, 320, 1518, 495), vals2,
                  colors2, True, highlight_idx=hi2, labels=labels2,
                  show_values=True)
        axis_labels(d, (1155, 320, 1518, 495), None, page.get("chart2_ylabel"))
        legend(d, (1080, 529), page.get("chart2_legend", []))
        tips.append((a2, page.get("tooltip2"), 1056, 1555, ROW1_TOP, ROW1_BOTTOM))
    elif layout == "matrix":
        card(d, (278, 246, 1030, 565), page["visuals"][0])
        labels1 = page.get("chart1_xlabels") or ["A", "B", "C", "D", "E", "F", "G"]
        a1 = heatmap(d, (322, 320, 986, 495), cols=len(labels1))
        axis_labels(d, (322, 320, 986, 495), labels1, page.get("chart1_ylabel"))
        legend(d, (322, 529), page.get("chart1_legend", []))
        tips.append((a1, page.get("tooltip1"), 300, 1020, ROW1_TOP, ROW1_BOTTOM))
        card(d, (1054, 246, 1565, 565), page["visuals"][1])
        n_parts = max(len(page.get("chart2_legend", [])) or 5, 3)
        parts = _shape(n_parts, peak_at=0)
        a2 = donut(d, (1168, 318, 1428, 510), parts, highlight_idx=0)
        legend(d, (1168, 522), page.get("chart2_legend", []))
        tips.append((a2, page.get("tooltip2"), 1076, 1555, ROW1_TOP, ROW1_BOTTOM))
    elif layout == "distribution":
        card(d, (278, 246, 930, 565), page["visuals"][0])
        labels1 = page.get("chart1_xlabels") or ["A", "B", "C", "D", "E", "F"]
        hi1 = _highlight_index(labels1, page.get("tooltip1"))
        vals1 = _shape(len(labels1), peak_at=hi1)
        a1 = bars(d, (320, 325, 888, 495), vals1, _risk_colors(vals1),
                  highlight_idx=hi1, labels=labels1, show_values=True)
        axis_labels(d, (320, 325, 888, 495), labels1, page.get("chart1_ylabel"))
        legend(d, (320, 529), page.get("chart1_legend", []))
        tips.append((a1, page.get("tooltip1"), 298, 920, ROW1_TOP, ROW1_BOTTOM))
        card(d, (954, 246, 1565, 565), page["visuals"][1])
        line_color2 = _legend_colors(page.get("chart2_legend", []), fallback=[COL["steel"]])[0]
        a2 = line_chart(d, (1002, 325, 1518, 495), line_color2,
                         [.18, .26, .39, .35, .52, .64, .71, .76, .74], highlight_idx=8)
        axis_labels(d, (1002, 325, 1518, 495), page.get("chart2_xlabels"), page.get("chart2_ylabel"))
        legend(d, (1002, 529), page.get("chart2_legend", []))
        tips.append((a2, page.get("tooltip2"), 976, 1555, ROW1_TOP, ROW1_BOTTOM))
    else:
        card(d, (278, 246, 1565, 565), page["visuals"][0])
        a1 = table(d, (310, 310, 1533, 535), 5, page.get("table_xlabels"), highlight_row=0)
        legend(d, (310, 548), page.get("table_legend", []))
        tips.append((a1, page.get("tooltip1"), 298, 1555, ROW1_TOP, ROW1_BOTTOM))
    card(d, (278, 590, 905, 850), page["visuals"][2])
    colors3 = _legend_colors(page.get("chart3_legend", []))
    a3 = bars(d, (320, 660, 860, 812), [.82, .63, .48, .71, .39],
              colors3, True, highlight_idx=0, show_values=True)
    legend(d, (320, 826), page.get("chart3_legend", []))
    card(d, (929, 590, 1565, 850), "What this means")
    for i, line in enumerate(textwrap.wrap(page["story"], 54)):
        txt(d, (963, 654 + i * 30), line, 18, COL["ink"])
    for anchor, tip, bl, br, bt, bb in tips:
        if anchor and tip:
            tooltip_bubble(d, anchor, tip.get("label", ""), tip.get("value", ""), bl, br, bt, bb)
    if annotated:
        overlay = Image.new("RGBA", (W, H), (255, 255, 255, 80))
        im = Image.alpha_composite(im.convert("RGBA"), overlay)
        d = ImageDraw.Draw(im)
        notes = [((250, 102), "1", "Headline KPIs"), ((250, 242), "2", "Primary decision view"),
                 ((905, 585), "3", "Narrative and action"), ((850, 6), "4", "Filter chips"),
                 ((1080, 345), "6", "Cross-filter highlight"),
                 ((1080, 400), "5", "Hover tooltip")]
        for (x, y), n, label in notes:
            d.ellipse((x, y, x + 34, y + 34), fill="#A23A3A")
            txt(d, (x + 17, y + 17), n, 16, "white", True, "mm")
            txt(d, (x + 43, y + 7), label, 15, "#7A2828", True)
    return im.convert("RGB")


def main():
    shots = ROOT / "powerbi/Screenshots"
    mocks = ROOT / "powerbi/Mockups"
    shots.mkdir(parents=True, exist_ok=True)
    mocks.mkdir(parents=True, exist_ok=True)
    for i, page in enumerate(SPEC["pages"]):
        slug = f"{i + 1:02d}_{page['slug']}"
        render(page, i).save(shots / f"{slug}.png", optimize=True)
        render(page, i, True).save(mocks / f"{slug}_annotated.png", optimize=True)
    print(f"Rendered {len(SPEC['pages'])} screenshots and {len(SPEC['pages'])} annotated mockups")


if __name__ == "__main__":
    main()
