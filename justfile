eval:
	python -m abm.audit --refined data/ann/mvs/combined_refined.json --base data/ann/mvs/combined.json --metrics-jsonl data/ann/mvs/llm_metrics.jsonl --out-dir reports --plots --stdout-summary

refine+eval:
	python -m abm.annotate.llm_refine --tagged data/ann/mvs/combined.json --out-json data/ann/mvs/combined_refined.json --out-md data/ann/mvs/review_refined.md --metrics-jsonl data/ann/mvs/llm_metrics.jsonl --cache-dir data/ann/mvs --max-concurrency 6 --skip-threshold 0.85 --votes 3 --status rich --verbose --manage-llm --model llama3.1:8b-instruct-fp16 --eval-after --eval-dir reports
