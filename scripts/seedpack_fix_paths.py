from pathlib import Path
import json, os
ROOT = Path(__file__).resolve().parents[1]
FILES = ROOT/"seed_pack/files"
for p in FILES.glob("*.json"):
    rec = json.loads(p.read_text(encoding="utf-8"))
    f = rec.get("file", "")
    if f.startswith(str(ROOT)):  # absolute -> repo-relative
        f = str(Path(f).resolve().relative_to(ROOT))
        rec["file"] = f
    target = f.replace("/", "__") + ".json"
    if p.name != target:
        (FILES/target).write_text(json.dumps(rec, indent=2), encoding="utf-8")
        os.remove(p)
    else:
        p.write_text(json.dumps(rec, indent=2), encoding="utf-8")
print("ok")
