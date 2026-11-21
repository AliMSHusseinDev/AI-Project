"""Reusable print layout and vector figures for the course submission."""

from math import atan2, cos, sin
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle
from reportlab.graphics.shapes import Drawing, Rect, Ellipse, Line, Polygon, String

ROOT = Path(__file__).resolve().parents[1]
GREEN = colors.HexColor("#1c5947")
INK = colors.HexColor("#223b34")
LIGHT = colors.HexColor("#edf4ef")
GRAY = colors.HexColor("#61746a")
GOLD = colors.HexColor("#ac692d")
WIDTH = 490


def paragraph(text, kind="body"):
    sizes = {
        "title": (25, 29),
        "heading": (13, 16),
        "body": (10.5, 15),
        "small": (9, 13),
        "cell": (9, 12),
    }
    size, leading = sizes[kind]
    bold = kind in ("title", "heading")
    return Paragraph(
        str(text),
        ParagraphStyle(
            kind,
            fontName="Helvetica-Bold" if bold else "Helvetica",
            textColor=GREEN if bold else INK,
            fontSize=size,
            leading=leading,
            spaceBefore=8 if kind == "heading" else 0,
            spaceAfter=8 if kind != "cell" else 0,
        ),
    )


def heading(text):
    return paragraph(text, "heading")


def table(rows, widths):
    data = [[paragraph(cell, "cell") for cell in row] for row in rows]
    result = Table(data, colWidths=widths, hAlign="LEFT", repeatRows=1)
    result.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#d4e5d8")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return result


def save(path, title, content, series="Course documentation"):
    path.parent.mkdir(parents=True, exist_ok=True)

    def frame(canvas, doc):
        w, h = A4
        canvas.setFillColor(GREEN)
        canvas.rect(0, h - 8, w, 8, fill=1, stroke=0)
        canvas.setFont("Helvetica-Bold", 9)
        canvas.drawString(50, h - 40, "FIELDLAB   /   " + series.upper())
        canvas.setFillColor(GRAY)
        canvas.setFont("Helvetica", 9)
        canvas.drawRightString(w - 50, h - 40, "AI310 / CS361    |    Fall 2026")
        canvas.setStrokeColor(colors.HexColor("#ccdbd0"))
        canvas.line(50, 42, w - 50, 42)
        canvas.drawString(50, 27, "Wireless sensor network deployment optimization")
        canvas.drawRightString(w - 50, 27, str(doc.page))

    doc = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        title=title,
        author="Fieldlab project",
        leftMargin=47,
        rightMargin=47,
        topMargin=53,
        bottomMargin=52,
    )
    doc.build(
        [paragraph(title, "title"), *content], onFirstPage=frame, onLaterPages=frame
    )


def label(d, x, y, text, size=9):
    for line_number, line in enumerate(text.split("\n")):
        d.add(
            String(
                x,
                y - line_number * (size + 2),
                line,
                fontName="Helvetica",
                fontSize=size,
                fillColor=INK,
                textAnchor="middle",
            )
        )


def arrow(d, points, caption=None):
    for (x, y), (xx, yy) in zip(points, points[1:]):
        d.add(Line(x, y, xx, yy, strokeColor=GRAY, strokeWidth=1.2))
    (x, y), (xx, yy) = points[-2:]
    angle = atan2(yy - y, xx - x)
    d.add(
        Polygon(
            [
                xx,
                yy,
                xx - 6 * cos(angle - 0.45),
                yy - 6 * sin(angle - 0.45),
                xx - 6 * cos(angle + 0.45),
                yy - 6 * sin(angle + 0.45),
            ],
            fillColor=GRAY,
            strokeColor=GRAY,
        )
    )
    if caption:
        label(d, *caption, 8)


def box(d, x, y, w, h, text, shape="box"):
    if shape == "ellipse":
        node = Ellipse(x, y, w / 2, h / 2)
    elif shape == "diamond":
        node = Polygon([x - w / 2, y, x, y + h / 2, x + w / 2, y, x, y - h / 2])
    else:
        node = Rect(
            x - w / 2,
            y - h / 2,
            w,
            h,
            rx=5 if shape == "process" else 0,
            ry=5 if shape == "process" else 0,
        )
    node.fillColor = LIGHT
    node.strokeColor = GREEN
    d.add(node)
    label(d, x, y - 3 + (len(text.split("\n")) - 1) * 5.5, text)


def flow(memetic):
    d = Drawing(WIDTH, 450)
    steps = [
        ("Start with a fixed environment", "ellipse"),
        ("Build visibility and links. Seed the population.", "box"),
        ("Score deployments and record the best.", "box"),
        ("Stop search?", "diamond"),
        ("Keep two elites. Pick parents by tournament.", "box"),
        ("Cross by region. Mutate sites. Score the child.", "box"),
    ]
    if memetic:
        steps += [
            (
                "On selected children, find holes and islands.\nTry short moves or remove a spare sensor.",
                "process",
            ),
            (
                "Score neighbors. Keep only a lower cost.\nStop after two rounds or at the budget.",
                "process",
            ),
        ]
    steps.append(("Fill the next population within the budget.", "box"))
    center = 155
    for i, (text, shape) in enumerate(steps):
        y = 425 - i * 43
        height = 34 if shape == "diamond" or "\n" in text else 26
        width = 122 if shape == "diamond" else 265
        box(d, center, y, width, height, text, shape)
        if i:
            prev = steps[i - 1]
            previous_height = 34 if prev[1] == "diamond" or "\n" in prev[0] else 26
            arrow(d, [(center, y + 43 - previous_height / 2), (center, y + height / 2)])
        if i == 3:
            label(d, 171, y - 25, "No", 8)
            arrow(d, [(center + 61, y), (345, y)], (280, y + 6, "Yes"))
            box(d, 404, y, 115, 34, "Validate coverage\nand routes", "process")
            arrow(d, [(404, y - 17), (404, y - 45)])
            box(d, 404, y - 59, 120, 28, "Best found result", "ellipse")
    last = 425 - (len(steps) - 1) * 43
    arrow(
        d,
        [(center, last - 13), (center, last - 30), (6, last - 30), (6, 339), (22, 339)],
    )
    return d


def dfd():
    d = Drawing(WIDTH, 227)
    box(d, 55, 187, 82, 32, "Student")
    box(d, 235, 187, 138, 42, "1. Check\nenvironment", "process")
    box(d, 411, 187, 130, 42, "2. Optimize\nand validate", "process")
    arrow(d, [(97, 187), (165, 187)], (131, 193, "settings"))
    arrow(d, [(304, 187), (346, 187)], (325, 193, "terrain"))
    # Parallel horizontal lines are a data store.
    d.add(Line(342, 119, 476, 119, strokeColor=GREEN))
    d.add(Line(342, 91, 476, 91, strokeColor=GREEN))
    label(d, 409, 102, "D1  Run results")
    arrow(d, [(411, 166), (411, 120)], (437, 140, "metrics"))
    box(d, 235, 55, 150, 42, "3. Display results\nor export a table", "process")
    arrow(d, [(411, 91), (411, 55), (311, 55)], (357, 61, "paired results"))
    arrow(d, [(160, 55), (55, 55), (55, 170)], (105, 61, "layout / table"))
    return d


def use_cases():
    d = Drawing(WIDTH, 274)
    d.add(Rect(128, 8, 352, 253, fillColor=None, strokeColor=GRAY))
    label(d, 304, 245, "Fieldlab deployment studio", 10)
    d.add(Ellipse(44, 148, 9, 9, fillColor=LIGHT, strokeColor=INK))
    for x, y, xx, yy in [
        (44, 139, 44, 110),
        (27, 128, 61, 128),
        (44, 110, 31, 92),
        (44, 110, 57, 92),
    ]:
        d.add(Line(x, y, xx, yy, strokeColor=INK))
    label(d, 44, 77, "Student")
    # One association per ellipse. The left rail bundles lines from the same actor.
    names = [
        "Configure environment",
        "Manage obstacles",
        "Generate obstacles",
        "Run GA",
        "Run MA",
        "Compare results",
        "Validate solution",
        "Save / load environment",
        "Download comparison",
    ]
    for i, name in enumerate(names):
        y = 221 - i * 24
        d.add(
            Line(
                62, 127, 206, y, strokeColor=colors.HexColor("#9bada2"), strokeWidth=0.7
            )
        )
        box(d, 307, y, 202, 22, name, "ellipse")
    return d


def architecture():
    d = Drawing(WIDTH, 265)
    box(d, 85, 235, 140, 32, "React + Canvas")
    box(d, 270, 235, 110, 32, "FastAPI jobs")
    arrow(d, [(156, 235), (214, 235)], (185, 242, "requests"))
    box(d, 420, 235, 111, 32, "CSV / PDF / PNG")
    arrow(d, [(326, 235), (364, 235)])
    box(d, 130, 169, 200, 36, "Worker process\nSingle, paired or benchmark run")
    arrow(d, [(270, 219), (270, 169), (231, 169)])
    box(d, 365, 169, 159, 36, "Independent audit\nSeparate geometry + DFS")
    arrow(d, [(231, 179), (284, 179)])
    box(d, 130, 103, 200, 36, "Shared GA engine\nMA adds bounded local search")
    arrow(d, [(130, 151), (130, 122)])
    box(d, 366, 103, 160, 36, "Fitness evaluator\nCoverage + base reachability")
    arrow(d, [(231, 103), (285, 103)])
    box(d, 366, 38, 184, 36, "Environment + geometry\nSite masks and radio neighbors")
    arrow(d, [(366, 85), (366, 57)])
    return d


def convergence(records):
    sample = [r for r in records if r["case"] == "scale40" and r["seed"] == 100]
    d = Drawing(WIDTH, 175)
    low = min(h["cost"] for r in sample for h in r["history"]) - 1
    high = max(h["cost"] for r in sample for h in r["history"]) + 1
    x = lambda n: 50 + n * 4
    y = lambda v: 32 + 112 * (v - low) / (high - low)
    for v in (low, (high + low) // 2, high):
        d.add(Line(50, y(v), 450, y(v), strokeColor=colors.lightgrey))
        label(d, 33, y(v) - 3, str(v), 8)
    for n in (0, 25, 50, 75, 100):
        label(d, x(n), 19, str(n), 8)
    label(d, 244, 4, "Unique fitness evaluations")
    for r, color in zip(sample, (GREEN, GOLD)):
        points = r["history"]
        for first, last in zip(points, points[1:]):
            d.add(
                Line(
                    x(first["evaluations"]),
                    y(first["cost"]),
                    x(last["evaluations"]),
                    y(first["cost"]),
                    strokeColor=color,
                    strokeWidth=2,
                )
            )
            d.add(
                Line(
                    x(last["evaluations"]),
                    y(first["cost"]),
                    x(last["evaluations"]),
                    y(last["cost"]),
                    strokeColor=color,
                    strokeWidth=2,
                )
            )
    label(d, 175, 159, "Best cost   |   GA in green, MA in orange")
    return d


def scale_chart(summary):
    """Mean feasible sensor count with a common zero baseline."""
    d = Drawing(WIDTH, 112)
    scale = 2.05
    origin = 89
    for i, name in enumerate(("scale20", "scale40", "scale60")):
        y = 85 - 29 * i
        label(d, 43, y - 2, name[5:] + " × " + name[5:], 9)
        for algorithm, offset, color in [("GA", 4, GREEN), ("MA", -7, GOLD)]:
            row = next(
                r for r in summary if r["case"] == name and r["algorithm"] == algorithm
            )
            width = scale * row["mean"]
            d.add(Rect(origin, y + offset, width, 7, fillColor=color, strokeColor=None))
            label(d, origin + width + 21, y + offset, row["mean"].__format__(".1f"), 8)
    d.add(Line(origin, 19, origin, 100, strokeColor=GRAY))
    label(d, 245, 5, "Mean active sensors from zero   |   GA in green, MA in orange")
    return d
