import ast
import datetime as dt
import json
import os
import re
import shutil
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
SEED_DIR = ROOT / "seed_pack"
SIZE_LIMIT = 500 * 1024  # 500 KB


def relpath(p: Path) -> str:
    return str(p.resolve().relative_to(ROOT))


def sanitize_filename(p: Path) -> str:
    return relpath(p).replace("/", "__")


def discover_modules() -> List[str]:
    mods: set[str] = set()
    for py in SRC.rglob("*.py"):
        if (
            "__pycache__" in py.parts
            or ".egg-info" in py.parts
            or any(part.startswith(".") for part in py.parts)
            or "tests" in py.parts
        ):
            continue
        if py == SRC / "__init__.py":
            continue
        if py.name == "__init__.py":
            rel = py.parent.relative_to(SRC)
        else:
            rel = py.relative_to(SRC).with_suffix("")
        mods.add(".".join(rel.parts))
    mods.discard("abm")
    return sorted(mods)


MODULES = discover_modules()


def discover_py_files() -> List[Path]:
    files: List[Path] = []
    for path in sorted(SRC.rglob("*.py")):
        if any(part.startswith(".") for part in path.parts):
            continue
        if "__pycache__" in path.parts:
            continue
        if any(part.startswith("tests") for part in path.parts):
            continue
        if path == SRC / "__init__.py":
            continue
        files.append(path)
    return files


def module_name_from_path(path: Path) -> str:
    rel = path.relative_to(SRC)
    if rel.name == "__init__.py":
        rel = rel.parent
    else:
        rel = rel.with_suffix("")
    return ".".join(rel.parts)


def get_docstring_summary(node: ast.AST) -> str:
    doc = ast.get_docstring(node) or ""
    if not doc:
        return "Auto-generated summary."
    first = doc.strip().splitlines()[0]
    return first.strip()


def function_signature(node: ast.FunctionDef) -> str:
    params = []
    for arg in node.args.args:
        params.append(arg.arg)
    if node.args.vararg:
        params.append("*" + node.args.vararg.arg)
    for arg in node.args.kwonlyargs:
        params.append(arg.arg)
    if node.args.kwarg:
        params.append("**" + node.args.kwarg.arg)
    return f"({', '.join(params)})"


def parse_file(path: Path) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text)
    module_name = module_name_from_path(path)
    summary = get_docstring_summary(tree)

    public_api: List[Dict[str, str]] = []
    errors: List[Dict[str, str]] = []
    deps_internal: set[str] = set()
    deps_external: set[str] = set()
    env_vars: set[str] = set()
    config_files: set[str] = set()
    cli_flags: List[Dict[str, Any]] = []
    is_cli = False
    import_aliases: Dict[str, str] = {}
    call_edges: List[Tuple[str, str]] = []

    # map imports
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                mod = alias.name
                asname = alias.asname or mod.split(".")[0]
                if mod.startswith("abm"):
                    deps_internal.add(mod)
                    import_aliases[asname] = mod
                else:
                    deps_external.add(mod.split(".")[0])
                    import_aliases[asname] = mod
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                mod = node.module
                base = mod
                if mod.startswith("abm"):
                    deps_internal.add(mod)
                else:
                    deps_external.add(mod.split(".")[0])
                for alias in node.names:
                    asname = alias.asname or alias.name
                    import_aliases[asname] = f"{base}.{alias.name}"

    # top-level defs
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            public_api.append({"name": node.name, "signature": function_signature(node), "kind": "function"})
        elif isinstance(node, ast.ClassDef):
            public_api.append({"name": node.name, "signature": "", "kind": "class"})
        elif isinstance(node, ast.If):
            if (
                isinstance(node.test, ast.Compare)
                and isinstance(node.test.left, ast.Name)
                and node.test.left.id == "__name__"
            ):
                is_cli = True

    # deeper scan for raises, env vars, config files, cli flags, call edges
    for func in [n for n in tree.body if isinstance(n, ast.FunctionDef)]:
        for sub in ast.walk(func):
            if isinstance(sub, ast.Call):
                # CLI flags
                if isinstance(sub.func, ast.Attribute) and sub.func.attr == "add_argument":
                    for arg in sub.args:
                        if isinstance(arg, ast.Constant) and isinstance(arg.value, str) and arg.value.startswith("-"):
                            cli_flags.append({"name": arg.value, "type": "unknown", "default": None})
                # call graph edges
                target = None
                if isinstance(sub.func, ast.Attribute) and isinstance(sub.func.value, ast.Name):
                    base = sub.func.value.id
                    if base in import_aliases:
                        target_mod = import_aliases[base]
                        target = f"{target_mod}.{sub.func.attr}"
                elif isinstance(sub.func, ast.Name):
                    base = sub.func.id
                    if base in import_aliases:
                        target = import_aliases[base]
                if target and target.startswith("abm"):
                    call_edges.append((f"{module_name}.{func.name}", target))
            elif isinstance(sub, ast.Raise) and sub.exc:
                exc = sub.exc
                name = None
                if isinstance(exc, ast.Call) and isinstance(exc.func, ast.Name):
                    name = exc.func.id
                elif isinstance(exc, ast.Name):
                    name = exc.id
                if name:
                    errors.append({"type": name, "when": "Unknown"})
        # end walk function
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript):
            if (
                isinstance(node.value, ast.Attribute)
                and isinstance(node.value.value, ast.Name)
                and node.value.value.id == "os"
                and node.value.attr == "environ"
            ):
                key_node = node.slice
                if isinstance(key_node, ast.Index):  # type: ignore[attr-defined]
                    key_node = key_node.value
                if isinstance(key_node, ast.Constant) and isinstance(key_node.value, str):
                    env_vars.add(key_node.value)
        if isinstance(node, ast.Call):
            if (
                isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Attribute)
                and isinstance(node.func.value.value, ast.Name)
                and node.func.value.value.id == "os"
                and node.func.value.attr == "environ"
                and node.func.attr == "get"
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                env_vars.add(node.args[0].value)
            if (
                isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "os"
                and node.func.attr == "getenv"
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                env_vars.add(node.args[0].value)
            if isinstance(node.func, ast.Attribute) and node.func.attr == "add_argument":
                for arg in node.args:
                    if isinstance(arg, ast.Constant) and isinstance(arg.value, str) and arg.value.startswith("-"):
                        cli_flags.append({"name": arg.value, "type": "unknown", "default": None})
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if re.search(r"\.(json|ya?ml|toml)$", node.value):
                config_files.add(node.value)

    file_record = {
        "file": relpath(path),
        "module": module_name,
        "summary": summary,
        "public_api": public_api,
        "cli": {"is_cli": is_cli, "flags": cli_flags, "examples": [f"python -m {module_name}"] if is_cli else []},
        "io_contracts": {"inputs": [], "outputs": [], "patterns": []},
        "errors_raised": errors,
        "dependencies": {"internal": sorted(deps_internal), "external": sorted(deps_external)},
        "evidence": [{"file": relpath(path), "lines": "1-1"}],
        "confidence": 0.7,
    }

    extras = {
        "env_vars": env_vars,
        "config_files": config_files,
        "is_cli": is_cli,
        "cli_flags": cli_flags,
        "module_name": module_name,
        "package": module_name.rsplit(".", 1)[0] if "." in module_name else module_name,
        "deps_internal": deps_internal,
        "deps_external": deps_external,
        "call_edges": call_edges,
    }
    return file_record, extras


def write_json(path: Path, data: Any, shards: List[str]) -> None:
    text = json.dumps(data, indent=2, ensure_ascii=False)
    size = len(text.encode("utf-8"))
    if size <= SIZE_LIMIT:
        path.write_text(text, encoding="utf-8")
    else:
        if isinstance(data, list):
            chunk: List[Any] = []
            part = 1
            for item in data:
                chunk.append(item)
                chunk_text = json.dumps(chunk, indent=2, ensure_ascii=False)
                if len(chunk_text.encode("utf-8")) > SIZE_LIMIT:
                    chunk.pop()
                    shard_path = path.with_suffix(f".part{part:02d}.json")
                    shard_path.write_text(json.dumps(chunk, indent=2, ensure_ascii=False), encoding="utf-8")
                    shards.append(str(shard_path.relative_to(SEED_DIR)))
                    part += 1
                    chunk = [item]
            if chunk:
                shard_path = path.with_suffix(f".part{part:02d}.json")
                shard_path.write_text(json.dumps(chunk, indent=2, ensure_ascii=False), encoding="utf-8")
                shards.append(str(shard_path.relative_to(SEED_DIR)))
        else:
            path.write_text(text, encoding="utf-8")


def main() -> None:
    if SEED_DIR.exists():
        shutil.rmtree(SEED_DIR)
    (SEED_DIR / "files").mkdir(parents=True, exist_ok=True)
    (SEED_DIR / "modules").mkdir(parents=True, exist_ok=True)
    (SEED_DIR / "inventories").mkdir(parents=True, exist_ok=True)
    (SEED_DIR / "graphs").mkdir(parents=True, exist_ok=True)
    (SEED_DIR / "decisions").mkdir(parents=True, exist_ok=True)
    (SEED_DIR / "schemas").mkdir(parents=True, exist_ok=True)

    file_records: List[Dict[str, Any]] = []
    packages: set[str] = set()
    cli_inventory: List[Dict[str, Any]] = []
    env_inventory: List[Dict[str, Any]] = []
    config_inventory: List[Dict[str, Any]] = []
    import_edges: set[Tuple[str, str]] = set()
    call_edges: set[Tuple[str, str]] = set()
    module_deps_internal: Dict[str, set[str]] = defaultdict(set)
    module_deps_external: Dict[str, set[str]] = defaultdict(set)
    module_env: Dict[str, set[str]] = defaultdict(set)
    module_configs: Dict[str, set[str]] = defaultdict(set)
    module_cli: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    file_paths = discover_py_files()

    for path in file_paths:
        record, extra = parse_file(path)
        file_records.append(record)

        pkg_full = extra["package"]
        parts = pkg_full.split(".")
        top_pkg = ".".join(parts[:2]) if len(parts) >= 2 else pkg_full
        if top_pkg != "abm":
            packages.add(top_pkg)

        if extra["is_cli"] and top_pkg != "abm":
            cli_entry = {
                "file": record["file"],
                "module": record["module"],
                "command": f"python -m {record['module']}",
                "flags": extra["cli_flags"],
                "examples": [f"python -m {record['module']}"]
            }
            cli_inventory.append(cli_entry)
            module_cli[top_pkg].append(cli_entry)

        for v in extra["env_vars"]:
            env_inventory.append({"env_var": v, "file": record["file"]})
            module_env[top_pkg].add(v)
        for c in extra["config_files"]:
            config_inventory.append({"file": record["file"], "config": c})
            module_configs[top_pkg].add(c)

        module_deps_internal[top_pkg].update(extra["deps_internal"])
        module_deps_external[top_pkg].update(extra["deps_external"])
        for dst in extra["deps_internal"]:
            import_edges.add((extra["module_name"], dst))
        for frm, to in extra["call_edges"]:
            call_edges.add((frm, to))

    shards: List[str] = []
    files_dir = SEED_DIR / "files"
    for rec in file_records:
        out_path = files_dir / f"{sanitize_filename(Path(rec['file']))}.json"
        write_json(out_path, rec, shards)

    modules_dir = SEED_DIR / "modules"
    for pkg in sorted(packages):
        pkg_files = [r for r in file_records if r["module"].startswith(pkg + ".") or r["module"] == pkg]
        last_mtime = max((ROOT / r["file"]).stat().st_mtime for r in pkg_files)
        key_components = []
        public_surfaces = []
        for r in pkg_files:
            for sym in r["public_api"]:
                if sym["kind"] == "class":
                    key_components.append({"name": sym["name"], "kind": "class", "file": r["file"], "summary": ""})
                elif sym["kind"] == "function" and not sym["name"].startswith("_"):
                    public_surfaces.append({"symbol": sym["name"], "signature": sym["signature"], "summary": ""})
        mod_record = {
            "id": pkg,
            "path_globs": [f"src/{pkg.replace('.', '/')}/**/*.py"],
            "purpose": "Auto-generated module summary.",
            "key_components": key_components,
            "public_surfaces": public_surfaces,
            "data_flow": "Unknown",
            "dependencies": {
                "imports_internal": sorted(module_deps_internal.get(pkg, set())),
                "imports_external": sorted(module_deps_external.get(pkg, set())),
            },
            "configs_env": {
                "env_vars": sorted(module_env.get(pkg.split('.')[0] if '.' in pkg else pkg, set())),
                "config_files": sorted(module_configs.get(pkg.split('.')[0] if '.' in pkg else pkg, set())),
            },
            "cli_entrypoints": module_cli.get(pkg, []),
            "invariants": [],
            "edge_cases": [],
            "known_gotchas": [],
            "related_tests": [],
            "status": {
                "maturity": "alpha",
                "owners": [],
                "last_touched_file_mtime": dt.datetime.fromtimestamp(last_mtime, dt.timezone.utc).isoformat(),
            },
        }
        write_json(modules_dir / f"{pkg}.json", mod_record, shards)

    write_json(SEED_DIR / "inventories" / "cli_tools.json", sorted(cli_inventory, key=lambda x: x["command"]), shards)
    write_json(
        SEED_DIR / "inventories" / "env_vars.json",
        sorted(env_inventory, key=lambda x: (x["env_var"], x["file"])),
        shards,
    )
    write_json(
        SEED_DIR / "inventories" / "config_files.json",
        sorted(config_inventory, key=lambda x: (x["config"], x["file"])),
        shards,
    )

    import_graph = {
        "nodes": MODULES,
        "edges": [
            {"from": src, "to": dst}
            for src, dst in sorted(import_edges)
            if src in MODULES and dst in MODULES
        ],
    }
    write_json(SEED_DIR / "graphs" / "import_graph.json", import_graph, shards)

    call_graph = {
        "edges": [
            {"from": frm, "to": to}
            for frm, to in sorted(call_edges)
        ]
    }
    write_json(SEED_DIR / "graphs" / "call_graph.json", call_graph, shards)

    # decisions
    decisions_md = SEED_DIR / "decisions" / "DESIGN_DECISIONS.md"
    decisions_md.write_text(
        "# Design Decisions\n\n## Pending transcripts to fold in\n- [ ] transcript_1.md\n- [ ] transcript_2.md\n- [ ] transcript_3.md (optional)\n",
        encoding="utf-8",
    )
    write_json(SEED_DIR / "decisions" / "decisions.json", [], shards)

    # schemas index and placeholders
    schemas_entries: List[Dict[str, Any]] = []
    schemas_dir = SEED_DIR / "schemas"
    docs_schemas = ROOT / "docs" / "chat_seed" / "04-schemas"
    if docs_schemas.exists():
        for p in sorted(docs_schemas.glob("*.json")):
            schemas_entries.append({"name": p.stem, "path": relpath(p), "inferred": False})
    else:
        schemas_dir.mkdir(parents=True, exist_ok=True)
        for stem in ["chapter", "segment", "casting_plan", "book_config"]:
            fp = schemas_dir / f"{stem}.schema.json"
            if not fp.exists():
                fp.write_text(
                    json.dumps({"$schema": "http://json-schema.org/draft-07/schema#", "title": stem, "type": "object"}, indent=2),
                    encoding="utf-8",
                )
            schemas_entries.append({"name": stem, "path": relpath(fp), "inferred": True})
    write_json(SEED_DIR / "schemas_index.json", {"schemas": schemas_entries}, shards)

    # umbrella schema (static)
    seed_schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "$id": "seedpack.schema.json",
        "$defs": {
            "file_record": {
                "type": "object",
                "required": [
                    "file",
                    "module",
                    "summary",
                    "public_api",
                    "cli",
                    "io_contracts",
                    "errors_raised",
                    "dependencies",
                    "evidence",
                    "confidence",
                ],
                "properties": {
                    "file": {"type": "string"},
                    "module": {"type": "string"},
                    "summary": {"type": "string"},
                    "public_api": {"type": "array", "items": {"type": "object"}},
                    "cli": {"type": "object"},
                    "io_contracts": {"type": "object"},
                    "errors_raised": {"type": "array", "items": {"type": "object"}},
                    "dependencies": {"type": "object"},
                    "evidence": {"type": "array", "items": {"type": "object"}},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                },
            },
            "module_record": {
                "type": "object",
                "required": [
                    "id",
                    "path_globs",
                    "purpose",
                    "key_components",
                    "public_surfaces",
                    "data_flow",
                    "dependencies",
                    "configs_env",
                    "cli_entrypoints",
                    "invariants",
                    "edge_cases",
                    "status",
                ],
                "properties": {
                    "id": {"type": "string"},
                    "path_globs": {"type": "array", "items": {"type": "string"}},
                    "purpose": {"type": "string"},
                    "key_components": {"type": "array", "items": {"type": "object"}},
                    "public_surfaces": {"type": "array", "items": {"type": "object"}},
                    "data_flow": {"type": "string"},
                    "dependencies": {"type": "object"},
                    "configs_env": {"type": "object"},
                    "cli_entrypoints": {"type": "array", "items": {"type": "object"}},
                    "invariants": {"type": "array", "items": {"type": "string"}},
                    "edge_cases": {"type": "array", "items": {"type": "string"}},
                    "status": {"type": "object"},
                },
            },
            "cli_tools": {"type": "array", "items": {"type": "object"}},
            "env_vars": {"type": "array", "items": {"type": "object"}},
            "config_files": {"type": "array", "items": {"type": "object"}},
            "import_graph": {
                "type": "object",
                "required": ["nodes", "edges"],
                "properties": {
                    "nodes": {"type": "array", "items": {"type": "string"}},
                    "edges": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["from", "to"],
                            "properties": {
                                "from": {"type": "string"},
                                "to": {"type": "string"},
                            },
                        },
                    },
                },
            },
            "call_graph": {
                "type": "object",
                "required": ["edges"],
                "properties": {
                    "edges": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["from", "to"],
                            "properties": {
                                "from": {"type": "string"},
                                "to": {"type": "string"},
                            },
                        },
                    }
                },
            },
            "index": {
                "type": "object",
                "required": [
                    "project",
                    "generated_at",
                    "code_root",
                    "modules",
                    "files_indexed",
                    "graphs",
                    "inventories",
                    "decisions",
                    "schemas_index",
                    "schema_version",
                    "shards",
                ],
                "properties": {
                    "project": {"type": "string"},
                    "generated_at": {"type": "string"},
                    "code_root": {"type": "string"},
                    "modules": {"type": "array", "items": {"type": "string"}},
                    "files_indexed": {"type": "integer"},
                    "graphs": {"type": "object"},
                    "inventories": {"type": "object"},
                    "decisions": {"type": "object"},
                    "schemas_index": {"type": "string"},
                    "schema_version": {"type": "string"},
                    "shards": {"type": "array", "items": {"type": "string"}},
                },
            },
            "schemas_index": {
                "type": "object",
                "required": ["schemas"],
                "properties": {
                    "schemas": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["name", "path", "inferred"],
                            "properties": {
                                "name": {"type": "string"},
                                "path": {"type": "string"},
                                "inferred": {"type": "boolean"},
                            },
                        },
                    }
                },
            },
        },
    }
    write_json(SEED_DIR / "schemas" / "seedpack.schema.json", seed_schema, shards)

    # README
    (SEED_DIR / "README.md").write_text(
        "# Seed Pack\n\nThis folder contains machine-readable context. Load `index.json` and follow paths for modules, files, graphs, inventories, and design decisions.",
        encoding="utf-8",
    )

    max_mtime = max((ROOT / r["file"]).stat().st_mtime for r in file_records)
    index = {
        "project": ROOT.name,
        "generated_at": dt.datetime.fromtimestamp(max_mtime, dt.timezone.utc).isoformat(),
        "code_root": "src",
        "modules": MODULES,
        "files_indexed": len(file_records),
        "graphs": {
            "import_graph": "graphs/import_graph.json",
            "call_graph": "graphs/call_graph.json",
        },
        "inventories": {
            "cli_tools": "inventories/cli_tools.json",
            "env_vars": "inventories/env_vars.json",
            "config_files": "inventories/config_files.json",
        },
        "decisions": {
            "markdown": "decisions/DESIGN_DECISIONS.md",
            "structured": "decisions/decisions.json",
        },
        "schemas_index": "schemas_index.json",
        "schema_version": "1.0.0",
        "shards": sorted(shards),
    }
    write_json(SEED_DIR / "index.json", index, shards)


if __name__ == "__main__":
    main()
