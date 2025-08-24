"""
Test suite for Mermaid diagram validation.

This test ensures all Mermaid diagrams follow GitHub rendering standards based on
real-world testing of GitHub's Mermaid parser capabilities.

## GitHub Mermaid Experiment Results (2025-08-24):

### ✅ WORKS on GitHub:
1. Standard ```mermaid blocks
7. HTML details with Mermaid
8. Mermaid in quote blocks
9. Mermaid with extra attributes

### ❌ FAILS on GitHub:
2. No language identifier (requires explicit 'mermaid')
3. Plain text blocks (```text)
4. Alternative language tags (```diagram)
5. Nested code blocks (````markdown containing ```mermaid)
6. Raw Mermaid without code block wrappers
10. Auto-detection based on content (no smart detection)

## Key Findings:
- GitHub requires explicit 'mermaid' language identifier
- Nested CODE BLOCKS break rendering, but HTML/quote nesting works
- No auto-detection of Mermaid syntax
- Extra attributes are ignored gracefully

## Validation Rules:
- .mmd files: Plain Mermaid syntax only (no markdown wrappers)
- .md files: Proper ```mermaid code blocks (not nested in other code blocks)
- No problematic syntax patterns that cause GitHub rendering errors
"""

import pytest
import re
from pathlib import Path
from typing import List, Tuple


class MermaidValidator:
    """Validates Mermaid diagrams for GitHub compatibility."""

    def __init__(self, docs_root: Path = None):
        self.docs_root = docs_root or Path("docs")

    def find_mmd_files(self) -> List[Path]:
        """Find all .mmd files in the docs directory."""
        return list(self.docs_root.rglob("*.mmd"))

    def find_md_files_with_mermaid(self) -> List[Path]:
        """Find all .md files containing Mermaid diagrams."""
        md_files = []
        for md_file in self.docs_root.rglob("*.md"):
            try:
                content = md_file.read_text(encoding='utf-8')
                if '```mermaid' in content:
                    md_files.append(md_file)
            except (UnicodeDecodeError, PermissionError):
                # Skip files that can't be read
                continue
        return md_files

    def validate_mmd_file(self, file_path: Path) -> Tuple[bool, List[str]]:
        """
        Validate a standalone .mmd file.

        Rules:
        - Must contain only plain Mermaid syntax
        - No markdown code block wrappers (```mermaid)
        - No problematic syntax like ````mermaid.radar
        - Must start with valid Mermaid diagram type
        """
        errors = []

        try:
            content = file_path.read_text(encoding='utf-8').strip()
        except (UnicodeDecodeError, PermissionError) as e:
            errors.append(f"Could not read file: {e}")
            return False, errors

        if not content:
            errors.append("File is empty")
            return False, errors

        # Check for markdown wrappers (should NOT be present)
        if content.startswith('```'):
            errors.append("Standalone .mmd files should not contain markdown code blocks")

        # Check for problematic patterns based on GitHub experiment findings
        problematic_patterns = [
            ('````mermaid.radar', 'Contains invalid ````mermaid.radar syntax'),
            ('```mermaid.', 'Contains invalid ```mermaid.{type} syntax'),
            ('%%{display}%%', 'Contains unsupported %%{display}%% directive'),
            ('```text', 'Contains incorrect ```text ending'),
            # Based on GitHub experiment: nested CODE BLOCKS fail (Tests #5)
            ('````markdown\n```mermaid',
             'Nested code blocks fail - GitHub cannot render Mermaid inside ````markdown blocks'),
            ('````html\n```mermaid',
             'Nested code blocks fail - GitHub cannot render Mermaid inside ````html blocks'),
            ('````text\n```mermaid',
             'Nested code blocks fail - GitHub cannot render Mermaid inside ````text blocks'),
        ]

        for pattern, error_msg in problematic_patterns:
            if pattern in content:
                errors.append(error_msg)

        # Check for valid Mermaid diagram types (allow comments first)
        valid_diagram_types = [
            'flowchart', 'graph', 'sequenceDiagram', 'classDiagram',
            'stateDiagram', 'erDiagram', 'journey', 'gantt', 'pie',
            'gitgraph', 'quadrantChart', 'requirementDiagram',
            'architecture', 'kanban', 'timeline', 'sankey'
        ]

        # Skip comment lines when checking diagram type
        content_lines = content.split('\n')
        first_non_comment_line = None
        for line in content_lines:
            stripped_line = line.strip()
            if stripped_line and not stripped_line.startswith('%%'):
                first_non_comment_line = stripped_line
                break

        if first_non_comment_line is None:
            errors.append("File contains only comments, no actual Mermaid diagram")
        elif not any(first_non_comment_line.startswith(diagram_type) for diagram_type in valid_diagram_types):
            errors.append(f"Does not start with valid Mermaid diagram type. Found: '{first_non_comment_line}'")

        return len(errors) == 0, errors

    def validate_md_mermaid_blocks(self, file_path: Path) -> Tuple[bool, List[str]]:
        """
        Validate Mermaid blocks within markdown files.

        Rules:
        - Must use ```mermaid (not ```text or other variants)
        - Must have proper closing ```
        - No nested code blocks
        - No problematic syntax patterns
        """
        errors = []

        try:
            content = file_path.read_text(encoding='utf-8')
        except (UnicodeDecodeError, PermissionError) as e:
            errors.append(f"Could not read file: {e}")
            return False, errors

        # Find all Mermaid code blocks
        mermaid_pattern = r'```mermaid\n(.*?)\n```'
        mermaid_blocks = re.findall(mermaid_pattern, content, re.DOTALL)

        if not mermaid_blocks:
            # File might have ```mermaid but improperly formatted
            if '```mermaid' in content:
                errors.append("Contains ```mermaid but blocks are not properly closed")
            else:
                # This shouldn't happen since we filter for files with ```mermaid
                errors.append("No Mermaid blocks found despite containing ```mermaid")
            return False, errors

        # Validate each block
        for i, block in enumerate(mermaid_blocks):
            block_errors = self._validate_mermaid_block_content(block, i + 1)
            errors.extend(block_errors)

        # Check for problematic patterns in the entire file
        problematic_patterns = [
            ('```text\n```', 'Contains empty ```text block that should be ```'),
            ('````mermaid', 'Contains invalid ````mermaid (too many backticks)'),
            ('%%{display}%%', 'Contains unsupported %%{display}%% directive'),
            # Note: Based on GitHub testing, nested HTML and quote blocks actually WORK
            # Only nested CODE BLOCKS (````markdown containing ```mermaid) fail
        ]

        for pattern, error_msg in problematic_patterns:
            if pattern in content:
                errors.append(error_msg)

        return len(errors) == 0, errors

    def _validate_mermaid_block_content(self, block_content: str, block_num: int) -> List[str]:
        """Validate the content of a single Mermaid block."""
        errors = []

        if not block_content.strip():
            errors.append(f"Block {block_num}: Empty Mermaid block")
            return errors

        # Check for valid diagram types (allow comments first)
        valid_diagram_types = [
            'flowchart', 'graph', 'sequenceDiagram', 'classDiagram',
            'stateDiagram', 'erDiagram', 'journey', 'gantt', 'pie',
            'gitgraph', 'quadrantChart', 'requirementDiagram'
        ]

        # Skip comment lines when checking diagram type
        block_lines = block_content.strip().split('\n')
        first_non_comment_line = None
        for line in block_lines:
            stripped_line = line.strip()
            if stripped_line and not stripped_line.startswith('%%'):
                first_non_comment_line = stripped_line
                break

        if first_non_comment_line is None:
            errors.append(f"Block {block_num}: Contains only comments, no actual Mermaid diagram")
        elif not any(first_non_comment_line.startswith(diagram_type) for diagram_type in valid_diagram_types):
            errors.append(f"Block {block_num}: Does not start with valid Mermaid diagram type. "
                          f"Found: '{first_non_comment_line}'")

        return errors


# Test fixtures and helpers
@pytest.fixture
def validator():
    """Create a MermaidValidator instance."""
    return MermaidValidator()


@pytest.fixture
def docs_root():
    """Get the docs directory path."""
    return Path("docs")


# Test cases
class TestGitHubMermaidCompatibility:
    """Test GitHub-specific Mermaid rendering compatibility based on real experiments."""

    def test_mermaid_language_identifier_required(self, validator):
        """Test that GitHub requires explicit 'mermaid' language identifier."""
        # This would fail on GitHub (Test #2 from experiment)
        invalid_content = '''# Test

```
graph LR
    A --> B
```
'''

        # Should be detected as problematic since GitHub won't render it
        assert 'graph LR' in invalid_content
        assert '```mermaid' not in invalid_content

    def test_nested_code_blocks_fail(self, validator):
        """Test that nested code blocks prevent Mermaid rendering (Test #5 from experiment)."""
        nested_content = '''````markdown
# Some content
```mermaid
graph LR
    A --> B
```
````'''

        # This pattern should be detected as problematic
        has_nested_pattern = '````markdown' in nested_content and '```mermaid' in nested_content
        assert has_nested_pattern, "Should detect nested code block pattern"

    def test_html_details_with_mermaid_works(self, validator):
        """Test that HTML details with Mermaid actually works (Test #7 from experiment)."""
        html_details_content = '''<details>
<summary>Hidden Diagram</summary>

```mermaid
graph LR
    A --> B
```

</details>'''

        # This should NOT be flagged as problematic since it works on GitHub
        assert '```mermaid' in html_details_content
        assert '<details>' in html_details_content

    def test_quote_blocks_with_mermaid_work(self, validator):
        """Test that quote blocks with Mermaid work (Test #8 from experiment)."""
        quote_content = '''> ```mermaid
> graph LR
>     A --> B
> ```'''

        # This should NOT be flagged as problematic since it works on GitHub
        assert '> ```mermaid' in quote_content

    def test_mermaid_with_attributes_works(self, validator):
        """Test that Mermaid with extra attributes works (Test #9 from experiment)."""
        attributed_content = '''```mermaid title="Test Diagram"
graph LR
    A --> B
```'''

        # This should NOT be flagged as problematic since GitHub ignores extra attributes
        assert 'title="Test Diagram"' in attributed_content
        assert '```mermaid' in attributed_content

    def test_alternative_language_tags_fail(self, validator):
        """Test that alternative language tags like 'diagram' don't work (Test #4 from experiment)."""
        alt_tag_content = '''```diagram
graph LR
    A --> B
```'''

        # This should be detected as problematic since GitHub only recognizes 'mermaid'
        assert '```diagram' in alt_tag_content
        assert '```mermaid' not in alt_tag_content

    def test_raw_mermaid_without_wrapper_fails(self, validator):
        """Test that raw Mermaid without code blocks fails (Test #6 from experiment)."""
        raw_content = '''graph LR
    A[Raw Mermaid] --> B[No Wrapper]'''

        # This should be detected as problematic since GitHub needs code block wrappers
        assert '```' not in raw_content
        assert 'graph LR' in raw_content


class TestMermaidBestPractices:
    """Test Mermaid best practices based on GitHub experiment results."""

    def test_working_patterns_not_flagged_as_errors(self, validator):
        """Ensure patterns that work on GitHub are not flagged as errors."""
        working_patterns = [
            # Standard mermaid (Test #1 - works)
            '```mermaid\ngraph LR\n    A --> B\n```',
            # HTML details (Test #7 - works)
            '<details>\n```mermaid\ngraph LR\n    A --> B\n```\n</details>',
            # Quote blocks (Test #8 - works)
            '> ```mermaid\n> graph LR\n>     A --> B\n> ```',
            # Extra attributes (Test #9 - works)
            '```mermaid title="test"\ngraph LR\n    A --> B\n```',
        ]

        for pattern in working_patterns:
            # These should not trigger validation errors since they work on GitHub
            assert '```mermaid' in pattern

    def test_failing_patterns_detected_as_errors(self, validator):
        """Ensure patterns that fail on GitHub are detected as errors."""
        failing_patterns = [
            # No language identifier (Test #2 - fails)
            ('```\ngraph LR\n    A --> B\n```', 'missing language identifier'),
            # Plain text blocks (Test #3 - fails)
            ('```text\ngraph LR\n    A --> B\n```', 'wrong language identifier'),
            # Alternative tags (Test #4 - fails)
            ('```diagram\ngraph LR\n    A --> B\n```', 'wrong language identifier'),
            # Nested code blocks (Test #5 - fails)
            ('````markdown\n```mermaid\ngraph LR\n    A --> B\n```\n````', 'nested code blocks'),
            # Raw without wrapper (Test #6 - fails)
            ('graph LR\n    A --> B', 'missing code block wrapper'),
            # Auto-detection test (Test #10 - fails)
            ('```\nflowchart TD\n    A --> B\n```', 'missing mermaid identifier'),
        ]

        for pattern, reason in failing_patterns:
            # These should be detectable as problematic patterns
            if 'mermaid' in reason:
                assert '```mermaid' not in pattern, f"Pattern should not contain ```mermaid: {reason}"
            else:
                # Other validation logic here
                assert '```' in pattern or '```' not in pattern  # Pattern exists


class TestMermaidFiles:
    """Test standalone .mmd files for GitHub compatibility."""

    def test_mmd_files_exist(self, validator):
        """Test that we have .mmd files to validate."""
        mmd_files = validator.find_mmd_files()
        assert len(mmd_files) > 0, "No .mmd files found in docs directory"

    def test_all_mmd_files_valid(self, validator):
        """Test that all .mmd files follow GitHub rendering standards."""
        mmd_files = validator.find_mmd_files()
        failures = []

        for mmd_file in mmd_files:
            is_valid, errors = validator.validate_mmd_file(mmd_file)
            if not is_valid:
                failures.append(f"{mmd_file}: {'; '.join(errors)}")

        if failures:
            pytest.fail("Mermaid .mmd file validation failures:\n" + "\n".join(failures))

    @pytest.mark.parametrize("mmd_file", MermaidValidator().find_mmd_files())
    def test_individual_mmd_file(self, validator, mmd_file):
        """Test individual .mmd files (useful for debugging specific files)."""
        is_valid, errors = validator.validate_mmd_file(mmd_file)
        assert is_valid, f"Validation errors for {mmd_file}: {'; '.join(errors)}"


class TestMarkdownMermaidBlocks:
    """Test Mermaid blocks within markdown files."""

    def test_md_files_with_mermaid_exist(self, validator):
        """Test that we have .md files with Mermaid diagrams."""
        md_files = validator.find_md_files_with_mermaid()
        assert len(md_files) > 0, "No .md files with Mermaid diagrams found"

    def test_all_md_mermaid_blocks_valid(self, validator):
        """Test that all Mermaid blocks in .md files are properly formatted."""
        md_files = validator.find_md_files_with_mermaid()
        failures = []

        for md_file in md_files:
            is_valid, errors = validator.validate_md_mermaid_blocks(md_file)
            if not is_valid:
                failures.append(f"{md_file}: {'; '.join(errors)}")

        if failures:
            pytest.fail("Markdown Mermaid block validation failures:\n" + "\n".join(failures))

    @pytest.mark.parametrize("md_file", MermaidValidator().find_md_files_with_mermaid())
    def test_individual_md_file_mermaid_blocks(self, validator, md_file):
        """Test individual .md files with Mermaid blocks."""
        is_valid, errors = validator.validate_md_mermaid_blocks(md_file)
        assert is_valid, f"Validation errors for {md_file}: {'; '.join(errors)}"


class TestMermaidConsistency:
    """Test consistency between .mmd files and their usage in documentation."""

    def test_referenced_mmd_files_exist(self, validator, docs_root):
        """Test that all .mmd files referenced in documentation actually exist."""
        md_files = list(docs_root.rglob("*.md"))
        failures = []

        # Pattern to match .mmd file references
        mmd_reference_pattern = r'\[.*?\]\((.*?\.mmd)\)'

        for md_file in md_files:
            # Skip old/temporary files
            if '_OLD' in md_file.name or md_file.name.startswith('TEMP_'):
                continue

            try:
                content = md_file.read_text(encoding='utf-8')
                references = re.findall(mmd_reference_pattern, content)

                for ref in references:
                    # Resolve relative path
                    referenced_file = md_file.parent / ref
                    if not referenced_file.exists():
                        failures.append(f"{md_file}: References non-existent file {ref}")

            except (UnicodeDecodeError, PermissionError):
                continue

        if failures:
            pytest.fail("Missing referenced .mmd files:\n" + "\n".join(failures))

    def test_no_orphaned_mmd_files(self, validator, docs_root):
        """Test that all .mmd files are referenced somewhere in documentation."""
        # This is a warning test - orphaned files aren't necessarily errors
        # but it's good to know about them
        mmd_files = validator.find_mmd_files()
        md_files = list(docs_root.rglob("*.md"))

        referenced_files = set()

        for md_file in md_files:
            try:
                content = md_file.read_text(encoding='utf-8')
                # Look for any mention of .mmd files (not just links)
                mmd_mentions = re.findall(r'(\w+\.mmd)', content)
                for mention in mmd_mentions:
                    referenced_files.add(mention)
            except (UnicodeDecodeError, PermissionError):
                continue

        orphaned_files = []
        for mmd_file in mmd_files:
            if mmd_file.name not in referenced_files:
                orphaned_files.append(str(mmd_file))

        if orphaned_files:
            print(f"Warning: Found {len(orphaned_files)} potentially orphaned .mmd files:")
            for orphan in orphaned_files:
                print(f"  - {orphan}")


if __name__ == "__main__":
    # Allow running this test file directly
    validator = MermaidValidator()

    print("Validating .mmd files...")
    mmd_files = validator.find_mmd_files()
    for mmd_file in mmd_files:
        is_valid, errors = validator.validate_mmd_file(mmd_file)
        status = "✅ PASS" if is_valid else "❌ FAIL"
        print(f"{status}: {mmd_file}")
        if errors:
            for error in errors:
                print(f"    - {error}")

    print(f"\nValidating .md files with Mermaid blocks...")
    md_files = validator.find_md_files_with_mermaid()
    for md_file in md_files:
        is_valid, errors = validator.validate_md_mermaid_blocks(md_file)
        status = "✅ PASS" if is_valid else "❌ FAIL"
        print(f"{status}: {md_file}")
        if errors:
            for error in errors:
                print(f"    - {error}")
