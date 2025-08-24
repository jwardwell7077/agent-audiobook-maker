# Emoji Test for Mermaid

Testing if emoji in Mermaid labels cause rendering issues on GitHub.

## Test with Emoji (Expected to FAIL)

```mermaid
graph LR
    A[📕 Start]  B[🔍 Process]
    B  C[🎵 End]
```

## Test without Emoji (Expected to WORK)

```mermaid  
graph LR
    A[Start]  B[Process]
    B  C[End]
```

**Hypothesis**: The emoji version will show "Error rendering embedded code" while the plain text version renders correctly.
