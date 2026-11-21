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
    expect(page.get_by_role("button", name="Generate obstacles")).to_be_enabled()
    assert page.title().startswith("AI Project")
    assert page.locator("nav button").all_text_contents() == ["Environment", "Results"]
    for obsolete in ("Engine online", "Advanced settings", "Fine sampling"):
        expect(page.get_by_text(obsolete, exact=True)).to_have_count(0)
    expect(page.get_by_label("Environment seed", exact=True)).to_be_visible()
    expect(page.get_by_label("Site spacing", exact=True)).to_be_visible()
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

    def stat(label):
        return page.locator("dl").get_by_text(label, exact=True).locator("../dd")

    # One large block can consume the full area without reaching the count cap.
    large = env | {"obstacles": [dict(id="area", x=0, y=0, w=10, h=6)]}
    load(large)
    button("Manual").click()
    expect(stat("Additional obstacles allowed")).to_have_text("0")
    expect(stat("Available monitoring points")).to_have_text("85")
    assert button("Add (O)").is_disabled()
    page.keyboard.press("o")
    expect(page.get_by_text("No additional obstacle fits", exact=False)).to_be_visible()
    page.locator("canvas").scroll_into_view_if_needed()
    page.mouse.click(*grid(5, 3))
    page.keyboard.press("r")
    drag((10, 6), (8, 6))
    expect(stat("Available monitoring points")).to_have_text("88")
    expect(stat("Additional obstacles allowed")).to_have_text("1")
    page.keyboard.press("Control+z")
    expect(stat("Available monitoring points")).to_have_text("85")
    page.keyboard.press("Control+y")
    expect(stat("Additional obstacles allowed")).to_have_text("1")
    evidence.append(
        "Live lattice counts and real addition capacity changed on resize, undo and redo."
    )
    load(env)
    button("Manual").click()
    page.locator("canvas").scroll_into_view_if_needed()
    drag((12.2, 12.7), (12.2, 2.7))
    assert snapshot()["base"] == [12, 2]
    drag((12.2, 2.7), (-1, 2.7))
    assert snapshot()["base"] == [10, 2]
    expect(button("Delete")).to_be_disabled()
    page.mouse.move(*grid(10.5, 2.5))
    page.keyboard.press("r")
    drag((11, 3), (13, 5))
    assert snapshot()["base_margin"] == 0
    page.keyboard.press("Control+z")
    page.keyboard.press("Control+z")
    assert snapshot() == env
    page.mouse.click(*grid(0.5, 0.5))
    page.mouse.click(*grid(12.5, 12.5))
    page.keyboard.press("r")
    drag((13, 13), (15, 15))
    bigger = snapshot()
    assert bigger == env | {"base_margin": 2}
    page.keyboard.press("Control+z")
    assert snapshot() == env
    page.keyboard.press("Control+y")
    assert snapshot() == bigger
    page.keyboard.press("Control+z")
    page.mouse.click(*grid(0.5, 0.5))
    expect(button("Delete")).to_be_disabled()
    evidence.append(
        "Station offset drag, swept collision, R resize around fixed center, footprint collision, mandatory station, undo and redo."
    )
    drag((2.2, 2.2), (15.2, 2.2))
    expect(stat("Blocked sites")).to_have_text("2")
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
    page.locator("#size").scroll_into_view_if_needed()
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
    seed_field = page.get_by_label("Environment seed", exact=True)
    previous = barrier
    for seed in (43, 44, 45):
        button("Generate obstacles").click()
        expect(seed_field).to_have_value(str(seed))
        current = snapshot()
        assert current["obstacles"] != previous["obstacles"]
        assert current["seed"] == seed and len(current["obstacles"]) == 66
        bx, by = current["base"]
        margin = current["base_margin"]
        occupied = {
            (x, y)
            for x in range(bx - margin, bx + margin + 1)
            for y in range(by - margin, by + margin + 1)
        }
        for r in current["obstacles"]:
            cells = {
                (x, y)
                for x in range(r["x"], r["x"] + r["w"])
                for y in range(r["y"], r["y"] + r["h"])
            }
            assert cells.isdisjoint(occupied)
            occupied.update(cells)
        previous = current
    seed_field.fill("42")
    seed_field.press("Enter")
    button("Generate obstacles").click()
    expect(
        page.get_by_text("Obstacles generated with seed 42.", exact=False)
    ).to_be_visible()
    assert snapshot() == barrier
    page.locator("#size").focus()
    page.keyboard.press("Home")
    assert snapshot() == barrier
    evidence.append(
        "At the 66-block cap, three more Generate clicks produced different, overlap-free maps. Re-entering seed 42 reproduced the first map. An invalid grid shrink preserved it."
    )
    load(env)
    for algorithm in ["GA", "MA"]:
        button(algorithm).click()
        expect(page.get_by_label("Local fraction", exact=True)).to_have_count(
            0 if algorithm == "GA" else 1
        )
        button("Run " + algorithm).click()
        expect(button("Validate Solution")).to_be_enabled(timeout=20000)
        button("Validate Solution").click()
        expect(page.get_by_text(algorithm + " · PASS", exact=True)).to_be_visible()
    button("Comparison").click()
    button("Run comparison").click()
    expect(button("Validate Solution")).to_be_enabled(timeout=20000)

    button("Validate Solution").click()
    expect(page.get_by_text("MA · PASS", exact=True)).to_be_visible()
    page.get_by_label("Displayed algorithm").select_option("1")
    button("Layers").click()
    page.get_by_label("Sensing circles").uncheck()
    button("Layers").click()
    evidence.append(
        "GA, MA and paired comparison completed. Both results passed independent validation. Algorithm switching and layer toggle worked."
    )
    button("Results").click()
    for extension, filename in (
        ("csv", "Comparison_Results.csv"),
        ("png", "Comparison_Table.png"),
        ("pdf", "Comparison_Report.pdf"),
    ):
        file = ROOT / "outputs" / filename
        if file.exists():
            raise RuntimeError("Use an empty outputs folder for browser QA.")
        page.get_by_label("Comparison export format").select_option(extension)
        with page.expect_download() as pending:
            button("Download Comparison").click()
        assert (
            pending.value.suggested_filename == filename
            and file.read_bytes() == Path(pending.value.path()).read_bytes()
        )
        file.unlink()
    button("Environment").click()
    page.locator("canvas").scroll_into_view_if_needed()
    drag((12.3, 12.6), (13.3, 13.6))
    assert snapshot()["base"] == [13, 13]
    expect(button("Validate Solution")).to_be_disabled()
    button("Results").click()
    expect(button("Download Comparison")).to_be_disabled()
    evidence.append(
        "Three real browser downloads matched server files. Moving the station invalidated validation and export."
    )
    assert not errors, errors
    evidence.append(
        "Two-page navigation, visible settings, and mode-specific Local fraction checked. No uncaught page errors."
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
