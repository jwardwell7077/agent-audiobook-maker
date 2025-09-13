from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class BookNLPConfig:
    """Configuration for running BookNLP as a sidecar."""

    model: str = "en"  # BookNLP language model key (e.g., "en")
    size: str = "big"  # BookNLP model size (e.g., "big" or "small")
    pipeline: str = "entity,quote,coref"  # Which BNLP pipeline steps to run
    java_opts: str = "-Xms1g -Xmx6g"
    timeout_s: int = 900
    prefer_python_api: bool = True  # try Python API first, then CLI
    keep_tmp: bool = False  # for debugging; writes run artifacts if True


class BookNLPAdapter:
    """Thin wrapper that runs BookNLP on raw text and returns quote attributions.

    Output format (per quote):
        {
          "start": int,          # char start (inclusive)
          "end": int,            # char end (exclusive)
          "speaker": str,        # BookNLP's best guess (surface string)
          "prob": float          # 0..1 if available (else 0.0)
        }
    """

    def __init__(self, cfg: BookNLPConfig | None = None, *, verbose: bool = False) -> None:
        self.cfg = cfg or BookNLPConfig()
        self.verbose = verbose
        self._booknlp_available = self._probe_available()

    # ---------------------- public API ---------------------- #

    def enabled(self) -> bool:
        """Return True if BookNLP is importable or its CLI exists."""
        return self._booknlp_available

    def annotate_text(self, text: str, work_id: str = "chapter") -> list[dict[str, Any]]:
        """Run BookNLP and return quote attributions as a list of dicts.

        Args:
            text: Full chapter text.
            work_id: An identifier used in BookNLP outputs.

        Returns:
            A list of quote dicts with character offsets and a speaker guess.
            Returns [] if BookNLP is unavailable or fails.
        """
        if not self._booknlp_available:
            if self.verbose:
                print("[booknlp] unavailable; returning empty results")
            return []

        tmp_dir = Path(tempfile.mkdtemp(prefix="abm_bnlp_"))  # cleaned unless keep_tmp
        in_txt = tmp_dir / f"{work_id}.txt"
        out_dir = tmp_dir / "out"
        in_txt.write_text(text, encoding="utf-8")

        try:
            if self.cfg.prefer_python_api:
                try:
                    return self._run_python_api(in_txt, out_dir, work_id)
                except Exception as e:
                    if self.verbose:
                        print(f"[booknlp] python API failed, falling back to CLI: {e}")
                    try:
                        return self._run_cli(in_txt, out_dir, work_id)
                    except Exception as e2:
                        if self.verbose:
                            print(f"[booknlp] CLI also failed: {e2}")
                        return []
            else:
                try:
                    return self._run_cli(in_txt, out_dir, work_id)
                except Exception as e2:
                    if self.verbose:
                        print(f"[booknlp] CLI failed: {e2}")
                    return []
        finally:
            if not self.cfg.keep_tmp:
                try:
                    shutil.rmtree(tmp_dir, ignore_errors=True)
                except Exception:
                    pass

    # ---------------------- internals ----------------------- #

    def _probe_available(self) -> bool:
        """Check for Python API or CLI availability, with verbose logging."""
        try:
            import importlib

            importlib.import_module("booknlp")
            if self.verbose:
                print("[booknlp] Python API available (version unknown)")
            return True
        except Exception as e:
            if self.verbose:
                print(f"[booknlp] Python API import failed: {e}")
        cli = shutil.which("booknlp")
        if self.verbose:
            print("[booknlp] CLI found at", cli if cli else "None")
        return cli is not None

    def _run_python_api(self, in_txt: Path, out_dir: Path, work_id: str) -> list[dict[str, Any]]:
        """Invoke BookNLP via Python API in a subprocess with safe fallback.

        BookNLP expects pipeline names like: entity,quote,coref (no "quote_attribution").
            'model' in params is the size ('big'|'small'); language is the first positional arg.
            We run in a subprocess so crashes don't poison our process.
        """
        out_dir.mkdir(parents=True, exist_ok=True)

        def _model_names(sz: str) -> tuple[str, str, str]:
            if sz == "small":
                return (
                    "entities_google_bert_uncased_L-4_H-256_A-4-v1.0.model",
                    "coref_google_bert_uncased_L-2_H-256_A-4-v1.0.model",
                    "speaker_google_bert_uncased_L-8_H-256_A-4-v1.0.1.model",
                )
            return (
                "entities_google_bert_uncased_L-6_H-768_A-12-v1.0.model",
                "coref_google_bert_uncased_L-12_H-768_A-12-v1.0.model",
                "speaker_google_bert_uncased_L-12_H-768_A-12-v1.0.1.model",
            )

        def _default_models_dir() -> Path:
            from pathlib import Path as _P

            return _P.home() / "booknlp_models"

        def _ensure_custom_params(pipeline: str, size: str) -> dict[str, str]:
            # Build explicit model paths and create a patched copy of the coref weights if needed.
            ent_name, coref_name, spk_name = _model_names(size)
            src_dir = _default_models_dir()
            ent = src_dir / ent_name
            coref = src_dir / coref_name
            spk = src_dir / spk_name
            patched_dir = src_dir / "patched"
            patched_dir.mkdir(parents=True, exist_ok=True)
            patched_coref = patched_dir / coref_name
            # Copy coref and patch only the copy
            try:
                if coref.exists():
                    shutil.copy2(coref, patched_coref)
                    self._patch_specific_weight(patched_coref)
                # Validate coref checkpoint; if corrupted, fall back to small model coref
                if not self._validate_weight(patched_coref):
                    if self.verbose:
                        print(f"[booknlp] invalid coref model {coref_name}; falling back to small coref")
                    _, small_coref, _ = _model_names("small")
                    small_coref_path = src_dir / small_coref
                    if small_coref_path.exists():
                        shutil.copy2(small_coref_path, patched_dir / small_coref)
                        patched_coref = patched_dir / small_coref
                        self._patch_specific_weight(patched_coref)
                    else:
                        # last resort: use whatever we had
                        patched_coref = coref
            except Exception as _e:
                if self.verbose:
                    print(f"[booknlp] warn: failed to prepare patched coref copy: {_e}")
                # fall back to original
                patched_coref = coref

            return {
                "pipeline": pipeline,
                "model": "custom",
                "entity_model_path": str(ent),
                "coref_model_path": str(patched_coref),
                "quote_attribution_model_path": str(spk),
            }

        def run_subprocess(pipeline: str, size: str) -> subprocess.CompletedProcess[bytes]:
            # Prefer using explicit custom model paths so we don't mutate original files
            params = _ensure_custom_params(pipeline, size)
            code = (
                "from booknlp.booknlp import BookNLP\n"
                f"params = {params!r}\n"
                f'bn = BookNLP("{self.cfg.model}", params)\n'
                f'bn.process(r"{in_txt}", r"{out_dir}", "{work_id}")\n'
            )
            return subprocess.run(["python", "-c", code], capture_output=True, timeout=self.cfg.timeout_s)

        def stderr_tail(cp: subprocess.CompletedProcess[bytes]) -> str:
            err = (cp.stderr or b"").decode("utf-8", "ignore")
            tail = "\n".join(err.strip().splitlines()[-3:])
            return tail

        # Attempt 1: configured pipeline with configured size
        size = self.cfg.size
        pipeline = self.cfg.pipeline or "entity,quote,coref"
        if self.verbose:
            print(
                f"[booknlp] python API run: {in_txt.name} → {out_dir} "
                f"(lang={self.cfg.model}, pipeline={pipeline}, model={size})"
            )
        cp = run_subprocess(pipeline, size)
        if cp.returncode != 0:
            tail = stderr_tail(cp).lower()
            if self.verbose:
                print(f"[booknlp] python API failed (rc={cp.returncode}); err tail: [{tail}]")

            # Known LitBank mismatch → patch cached weights and retry once
            if "position_ids" in tail or "unexpected key(s) in state_dict" in tail:
                self._patch_cached_weights()
                if self.verbose:
                    print(f"[booknlp] retry after patch: {pipeline}")
                cp = run_subprocess(pipeline, size)

            # If still failing, try minimal pipeline
            if cp.returncode != 0:
                if self.verbose:
                    print("[booknlp] retry minimal pipeline: entity,quote")
                cp = run_subprocess("entity,quote", size)

            # Last resort: try small model
            if cp.returncode != 0 and size != "small":
                if self.verbose:
                    print("[booknlp] retry with small model: entity,quote")
                cp = run_subprocess("entity,quote", "small")

            if cp.returncode != 0:
                raise RuntimeError(f"BookNLP python failed: rc={cp.returncode}; tail={stderr_tail(cp)}")

        return self._load_quotes(out_dir, work_id)

    def _patch_specific_weight(self, path: Path) -> bool:
        """Patch a single checkpoint file in-place if it has the extra position_ids key.

        Returns True if patched, False otherwise.
        """
        try:
            import torch

            sd = torch.load(path, map_location="cpu")
            if isinstance(sd, dict):
                d = sd.get("state_dict", sd)
                if isinstance(d, dict) and "bert.embeddings.position_ids" in d:
                    if self.verbose:
                        print(f"[booknlp] patching weight: {path}")
                    d.pop("bert.embeddings.position_ids", None)
                    torch.save(sd, path)
                    return True
        except Exception:
            return False
        return False

    def _validate_weight(self, path: Path) -> bool:
        try:
            import torch

            _ = torch.load(path, map_location="cpu")
            return True
        except Exception:
            return False

    def _patch_cached_weights(self) -> int:
        """Remove the extra 'bert.embeddings.position_ids' key from cached BookNLP weights.

        Returns:
            The number of files patched.
        """
        try:
            import torch
        except Exception:
            if self.verbose:
                print("[booknlp] torch not available; cannot patch cached weights")
            return 0

        roots: list[Path] = []
        # Default cache location used by some versions
        cache_root = Path.home() / ".booknlp"
        if cache_root.exists():
            roots.append(cache_root)
        # Primary model cache used by english_booknlp.py
        models_root = Path.home() / "booknlp_models"
        if models_root.exists():
            roots.append(models_root)
        # Also scan installed package directory as a fallback
        try:
            import importlib

            booknlp = importlib.import_module("booknlp")
            pkg_root = Path(getattr(booknlp, "__file__", "")).resolve().parent
            if pkg_root.exists():
                roots.append(pkg_root)
        except Exception:
            pass

        if not roots:
            return 0

        candidates: list[Path] = []
        for r in roots:
            candidates.extend(list(r.rglob("*.pt")))
            candidates.extend(list(r.rglob("*.bin")))
            candidates.extend(list(r.rglob("*.pth")))
            # BookNLP downloads model checkpoints with the extension ".model"
            candidates.extend(list(r.rglob("*.model")))
        patched = 0
        for p in candidates:
            try:
                sd = torch.load(p, map_location="cpu")
                # Handle either a plain state dict or a dict with 'state_dict'
                if isinstance(sd, dict):
                    d = sd.get("state_dict", sd)
                    if isinstance(d, dict) and "bert.embeddings.position_ids" in d:
                        if self.verbose:
                            print(f"[booknlp] patching cached weight: {p}")
                        d.pop("bert.embeddings.position_ids", None)
                        torch.save(sd, p)
                        patched += 1
            except Exception:
                # skip non-torch or unreadable files
                continue

        if self.verbose and patched:
            print(f"[booknlp] patched weights: {patched}")
        return patched

    def _run_cli(self, in_txt: Path, out_dir: Path, work_id: str) -> list[dict[str, Any]]:
        """Invoke BookNLP via CLI subprocess."""
        out_dir.mkdir(parents=True, exist_ok=True)
        env = dict(os.environ)
        env["JAVA_TOOL_OPTIONS"] = self.cfg.java_opts

        def build_cmd(flag: str, pipeline: str) -> list[str]:
            return [
                "booknlp",
                flag,
                pipeline,
                "--model",
                self.cfg.model,
                "--input",
                str(in_txt),
                "--output",
                str(out_dir),
                "--id",
                work_id,
            ]

        # Prefer --pipeline flag with configured pipeline
        pipeline = self.cfg.pipeline or "entity,quote,coref"
        cmd = build_cmd("--pipeline", pipeline)
        if self.verbose:
            print(f"[booknlp] CLI run: {' '.join(cmd)}")
        try:
            subprocess.run(cmd, check=True, env=env, timeout=self.cfg.timeout_s)
        except subprocess.CalledProcessError as e:
            # Fallback to legacy --pipe flag
            if self.verbose:
                print(f"[booknlp] CLI failed (code {e.returncode}); retrying with --pipe")
            cmd2 = build_cmd("--pipe", pipeline)
            if self.verbose:
                print(f"[booknlp] CLI run: {' '.join(cmd2)}")
            subprocess.run(cmd2, check=True, env=env, timeout=self.cfg.timeout_s)
        return self._load_quotes(out_dir, work_id)

    def _load_quotes(self, out_dir: Path, work_id: str) -> list[dict[str, Any]]:
        """Try common BookNLP quote outputs (TSV or JSON)."""
        # Try JSON first (v2+)
        json_path = out_dir / work_id / "quotes" / "quotes.json"
        if json_path.exists():
            try:
                data = json.loads(json_path.read_text(encoding="utf-8"))
                return self._parse_json_quotes(data)
            except Exception:
                pass

        # Try TSV fallback
        tsv_path = out_dir / work_id / "quotes" / "quotes.tsv"
        if tsv_path.exists():
            return self._parse_tsv_quotes(tsv_path)

        # Newer CLI/API sometimes output flat files: out/{work_id}.quotes + out/{work_id}.tokens
        flat_quotes = out_dir / f"{work_id}.quotes"
        flat_tokens = out_dir / f"{work_id}.tokens"
        if flat_quotes.exists():
            try:
                return self._parse_quotes_with_tokens(flat_quotes, flat_tokens if flat_tokens.exists() else None)
            except Exception as e:
                if self.verbose:
                    print(f"[booknlp] failed to parse flat quotes: {e}")

        if self.verbose:
            root = out_dir / work_id
            print(f"[booknlp] no quotes found under {root / 'quotes'}")
            # Print a compact tree to help diagnose alternate output layouts
            try:
                for p in sorted(root.rglob("*")):
                    rel = p.relative_to(out_dir)
                    # limit depth and number of entries
                    parts = list(rel.parts)
                    if len(parts) <= 4:
                        kind = "/" if p.is_dir() else ""
                        print(f"[booknlp] out: {rel}{kind}")
            except Exception:
                pass
        return []

    @staticmethod
    def _parse_json_quotes(data: Any) -> list[dict[str, Any]]:
        """Parse BookNLP quotes.json (schema may vary across versions)."""
        out: list[dict[str, Any]] = []
        # Expect list of quotes with char offsets and attributed speaker string
        # Example fields (approx): {"char_start": 10, "char_end": 25, "speaker": "Quinn", "confidence": 0.83}
        for q in data if isinstance(data, list) else data.get("quotes", []):
            try:
                out.append(
                    {
                        "start": int(q.get("char_start")),
                        "end": int(q.get("char_end")),
                        "speaker": str(q.get("speaker") or "").strip() or "Unknown",
                        "prob": float(q.get("confidence") or 0.0),
                    }
                )
            except Exception:
                continue
        return out

    @staticmethod
    def _parse_tsv_quotes(path: Path) -> list[dict[str, Any]]:
        """Parse BookNLP quotes.tsv (fallback). Expected columns include char offsets."""
        out: list[dict[str, Any]] = []
        rows = path.read_text(encoding="utf-8").splitlines()
        if not rows:
            return out
        header = rows[0].split("\t")
        idx = {name: i for i, name in enumerate(header)}

        def col(r: list[str], name: str, default: Any = "") -> Any:
            j = idx.get(name)
            return r[j] if j is not None and j < len(r) else default

        for line in rows[1:]:
            r = line.split("\t")
            try:
                start = int(col(r, "char_start", "0"))
                end = int(col(r, "char_end", "0"))
                speaker = (col(r, "speaker", "") or "").strip() or "Unknown"
                prob = float(col(r, "confidence", "0.0") or 0.0)
                out.append({"start": start, "end": end, "speaker": speaker, "prob": prob})
            except Exception:
                continue
        return out

    @staticmethod
    def _parse_quotes_with_tokens(quotes_path: Path, tokens_path: Path | None) -> list[dict[str, Any]]:
        """Parse flat BookNLP '{work_id}.quotes' using optional '{work_id}.tokens' for char offsets.

        quotes format header usually includes:
          quote_start, quote_end, mention_start, mention_end, mention_phrase, char_id, quote

        tokens header should include:
          token_ID_within_document, byte_onset, byte_offset
        """
        out: list[dict[str, Any]] = []

        # Build token index -> (onset, offset) map if tokens available
        tok_map: dict[int, tuple[int, int]] = {}
        if tokens_path and tokens_path.exists():
            rows = tokens_path.read_text(encoding="utf-8").splitlines()
            if rows:
                header = rows[0].split("\t")
                tid = {name: i for i, name in enumerate(header)}

                def tcol(r: list[str], name: str, default: str = "0") -> str:
                    j = tid.get(name)
                    return r[j] if j is not None and j < len(r) else default

                for line in rows[1:]:
                    if not line.strip():
                        continue
                    r = line.split("\t")
                    try:
                        idx = int(tcol(r, "token_ID_within_document", "0"))
                        onset = int(tcol(r, "byte_onset", "0"))
                        offset = int(tcol(r, "byte_offset", "0"))
                        tok_map[idx] = (onset, offset)
                    except Exception:
                        continue

        # Parse quotes
        qrows = quotes_path.read_text(encoding="utf-8").splitlines()
        if not qrows:
            return out
        qhdr = qrows[0].split("\t")
        qid = {name: i for i, name in enumerate(qhdr)}

        def qcol(r: list[str], name: str, default: str = "") -> str:
            j = qid.get(name)
            return r[j] if j is not None and j < len(r) else default

        for line in qrows[1:]:
            if not line.strip():
                continue
            r = line.split("\t")
            try:
                q_start_tok = int(qcol(r, "quote_start", "0"))
                q_end_tok = int(qcol(r, "quote_end", "0"))
                speaker = (qcol(r, "mention_phrase", "") or "").strip() or "Unknown"
                # Map to char offsets if possible; else leave zeros
                if tok_map:
                    start_char = tok_map.get(q_start_tok, (0, 0))[0]
                    end_char = tok_map.get(q_end_tok, (0, 0))[1]
                else:
                    # Fallback: we don't have token char mapping; we cannot compute offsets reliably
                    start_char = 0
                    end_char = 0
                out.append({"start": int(start_char), "end": int(end_char), "speaker": speaker, "prob": 0.0})
            except Exception:
                continue
        return out
