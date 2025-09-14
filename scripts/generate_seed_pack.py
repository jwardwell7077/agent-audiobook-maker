import os, json, ast, re, datetime
from pathlib import Path
from typing import Any
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
OUT = ROOT / 'seed_pack'

MODULES = [
    'abm.annotate', 'abm.audio', 'abm.audit', 'abm.classifier', 'abm.ingestion',
    'abm.llm', 'abm.parse', 'abm.profiles', 'abm.sidecar', 'abm.structuring', 'abm.voice'
]

def module_name_from_path(path: Path) -> str:
    rel = path.relative_to(SRC)
    return '.'.join(rel.with_suffix('').parts)

def get_docstring_summary(node: ast.AST) -> str:
    doc = ast.get_docstring(node) or ''
    if not doc:
        return 'Unknown'
    sentences = re.split(r'(?<=[.!?])\s+', doc.strip())
    return ' '.join(sentences[:2])

def function_signature(node: ast.FunctionDef) -> str:
    params = []
    for arg in node.args.args:
        params.append(arg.arg)
    if node.args.vararg:
        params.append('*' + node.args.vararg.arg)
    for arg in node.args.kwonlyargs:
        params.append(arg.arg)
    if node.args.kwarg:
        params.append('**' + node.args.kwarg.arg)
    return f"({', '.join(params)})"

def parse_file(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding='utf-8')
    tree = ast.parse(text)
    module = module_name_from_path(path)
    summary = get_docstring_summary(tree)

    classes = []
    functions = []
    env_vars = set()
    internal_imports = set()
    external_imports = set()
    errors = []
    has_main = False

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
            classes.append({'name': node.name, 'kind': 'class', 'methods': methods, 'doc': get_docstring_summary(node)})
        elif isinstance(node, ast.FunctionDef) and node in tree.body:
            functions.append({'name': node.name, 'kind': 'function', 'signature': function_signature(node), 'doc': get_docstring_summary(node)})
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            else:
                if node.module:
                    names = [node.module]
            for name in names:
                if name.startswith('abm'):
                    internal_imports.add(name)
                else:
                    external_imports.add(name.split('.')[0])
        if isinstance(node, ast.Subscript):
            if isinstance(node.value, ast.Attribute) and isinstance(node.value.value, ast.Name) and node.value.value.id == 'os' and node.value.attr == 'environ':
                key = None
                if isinstance(node.slice, ast.Index):
                    sl = node.slice.value
                else:
                    sl = node.slice
                if isinstance(sl, ast.Constant) and isinstance(sl.value, str):
                    env_vars.add(sl.value)
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) and node.func.value.id == 'os' and node.func.attr == 'getenv':
                if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                    env_vars.add(node.args[0].value)
        if isinstance(node, ast.Raise) and node.exc:
            exc_name = None
            if isinstance(node.exc, ast.Call) and isinstance(node.exc.func, ast.Name):
                exc_name = node.exc.func.id
            elif isinstance(node.exc, ast.Name):
                exc_name = node.exc.id
            if exc_name:
                errors.append({'type': exc_name, 'when': 'Unknown'})
        if isinstance(node, ast.If):
            if isinstance(node.test, ast.Compare):
                left = node.test.left
                if isinstance(left, ast.Name) and left.id == '__name__':
                    has_main = True

    symbols = classes + functions
    if has_main:
        symbols.append({'name': '__main__', 'kind': 'cli', 'entrypoint': f'python -m {module}', 'flags': []})

    record = {
        'file': str(path),
        'module': module.rsplit('.', 1)[0] if '.' in module else module,
        'summary': summary,
        'top_level_symbols': symbols,
        'io_contracts': {'inputs': [], 'outputs': [], 'file_patterns_written': [], 'stdout_side_effects': []},
        'dependencies': {'imports_internal': sorted(internal_imports), 'imports_external': sorted(external_imports)},
        'errors_raised': errors,
        'env_vars': sorted(env_vars)
    }
    return record

# Parse all files
file_records = [parse_file(p) for p in sorted(SRC.rglob('*.py'))]

files_dir = OUT / 'files'
files_dir.mkdir(parents=True, exist_ok=True)
for rec in file_records:
    rel = Path(rec['file'])
    name = str(rel).replace('/', '__') + '.json'
    with open(files_dir / name, 'w', encoding='utf-8') as f:
        json.dump(rec, f, indent=2)

# Aggregate modules
pkg_records = defaultdict(list)
for rec in file_records:
    pkg_records[rec['module']].append(rec)

modules_dir = OUT / 'modules'
modules_dir.mkdir(parents=True, exist_ok=True)
for pkg, recs in pkg_records.items():
    path_globs = [f'src/{pkg.replace('.', '/')}/**/*.py']
    imports_internal = sorted({imp for r in recs for imp in r['dependencies']['imports_internal']})
    imports_external = sorted({imp for r in recs for imp in r['dependencies']['imports_external']})
    last_mtime = max(Path(r['file']).stat().st_mtime for r in recs)
    mrec = {
        'id': pkg,
        'path_globs': path_globs,
        'purpose': 'Unknown',
        'key_components': [],
        'public_surfaces': [],
        'data_flow': 'Unknown',
        'dependencies': {'imports_internal': imports_internal, 'imports_external': imports_external},
        'configs_env': {'env_vars': [], 'config_files': []},
        'cli_entrypoints': [],
        'invariants': [],
        'edge_cases': [],
        'known_gotchas': [],
        'related_tests': [],
        'status': {'maturity': 'Unknown', 'owners': [], 'last_touched_file_mtime': datetime.datetime.utcfromtimestamp(last_mtime).isoformat()}
    }
    for r in recs:
        for sym in r['top_level_symbols']:
            if sym['kind'] == 'class':
                mrec['key_components'].append({'name': sym['name'], 'kind': 'class', 'file': r['file'], 'summary': sym.get('doc', '')})
            elif sym['kind'] == 'function' and not sym['name'].startswith('_'):
                mrec['public_surfaces'].append({'symbol': sym['name'], 'signature': sym.get('signature', ''), 'summary': sym.get('doc', '')})
            elif sym['kind'] == 'cli':
                mrec['cli_entrypoints'].append({'file': r['file'], 'module': pkg, 'command': sym['entrypoint'], 'flags': sym.get('flags', [])})
    with open(modules_dir / f'{pkg}.json', 'w', encoding='utf-8') as f:
        json.dump(mrec, f, indent=2)

# Inventories
env_inventory = []
for rec in file_records:
    for var in rec['env_vars']:
        env_inventory.append({'file': rec['file'], 'env_var': var, 'purpose': 'Unknown'})
inv_dir = OUT / 'inventories'
inv_dir.mkdir(parents=True, exist_ok=True)
with open(inv_dir / 'env_vars.json', 'w', encoding='utf-8') as f:
    json.dump(env_inventory, f, indent=2)
with open(inv_dir / 'cli_tools.json', 'w', encoding='utf-8') as f:
    json.dump([], f, indent=2)
with open(inv_dir / 'config_files.json', 'w', encoding='utf-8') as f:
    json.dump([], f, indent=2)

# Graphs
nodes = sorted(pkg_records.keys())
import_edges = []
for rec in file_records:
    src = rec['module']
    for dst in rec['dependencies']['imports_internal']:
        if dst in nodes:
            import_edges.append({'from': src, 'to': dst})
graphs_dir = OUT / 'graphs'
graphs_dir.mkdir(parents=True, exist_ok=True)
with open(graphs_dir / 'import_graph.json', 'w', encoding='utf-8') as f:
    json.dump({'nodes': nodes, 'edges': import_edges}, f, indent=2)
with open(graphs_dir / 'call_graph.json', 'w', encoding='utf-8') as f:
    json.dump({'nodes': [], 'edges': []}, f, indent=2)

# Decisions
dec_dir = OUT / 'decisions'
dec_dir.mkdir(parents=True, exist_ok=True)
with open(dec_dir / 'DESIGN_DECISIONS.md', 'w', encoding='utf-8') as f:
    f.write('# Design Decisions\n\n')
    f.write('## Pending transcripts to fold in\n- [ ] transcript_1.md\n- [ ] transcript_2.md\n- [ ] transcript_3.md (optional)\n')
with open(dec_dir / 'decisions.json', 'w', encoding='utf-8') as f:
    json.dump([], f, indent=2)

# Schema
schema_dir = OUT / 'schemas'
schema_dir.mkdir(parents=True, exist_ok=True)
seed_schema = {
    'module_record': {
        'type': 'object',
        'required': ['id', 'path_globs'],
        'properties': {
            'id': {'type': 'string'},
            'path_globs': {'type': 'array', 'items': {'type': 'string'}}
        }
    },
    'file_record': {
        'type': 'object',
        'required': ['file', 'module'],
        'properties': {
            'file': {'type': 'string'},
            'module': {'type': 'string'}
        }
    }
}
with open(schema_dir / 'seedpack.schema.json', 'w', encoding='utf-8') as f:
    json.dump(seed_schema, f, indent=2)

# README and index
with open(OUT / 'README.md', 'w', encoding='utf-8') as f:
    f.write('# Seed Pack\n\nThis directory contains a machine-readable seed pack summarizing the project.\n')
index = {
    'project': ROOT.name,
    'generated_at': datetime.datetime.utcnow().isoformat(),
    'code_root': 'src',
    'modules': MODULES,
    'files_indexed': len(file_records),
    'graphs': {
        'import_graph': 'graphs/import_graph.json',
        'call_graph': 'graphs/call_graph.json'
    },
    'inventories': {
        'cli_tools': 'inventories/cli_tools.json',
        'env_vars': 'inventories/env_vars.json',
        'config_files': 'inventories/config_files.json'
    },
    'decisions': {
        'markdown': 'decisions/DESIGN_DECISIONS.md',
        'structured': 'decisions/decisions.json'
    },
    'schema_version': '1.0.0'
}
with open(OUT / 'index.json', 'w', encoding='utf-8') as f:
    json.dump(index, f, indent=2)
