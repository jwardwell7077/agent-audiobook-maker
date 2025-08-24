from __future__ import annotations

import os
import re
from pathlib import Path
from typing import NamedTuple

# --------- Config ----------
# Diagram types that are broadly supported on GitHub (safe set).
ALLOWED_HEADER_PREFIXES = (
    "flowchart ",  # e.g., flowchart LR
    "graph ",  # older; still accepted in many versions (TD/LR/BT/RL)
    "sequenceDiagram",
    "classDiagram",
    "stateDiagram-v2",
    "erDiagram",
    "gantt",
    "journey",
    "pie",
    "gitGraph",  # aka Gitgraph
    "info",  # renders diagnostic version box
)

# Mermaid comments are "%%". People often mistakenly use // or <!-- --> .
FORBIDDEN_COMMENT_TOKENS = (r"(?<!%)//", r"<!--", r"-->")

# Very common arrow typos from other DSLs (e.g., "=>").
OBVIOUS_BAD_ARROWS = ("=>",)  # Mermaid uses -->, --- , -.->, ==>, etc., but "=>" alone is wrong.

# If you keep `.mermaidrc` init overrides minimal, consider allowing this directive.
INIT_DIRECTIVE_RE = re.compile(r"^\s*%%\{.*\}\%%\s*$")

# Special characters that often need quoting when used in node labels with [].
SPECIALS_NEEDING_QUOTES = set(":{}|")

# --------- Helpers ----------


class Issue(NamedTuple):
    file: Path
    line: int
    msg: str


FENCE_START_RE = re.compile(r"^```(\w+)\s*$")
FENCE_END_RE = re.compile(r"^```\s*$")


def markdown_files(root: Path) -> list[Path]:
    """Scan repo for Markdown files; allow override via MERMAID_MD_ROOT."""
    base = Path(os.environ.get("MERMAID_MD_ROOT", root))
    return [p for p in base.rglob("*.md") if p.is_file()]


def extract_mermaid_blocks(text: str) -> list[tuple[int, str]]:
    """
    Returns list of (start_line_number, block_text) for each ```mermaid block.
    start_line_number is 1-based for friendly error reporting.
    """
    lines = text.splitlines()
    out: list[tuple[int, str]] = []
    i = 0
    while i < len(lines):
        m = FENCE_START_RE.match(lines[i])
        if m:
            lang = m.group(1).strip().lower()
            i0 = i
            i += 1
            block_lines = []
            while i < len(lines) and not FENCE_END_RE.match(lines[i]):
                block_lines.append(lines[i])
                i += 1
            # If fence wasn't closed, treat content to EOF
            block = "\n".join(block_lines)
            if lang == "mermaid":
                out.append((i0 + 1, block))  # report from fence line (1-based)
        i += 1
    return out


def first_nonempty_line(s: str) -> tuple[int, str] | None:
    for idx, line in enumerate(s.splitlines(), start=1):
        if line.strip():
            return idx, line
    return None


def has_allowed_header(header_line: str) -> bool:
    # No leading indentation allowed on the header line
    if header_line != header_line.lstrip():
        return False
    return any(header_line.startswith(prefix) for prefix in ALLOWED_HEADER_PREFIXES)


def check_subgraph_balance(block: str) -> str | None:
    """
    Simple balance checker for flowchart/graph: counts 'subgraph' and 'end' tokens.
    Not a full parser; catches common missing 'end' or extra 'end'.
    """
    sub = len(re.findall(r"(^|\s)subgraph(\s|$)", block))
    end = len(re.findall(r"(^|\s)end(\s|$)", block))
    if sub != end:
        return f"unbalanced subgraph/end (subgraph={sub}, end={end})"
    return None


def bad_comment_token_positions(block: str) -> list[int]:
    bad_lines: list[int] = []
    for n, line in enumerate(block.splitlines(), start=1):
        for token_re in FORBIDDEN_COMMENT_TOKENS:
            if re.search(token_re, line):
                bad_lines.append(n)
                break
    return bad_lines


def obvious_bad_arrows_positions(block: str) -> list[int]:
    bad_lines: list[int] = []
    for n, line in enumerate(block.splitlines(), start=1):
        # ignore lines that are comments
        if line.strip().startswith("%%"):
            continue
        for tok in OBVIOUS_BAD_ARROWS:
            # Allow "==>" because it IS valid; we only flag bare "=>"
            if tok in line and "==>" not in line:
                bad_lines.append(n)
                break
    return bad_lines


def needs_quoting(label: str) -> bool:
    # crude: if label has unescaped special chars and isn't quoted with "..."
    return any(ch in SPECIALS_NEEDING_QUOTES for ch in label)


def suspicious_unquoted_labels(block: str) -> list[int]:
    """
    Heuristic: finds A[ ... ] nodes and warns if label contains special chars
    and isn't wrapped in double quotes. False positives are possible; this is a warning.
    """
    warn_lines: list[int] = []
    node_re = re.compile(r"""\[[^\]]+\]""")
    for n, line in enumerate(block.splitlines(), start=1):
        for m in node_re.finditer(line):
            label = m.group(0)[1:-1]  # inside []
            stripped = label.strip()
            if stripped.startswith('"') and stripped.endswith('"'):
                continue
            if needs_quoting(stripped):
                warn_lines.append(n)
                break
    return warn_lines


def init_directive_position(block: str) -> str | None:
    """
    GitHub supports init directive; safest is as the very first non-empty line,
    followed immediately by a valid header.
    """
    lines = block.splitlines()
    # find first non-empty
    idx_line = first_nonempty_line(block)
    if not idx_line:
        return None
    idx, line = idx_line
    if INIT_DIRECTIVE_RE.match(line):
        # next non-empty must be the header
        rest = "\n".join(lines[idx:])
        next_line = first_nonempty_line(rest)
        if not next_line:
            return "init directive present but missing diagram header after it"
        _, hline = next_line
        if not has_allowed_header(hline):
            return "init directive present but the following line is not a valid diagram header"
        return None
    else:
        # no init directive => OK
        return None


def validate_mermaid_block(file: Path, fence_start_line: int, block: str) -> list[Issue]:
    issues: list[Issue] = []

    # 1) First non-empty, non-comment line must be a valid header
    # Allow leading Mermaid comments (%% ...) before the header.
    fnl = first_nonempty_line(block)
    if not fnl:
        issues.append(Issue(file, fence_start_line, "empty mermaid block"))
        return issues

    idx, line = fnl
    # Skip leading comment lines
    lines = block.splitlines()
    current_idx = idx
    current_line = line
    while current_line.strip().startswith("%%"):
        # move to the next non-empty line after this one
        rest = "\n".join(lines[current_idx:])
        nxt = first_nonempty_line(rest)
        if not nxt:
            issues.append(Issue(file, fence_start_line + current_idx, "only comments; missing diagram header"))
            return issues
        off, current_line = nxt
        current_idx += off

    idx, line = current_idx, current_line
    if INIT_DIRECTIVE_RE.match(line):
        # validate directive position/next line
        msg = init_directive_position(block)
        if msg:
            issues.append(Issue(file, fence_start_line + idx, msg))
        # move header check to the next non-empty after directive (already enforced)
    elif not has_allowed_header(line):
        issues.append(
            Issue(
                file,
                fence_start_line + idx,
                "first non-empty line must be a valid diagram header "
                f"(got: {line!r}). Expected one of: {', '.join(ALLOWED_HEADER_PREFIXES)}",
            )
        )

    # 2) Header cannot be indented
    if line != line.lstrip():
        issues.append(Issue(file, fence_start_line + idx, "diagram header must not be indented"))

    # 3) For flowchart/graph, check subgraph/end balance
    header_line = line.strip()
    if header_line.startswith(("flowchart ", "graph ")):
        bal = check_subgraph_balance(block)
        if bal:
            issues.append(Issue(file, fence_start_line + idx, bal))

    # 4) Comments must use %% only
    bad_comment_lines = bad_comment_token_positions(block)
    issues.extend(
        [
            Issue(
                file,
                fence_start_line + n,
                "invalid comment token inside mermaid block; use '%%' for comments",
            )
            for n in bad_comment_lines
        ]
    )

    # 5) Flag obvious arrow typos (heuristic)
    bad_arrow_lines = obvious_bad_arrows_positions(block)
    issues.extend(
        [
            Issue(
                file,
                fence_start_line + n,
                "suspicious arrow '=>' found; Mermaid uses '-->' (and variants).",
            )
            for n in bad_arrow_lines
        ]
    )

    # 6) Warn on labels that probably need quoting when inside [ ... ]
    warn_lines = suspicious_unquoted_labels(block)
    issues.extend(
        [
            Issue(
                file,
                fence_start_line + n,
                'node label likely needs quotes due to special characters (wrap with " )',
            )
            for n in warn_lines
        ]
    )

    return issues


# --------- Tests ----------


def test_mermaid_blocks_renderable() -> None:
    """
    Scans all markdown files for ```mermaid blocks and checks a suite of
    GitHub-friendly syntax rules. Fails with a consolidated, actionable report.
    Set MERMAID_MD_ROOT to limit the scan to a subdirectory.
    """
    root = Path(".").resolve()
    all_md = markdown_files(root)
    all_issues: list[Issue] = []

    for md_file in all_md:
        text = md_file.read_text(encoding="utf-8", errors="replace")
        blocks = extract_mermaid_blocks(text)
        for fence_line, block in blocks:
            issues = validate_mermaid_block(md_file, fence_line, block)
            all_issues.extend(issues)

    if all_issues:
        # Build a readable report
        lines: list[str] = [
            f"{iss.file}:{iss.line}: {iss.msg}" for iss in sorted(all_issues, key=lambda x: (str(x.file), x.line))
        ]
        report = "\n".join(lines)
        raise AssertionError(
            "Mermaid syntax check failed.\n"
            "Fix the issues below or suppress specific heuristics if needed.\n\n" + report
        )
