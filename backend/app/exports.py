import csv
import io
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from PIL import Image, ImageDraw, ImageFont
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer
from reportlab.lib.styles import getSampleStyleSheet

OUTPUT = Path(__file__).resolve().parents[2] / "outputs"
FILES = {
    "csv": ("Comparison_Results.csv", "text/csv"),
    "pdf": ("Comparison_Report.pdf", "application/pdf"),
    "png": ("Comparison_Table.png", "image/png"),
}


def comparison_rows(results):
    def column(r):
        return [
            "Feasible" if r["feasible"] else "Infeasible",
            r["count"],
            round(r["coverage"], 3),
            r["monitoring_mode"].title(),
            f"{r['monitoring_count'] - len(r['holes'])} / {r['monitoring_count']}",
            round(r["connectivity"], 3),
            len(r["unreachable"]),
            round(r["seconds"], 4),
            r["evaluations"],
            r["generations"],
            r["termination"],
            r["cost"],
            r["local"]["improvements"] if r["algorithm"] == "MA" else "—",
        ]

    metrics = [
        "Solution status",
        "Active sensors",
        "Monitoring coverage (%)",
        "Monitoring mode",
        "Covered / required points",
        "Connectivity (%)",
        "Disconnected sensors",
        "Execution time (s)",
        "Unique fitness evaluations",
        "Generations completed",
        "Termination reason",
        "Best cost",
        "MA local improvements",
    ]
    return [
        ["Metric", "GA", "MA"],
        *map(list, zip(metrics, column(results[0]), column(results[1]))),
    ]


def font(size):
    for filename in ("DejaVuSans.ttf", "arial.ttf"):
        try:
            return ImageFont.truetype(filename, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


def export(results, format, directory=None):
    rows = comparison_rows(results)
    buffer = io.BytesIO()
    if format == "csv":
        table = io.StringIO(newline="")
        csv.writer(table).writerows(rows)
        buffer.write(table.getvalue().encode("utf-8"))
    elif format == "pdf":
        styles = getSampleStyleSheet()
        table = Table(rows, colWidths=[197, 115, 115], rowHeights=28)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#254d83")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [colors.white, colors.HexColor("#eff6f5")],
                    ),
                ]
            )
        )
        SimpleDocTemplate(buffer, title="Deployment comparison").build(
            [
                Paragraph("GA and MA deployment comparison", styles["Title"]),
                Spacer(1, 12),
                Paragraph(
                    f"Environment {results[0]['environment_id']} | Algorithm seed {results[0]['seed']}",
                    styles["Normal"],
                ),
                Spacer(1, 20),
                table,
            ]
        )
    else:
        image = Image.new("RGB", (1120, 72 * len(rows)), "white")
        draw = ImageDraw.Draw(image)
        for index, row in enumerate(rows):
            top = index * 72
            color = (
                "#254d83" if index == 0 else ("#edf5f2" if index % 2 == 0 else "white")
            )
            draw.rectangle((0, top, 1120, top + 71), fill=color)
            for left, value in zip((25, 450, 785), row):
                draw.text(
                    (left, top + 17),
                    str(value),
                    font=font(29),
                    fill="white" if index == 0 else "#193c37",
                )
        image.save(buffer, "PNG")
    directory = directory or OUTPUT
    directory.mkdir(exist_ok=True, parents=True)
    filename, media = FILES[format]
    data = buffer.getvalue()
    with NamedTemporaryFile(dir=directory, delete=False) as temp:
        temp.write(data)
    os.replace(temp.name, directory / filename)
    return data, filename, media
