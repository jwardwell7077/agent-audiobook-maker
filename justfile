eval:
	python -m abm.audit --refined data/ann/private_book/combined_refined.json --base data/ann/private_book/combined.json --metrics-jsonl data/ann/private_book/llm_metrics.jsonl --out-dir reports --plots --stdout-summary

refine+eval:
	python -m abm.annotate.llm_refine --tagged data/ann/private_book/combined.json --out-json data/ann/private_book/combined_refined.json --out-md data/ann/private_book/review_refined.md --metrics-jsonl data/ann/private_book/llm_metrics.jsonl --cache-dir data/ann/private_book --max-concurrency 6 --skip-threshold 0.85 --votes 3 --status rich --verbose --manage-llm --model llama3.1:8b-instruct-fp16 --eval-after --eval-dir reports
