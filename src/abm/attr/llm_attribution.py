from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from time import time
from typing import Any

from abm.attr.ollama_backend import OllamaBackend, OllamaConfig


@dataclass
class LLMAttrConfig:
    context_radius: int = 4
    max_json_retries: int = 2
    temperature: float = 0.4
    min_conf_for_skip: float = 0.85
    cache_dir: str = ".cache/abm"
    model_name: str = "llama3.1:8b-instruct"
    prompt_version: str = "v2"
    timeout_s: float = 30.0
    re_attribute_all: bool = False  # can be set True to force all spans through LLM
    base_url: str = "http://localhost:11434"


def _cache_key(payload: dict[str, Any]) -> str:
    s = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


class LLMAttributor:
    """LLM Attribution orchestrator (skeleton).

    Implements selection of target spans and prepares prompts/contexts.
    JSON parsing, retries, and fallbacks to be implemented per spec.
    """

    def __init__(self, config: LLMAttrConfig | None = None) -> None:
        self.config = config or LLMAttrConfig()
        self._backend = OllamaBackend(
            OllamaConfig(
                base_url=self.config.base_url,
                model_name=self.config.model_name,
                temperature=self.config.temperature,
                timeout_s=self.config.timeout_s,
            )
        )

    def run(self, spans_attr: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        out: list[dict[str, Any]] = []
        cache_hits = 0
        cache_misses = 0
        cache_base = Path(self.config.cache_dir).expanduser().resolve() / "llm_attr"
        # Meta counters
        dialogue_spans = 0
        llm_attempted = 0
        generic_blocked_count = 0
        verbose_replaced_count = 0
        unknown_after_llm = 0
        final_unknown = 0

        # Disallow / generic role list (lowercase)
        disallowed_generics = {
            "protagonist",
            "main character",
            "the character",
            "character",
            "speaker",
            "the speaker",
            "player",
            "the player",
            "narrator",
            "the narrator",
            "detective",  # role unless explicitly named elsewhere
        }

        # Provide few-shot examples once (embedded in every prompt for simplicity; could optimize later)
        FEW_SHOT = (
            "Examples:\n"
            "Example 1:\n"
            'dialogue_text: "Where is the map?"\n'
            'narration_before: ["Tom adjusted his pack."]\n'
            'Return: {"speaker":"Tom","confidence":1.0,"rationale":"Exact name Tom appears just before."}\n\n'
            "Example 2:\n"
            'dialogue_text: "We should hurry."\n'
            'narration_before: ["The wind howled."]\n'
            'narration_after: ["They marched on."]\n'
            'Return: {"speaker":"Unknown","confidence":0.0,"rationale":"No character names nearby."}\n\n'
            "Example 3:\n"
            'dialogue_text: "I won\'t give up."\n'
            'narration_before: ["The hero stumbled forward."]\n'
            'Return: {"speaker":"Unknown","confidence":0.0,"rationale":"Only generic role word present."}'
        )

        for g_idx, rec in enumerate(spans_attr):
            typ = (rec.get("type") or rec.get("role") or "").lower()
            attr = rec.get("attribution") or {}
            conf = float(attr.get("confidence") or 0.0)
            method = str(attr.get("method") or "")

            target = self.config.re_attribute_all or (
                typ == "dialogue"
                and (
                    not attr.get("speaker")
                    or method == "unknown"
                    or conf < self.config.min_conf_for_skip
                    or str(attr.get("speaker")).strip().lower()
                    in {
                        "protagonist",
                        "main character",
                        "the character",
                        "character",
                        "narrator",
                        "the narrator",
                        "speaker",
                        "the speaker",
                        "player",
                        "the player",
                        "detective",
                    }
                )
            )

            if typ == "dialogue":
                dialogue_spans += 1

            if not target:
                out.append(rec)
                continue

            # Build escalating context prompts without heuristic contamination
            dialogue_text = str(rec.get("text_norm") or rec.get("text_raw") or "")

            def gather_context(seq: list[dict[str, Any]], idx: int, radius: int) -> tuple[list[str], list[str]]:
                before: list[str] = []
                after: list[str] = []
                # Collect narration spans only; asymmetric allocation: 2x before vs after
                # before: older→newer, then we truncate to the last N to prioritize recent ones
                # after: in order
                # 1) gather raw lists
                for j in range(max(0, idx - radius * 2), idx):
                    lab = (seq[j].get("type") or seq[j].get("role") or "").lower()
                    if lab == "narration":
                        txt = str(seq[j].get("text_norm") or seq[j].get("text_raw") or "")
                        if txt:
                            before.append(txt)
                for j in range(idx + 1, min(len(seq), idx + 1 + radius)):
                    lab = (seq[j].get("type") or seq[j].get("role") or "").lower()
                    if lab == "narration":
                        txt = str(seq[j].get("text_norm") or seq[j].get("text_raw") or "")
                        if txt:
                            after.append(txt)
                # 2) approximate token clamp (by char length)

                def clamp_list(items: list[str], max_chars: int) -> list[str]:
                    out_l: list[str] = []
                    total = 0
                    for t in items:
                        if total + len(t) > max_chars:
                            break
                        out_l.append(t)
                        total += len(t)
                    return out_l

                before = clamp_list(before, 1200)
                after = clamp_list(after, 600)
                return before, after

            # Retry 1: dialogue only
            def make_prompt(
                d_text: str,
                before_ctx: list[str] | None = None,
                after_ctx: list[str] | None = None,
                dialogue_window: list[dict[str, str]] | None = None,
                recent_speakers: list[str] | None = None,
            ) -> str:
                parts: list[str] = []
                parts.append(
                    "You perform precise speaker attribution for a novel. "
                    'Return ONLY one JSON object: {"speaker": string, "confidence": number, "rationale": string}.'
                )
                parts.append(
                    "Rules: speaker must be a short existing character name (≤3 words, ≤25 chars) from evidence. "
                    "If none, return Unknown."
                )
                parts.append(
                    "Disallowed generic role words (use Unknown instead): "
                    "protagonist, main character, the character, character, narrator, the narrator, "
                    "speaker, the speaker, player, the player, detective."
                )
                parts.append(
                    "Confidence rubric: 1.0 exact name+dialogue verb; 0.8 strong continuity; "
                    "0.6 weak inference; 0.0 Unknown (never >0.0)."
                )
                parts.append(FEW_SHOT)
                parts.append(f"dialogue_text: {json.dumps(d_text)}")
                if before_ctx is not None:
                    parts.append(f"narration_before: {json.dumps(before_ctx)}")
                if after_ctx is not None:
                    parts.append(f"narration_after: {json.dumps(after_ctx)}")
                if dialogue_window is not None:
                    parts.append(f"dialogue_window: {json.dumps(dialogue_window)}")
                if recent_speakers is not None:
                    parts.append(f"recent_speakers: {json.dumps(recent_speakers)}")
                parts.append("Return only JSON. No prose, no markdown.")
                return "\n".join(parts)

            # Find our index within the block sequence if available
            seq: list[dict[str, Any]] = []
            idx_in_seq: int | None = None
            # Primary: use explicit block sequence if provided
            if isinstance(rec.get("_block_seq"), list):
                block_spans = rec["_block_seq"]
                val = rec.get("_block_index")
                if isinstance(val, int):
                    idx_in_seq = val
                    seq = block_spans
            else:
                # Fallback: treat the entire incoming span list as a sequence so we still get
                # surrounding narration context. This is a heuristic until upstream grouping
                # provides tighter blocks. Safe because gather_context filters for narration only.
                seq = spans_attr
                idx_in_seq = g_idx

            # Build dialogue_window (local surrounding dialogue lines w/ current attributed speakers if any)
            def build_dialogue_window(
                seq_all: list[dict[str, Any]], center: int, radius: int = 3
            ) -> list[dict[str, str]]:
                window: list[dict[str, str]] = []
                start = max(0, center - radius)
                end = min(len(seq_all), center + radius + 1)
                for j in range(start, end):
                    if j == center:
                        continue
                    lab = (seq_all[j].get("type") or seq_all[j].get("role") or "").lower()
                    if lab == "dialogue":
                        atp = seq_all[j].get("attribution") or {}
                        spk = str(atp.get("speaker") or "").strip()
                        txt = str(seq_all[j].get("text_norm") or seq_all[j].get("text_raw") or "")
                        if txt:
                            window.append({"speaker": spk, "text": txt[:140]})
                return window[:6]

            def build_recent_speakers(already: list[dict[str, Any]], limit: int = 5) -> list[str]:
                names: list[str] = []
                seen: set[str] = set()
                for prev in reversed(already):
                    lab = (prev.get("type") or prev.get("role") or "").lower()
                    if lab == "dialogue":
                        atp = prev.get("attribution") or {}
                        spk = str(atp.get("speaker") or "").strip()
                        if spk and spk.lower() not in seen:
                            names.append(spk)
                            seen.add(spk.lower())
                        if len(names) >= limit:
                            break
                return list(reversed(names))

            retries = max(1, int(self.config.max_json_retries))
            attempts: list[dict[str, Any]] = []

            # Attempt 1
            attempts.append(
                {
                    "prompt": make_prompt(dialogue_text),
                    "payload": {
                        "dialogue_text": dialogue_text,
                        "narration_before": None,
                        "narration_after": None,
                        "dialogue_window": None,
                        "recent_speakers": None,
                        "prompt_version": self.config.prompt_version,
                        "model_name": self.config.model_name,
                        "temperature": self.config.temperature,
                        "v": "v2",
                    },
                }
            )

            # Attempt 2 (add context)
            if seq and idx_in_seq is not None:
                b, a = gather_context(seq, idx_in_seq, int(self.config.context_radius))
                dwin = build_dialogue_window(seq, idx_in_seq, 3)
                rrecent = build_recent_speakers(out, 5)
                attempts.append(
                    {
                        "prompt": make_prompt(dialogue_text, b, a, dwin, rrecent),
                        "payload": {
                            "dialogue_text": dialogue_text,
                            "narration_before": b,
                            "narration_after": a,
                            "dialogue_window": dwin,
                            "recent_speakers": rrecent,
                            "prompt_version": self.config.prompt_version,
                            "model_name": self.config.model_name,
                            "temperature": self.config.temperature,
                            "v": "v2",
                        },
                    }
                )

            # Attempt 3 (expanded window)
            if seq and idx_in_seq is not None:
                b2, a2 = gather_context(seq, idx_in_seq, int(self.config.context_radius) * 2)
                dwin2 = build_dialogue_window(seq, idx_in_seq, 5)
                rrecent2 = build_recent_speakers(out, 7)
                attempts.append(
                    {
                        "prompt": make_prompt(dialogue_text, b2, a2, dwin2, rrecent2),
                        "payload": {
                            "dialogue_text": dialogue_text,
                            "narration_before": b2,
                            "narration_after": a2,
                            "dialogue_window": dwin2,
                            "recent_speakers": rrecent2,
                            "prompt_version": self.config.prompt_version,
                            "model_name": self.config.model_name,
                            "temperature": self.config.temperature,
                            "v": "v2",
                        },
                    }
                )

            # Trim to retry budget
            attempts = attempts[:retries]

            parsed: dict[str, Any] | None = None
            raw_text: str | None = None
            cache_key_used: str | None = None
            cache_hit_this: bool = False
            for attempt in attempts:
                prompt = attempt["prompt"]
                payload = attempt["payload"]
                # Compute cache key and check disk
                key = _cache_key(payload)
                shard = key[:2]
                cache_path = cache_base / shard / f"{key}.json"
                cache_key_used = key
                raw: str
                if cache_path.exists():
                    try:
                        with cache_path.open("r", encoding="utf-8") as f:
                            cached = json.load(f)
                        raw = str(cached.get("raw_text") or "")
                        cache_hit_this = True
                    except Exception:
                        raw = self._backend.generate(prompt)
                else:
                    raw = self._backend.generate(prompt)
                    try:
                        cache_path.parent.mkdir(parents=True, exist_ok=True)
                        with cache_path.open("w", encoding="utf-8") as f:
                            json.dump(
                                {
                                    "request": payload,
                                    "raw_text": raw,
                                    "ts": time(),
                                },
                                f,
                                ensure_ascii=False,
                            )
                    except Exception:
                        # Ignore cache write errors
                        pass
                raw_text = raw
                try:
                    parsed = json.loads(raw)
                except Exception:
                    start = raw.find("{")
                    end = raw.rfind("}")
                    if 0 <= start < end:
                        try:
                            parsed = json.loads(raw[start : end + 1])
                        except Exception:
                            parsed = None
                if isinstance(parsed, dict):
                    # If speaker is generic/unknown and we have more attempts, try next (expanded set)
                    sp_raw = parsed.get("speaker") if isinstance(parsed, dict) else None
                    if isinstance(sp_raw, str):
                        sp_l = sp_raw.strip().lower()
                        generic_tokens = {
                            "",
                            "unknown",
                            "protagonist",
                            "main character",
                            "the character",
                            "character",
                            "speaker",
                            "the speaker",
                            "player",
                            "the player",
                            "narrator",
                            "the narrator",
                        }
                        if sp_l in generic_tokens and attempt is not attempts[-1]:
                            parsed = None
                            continue
                    break
            if not isinstance(parsed, dict):
                parsed = {"speaker": "", "confidence": 0.0, "rationale": "parse_error"}

            new_attr = dict(attr)
            speaker = ""
            new_conf = conf
            llm_attempted += 1
            if isinstance(parsed, dict):
                sp = parsed.get("speaker")
                if isinstance(sp, str):
                    speaker = sp.strip()
                c = parsed.get("confidence")
                if isinstance(c, int | float):
                    new_conf = max(0.0, min(1.0, float(c)))
                elif isinstance(c, str):
                    try:
                        new_conf = max(0.0, min(1.0, float(c.strip())))
                    except ValueError:
                        pass

            # Simple fallback: if empty speaker, keep previous speaker or leave empty; actual fallback in next iteration
            # Fallbacks to guarantee non-empty speaker
            qa_flags: list[str] = []
            final_speaker = speaker.strip()
            fallback_method: str | None = None
            if not final_speaker:
                # 1) continuity_prev within the same sequence (search backward then forward)
                def find_prev_dialogue(
                    from_idx: int,
                    max_lookback: int = 3,
                    seq_in: list[dict[str, Any]] | None = None,
                ) -> str:
                    base_seq = seq_in if seq_in is not None else []
                    if not base_seq or from_idx is None:
                        return ""
                    # backward
                    for j in range(max(0, from_idx - max_lookback), from_idx):
                        if (base_seq[j].get("type") or base_seq[j].get("role") or "").lower() == "dialogue":
                            at = base_seq[j].get("attribution") or {}
                            spk = str(at.get("speaker") or "").strip()
                            if spk:
                                return spk
                    # forward small window
                    for j in range(from_idx + 1, min(len(base_seq), from_idx + 1 + max_lookback)):
                        if (base_seq[j].get("type") or base_seq[j].get("role") or "").lower() == "dialogue":
                            at = base_seq[j].get("attribution") or {}
                            spk = str(at.get("speaker") or "").strip()
                            if spk:
                                return spk
                    return ""

                if idx_in_seq is not None:
                    prev_spk = find_prev_dialogue(idx_in_seq, 3, seq)
                    if prev_spk:
                        final_speaker = prev_spk
                        fallback_method = "continuity_prev"
                        new_conf = max(new_conf, 0.55)
                        qa_flags.append("fallback_continuity_prev")

            if not final_speaker:
                # 2) narration cue (simple proper-noun heuristic from before_ctx if available)
                cue = ""
                if attempts and isinstance(attempts[0].get("payload"), dict):
                    # prefer context attempt (index 1), else last attempt
                    ctx_idx = min(len(attempts) - 1, 1)
                    payload_ctx = attempts[ctx_idx].get("payload", {})
                    bctx = payload_ctx.get("narration_before")
                    if isinstance(bctx, list):
                        import re

                        for s in bctx:
                            for tok in re.findall(r"[A-Z][a-zA-Z]{2,}", s):
                                if tok.lower() not in {"he", "she", "they", "him", "her", "them"}:
                                    cue = tok
                                    break
                            if cue:
                                break
                if cue:
                    final_speaker = cue
                    fallback_method = "llm_fallback_narration_cue"
                    new_conf = max(new_conf, 0.5)
                    qa_flags.append("fallback_narration_cue")

            if not final_speaker:
                # 3) global continuity: last dialogue speaker in output so far
                for prev in reversed(out):
                    if (prev.get("type") or prev.get("role") or "").lower() == "dialogue":
                        atp = prev.get("attribution") or {}
                        sp_prev = str(atp.get("speaker") or "").strip()
                        if sp_prev:
                            final_speaker = sp_prev
                            fallback_method = "continuity_prev_global"
                            new_conf = max(new_conf, 0.5)
                            qa_flags.append("fallback_continuity_prev_global")
                            break

            # Post-parse normalization & generic blocking
            norm_speaker = final_speaker
            qa_flags_norm: list[str] = []
            low_norm = norm_speaker.lower()
            if low_norm in disallowed_generics:
                norm_speaker = "Unknown"
                qa_flags_norm.append("generic_blocked")
                generic_blocked_count += 1
            # Verbose phrase guard
            if norm_speaker and (len(norm_speaker) > 40 or len(norm_speaker.split()) > 5):
                norm_speaker = "Unknown"
                qa_flags_norm.append("verbose_label_replaced")
                verbose_replaced_count += 1
            # Confidence calibration for Unknown
            if norm_speaker.lower() == "unknown" and new_conf > 0.0:
                new_conf = 0.0
                qa_flags_norm.append("confidence_reset_unknown")
                unknown_after_llm += 1
            elif norm_speaker.lower() == "unknown":
                unknown_after_llm += 1
            if norm_speaker.lower() == "unknown":
                final_unknown += 1

            new_attr["speaker"] = norm_speaker or str(attr.get("speaker") or "Someone")
            new_attr["method"] = fallback_method or "llm"
            new_attr["confidence"] = new_conf
            ev = dict(new_attr.get("evidence") or {})
            ev.update(
                {
                    "prompt_version": self.config.prompt_version,
                    "backend": "ollama",
                    "model": self.config.model_name,
                    "raw_text_present": bool(raw_text),
                    "cache_key": cache_key_used,
                    "cache_hit": cache_hit_this,
                }
            )
            if qa_flags:
                ev["qa_flags"] = qa_flags
            if qa_flags_norm:
                ev.setdefault("qa_flags", [])
                ev["qa_flags"].extend(qa_flags_norm)
            new_attr["evidence"] = ev

            new_rec = dict(rec)
            new_rec["attribution"] = new_attr
            out.append(new_rec)
            if cache_hit_this:
                cache_hits += 1
            else:
                cache_misses += 1

        meta = {
            "component": "LLMAttributor",
            "prompt_version": self.config.prompt_version,
            "model_name": self.config.model_name,
            "cache_hits": cache_hits,
            "cache_misses": cache_misses,
            "dialogue_spans": dialogue_spans,
            "llm_attempted": llm_attempted,
            "generic_blocked": generic_blocked_count,
            "verbose_replaced": verbose_replaced_count,
            "unknown_after_llm": unknown_after_llm,
            "final_unknown": final_unknown,
        }
        return out, meta
