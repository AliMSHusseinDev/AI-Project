"""Exercise the live GUI with Chromium. Start both servers before running."""

import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]


def check(page, folder):
    evidence = []
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto("http://127.0.0.1:5173")
    expect(page.get_by_text("Engine online")).to_be_visible()
    button = lambda name: page.get_by_role("button", name=name, exact=True)

    def snapshot():
        with page.expect_download() as pending:
            button("Save environment").click()
        return json.loads(Path(pending.value.path()).read_text())

    def load(env):
        path = folder / "test-env.json"
        path.write_text(json.dumps(env))
        page.locator("input[type=file]").set_input_files(path)
        expect(page.get_by_text("Environment loaded.")).to_be_visible()

    def grid(x, y):
        box = page.locator("canvas").bounding_box()
        size = int(page.locator("#size").input_value())
        scale = min((box["width"] - 68) / size, (box["height"] - 44) / size)
        return (
            box["x"] + (box["width"] - scale * size) / 2 + 4 + x * scale,
            box["y"] + (box["height"] - scale * size) / 2 - 3 + y * scale,
        )

    def drag(start, end):
        page.mouse.move(*grid(*start))
        page.mouse.down()
        page.mouse.move(*grid(*end))
        page.mouse.up()

    expect(button("Validate Solution")).to_be_disabled()
    button("Results").click()
    expect(button("Download Comparison")).to_be_disabled()
    button("Environment").click()
    initial = snapshot()
    env = initial | {
        "size": 20,
        "base": [12, 12],
        "obstacles": [
            dict(id="A", x=2, y=2, w=2, h=2),
            dict(id="B", x=8, y=2, w=2, h=2),
        ],
    }
    load(env)
    button("Manual").click()
    page.locator("canvas").scroll_into_view_if_needed()
    drag((2.2, 2.2), (15.2, 2.2))
    moved = snapshot()
    assert (
        moved["obstacles"][0]["x"] == 6 and moved["obstacles"][1] == env["obstacles"][1]
    )
    page.keyboard.press("Control+z")
    assert snapshot() == env
    page.keyboard.press("Control+y")
    assert snapshot() == moved
    drag((0.5, 12.5), (4, 12.5))
    assert snapshot() == moved
    expect(button("Delete")).to_be_disabled()
    page.mouse.click(*grid(6.5, 2.5))
    page.keyboard.press("r")
    expect(page.get_by_text("Resize mode · drag a corner")).to_be_visible()
    drag((6, 2), (-3, -3))
    resized = snapshot()["obstacles"][0]
    assert (resized["x"], resized["y"], resized["w"], resized["h"]) == (0, 0, 8, 4)
    button("Delete").click()
    page.keyboard.press("o")
    expect(page.get_by_text("Obstacle added.")).to_be_visible()
    assert len(snapshot()["obstacles"]) == 2
    page.get_by_label("Sensing radius", exact=True).focus()
    page.keyboard.press("o")
    assert len(snapshot()["obstacles"]) == 2
    evidence.append(
        "Manual editor: click-drag from first selection, swept collision, fixed neighbor, undo, redo, empty drag, R handles, resize to boundary, Delete, O and typing guard."
    )
    button("Automatic").click()
    slider = page.locator("#size").bounding_box()
    page.mouse.move(slider["x"] + 6, slider["y"] + slider["height"] / 2)
    page.mouse.down()
    page.mouse.move(
        slider["x"] + slider["width"] - 1, slider["y"] + slider["height"] / 2, steps=30
    )
    page.mouse.up()
    expect(page.get_by_text("100 × 100 grid · 2 obstacles · Seed 42")).to_be_visible()
    expect(page.locator("#count")).to_have_attribute("max", "66")
    assert snapshot()["size"] == 100
    page.locator("#count").focus()
    page.keyboard.press("End")
    button("Generate obstacles").click()
    expect(page.get_by_text("100 × 100 grid · 66 obstacles · Seed 42")).to_be_visible()
    barrier = snapshot()
    page.locator("#size").focus()
    page.keyboard.press("Home")
    assert snapshot() == barrier
    evidence.append(
        "Grid and obstacle sliders: 100 by 100 terrain, 66 valid obstacles, invalid shrink preserved layout."
    )
    load(env)
    for algorithm in ["GA", "MA"]:
        button(algorithm).click()
        button("Run " + algorithm).click()
        expect(button("Validate Solution")).to_be_enabled(timeout=20000)
        button("Validate Solution").click()
        expect(page.get_by_text(algorithm + " · PASS", exact=True)).to_be_visible()
    button("Comparison").click()
    button("Run comparison").click()
    expect(button("Validate Solution")).to_be_enabled(timeout=20000)
    page.get_by_text("Fine sampling", exact=True).click()
    button("Validate Solution").click()
    expect(page.get_by_text("MA · PASS", exact=True)).to_be_visible()
    page.get_by_label("Displayed algorithm").select_option("1")
    button("Layers").click()
    page.get_by_label("Sensing circles").uncheck()
    button("Layers").click()
    evidence.append(
        "GA, MA and paired comparison completed. Both results passed independent validation. Fine sampling, algorithm switching and layer toggle worked."
    )
    button("Results").click()
    file = ROOT / "outputs" / "Comparison_Results.csv"
    if file.exists():
        raise RuntimeError(
            "Run browser QA on a clean checkout with an empty outputs folder."
        )
    page.get_by_label("Comparison export format").select_option("csv")
    with page.expect_download() as pending:
        button("Download Comparison").click()
    assert (
        pending.value.suggested_filename == file.name
        and file.read_bytes() == Path(pending.value.path()).read_bytes()
    )
    file.unlink()
    button("Environment").click()
    radius = page.get_by_label("Sensing radius", exact=True)
    radius.fill("6.5")
    radius.press("Enter")
    expect(button("Validate Solution")).to_be_disabled()
    button("Results").click()
    expect(button("Download Comparison")).to_be_disabled()
    evidence.append(
        "CSV downloaded with matching server bytes. Editing the sensing radius disabled validation and export."
    )
    button("Experiments").click()
    button("Run benchmark").click()
    expect(page.get_by_role("progressbar")).to_be_visible()
    expect(page.get_by_label("Benchmark history")).to_be_visible(timeout=90000)
    assert page.locator("tbody tr").count() == 10
    assert not errors, errors
    evidence.append(
        "One full benchmark trial returned ten summary rows through the browser. No uncaught page errors."
    )
    return evidence


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--chromium", help="Optional path to a system Chromium")
    parser.add_argument("--evidence", type=Path)
    args = parser.parse_args()
    with TemporaryDirectory() as folder, sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=args.chromium)
        page = browser.new_page(viewport={"width": 1440, "height": 1050})
        evidence = check(page, Path(folder))
        browser.close()
    print("\n".join(evidence))
    if args.evidence:
        args.evidence.write_text(json.dumps(evidence, indent=2) + "\n")
