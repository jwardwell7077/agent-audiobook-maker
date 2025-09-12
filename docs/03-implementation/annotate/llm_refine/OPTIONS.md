# `llm_refine` CLI Options

```
usage: llm_refine.py [-h] --tagged TAGGED --out-json OUT_JSON [--out-md OUT_MD] [--endpoint ENDPOINT] [--model MODEL]
                     [--manage-llm] [--skip-threshold SKIP_THRESHOLD] [--votes VOTES] [--cache CACHE]

Stage B: LLM refinement for low-confidence/Unknown spans.

options:
  -h, --help            show this help message and exit
  --tagged TAGGED       Path to Stage A combined.json
  --out-json OUT_JSON   Path to write refined JSON
  --out-md OUT_MD       Optional summary markdown
  --endpoint ENDPOINT   OpenAI-compatible base URL
  --model MODEL         Model id/name
  --manage-llm          Start/stop local LLM service automatically (Ollama)
  --skip-threshold SKIP_THRESHOLD
                        Skip spans with conf >= this
  --votes VOTES         Majority vote count per span
  --cache CACHE         Optional path to SQLite cache file
```
