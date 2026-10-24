"""Real browser interaction, JSON download, and responsive layout check.

Start python -m wsn serve first. Requires optional Playwright and Chromium.
"""

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from playwright.sync_api import sync_playwright
from wsn.verify import verify_result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base-url', default='http://127.0.0.1:8000')
    parser.add_argument('--screenshot', default='results/local/demo.png')
    args = parser.parse_args()
    errors = []
    with sync_playwright() as p:
        executable = shutil.which('chromium') or shutil.which('google-chrome')
        browser = p.chromium.launch(executable_path=executable, headless=True,
                                    args=['--no-sandbox', '--disable-dev-shm-usage'])
        page = browser.new_page(viewport={'width': 1440, 'height': 1150}, device_scale_factor=1)
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(args.base_url, wait_until='networkidle')
        for algorithm in ('ga', 'ma'):
            page.select_option('#terrain', 'two_walls')
            page.select_option('#algorithm', algorithm)
            page.fill('#seed', '11')
            page.fill('#generations', '70')
            with page.expect_response('**/api/solve') as pending:
                page.click('#run')
            response = pending.value
            assert response.ok, response.text()
            result = response.json()
            assert verify_result(result)['feasible']
            page.wait_for_function("document.getElementById('status').textContent.startsWith('Feasible layout.')")
            assert page.locator('#sensors').inner_text() == str(result['metrics']['sensors'])
            with page.expect_download() as download:
                page.click('#download')
            saved = json.loads(Path(download.value.path()).read_text())
            assert saved['coordinates'] == result['coordinates']
            assert verify_result(saved)['feasible']
            print(algorithm.upper(), 'browser solve and download passed:', result['metrics'], flush=True)
        screenshot = Path(args.screenshot)
        screenshot.parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(screenshot), full_page=True)
        for width in (1440, 768, 390):
            page.set_viewport_size({'width': width, 'height': 900})
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), f'Layout overflows at width {width}'
        assert not errors, errors
        browser.close()
    print('Browser checks passed: GA, MA, downloads, three screen widths, and no JavaScript errors.')


if __name__ == '__main__':
    main()
