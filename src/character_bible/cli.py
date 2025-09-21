from __future__ import annotations

import glob
import os
from pathlib import Path
from typing import Iterable, List, Sequence

import click

from .build import build_all
from .extract import parse_candidate, seed_from_counts
from .files import load_chapters, save_json
from .llm_client import LLMClient
from .scan import count_mentions, find_mentions
from .schema import CharacterProfile

DEFAULT_SCAN_OUT = "scan_counts.json"
DEFAULT_BIBLE_OUT = "character_bible.json"


def _expand_paths(paths: Iterable[str]) -> List[str]:
    expanded: List[str] = []
    for pattern in paths:
        matches = sorted(glob.glob(pattern))
        if matches:
            expanded.extend(matches)
        else:
            expanded.append(pattern)
    return expanded


def _read_names_file(path: Path | None) -> List[str]:
    if not path:
        return []
    data = path.read_text(encoding="utf-8")
    lines = []
    for line in data.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        lines.append(stripped)
    return lines


def _collect_candidates(names_path: str | None, inline: Sequence[str]) -> List[str]:
    candidates: List[str] = []
    if names_path:
        candidates.extend(_read_names_file(Path(names_path)))
    candidates.extend([name for name in inline if name])
    if not candidates:
        raise click.ClickException("No character names were provided.")
    return candidates


def _create_client(
    llm_base_url: str | None,
    llm_model: str | None,
    temperature: float,
    seed: int | None,
    api_key_env: str | None,
) -> LLMClient:
    api_key: str | None = None
    if api_key_env:
        api_key = os.getenv(api_key_env)
    return LLMClient(
        base_url=llm_base_url or os.getenv("LLM_BASE_URL"),
        api_key=api_key,
        model=llm_model or os.getenv("LLM_MODEL", "gpt-4o-mini"),
        temperature=temperature,
        seed=seed,
    )


def _serialize_profiles(profiles: Sequence[CharacterProfile]) -> List[dict]:
    return [profile.model_dump(mode="json") for profile in profiles]


def _serialize_counts(
    chapters: Sequence[dict[str, str]],
    candidates: List[str],
    max_hits: int,
    sent_window: int,
) -> List[dict]:
    rows: List[dict] = []
    for raw in candidates:
        try:
            name, aliases = parse_candidate(raw)
        except ValueError:
            continue
        count = count_mentions(chapters, name, aliases)
        evidence = find_mentions(
            chapters,
            name,
            aliases,
            max_hits=max_hits,
            sent_window=sent_window,
        )
        rows.append(
            {
                "name": name,
                "aliases": aliases,
                "count": count,
                "first_mentions": [snippet.model_dump(mode="json") for snippet in evidence],
            }
        )
    return rows


@click.group()
def main() -> None:
    """Character bible builder CLI."""


@main.command()
@click.option("--chapters", "chapters_paths", multiple=True, required=True, help="Paths or globs to chapter JSON files.")
@click.option("--names", "names_path", type=click.Path(path_type=Path), help="Path to newline-delimited character names.")
@click.option("--name", "inline_names", multiple=True, help="Provide a character name directly (can be repeated).")
@click.option("--out", "output_path", default=DEFAULT_SCAN_OUT, show_default=True, help="Where to write the counts JSON.")
@click.option("--max-hits", default=5, show_default=True, help="Maximum evidence snippets to capture per character.")
@click.option("--window", default=1, show_default=True, help="Sentence window size when capturing evidence.")
@click.option("--seed", default=None, type=int, help="Seed placeholder for interface parity (unused).")
def scan(
    chapters_paths: Sequence[str],
    names_path: Path | None,
    inline_names: Sequence[str],
    output_path: str,
    max_hits: int,
    window: int,
    seed: int | None,
) -> None:
    """Count character mentions and preview first evidence snippets."""

    chapter_files = _expand_paths(chapters_paths)
    chapters = load_chapters(chapter_files)
    candidates = _collect_candidates(str(names_path) if names_path else None, inline_names)

    rows = _serialize_counts(chapters, candidates, max_hits=max_hits, sent_window=window)

    if not rows:
        raise click.ClickException("No valid character names were parsed.")

    name_width = max(len(row["name"]) for row in rows)
    header = f"{'Name'.ljust(name_width)}  Count  First mention"
    click.echo(header)
    click.echo("-" * len(header))
    for row in rows:
        first_location = row["first_mentions"][0]["location"] if row["first_mentions"] else "-"
        click.echo(f"{row['name'].ljust(name_width)}  {row['count']:>5}  {first_location}")

    save_json(output_path, rows)


@main.command()
@click.option("--chapters", "chapters_paths", multiple=True, required=True, help="Paths or globs to chapter JSON files.")
@click.option("--names", "names_path", type=click.Path(path_type=Path), help="Path to newline-delimited character names.")
@click.option("--name", "inline_names", multiple=True, help="Provide a character name directly (can be repeated).")
@click.option("--out", "output_path", default=DEFAULT_BIBLE_OUT, show_default=True, help="Output path for the character bible JSON.")
@click.option("--max-hits", default=5, show_default=True, help="Maximum evidence snippets per character.")
@click.option("--window", default=1, show_default=True, help="Sentence window size when capturing evidence.")
@click.option("--seed", default=None, type=int, help="Seed passed to the LLM provider when supported.")
@click.option("--llm-base-url", default=None, help="Override the LLM base URL (defaults to $LLM_BASE_URL).")
@click.option("--llm-model", default=None, help="Override the LLM model name (defaults to $LLM_MODEL).")
@click.option("--temperature", default=0.0, show_default=True, type=float, help="LLM sampling temperature.")
@click.option("--api-key-env", default="LLM_API_KEY", show_default=True, help="Environment variable to read the API key from.")
def draft(
    chapters_paths: Sequence[str],
    names_path: Path | None,
    inline_names: Sequence[str],
    output_path: str,
    max_hits: int,
    window: int,
    seed: int | None,
    llm_base_url: str | None,
    llm_model: str | None,
    temperature: float,
    api_key_env: str | None,
) -> None:
    """Build bible entries for specified characters using the configured LLM."""

    chapter_files = _expand_paths(chapters_paths)
    chapters = load_chapters(chapter_files)
    candidates = _collect_candidates(str(names_path) if names_path else None, inline_names)

    seeds = seed_from_counts(chapters, candidates)
    if not seeds:
        raise click.ClickException("No valid character seeds were produced.")

    client = _create_client(llm_base_url, llm_model, temperature, seed, api_key_env)

    profiles = build_all(chapters, seeds, client, max_hits=max_hits, sent_window=window)
    save_json(output_path, _serialize_profiles(profiles))

    click.echo(f"Wrote {len(profiles)} character profiles to {output_path}.")


@main.command()
@click.option("--chapters", "chapters_paths", multiple=True, required=True, help="Paths or globs to chapter JSON files.")
@click.option("--names", "names_path", type=click.Path(path_type=Path), required=True, help="Path to newline-delimited character names.")
@click.option("--out", "output_path", default=DEFAULT_BIBLE_OUT, show_default=True, help="Output path for the character bible JSON.")
@click.option("--max-hits", default=5, show_default=True, help="Maximum evidence snippets per character.")
@click.option("--window", default=1, show_default=True, help="Sentence window size when capturing evidence.")
@click.option("--seed", default=None, type=int, help="Seed passed to the LLM provider when supported.")
@click.option("--llm-base-url", default=None, help="Override the LLM base URL (defaults to $LLM_BASE_URL).")
@click.option("--llm-model", default=None, help="Override the LLM model name (defaults to $LLM_MODEL).")
@click.option("--temperature", default=0.0, show_default=True, type=float, help="LLM sampling temperature.")
@click.option("--api-key-env", default="LLM_API_KEY", show_default=True, help="Environment variable to read the API key from.")
@click.option("--threshold", default=3, show_default=True, type=int, help="Minimum mentions required to include a character.")
def all(
    chapters_paths: Sequence[str],
    names_path: Path,
    output_path: str,
    max_hits: int,
    window: int,
    seed: int | None,
    llm_base_url: str | None,
    llm_model: str | None,
    temperature: float,
    api_key_env: str | None,
    threshold: int,
) -> None:
    """End-to-end pipeline: count, filter, and build the character bible."""

    chapter_files = _expand_paths(chapters_paths)
    chapters = load_chapters(chapter_files)
    candidates = _collect_candidates(str(names_path), [])

    seeds = seed_from_counts(chapters, candidates)
    if threshold > 0:
        filtered_seeds = []
        for seed_model in seeds:
            count = count_mentions(chapters, seed_model.name, seed_model.aliases)
            if count >= threshold:
                filtered_seeds.append(seed_model)
        seeds = filtered_seeds

    if not seeds:
        raise click.ClickException("No characters met the mention threshold.")

    client = _create_client(llm_base_url, llm_model, temperature, seed, api_key_env)
    profiles = build_all(chapters, seeds, client, max_hits=max_hits, sent_window=window)
    save_json(output_path, _serialize_profiles(profiles))

    click.echo(f"Wrote {len(profiles)} character profiles to {output_path}.")


if __name__ == "__main__":
    main()
