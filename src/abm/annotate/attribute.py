# src/abm/annotate/attribute.py
from __future__ import annotations

import os
import re
import warnings
from dataclasses import dataclass
from typing import Any, cast

# --- Optional deps (handled gracefully) ---
try:
    import spacy as spacy_mod

    _HAS_SPACY = True
except Exception:
    # Fall back to dummy object; guarded by _HAS_SPACY checks elsewhere
    spacy_mod = None  # type: ignore
    _HAS_SPACY = False

# Avoid optional torchvision import path inside Transformers (not needed for NLP)
os.environ.setdefault("TRANSFORMERS_NO_TORCHVISION", "1")

# Suppress torch CUDA pynvml deprecation warning emitted during torch.cuda init
# Message typically: "The pynvml package is deprecated. Please install nvidia-ml-py instead."
warnings.filterwarnings("ignore", category=FutureWarning, message=r"The pynvml package is deprecated.*")

# Optional fastcoref availability flag (import guarded)
try:  # pragma: no cover - optional import
    import fastcoref  # type: ignore  # noqa: F401

    _HAS_COREF = True
except Exception:  # pragma: no cover - import guard
    _HAS_COREF = False


@dataclass
class AttributeConfig:
    """Config for attribution engine."""

    llm_threshold: float = 0.90
    context_chars: int = 220
    coref_context_chars: int = 400
    stop_at_scene_break: bool = True
    prefer_transformer_spacy: bool = True
    # Bounded-context attribution knobs
    max_context_chars: int = 600  # hard cap
    min_context_chars: int = 240  # first try
    mid_context_chars: int = 480  # second try
    max_sents: int = 2  # clamp to N sentence ends
    clip_at_next_quote: bool = True  # stop at the next opening quote
    stop_at_double_newline: bool = True  # stop at blank line/scene break


SPEECH_VERBS_STRONG = {
    "say",
    "ask",
    "reply",
    "respond",
    "answer",
    "remark",
    "state",
    "declare",
    "add",
    "explain",
    "announce",
    "admit",
    "agree",
    "concede",
    "insist",
    "suggest",
    "propose",
    "demand",
    "order",
    "command",
    "urge",
    "warn",
    "promise",
    "assure",
    "remind",
    "request",
    "shout",
    "yell",
    "scream",
    "bellow",
    "roar",
    "holler",
    "call",
    "cry",
    "exclaim",
    "shriek",
    "whisper",
    "murmur",
    "mutter",
    "mumble",
    "hiss",
    "growl",
    "snarl",
    "bark",
    "grumble",
    "sob",
    "stammer",
    "stutter",
    "blurt",
    "quip",
    "joke",
    "tease",
    "protest",
    "object",
    "counter",
    "retort",
    "interject",
    "interpose",
    "intervene",
    "interrupt",
    "inquire",
    "question",
    "press",
    "note",
    "observe",
    "comment",
    "mention",
    "inform",
}
SPEECH_VERBS_MEDIUM = {
    "chime",
    "butt",
    "cut",
    "break",
    "pipe",
    "trail",
    "continue",
    "talk",
    "speak",
    "gasp",
    "sigh",
    "groan",
    "moan",
    "snort",
    "sniff",
}
PHRASAL_SPEECH_VERBS = {
    "chime in": "chime_in",
    "butt in": "butt_in",
    "cut in": "cut_in",
    "break in": "break_in",
    "pipe up": "pipe_up",
    "call out": "call_out",
    "call over": "call_over",
    "call up": "call_up",
    "go on": "go_on",
    "trail off": "trail_off",
    "speak up": "speak_up",
    "speak out": "speak_out",
}
SPEECH_VERBS_WEAK = {"smile", "smirk", "glower", "glare", "laugh", "beam", "grin", "shrug", "scoff", "sneer"}
SPEECH_LEMMAS = SPEECH_VERBS_STRONG | SPEECH_VERBS_MEDIUM | SPEECH_VERBS_WEAK

RE_THOUGHT_CUE = re.compile(r"\b([A-Z][a-z]+)\s+thought\b")
RE_DESCRIPTOR = re.compile(
    r"\b(a|the)\s+(?P<desc>(female|male)\s+voice|young\s+man|confident\s+young\s+voice)\s+"
    r"(said|asked|replied|called|cried)\b",
    re.IGNORECASE,
)


class AttributeEngine:
    """Speaker attribution using rules → coref → optional LLM."""

    def __init__(
        self,
        mode: str = "high",
        llm_tag: str | None = None,
        config: AttributeConfig | None = None,
        verbose: bool = False,
        force_spacy_model: str | None = None,
        use_coref: bool = True,
    ) -> None:
        self.mode = mode
        self.llm_tag = llm_tag
        self.cfg = config or AttributeConfig()
        self.verbose = verbose
        self.force_spacy_model = force_spacy_model
        self.use_coref = use_coref

        # Pipelines
        self.ner_nlp: Any | None = None
        self.dep_nlp: Any | None = None
        self.dep_matcher: Any | None = None
        self.coref_nlp: Any | None = None

        if _HAS_SPACY:
            # Prefer GPU if available (spaCy/transformers will leverage torch CUDA)
            self.on_gpu = False
            try:
                import torch as _torch

                cuda_ok = bool(_torch.cuda.is_available())
                print(f"[attribute] CUDA available: {cuda_ok}")
                self.on_gpu = cuda_ok
            except Exception:
                self.on_gpu = False
            # Prefer GPU when present, but don't hard-require CuPy
            try:
                _pref = getattr(spacy_mod, "prefer_gpu", None)
                if callable(_pref):
                    _pref()
            except Exception:
                pass
            model_name = self.force_spacy_model or (
                "en_core_web_trf" if (self.mode == "high" and self.cfg.prefer_transformer_spacy) else "en_core_web_sm"
            )
            if self.verbose:
                print(f"[attribute] loading spaCy model: {model_name}")
            self.ner_nlp = self._safe_load_spacy(model_name)
            self.dep_nlp = self.ner_nlp
            if self.verbose:
                print("[attribute] building dependency matcher")
            # Import here to avoid top-level type assignment and ease optionality
            from spacy.matcher import DependencyMatcher as _DM  # type: ignore

            DM: Any = cast(Any, _DM)
            assert self.dep_nlp is not None
            vocab_any = cast(Any, self.dep_nlp).vocab
            self.dep_matcher = DM(vocab_any)
            self._init_dep_patterns()
        else:
            if self.verbose:
                print("[attribute] spaCy not available")

        if _HAS_SPACY and _HAS_COREF and self.use_coref:
            try:
                # Ensure the spaCy factory for fastcoref is registered before add_pipe
                from fastcoref import spacy_component  # noqa: F401

                if self.verbose:
                    print("[attribute] loading fastcoref pipeline")

                sp: Any = cast(Any, spacy_mod)
                cnlp = sp.load("en_core_web_sm", exclude=["ner", "lemmatizer", "textcat"])
                add_cfg = {}
                try:
                    import torch as _torch

                    add_cfg = {"device": "cuda:0" if _torch.cuda.is_available() else "cpu"}
                except Exception:
                    add_cfg = {"device": "cpu"}
                # device config is best-effort; component will default to torch device
                cnlp.add_pipe("fastcoref", config=add_cfg)
                self.coref_nlp = cnlp
            except Exception as e:
                if self.verbose:
                    print(f"[attribute] fastcoref unavailable: {e}")
                self.coref_nlp = None
        else:
            if self.verbose:
                print("[attribute] coref disabled")
            self.coref_nlp = None

    # --------------------------- Public API ---------------------------

    def _init_dep_patterns(self) -> None:
        """Install dependency patterns for 'speech-verb + subject' attribution.

        Adds a single rule that matches a reporting verb with a nominal subject
        (proper noun or pronoun). This feeds _try_dep_subject.
        """
        if not (_HAS_SPACY and self.dep_nlp is not None and self.dep_matcher is not None):
            return

        # Clear if already present (defensive for hot-reloads)
        try:
            self.dep_matcher.remove("REPORT_VERB_SUBJ")
        except Exception:
            pass

        pattern = [
            {
                "RIGHT_ID": "verb",
                "RIGHT_ATTRS": {"LEMMA": {"IN": list(SPEECH_LEMMAS)}, "POS": "VERB"},
            },
            {
                "LEFT_ID": "verb",
                "REL_OP": ">",
                "RIGHT_ID": "subj",
                "RIGHT_ATTRS": {"DEP": {"IN": ["nsubj", "nsubjpass"]}, "POS": {"IN": ["PROPN", "PRON"]}},
            },
        ]

        self.dep_matcher.add("REPORT_VERB_SUBJ", [pattern])

    def attribute_span(
        self,
        text: str,
        span_chars: tuple[int, int],
        span_type: str,
        roster: dict[str, list[str]],
        neighbors: tuple[dict[str, int] | None, dict[str, int] | None] | None = None,
        doc: Any | None = None,
    ) -> tuple[str, str, float]:
        # Non-dialogue is handled by caller; be defensive anyway
        if span_type in {"System"}:
            return "System", "rule:system_line", 1.0
        if span_type in {"Meta", "SectionBreak", "Heading"}:
            return "Narrator", "rule:non_story", 1.0
        if span_type == "Narration":
            return "Narrator", "rule:default_narration", 0.99

        # Thought cue
        speaker, method, conf = self._try_thought_cue(text, span_chars, span_type, roster)
        if speaker:
            return speaker, method, conf

        # Descriptor (“the female voice said”)
        speaker, method, conf = self._try_descriptor(text, span_chars)
        if speaker:
            return speaker, method, conf

        # If we have a full-doc parse, try sentence-bounded dependency first
        if doc is not None:
            try:
                a, b = span_chars
                # Find containing sentences for start and end
                sents = list(getattr(doc, "sents", []))
                sent_a = next(
                    (s for s in sents if getattr(s, "start_char", -1) <= a < getattr(s, "end_char", -1)),
                    None,
                )
                sent_b = next(
                    (s for s in sents if getattr(s, "start_char", -1) < b <= getattr(s, "end_char", -1)),
                    None,
                )
                regions: list[tuple[int, int]] = []
                if sent_b is not None:
                    # forward region: from quote end to end of next sentence (max clamp)
                    try:
                        next_sent = sent_b.nbor(1)
                    except Exception:
                        next_sent = None
                    f_end = getattr(next_sent, "end_char", getattr(sent_b, "end_char", b))
                    regions.append((b, min(len(text), f_end, b + self.cfg.max_context_chars)))
                if sent_a is not None:
                    # backward region: from start of previous sentence to quote start (max clamp)
                    try:
                        prev_sent = sent_a.nbor(-1)
                    except Exception:
                        prev_sent = None
                    _start = getattr(prev_sent, "start_char", getattr(sent_a, "start_char", a))
                    regions.append((max(0, a - self.cfg.max_context_chars), a))

                for ra, rb in regions:
                    speaker, method, conf = self._dep_in_window(text, ra, rb, b, roster)
                    if speaker:
                        return speaker, method, conf
            except Exception:
                # Fall through to window-based approach
                pass

        # Dependency subject (bounded windows if neighbors are provided)
        if neighbors is not None:
            prev_lite, next_lite = neighbors
            for a, b in self._bounded_windows(text, span_chars[0], span_chars[1], prev_lite, next_lite):
                speaker, method, conf = self._dep_in_window(text, a, b, span_chars[1], roster)
                if speaker:
                    return speaker, method, conf
            # Fallback to legacy ±context if bounded windows didn't yield a result
            speaker, method, conf = self._try_dep_subject(text, span_chars, roster)
            if speaker:
                return speaker, method, conf
        else:
            speaker, method, conf = self._try_dep_subject(text, span_chars, roster)
            if speaker:
                return speaker, method, conf

        # LLM fallback hook (optional; default off)
        if self.llm_tag and self.cfg.llm_threshold > 0:
            llm_speaker, llm_conf = self._ask_llm(text, span_chars, roster)
            if llm_conf > 0.0:
                return llm_speaker, "llm", llm_conf

        return "Unknown", "rule:unknown", 0.50 if span_type in {"Dialogue", "Thought"} else 0.99

    # --------------------------- Rule helpers ---------------------------

    def _clip_forward(self, s: str) -> str:
        """Clamp forward context to max_sents and stop tokens."""
        out = s
        if self.cfg.stop_at_double_newline:
            out = out.split("\n\n", 1)[0]
        if self.cfg.clip_at_next_quote:
            qpos = out.find('"')
            if qpos != -1:
                out = out[:qpos]
        # sentence clamp (cheap heuristic): count .?! (keep at most cfg.max_sents)
        cnt = 0
        for i, ch in enumerate(out):
            if ch in ".?!":
                cnt += 1
                if cnt >= self.cfg.max_sents:
                    return out[: i + 1]
        return out

    def _clip_backward(self, s: str) -> str:
        """Clamp backward context to last max_sents sentences and stop tokens."""
        out = s
        if self.cfg.stop_at_double_newline and "\n\n" in out:
            out = out.split("\n\n")[-1]
        if self.cfg.clip_at_next_quote:
            # avoid crossing into a previous quote too far back
            qpos = out.rfind('"')
            if qpos != -1:
                out = out[qpos + 1 :]
        # keep only last max_sents sentences (cheap heuristic)
        ends = [i for i, ch in enumerate(out) if ch in ".?!"]
        if len(ends) > self.cfg.max_sents:
            cut = ends[-self.cfg.max_sents]
            return out[cut + 1 :]
        return out

    def _dep_in_window(
        self,
        text: str,
        a: int,
        b: int,
        quote_end: int,
        roster: dict[str, list[str]],
    ) -> tuple[str | None, str, float]:
        """Run dependency rule inside [a:b] (absolute char offsets)."""
        if not _HAS_SPACY or self.dep_nlp is None or self.dep_matcher is None:
            return None, "", 0.0
        ctx = text[a:b]
        if not ctx.strip():
            return None, "", 0.0
        doc = self.dep_nlp(ctx)
        rel_end_char = max(0, min(len(ctx) - 1, quote_end - a))
        rel_end_tok = min(range(len(doc)), key=lambda i: abs(doc[i].idx - rel_end_char)) if len(doc) else 0

        matches = self.dep_matcher(doc) if self.dep_matcher is not None else []
        if not matches:
            # fall back to phrasal rule in this window
            return self._try_phrasal_dep(doc, rel_end_tok, roster, a)

        best = None
        for _, (verb_i, subj_i) in matches:
            dist = abs(verb_i - rel_end_tok)
            if best is None or dist < best[2]:
                best = (verb_i, subj_i, dist)
        if best is None:
            return None, "", 0.0

        _, subj_i, _ = best
        subj = doc[subj_i]
        if subj.pos_ == "PROPN":
            canon = self._canonical_from_roster(subj.text, roster)
            return (canon or subj.text), "rule:dep_subj", 0.95 if canon else 0.92
        if subj.pos_ == "PRON":
            name = self._resolve_pronoun_coref(ctx, (subj.idx, subj.idx + len(subj)))
            if name:
                canon = self._canonical_from_roster(name, roster)
                return (canon or name), "rule:coref", 0.86 if canon else 0.84
        return None, "", 0.0

    def _bounded_windows(
        self,
        text: str,
        s: int,
        e: int,
        prev_lite: dict[str, int] | None,
        next_lite: dict[str, int] | None,
    ) -> list[tuple[int, int]]:
        """Return candidate [a:b] absolute windows (forward first, then backward) with dynamic sizes."""
        sizes = (self.cfg.min_context_chars, self.cfg.mid_context_chars, self.cfg.max_context_chars)
        forward_limit = int(next_lite["start"]) if next_lite is not None else len(text)
        backward_limit = int(prev_lite["end"]) if prev_lite is not None else 0

        windows: list[tuple[int, int]] = []
        # forward tries
        for L in sizes:
            a = e
            b = min(forward_limit, e + L)
            frag = self._clip_forward(text[a:b])
            if frag:
                windows.append((a, a + len(frag)))
        # backward tries
        for L in sizes:
            b = s
            a = max(backward_limit, s - L)
            frag = self._clip_backward(text[a:b])
            if frag:
                windows.append((b - len(frag), b))
        return windows

    def _try_thought_cue(
        self, text: str, span_chars: tuple[int, int], span_type: str, roster: dict[str, list[str]]
    ) -> tuple[str | None, str, float]:
        if span_type != "Thought":
            return None, "", 0.0
        s, e = span_chars
        for ctx in (text[e : min(len(text), e + 140)], text[max(0, s - 140) : s]):
            m = RE_THOUGHT_CUE.search(ctx)
            if not m:
                continue
            name = m.group(1)
            canon = self._canonical_from_roster(name, roster)
            return (canon or name), "rule:thought_cue", 0.90 if canon else 0.88
        return None, "", 0.0

    def _try_descriptor(self, text: str, span_chars: tuple[int, int]) -> tuple[str | None, str, float]:
        s, e = span_chars
        for ctx in (text[e : min(len(text), e + 160)], text[max(0, s - 160) : s]):
            m = RE_DESCRIPTOR.search(ctx)
            if not m:
                continue
            desc = m.group("desc").title().replace(" ", "")
            return f"Unknown-{desc}", "rule:descriptor", 0.75
        return None, "", 0.0

    def _try_dep_subject(
        self, text: str, span_chars: tuple[int, int], roster: dict[str, list[str]]
    ) -> tuple[str | None, str, float]:
        if not _HAS_SPACY or self.dep_nlp is None or self.dep_matcher is None:
            return None, "", 0.0

        s, e = span_chars
        a, b = max(0, s - self.cfg.context_chars), min(len(text), e + self.cfg.context_chars)
        ctx = text[a:b]
        doc = self.dep_nlp(ctx)
        if not doc:
            return None, "", 0.0
        rel_end_char = e - a
        rel_end_tok = min(range(len(doc)), key=lambda i: abs(doc[i].idx - rel_end_char)) if len(doc) > 0 else 0

        matches = self.dep_matcher(doc) if self.dep_matcher is not None else []
        if not matches:
            return self._try_phrasal_dep(doc, rel_end_tok, roster, a)

        best = None
        for _, (verb_i, subj_i) in matches:
            dist = abs(verb_i - rel_end_tok)
            if best is None or dist < best[2]:
                best = (verb_i, subj_i, dist)
        if best is None:
            return None, "", 0.0

        _, subj_i, _ = best
        subj = doc[subj_i]
        if subj.pos_ == "PROPN":
            canon = self._canonical_from_roster(subj.text, roster)
            return (canon or subj.text), "rule:dep_subj", 0.95 if canon else 0.92
        if subj.pos_ == "PRON":
            name = self._resolve_pronoun_coref(ctx, (subj.idx, subj.idx + len(subj)))
            if name:
                canon = self._canonical_from_roster(name, roster)
                return (canon or name), "rule:coref", 0.86 if canon else 0.84
        return None, "", 0.0

    def _try_phrasal_dep(
        self,
        doc: Any,
        rel_end_tok: int,
        roster: dict[str, list[str]],
        base_offset: int,
    ) -> tuple[str | None, str, float]:
        if not _HAS_SPACY:
            return None, "", 0.0
        best: tuple[int, int, int] | None = None
        for i in range(len(doc) - 1):
            bigram = f"{doc[i].lemma_.lower()} {doc[i + 1].lemma_.lower()}"
            if bigram in PHRASAL_SPEECH_VERBS:
                dist = abs(i - rel_end_tok)
                if best is None or dist < best[2]:
                    best = (i, i + 1, dist)
        if best is None:
            return None, "", 0.0

        i0, i1, _ = best
        win_lo = max(0, min(i0, i1) - 12)
        win_hi = min(len(doc), max(i0, i1) + 12)
        subj_token = None
        for t in doc[win_lo:win_hi]:
            if t.dep_ in {"nsubj", "nsubjpass"} and t.pos_ in {"PROPN", "PRON"}:
                subj_token = t
                break
        if subj_token is None:
            return None, "", 0.0

        if subj_token.pos_ == "PROPN":
            canon = self._canonical_from_roster(subj_token.text, roster)
            return (canon or subj_token.text), "rule:dep_phrasal", 0.90 if canon else 0.88

        # Otherwise, try pronoun coref within this window
        name = self._resolve_pronoun_coref(cast(Any, doc).text, (subj_token.idx, subj_token.idx + len(subj_token)))
        if name:
            canon = self._canonical_from_roster(name, roster)
            return (canon or name), "rule:coref", 0.84 if canon else 0.82
        return None, "", 0.0

    # --------------------------- Coref ---------------------------

    def _resolve_pronoun_coref(self, context_text: str, pron_rel_span: tuple[int, int]) -> str | None:
        if not (_HAS_SPACY and _HAS_COREF) or self.coref_nlp is None:
            return None
        doc = self.coref_nlp(context_text)
        clusters = getattr(doc._, "coref_clusters", None)
        if not clusters:
            return None
        for cluster in clusters:
            pron_in = any(s <= pron_rel_span[0] < e for (s, e) in cluster)
            if not pron_in:
                continue
            prev = [(s, e) for (s, e) in cluster if s < pron_rel_span[0]]
            prev.sort(key=lambda p: p[1], reverse=True)
            for s, e in prev:
                candidate = context_text[s:e]
                if candidate and candidate[0].isupper():
                    return candidate
        return None

    # --------------------------- Utils ---------------------------

    @staticmethod
    def _canonical_from_roster(name: str, roster: dict[str, list[str]]) -> str | None:
        for canon, aliases in roster.items():
            if name == canon or name in aliases:
                return canon
        return None

    @staticmethod
    def _safe_load_spacy(model: str) -> object:
        assert _HAS_SPACY
        try:
            return cast(Any, spacy_mod).load(model)
        except Exception:
            return cast(Any, spacy_mod).load("en_core_web_sm")

    # --------------------------- LLM hook ---------------------------

    def _ask_llm(self, text: str, span_chars: tuple[int, int], roster: dict[str, list[str]]) -> tuple[str, float]:
        # Wire this to your local server if desired.
        return "Unknown", 0.0
