"""Reproduce the five published comparisons through the running local web interface."""

import argparse
import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

CASES = [(20, 0), (20, 2), (40, 0), (40, 8), (60, 18)]


def exercise(page):
    page.goto("http://127.0.0.1:5173")
    button = lambda name: page.get_by_role("button", name=name, exact=True)
    expect(button("Generate obstacles")).to_be_enabled()
    records = []

    def number(label, value):
        field = page.get_by_label(label, exact=True)
        field.fill(str(value))
        field.press("Enter")
        expect(field).to_have_value(str(value))

    def generate(count):
        slider = page.locator("#count")
        slider.press("Home")
        for _ in range(count):
            slider.press("ArrowRight")
        with page.expect_response(lambda r: r.url.endswith("/api/generate")) as reply:
            button("Generate obstacles").click()
        assert reply.value.ok
        env = reply.value.json()
        assert len(env["obstacles"]) == count
        return env

    for index, (size, count) in enumerate(CASES, 1):
        button("Automatic").click()
        button("Automatic monitoring points").click()
        generate(0)
        number("Grid size value", size)
        number("Base station X", size // 2)
        number("Base station Y", size // 2)
        for label, value in [
            ("Environment seed", 42),
            ("Site spacing", 2),
            ("Sensing radius", 5.5),
            ("Communication radius", 8),
        ]:
            number(label, value)
        env = generate(count)
        button("Comparison").click()
        for label, value in [
            ("Algorithm seed", 7),
            ("Evaluation budget", 600),
            ("Population", 18),
            ("Generations", 40),
            ("Local fraction", 0.45),
        ]:
            number(label, value)
        with page.expect_response(
            lambda r: r.url.endswith("/api/jobs") and r.request.method == "POST"
        ) as job:
            button("Run comparison").click()
        job_url = job.value.url + "/" + job.value.json()["id"]
        expect(button("Validate Solution")).to_be_enabled(timeout=120000)
        with page.expect_response(lambda r: r.url == job_url + "/validate") as audit:
            button("Validate Solution").click()
        audits = audit.value.json()
        response = page.request.get(job_url).json()
        assert response["state"] == "complete"
        results = response["result"]
        button("Results").click()
        for label, key in [
            ("Active sensors", "count"),
            ("Unique fitness evaluations", "evaluations"),
            ("Generations completed", "generations"),
            ("Termination reason", "termination"),
        ]:
            cells = (
                page.get_by_role("row")
                .filter(has=page.get_by_role("cell", name=label, exact=True))
                .locator("td")
            )
            expect(cells.nth(1)).to_have_text(str(results[0][key]))
            expect(cells.nth(2)).to_have_text(str(results[1][key]))
        records.append(
            dict(experiment=index, environment=env, results=results, validation=audits)
        )
        print(
            index,
            size,
            count,
            [
                (r["count"], r["evaluations"], r["termination"], a["passed"])
                for r, a in zip(results, audits)
            ],
            flush=True,
        )
        button("Environment").click()
    return records


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--chromium")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=args.chromium)
        data = exercise(browser.new_page(viewport={"width": 1440, "height": 1000}))
        browser.close()
    args.out.write_text(json.dumps(data, separators=(",", ":")) + "\n", encoding="utf8")
