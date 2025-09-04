#!/usr/bin/env python3
"""
Clean Whitespace Script

This script scans Python files and removes spaces/tabs from otherwise empty
lines while preserving the newlines. This is useful for maintaining clean code
formatting and passing linting checks that flag trailing whitespace.

Usage:
    python clean_whitespace.py <file_path>
    python clean_whitespace.py <directory_path>  # processes all .py files
"""

import argparse
import sys
from pathlib import Path


def clean_empty_lines(content: str) -> tuple[str, int]:
    """
    Remove spaces and tabs from empty lines while preserving newlines.

    Args:
        content: The file content as a string

    Returns:
        Tuple of (cleaned_content, number_of_lines_cleaned)
    """
    lines = content.splitlines(keepends=True)
    cleaned_lines = []
    lines_cleaned = 0

    for line in lines:
        # Check if line contains only whitespace (spaces/tabs)
        if line.strip() == "" and line != "\n" and line.endswith("\n"):
            # Replace with just newline
            cleaned_lines.append("\n")
            lines_cleaned += 1
        else:
            # Keep line as-is
            cleaned_lines.append(line)

    return "".join(cleaned_lines), lines_cleaned


def process_file(file_path: Path, dry_run: bool = False) -> bool:
    """
    Process a single Python file to clean empty lines.

    Args:
        file_path: Path to the Python file
        dry_run: If True, don't modify files, just report what would be done

    Returns:
        True if file was modified (or would be modified in dry-run),
        False otherwise
    """
    try:
        with open(file_path, encoding="utf-8") as f:
            original_content = f.read()

        cleaned_content, lines_cleaned = clean_empty_lines(original_content)

        if lines_cleaned > 0:
            if dry_run:
                print(f"[DRY RUN] Would clean {lines_cleaned} empty lines in: {file_path}")
                return True
            else:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(cleaned_content)
                print(f"✅ Cleaned {lines_cleaned} empty lines in: {file_path}")
                return True
        else:
            if not dry_run:
                print(f"✓ No empty lines to clean in: {file_path}")
            return False

    except Exception as e:
        print(f"❌ Error processing {file_path}: {e}", file=sys.stderr)
        return False


def find_python_files(path: Path) -> list[Path]:
    """
    Find all Python files in a directory recursively.

    Args:
        path: Directory path to search

    Returns:
        List of Python file paths
    """
    python_files = []

    if path.is_file() and path.suffix == ".py":
        return [path]
    elif path.is_dir():
        python_files.extend(
            [
                py_file
                for py_file in path.rglob("*.py")
                if (".venv" not in py_file.parts and "__pycache__" not in py_file.parts)
            ]
        )

    return python_files


def main():
    parser = argparse.ArgumentParser(
        description=("Clean empty lines in Python files by removing spaces/tabs while preserving newlines"),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s file.py                    # Clean single file
  %(prog)s src/                       # Clean all .py files in src/ recursively
  %(prog)s --dry-run src/             # Preview changes without modifying files
  %(prog)s --verbose src/             # Show detailed output for all files
        """,
    )

    parser.add_argument("path", type=Path, help="Python file or directory to process")

    parser.add_argument("--dry-run", action="store_true", help="Preview changes without modifying files")

    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show output for all files, including those with no changes"
    )

    args = parser.parse_args()

    if not args.path.exists():
        print(f"❌ Error: Path does not exist: {args.path}", file=sys.stderr)
        sys.exit(1)

    python_files = find_python_files(args.path)

    if not python_files:
        print(f"❌ No Python files found in: {args.path}")
        sys.exit(1)

    print(f"🔍 Found {len(python_files)} Python file(s) to process")
    if args.dry_run:
        print("🔍 DRY RUN MODE - No files will be modified")
    print()

    modified_count = 0
    total_count = len(python_files)

    for py_file in sorted(python_files):
        was_modified = process_file(py_file, dry_run=args.dry_run)
        if was_modified:
            modified_count += 1
        elif args.verbose and not args.dry_run:
            print(f"✓ No changes needed: {py_file}")

    print()
    print("📊 Summary:")
    print(f"   Files processed: {total_count}")
    modified_text = "that would be " if args.dry_run else ""
    print(f"   Files {modified_text}modified: {modified_count}")
    print(f"   Files unchanged: {total_count - modified_count}")

    if args.dry_run and modified_count > 0:
        print("\n💡 Run without --dry-run to apply changes")
    elif modified_count > 0:
        print("\n🎉 Whitespace cleanup completed!")


if __name__ == "__main__":
    main()
