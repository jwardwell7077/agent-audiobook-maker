import json
import sys
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[1]
SEED_DIR = ROOT / "seed_pack"
SIZE_LIMIT = 500 * 1024


def load_schema() -> dict:
    with open(SEED_DIR / "schemas" / "seedpack.schema.json", "r", encoding="utf-8") as f:
        return json.load(f)


def main() -> None:
    schema = load_schema()
    errors: list[str] = []

    with open(SEED_DIR / "index.json", "r", encoding="utf-8") as f:
        index = json.load(f)
    jsonschema.validate(index, schema["$defs"]["index"])
    shards = set(index.get("shards", []))

    for path in SEED_DIR.rglob("*.json"):
        rel = path.relative_to(SEED_DIR)
        if rel.as_posix() == "schemas/seedpack.schema.json":
            continue
        if path.stat().st_size > SIZE_LIMIT and str(rel) not in shards:
            errors.append(f"{rel} exceeds 500KB and is not sharded")

    # validate file records
    for path in (SEED_DIR / "files").glob("*.json"):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        jsonschema.validate(data, schema["$defs"]["file_record"])
        if not Path(ROOT / data["file"]).exists():
            errors.append(f"missing file {data['file']}")
        for ev in data.get("evidence", []):
            if not Path(ROOT / ev["file"]).exists():
                errors.append(f"missing evidence file {ev['file']}")
        conf = data.get("confidence", 0)
        if not (0 <= conf <= 1):
            errors.append(f"confidence out of range in {path}")

    # module records
    for path in (SEED_DIR / "modules").glob("*.json"):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        jsonschema.validate(data, schema["$defs"]["module_record"])

    inv_dir = SEED_DIR / "inventories"
    jsonschema.validate(json.load(open(inv_dir / "cli_tools.json", "r", encoding="utf-8")), schema["$defs"]["cli_tools"])
    jsonschema.validate(json.load(open(inv_dir / "env_vars.json", "r", encoding="utf-8")), schema["$defs"]["env_vars"])
    jsonschema.validate(json.load(open(inv_dir / "config_files.json", "r", encoding="utf-8")), schema["$defs"]["config_files"])

    jsonschema.validate(json.load(open(SEED_DIR / "graphs" / "import_graph.json", "r", encoding="utf-8")), schema["$defs"]["import_graph"])
    jsonschema.validate(json.load(open(SEED_DIR / "graphs" / "call_graph.json", "r", encoding="utf-8")), schema["$defs"]["call_graph"])

    jsonschema.validate(json.load(open(SEED_DIR / "schemas_index.json", "r", encoding="utf-8")), schema["$defs"]["schemas_index"])

    if errors:
        for e in errors:
            print(e)
        sys.exit(1)
    print("seed pack valid")


if __name__ == "__main__":
    main()
