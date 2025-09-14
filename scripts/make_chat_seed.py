import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SP = ROOT / "seed_pack"
OUT_DIR = ROOT / "docs" / "chat_seed"


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _build_doc(limit_bytes: int, cli_limit: int) -> str:
    idx = _load_json(SP / "index.json")
    import_graph = _load_json(SP / "graphs" / "import_graph.json")
    cli_tools = _load_json(SP / "inventories" / "cli_tools.json")
    schemas = _load_json(SP / "schemas_index.json")
    modules_info = []
    modules_dir = SP / "modules"
    for mp in sorted(modules_dir.glob("*.json"))[:10]:
        data = _load_json(mp)
        modules_info.append((mp.stem, data.get("purpose", "")))
    parts = []
    parts.append("# Chat Seed\n")
    parts.append("## Primer\nThis project seed pack provides context for a GPT-5 subject-matter expert.\n")
    nodes = import_graph.get("nodes", [])[:10]
    edges = [e for e in import_graph.get("edges", []) if e["from"] in nodes and e["to"] in nodes][:10]
    mermaid_lines = ["graph LR"]
    for e in edges:
        mermaid_lines.append(f"{e['from'].replace('.', '_')}-->{e['to'].replace('.', '_')}")
    parts.append("## Pipeline\n```mermaid\n" + "\n".join(mermaid_lines) + "\n```\n")
    mod_lines = [f"- **{m}**: {p}" for m, p in modules_info]
    parts.append("## Top Modules\n" + "\n".join(mod_lines) + "\n")
    cli_lines = []
    for c in cli_tools[:cli_limit]:
        flags = " ".join(f["name"] for f in c.get("flags", [])[:3])
        cli_lines.append(f"- `{c['command']}` {flags}")
    parts.append("## CLI Tools\n" + "\n".join(cli_lines) + "\n")
    schema_lines = [f"- {s['name']}: {s['path']}" for s in schemas.get("schemas", [])]
    parts.append("## Schemas\n" + "\n".join(schema_lines) + "\n")
    parts.append("## Decisions\n" + "\n".join(["- TBD"] * 6) + "\n")
    parts.append("## Open Issues\n" + "\n".join(["- TBD"] * 5) + "\n")
    doc = "\n".join(parts)
    data = doc.encode("utf-8")
    if len(data) > limit_bytes:
        doc = data[:limit_bytes].decode("utf-8", "ignore")
    return doc


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--min-kb", type=int, default=12)
    parser.add_argument("--full-kb", type=int, default=30)
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    min_doc = _build_doc(args.min_kb * 1024, 4)
    (OUT_DIR / "CHAT_SEED_MIN.md").write_text(min_doc, encoding="utf-8")
    full_doc = _build_doc(args.full_kb * 1024, 8)
    (OUT_DIR / "CHAT_SEED_FULL.md").write_text(full_doc, encoding="utf-8")


if __name__ == "__main__":
    main()
