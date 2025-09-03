# Data Schemas

> **Purpose**: Core data structures and formats used throughout the Agent Audiobook Maker system.

This section defines the structured data formats that serve as contracts between system components. All schemas follow versioning conventions and include both human-readable documentation and machine-readable JSON schema definitions.

## Overview

The system uses three main data formats:

1. **Structured JSON** - Volume manifests and chapter data from ingestion
2. **Annotation Schema** - Rich utterance annotations from the multi-agent pipeline  
3. **JSON Schema Definitions** - Machine-readable validation schemas

## Data Flow

```mermaid
graph LR
    PDF[📕 PDF Input] --> Structured[📊 Structured JSON]
    Structured --> Annotation[🏷️ Annotation Schema]
    Annotation --> Audio[🎵 Audio Output]
    
    Structured --> Validation{✅ JSON Schema}
    Annotation --> Validation
```text

## Documents in This Section

### 📊 [Structured JSON Schema](STRUCTURED_JSON_SCHEMA.md)

**Core ingestion format** - Volume manifest and per-chapter data structure

- Volume manifest with embedded chapters (v1.1+)
- Per-chapter JSON format (optional materialized view)
- Content-addressable hashing for reproducibility
- Schema versioning and migration strategy

**Key Features:**

- Deterministic output with stable hashes
- Embedded chapter content for simplicity
- Rich metadata including extraction stats
- Generator information for debugging

### 🏷️ [Annotation Schema](ANNOTATION_SCHEMA.md)  

**Multi-agent annotation format** - Rich utterance data with ML annotations

- Versioned annotation layers (segmentation → speaker → emotion → prosody)
- Hashing strategy excluding non-deterministic fields
- Quality assurance flags and confidence scores
- SSML and TTS rendering metadata

**Evolution Path:**

- v1: Basic segmentation (dialogue/narration) - **Legacy LangFlow**
- v1.5: Two-agent system (hybrid classification + speaker attribution) - **Current** 
- v2: Enhanced CrewAI integration with emotion classification - **Phase 2**
- v3: Prosody analysis and quality gates - **Phase 3**  
- v4: SSML generation and TTS metadata - **Phase 4**

### 📋 [JSON Schema Files](schemas/)

**Machine-readable validation** - Formal schema definitions for automated validation

- Classifier schemas for section detection
- Version-controlled schema evolution
- Integration with CI/CD validation pipelines

## Schema Design Principles

### Contracts

- Spans Attribution Contract: [SPANS_ATTR_CONTRACT.md](SPANS_ATTR_CONTRACT.md)

### Versioning Strategy

- **Semantic versioning** for breaking changes (major.minor.patch)
- **Layer-based versioning** for annotation enrichment
- **Migration paths** documented for all schema updates
- **Backward compatibility** maintained where possible

### Hashing and Determinism

- **Content-addressable** hashing for caching and validation
- **Deterministic exclusions** for volatile fields (timestamps, rationale)
- **Reproducible outputs** essential for testing and regression detection

### Extensibility

- **Optional fields** for future enhancements
- **Metadata sections** for tooling and debugging information
- **Hook points** for custom annotations and processing

## Usage Patterns

### For Developers

- **Read schemas first** before implementing components
- **Validate data** at component boundaries
- **Use content hashes** for caching and idempotency checks
- **Follow migration guides** when updating to new schema versions

### For Data Scientists

- **Understand annotation layers** and their confidence scores
- **Use schema validation** to ensure data quality
- **Leverage versioning** to track model improvements over time

### For QA/Testing

- **Validate outputs** against schemas in automated tests
- **Use hash comparison** for regression detection
- **Test schema migrations** with real data samples

## Related Sections

- 📝 [Component Specifications](../components/README.md) - How components use these schemas
- 🛠️ [Implementation](../../03-implementation/README.md) - Schema usage in code
- 🎨 [Diagrams](../../04-diagrams/flows/) - Visual representation of data flows

---

*Part of [Specifications](../README.md) | [Documentation Index](../../README.md)*
