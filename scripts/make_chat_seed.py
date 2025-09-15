import json
import argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SP=ROOT/"seed_pack"
def load(p): return json.loads((SP/p).read_text(encoding="utf-8"))
def msg(limit):
    idx=load("index.json"); mods=idx.get("modules",[])[:10]
    g=load("graphs/import_graph.json"); clis=json.loads((SP/"inventories/cli_tools.json").read_text(encoding="utf-8") or "[]")
    primer="Agent-Audiobook-Maker turns PDFs into chapterized JSON and multi-voice audio locally (Piper/XTTS). Staged pipeline ensures debuggable artifacts and reproducibility."
    lines=["# Chat SME Seed (MIN)","", "## Primer", primer, "",
           "## Pipeline (Mermaid)", "flowchart TD",
           "  A[PDF]-->B[pdf_to_raw_text]; B-->C[raw_to_welldone]; C-->D[welldone_to_json]; D-->E[classifier_cli]; E-->F[voicecasting]; F-->G[render_chapter]; G-->H[album_norm]; H-->I[package_book]",
           "", "## Modules (top 10)"]
    lines += [f"- **{m}** — see seed_pack/modules/{m}.json" for m in mods]
    lines += ["", "## CLIs (sample)"]
    for c in clis[:8]:
        ex = c.get("examples",[""])[0] if c.get("examples") else f"python -m {c['module']}"
        lines.append(f"- `{ex}`")
    return ("\n".join(lines))[:limit]
if __name__=="__main__":
    ap=argparse.ArgumentParser(); ap.add_argument("--min-kb", type=int, default=12); ap.add_argument("--full-kb", type=int, default=30); a=ap.parse_args()
    (ROOT/"docs/chat_seed").mkdir(parents=True, exist_ok=True)
    (ROOT/"docs/chat_seed/CHAT_SEED_MIN.md").write_text(msg(a.min_kb*1024), encoding="utf-8")
    (ROOT/"docs/chat_seed/CHAT_SEED_FULL.md").write_text(msg(a.full_kb*1024), encoding="utf-8")
