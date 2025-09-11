# Troubleshooting Guide

> **Purpose**: Solutions for common problems, error messages, and unexpected behavior in the Agent Audiobook Maker project.

This guide is organized by problem area to help you quickly find solutions. Check the relevant section based on where you're encountering issues.

## Quick Problem Identification

| Symptom                           | Likely Area       | See Section                               |
| --------------------------------- | ----------------- | ----------------------------------------- |
| Import errors, missing modules    | Environment Setup | [Python Environment](#python-environment) |
| Processing fails on certain books | Data Quality      | [Text Processing](#text-processing)       |
| Slow processing, memory errors    | Performance       | [Performance Issues](#performance-issues) |
| Tests failing, build errors       | Development       | [Development Issues](#development-issues) |

## Python Environment

### Virtual Environment Issues

**Problem**: `pip install` fails or installs to wrong location

```bash
ERROR: Could not install packages due to an EnvironmentError
```

**Solution**: Ensure virtual environment is activated

```bash
# Create new virtual environment
python -m venv venv

# Activate (Linux/Mac)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate

# Verify activation - should show venv path
which python
```

**Problem**: Import errors despite packages being installed

```python
ModuleNotFoundError: No module named 'some_module'
```

**Solutions**:

1. Check virtual environment activation: `which python`
1. Reinstall requirements: `pip install -r requirements-dev.txt`
1. Check Python version: `python --version` (should be 3.11+)
1. Clear pip cache: `pip cache purge`

### Dependency Conflicts

**Problem**: Package version conflicts during installation

```bash
ERROR: pip's dependency resolver does not currently support backtracking
```

**Solutions**:

1. Create fresh virtual environment
1. Install packages individually to identify conflicts
1. Check `requirements-dev.txt` for version pins
1. Use `pip-tools` to resolve dependencies

### Python Version Issues

**Problem**: Code fails with syntax or compatibility errors

**Check Python version**:

```bash
python --version  # Should be 3.11+
```

**Solutions**:

1. Install Python 3.11 or higher
1. Update virtual environment to use correct Python
1. Use `pyenv` for Python version management

<!-- Removed deprecated LangFlow troubleshooting section -->

<!-- Removed deprecated LangFlow component loading issues -->

**Problem**: Custom components don't appear in UI

**Check component structure**:

<!-- Removed details specific to LangFlow component directory layout -->

### Workflow Execution Failures

**Problem**: Workflows fail during execution

```text
Component execution failed: [Component Name]
```

**Debugging steps**:

1. Inspect logs for the failing component or script
1. Test component with minimal input
1. Verify input/output data types match
1. Check for missing required inputs

**Common causes**:

- Data type mismatches between components
- Missing required input parameters
- File path issues (use absolute paths)
- Network connectivity problems

## Text Processing

### File Format Issues

**Problem**: PDF extraction produces garbled text

```text
Extracted text contains: ï¿½ï¿½ï¿½ symbols
```

**Solutions**:

1. Check PDF is not password-protected
1. Try different PDF extraction method
1. Verify PDF is text-based (not scanned images)
1. Check for encoding issues: `file -bi your_file.pdf`

### Character Encoding Problems

**Problem**: Special characters display incorrectly

```text
UnicodeDecodeError: 'utf-8' codec can't decode byte
```

**Solutions**:

1. Detect file encoding: `chardet your_file.txt`
1. Convert to UTF-8: `iconv -f ISO-8859-1 -t UTF-8 input.txt > output.txt`
1. Handle encoding in Python:

```python
with open('file.txt', 'r', encoding='utf-8', errors='replace') as f:
    content = f.read()
```

### Segmentation Issues

**Problem**: Dialogue detection fails or produces poor results

**Common causes**:

- Inconsistent quote styles ("curly" vs "straight" quotes)
- Missing or malformed dialogue tags
- Complex nested dialogue
- Non-standard formatting

**Solutions**:

1. Normalize quotes before processing
1. Adjust dialogue detection parameters
1. Add custom rules for specific book formatting
1. Manual review and correction of sample chapters

## Performance Issues

### Memory Problems

**Problem**: Processing runs out of memory

```text
MemoryError: Unable to allocate array
```

**Solutions**:

1. Process books in smaller chunks
1. Increase system swap space
1. Use streaming processing for large files
1. Profile memory usage to identify bottlenecks

### Slow Processing

**Problem**: Processing takes much longer than expected

**Diagnostic steps**:

1. Profile processing time by component
1. Check system resource usage
1. Identify bottleneck operations
1. Test with smaller sample files

**Optimization approaches**:

1. Parallel processing for independent operations
1. Caching for repeated operations
1. Optimize text processing algorithms
1. Use more efficient data structures

### Disk Space Issues

**Problem**: Running out of storage during processing

**Solutions**:

1. Clean temporary files: `rm -rf /tmp/abm_*`
1. Archive or delete old output files
1. Process books individually rather than batches
1. Monitor disk usage: `df -h`

## Development Issues

### Testing Problems

**Problem**: Tests fail unexpectedly

```bash
FAILED tests/test_something.py::test_function - AssertionError
```

**Solutions**:

1. Run single test for debugging: `pytest tests/test_file.py::test_name -v`
1. Check test data and fixtures are available
1. Verify test environment matches requirements
1. Clear test cache: `pytest --cache-clear`

### Linting Failures

**Problem**: Code fails linting checks

```bash
pylint: error: Your code has been rated at 5.0/10
```

**Solutions**:

1. Fix formatting: `black src/`
1. Sort imports: `isort src/`
1. Check type hints: `mypy src/`
1. Address specific pylint warnings

### Git Issues

**Problem**: Git operations fail or behave unexpectedly

**Common issues**:

1. Merge conflicts: Use `git mergetool` or manual resolution
1. Large file issues: Check if files should be in `.gitignore`
1. Branch confusion: Use `git status` and `git branch` to orient
1. Permission issues: Check SSH keys and repository access

## Component Development Issues

### Custom Component Problems

**Problem**: New component doesn't work as expected

**Development checklist**:

1. Component inherits from correct base class
1. Input/output types properly defined
1. Required methods implemented
1. Error handling included
1. Unit tests written and passing

### Data Flow Issues

**Problem**: Components don't connect properly in workflows

**Common causes**:

1. Output type doesn't match input type
1. Data structure inconsistencies
1. Missing error handling
1. Asynchronous processing issues

## Getting Help

### Information to Gather

When reporting issues, include:

1. **Environment**: Python version, OS, installed packages
1. **Steps to reproduce**: Exact commands and inputs used
1. **Error messages**: Complete error output, not just snippets
1. **Context**: What were you trying to accomplish?

### Useful Diagnostic Commands

```bash
# System information
python --version
pip list
uname -a

# Project status
git status
git branch
make test

# Python & environment
python --version
pip list
```

### Where to Ask

1. **Check existing issues**: GitHub repository issues
1. **Search documentation**: This documentation set
1. **Community resources**: LangFlow Discord, Stack Overflow
1. **Create new issue**: GitHub with detailed information

## Prevention Tips

### Best Practices

1. **Always use virtual environments** for Python development
1. **Test with small samples** before processing large books
1. **Version control everything** - commit frequently
1. **Monitor resource usage** during processing
1. **Keep dependencies updated** but test after updates

### Regular Maintenance

1. **Clean temporary files** weekly
1. **Update documentation** when processes change
1. **Run full test suite** before major changes
1. **Back up important data** and configurations
1. **Review and update** troubleshooting guide based on new issues

______________________________________________________________________

*Part of [Appendices](README.md) | [Documentation Index](../README.md)*
