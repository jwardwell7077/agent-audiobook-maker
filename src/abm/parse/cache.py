from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class DocCacheConfig:
    """Configuration for chapter Doc caching."""

    cache_dir: Path
    model_name: str = "en_core_web_trf"
    batch_size: int = 8
    # Guard against very large chapters
    max_length: int = 200_000


class DocCache:
    """Parse chapters with spaCy once, cache to DocBin on disk, and reload quickly."""

    def __init__(self, cfg: DocCacheConfig, *, verbose: bool = False) -> None:
        self.cfg = cfg
        self.verbose = verbose
        self.cfg.cache_dir.mkdir(parents=True, exist_ok=True)
        self._nlp: Any = None

    @property
    def nlp(self) -> Any:
        if self._nlp is None:
            import spacy  # local import

            if self.verbose:
                print(f"[parse] loading spaCy model: {self.cfg.model_name}")
            nlp = spacy.load(self.cfg.model_name)
            # Ensure large docs do not raise
            try:
                nlp.max_length = max(getattr(nlp, "max_length", 1_000_000), self.cfg.max_length)
            except Exception:
                pass
            self._nlp = nlp
        return self._nlp

    def _doc_path(self, chapter_index: int, title: str, text: str) -> Path:
        h = hashlib.sha256()
        h.update(str(chapter_index).encode())
        h.update(title.encode())
        h.update(str(len(text)).encode())
        h.update(text[:2048].encode())  # lightweight content checksum
        key = h.hexdigest()[:16]
        return self.cfg.cache_dir / f"ch_{chapter_index:04d}_{key}.spacy"

    def load_or_parse(self, chapters: list[dict[str, Any]]) -> list[tuple[dict[str, Any], Any]]:
        """Return list of (chapter_dict, Doc-like), loading from cache or parsing in batches."""
        # Local import to avoid top-level dependency
        from spacy.tokens import DocBin

        to_parse: list[tuple[int, dict[str, Any], Path]] = []
        ready: list[tuple[dict[str, Any], Any]] = []

        for ch in chapters:
            idx = int(ch.get("chapter_index", -1))
            title = ch.get("title") or f"ch_{idx}"
            text = ch.get("text") or "\n".join(ch.get("paragraphs", []))
            p = self._doc_path(idx, str(title), str(text))
            if p.exists():
                try:
                    db = DocBin().from_bytes(p.read_bytes())
                    docs = list(db.get_docs(self.nlp.vocab))
                    if docs:
                        ready.append((ch, docs[0]))
                        continue
                except Exception:
                    # fall through to re-parse if cache corrupt
                    pass
            to_parse.append((idx, {"idx": idx, "title": title, "text": text}, p))

        if not to_parse:
            if self.verbose:
                print("[parse] all chapters loaded from cache")
            return ready

        if self.verbose:
            print(f"[parse] parsing {len(to_parse)} chapters with nlp.pipe(batch_size={self.cfg.batch_size})")

        texts = [it[1]["text"] for it in to_parse]
        docs = self.nlp.pipe(texts, batch_size=self.cfg.batch_size)

        for (idx, _meta, p), doc in zip(to_parse, docs, strict=True):
            try:
                db = DocBin(store_user_data=False)
                db.add(doc)
                p.write_bytes(db.to_bytes())
            except Exception:
                pass
            # Match back to original chapter dict by index
            ch = next(c for c in chapters if int(c.get("chapter_index", -1)) == idx)
            ready.append((ch, doc))

        return ready
