import json
from pathlib import Path

from app.main import app


def main() -> None:
    root_dir = Path(__file__).resolve().parents[3]
    output_path = root_dir / "packages" / "shared" / "openapi.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        f"{json.dumps(app.openapi(), indent=2, sort_keys=True)}\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
