import argparse
import json
import os
from .section_classifier import classify_blocks


def main():
    p = argparse.ArgumentParser(description="JSONL-only section classifier")
    p.add_argument("input_jsonl", help="Input JSONL file (blocks)")
    p.add_argument("output_dir", help="Output directory for artifacts")
    args = p.parse_args()

    if not args.input_jsonl.endswith(".jsonl"):
        raise SystemExit("Error: input must be a .jsonl file")

    result = classify_blocks(args.input_jsonl)

    os.makedirs(args.output_dir, exist_ok=True)
    with open(os.path.join(args.output_dir, "toc.json"), "w", encoding="utf-8") as f:
        json.dump(result["toc"], f, ensure_ascii=False, indent=2)
    with open(os.path.join(args.output_dir, "chapters.json"), "w", encoding="utf-8") as f:
        json.dump(result["chapters"], f, ensure_ascii=False, indent=2)
    with open(os.path.join(args.output_dir, "front_matter.json"), "w", encoding="utf-8") as f:
        json.dump(result["front_matter"], f, ensure_ascii=False, indent=2)
    with open(os.path.join(args.output_dir, "back_matter.json"), "w", encoding="utf-8") as f:
        json.dump(result["back_matter"], f, ensure_ascii=False, indent=2)

    print(f"Wrote artifacts to {args.output_dir}")


if __name__ == "__main__":
    main()
