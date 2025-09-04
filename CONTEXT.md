# Audio Book Maker - Project Context

## Core Project Tenant: 🏗️ ENGINEERING DISCIPLINE OVER QUICK FIXES

**Established**: August 23, 2025

This principle is fundamental to all project development:

### 1. Documentation-First Approach

- ✅ Analyze official documentation before implementation
- ✅ Understand requirements before coding
- ❌ **Never**: Trial-and-error guessing or random attempts

### 2. Logic Preservation

- ✅ Systematic analysis of existing functionality before changes
- ✅ Preserve and enhance algorithms rather than losing features
- ❌ **Never**: Delete code without understanding its purpose

### 3. Technical Debt Elimination

- ✅ Clean directory structure and professional code organization
- ✅ Proper inheritance patterns and best practices
- ❌ **Never**: Quick fixes that create more problems later

### 4. Systematic Testing

- ✅ Comprehensive testing and validation before deployment
- ✅ Verify inheritance, imports, and component discovery
- ❌ **Never**: "Hope it works" deployments

**Reference**: See `/docs/LANGFLOW_COMPONENT_SUCCESS_CLEAN.md` for the complete success story demonstrating these principles.

______________________________________________________________________

## Type Checker Tip: Explicit List Annotations

If you see errors like:

- Type of "append" is partially unknown
- Type of "append" is "(object: Unknown, /) -> None"

This means the type checker (e.g., Pyright, MyPy) cannot infer the type of your list.

**Solution**: Always use explicit type annotations for empty lists or dictionaries

**Example**:

```python
body_parts: list[str] = []
for i in range(1, chapter_count + 1):
    body_parts.append(f"Chapter {i}: Title {i}\\nBody {i} text.")
```

This ensures the type checker knows body_parts is a list of strings, resolving the warning.
