# Troubleshooting Guide

> **Purpose**: Solutions for common problems, error messages, and unexpected behavior in the Agent Audiobook Maker project.

This guide is organized by problem area to help you quickly find solutions. Check the relevant section based on where you're encountering issues.

## Quick Problem Identification

| Symptom | Likely Area | See Section |
|---------|-------------|-------------|
| Import errors, missing modules | Environment Setup | [Python Environment](#python-environment) |
| LangFlow UI won't start | LangFlow Issues | [LangFlow Problems](#langflow-problems) |
| Components don't appear | Component Loading | [Component Loading Issues](#component-loading-issues) |
| Processing fails on certain books | Data Quality | [Text Processing](#text-processing) |
| Slow processing, memory errors | Performance | [Performance Issues](#performance-issues) |
| Tests failing, build errors | Development | [Development Issues](#development-issues) |

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
ModuleNotFoundError: No module named 'langflow'
```

**Solutions**:

1. Check virtual environment activation: `which python`
2. Reinstall requirements: `pip install -r requirements-dev.txt`
3. Check Python version: `python --version` (should be 3.11+)
4. Clear pip cache: `pip cache purge`

### Dependency Conflicts

**Problem**: Package version conflicts during installation

```bash
ERROR: pip's dependency resolver does not currently support backtracking
```

**Solutions**:

1. Create fresh virtual environment
2. Install packages individually to identify conflicts
3. Check `requirements-dev.txt` for version pins
4. Use `pip-tools` to resolve dependencies

### Python Version Issues

**Problem**: Code fails with syntax or compatibility errors

**Check Python version**:

```bash
python --version  # Should be 3.11+
```

**Solutions**:

1. Install Python 3.11 or higher
2. Update virtual environment to use correct Python
3. Use `pyenv` for Python version management

## LangFlow Problems

### UI Won't Start

**Problem**: LangFlow server fails to start

```bash
Error starting LangFlow server
```

**Diagnostic steps**:

```bash
# Check if port is in use
lsof -i :7860

# Try different port
langflow run --port 7861

# Check LangFlow installation
langflow --version
```

**Solutions**:

1. Kill existing LangFlow processes: `pkill -f langflow`
2. Try different port: `langflow run --port 8080`
3. Clear LangFlow cache: `rm -rf ~/.cache/langflow`
4. Reinstall LangFlow: `pip uninstall langflow && pip install langflow`

### Component Loading Issues

**Problem**: Custom components don't appear in UI

**Check component structure**:

```bash
# Components must be in proper package structure
src/abm/lf_components/
├── __init__.py
├── audiobook/
│   ├── __init__.py
│   └── your_component.py
```

**Diagnostic steps**:

1. Check component inherits from `Component`
2. Verify `__init__.py` files exist
3. Check component imports don't fail
4. Restart LangFlow after changes

**Solutions**:

1. Add missing `__init__.py` files
2. Fix import errors in component files
3. Check component class name matches file name
4. Verify component directory is in Python path

### Workflow Execution Failures

**Problem**: Workflows fail during execution

```
Component execution failed: [Component Name]
```

**Debugging steps**:

1. Check component logs in LangFlow UI
2. Test component with minimal input
3. Verify input/output data types match
4. Check for missing required inputs

**Common causes**:

- Data type mismatches between components
- Missing required input parameters
- File path issues (use absolute paths)
- Network connectivity problems

## Text Processing

### File Format Issues

**Problem**: PDF extraction produces garbled text

```
Extracted text contains: ï¿½ï¿½ï¿½ symbols
```

**Solutions**:

1. Check PDF is not password-protected
2. Try different PDF extraction method
3. Verify PDF is text-based (not scanned images)
4. Check for encoding issues: `file -bi your_file.pdf`

### Character Encoding Problems

**Problem**: Special characters display incorrectly

```
UnicodeDecodeError: 'utf-8' codec can't decode byte
```

**Solutions**:

1. Detect file encoding: `chardet your_file.txt`
2. Convert to UTF-8: `iconv -f ISO-8859-1 -t UTF-8 input.txt > output.txt`
3. Handle encoding in Python:

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
2. Adjust dialogue detection parameters
3. Add custom rules for specific book formatting
4. Manual review and correction of sample chapters

## Performance Issues

### Memory Problems

**Problem**: Processing runs out of memory

```
MemoryError: Unable to allocate array
```

**Solutions**:

1. Process books in smaller chunks
2. Increase system swap space
3. Use streaming processing for large files
4. Profile memory usage to identify bottlenecks

### Slow Processing

**Problem**: Processing takes much longer than expected

**Diagnostic steps**:

1. Profile processing time by component
2. Check system resource usage
3. Identify bottleneck operations
4. Test with smaller sample files

**Optimization approaches**:

1. Parallel processing for independent operations  
2. Caching for repeated operations
3. Optimize text processing algorithms
4. Use more efficient data structures

### Disk Space Issues

**Problem**: Running out of storage during processing

**Solutions**:

1. Clean temporary files: `rm -rf /tmp/langflow_*`
2. Archive or delete old output files
3. Process books individually rather than batches
4. Monitor disk usage: `df -h`

## Development Issues

### Testing Problems

**Problem**: Tests fail unexpectedly

```bash
FAILED tests/test_something.py::test_function - AssertionError
```

**Solutions**:

1. Run single test for debugging: `pytest tests/test_file.py::test_name -v`
2. Check test data and fixtures are available
3. Verify test environment matches requirements
4. Clear test cache: `pytest --cache-clear`

### Linting Failures

**Problem**: Code fails linting checks

```bash
pylint: error: Your code has been rated at 5.0/10
```

**Solutions**:

1. Fix formatting: `black src/`
2. Sort imports: `isort src/`
3. Check type hints: `mypy src/`
4. Address specific pylint warnings

### Git Issues

**Problem**: Git operations fail or behave unexpectedly

**Common issues**:

1. Merge conflicts: Use `git mergetool` or manual resolution
2. Large file issues: Check if files should be in `.gitignore`
3. Branch confusion: Use `git status` and `git branch` to orient
4. Permission issues: Check SSH keys and repository access

## Component Development Issues

### Custom Component Problems

**Problem**: New component doesn't work as expected

**Development checklist**:

1. Component inherits from correct base class
2. Input/output types properly defined
3. Required methods implemented
4. Error handling included
5. Unit tests written and passing

### Data Flow Issues

**Problem**: Components don't connect properly in workflows

**Common causes**:

1. Output type doesn't match input type
2. Data structure inconsistencies
3. Missing error handling
4. Asynchronous processing issues

## Getting Help

### Information to Gather

When reporting issues, include:

1. **Environment**: Python version, OS, installed packages
2. **Steps to reproduce**: Exact commands and inputs used
3. **Error messages**: Complete error output, not just snippets
4. **Context**: What were you trying to accomplish?

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

# LangFlow diagnostics  
langflow --version
ps aux | grep langflow
```

### Where to Ask

1. **Check existing issues**: GitHub repository issues
2. **Search documentation**: This documentation set
3. **Community resources**: LangFlow Discord, Stack Overflow
4. **Create new issue**: GitHub with detailed information

## Prevention Tips

### Best Practices

1. **Always use virtual environments** for Python development
2. **Test with small samples** before processing large books
3. **Version control everything** - commit frequently
4. **Monitor resource usage** during processing
5. **Keep dependencies updated** but test after updates

### Regular Maintenance

1. **Clean temporary files** weekly
2. **Update documentation** when processes change
3. **Run full test suite** before major changes
4. **Back up important data** and configurations
5. **Review and update** troubleshooting guide based on new issues

---

*Part of [Appendices](README.md) | [Documentation Index](../README.md)*
