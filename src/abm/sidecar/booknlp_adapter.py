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
                    return self._run_cli(in_txt, out_dir, work_id)
            else:
                return self._run_cli(in_txt, out_dir, work_id)
        finally:
            if not self.cfg.keep_tmp:
                try:
                    shutil.rmtree(tmp_dir, ignore_errors=True)
                except Exception:
                    pass

    # ---------------------- internals ----------------------- #

    def _probe_available(self) -> bool:
        """Check for Python API or CLI availability."""
        try:
            import booknlp  # type: ignore  # noqa: F401

            return True
        except Exception:
            pass
        cli = shutil.which("booknlp")
        return cli is not None

    def _run_python_api(self, in_txt: Path, out_dir: Path, work_id: str) -> list[dict[str, Any]]:
        """Invoke BookNLP via Python API."""
        from booknlp.booknlp import BookNLP  # type: ignore

        out_dir.mkdir(parents=True, exist_ok=True)
        params = {"pipeline": "entity,quote,quote_attribution", "model": self.cfg.model}
        if self.verbose:
            print(f"[booknlp] python API run: {in_txt.name} → {out_dir}")
        nlp = BookNLP(self.cfg.model)
        nlp.process(in_txt, out_dir, work_id, **params)  # writes to out_dir/work_id/*
        return self._load_quotes(out_dir, work_id)

    def _run_cli(self, in_txt: Path, out_dir: Path, work_id: str) -> list[dict[str, Any]]:
        """Invoke BookNLP via CLI subprocess."""
        out_dir.mkdir(parents=True, exist_ok=True)
        env = dict(os.environ)
        env["JAVA_TOOL_OPTIONS"] = self.cfg.java_opts

        cmd = [
            "booknlp",
            "--pipe",
            "entity,quote,quote_attribution",
            "--model",
            self.cfg.model,
            "--input",
            str(in_txt),
            "--output",
            str(out_dir),
            "--id",
            work_id,
        ]
        if self.verbose:
            print(f"[booknlp] CLI run: {' '.join(cmd)}")
        subprocess.run(cmd, check=True, env=env, timeout=self.cfg.timeout_s)
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

        if self.verbose:
            print(f"[booknlp] no quotes found under {out_dir / work_id / 'quotes'}")
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
