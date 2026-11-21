from pathlib import Path
from backend.app.benchmarks import CASES, scenario

if __name__ == "__main__":
    folder = Path(__file__).parent / "scenarios"
    folder.mkdir(exist_ok=True)
    for name in CASES:
        (folder / f"{name}.json").write_text(
            scenario(name).model_dump_json(indent=2) + "\n", encoding="utf8"
        )
