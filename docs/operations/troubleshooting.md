# Troubleshooting Guide

> Purpose: Solutions for common problems, error messages, and unexpected behavior in the Agent Audiobook Maker project.

This guide is organized by problem area to help you quickly find solutions. Check the relevant section based on where you're encountering issues.

## Quick Problem Identification

| Symptom                           | Likely Area       | See Section                               |
| --------------------------------- | ----------------- | ----------------------------------------- |
| Import errors, missing modules    | Environment Setup | Python Environment                         |
| Processing fails on certain books | Data Quality      | Text Processing                            |
| Slow processing, memory errors    | Performance       | Performance Issues                         |
| Tests failing, build errors       | Development       | Development Issues                         |

## Python Environment

### Virtual Environment Issues

Problem: `pip install` fails or installs to wrong location

Solution: Ensure virtual environment is activated; verify with `which python`. If needed, recreate the venv and reinstall `requirements-dev.txt`.

### Dependency Conflicts

Problem: Package version conflicts during installation

Solutions: Fresh virtual environment; install incrementally to identify conflicts; check `requirements-dev.txt` pins; consider `pip-tools`.

### Python Version Issues

Ensure Python 3.11+.

## Workflow Execution Failures

Problem: Workflow components fail during execution

Debugging steps: Inspect logs, test minimal inputs, verify I/O types, check required parameters and file paths.

Common causes: Data type mismatches, missing inputs, path issues, network/engine availability.

## Text Processing

### File Format Issues

PDF extraction garbled: verify non-password PDF, try alternate extractor, ensure text-based PDF, check encoding.

### Character Encoding Problems

Use `chardet`, convert to UTF-8, and open with `encoding='utf-8', errors='replace'` when necessary.

### Segmentation Issues

Normalize quotes, adjust detection parameters, add custom rules, and review sample chapters manually.

## Performance Issues

### Memory Problems

Process smaller chunks, increase swap, stream processing, and profile memory.

### Slow Processing

Profile time, check resources, identify bottlenecks, test on smaller samples; use parallelism and caching judiciously.

### Disk Space Issues

Clean temporary files, archive old outputs, process individually, monitor `df -h`.

## Development Issues

### Testing Problems

Run targeted tests, verify fixtures, align env with requirements, clear pytest cache.

### Linting Failures

Format with Black, sort imports, check type hints, address warnings.

### Git Issues

Resolve conflicts, ensure large files are ignored, verify branches and permissions.

## Component Development Issues

### Custom Component Problems

Confirm inheritance, I/O types, required methods, error handling, and tests.

### Data Flow Issues

Match output/input types, ensure data structure consistency, handle errors, and mind async.

## Getting Help

Gather environment, repro steps, full errors, and context. Useful commands: `python --version`, `pip list`, `uname -a`, `git status`, `git branch`, `make test`.

## Prevention Tips

Use venvs, test with small samples, commit frequently, monitor resources, and keep dependencies updated.
