# Type Checker Tip: Explicit List Annotations

# 

# If you see errors like

# Type of "append" is partially unknown

# Type of "append" is "(object: Unknown, /) -> None"

# This means the type checker (e.g., Pyright, MyPy) cannot infer the type of your list

# Solution: Always use explicit type annotations for empty lists or dictionaries

# 

# Example

# body_parts: list[str] = []

# for i in range(1, chapter_count + 1)

# body_parts.append(f"Chapter {i}: Title {i}\\nBody {i} text.")

# 

# This ensures the type checker knows body_parts is a list of strings, resolving the warning
