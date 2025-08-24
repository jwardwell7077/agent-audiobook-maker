# 01. Project Overview

> **Purpose**: High-level understanding of what Agent Audiobook Maker does, why it exists, and how it's architected.

## Quick Overview

Agent Audiobook Maker is a local-first, multi-agent system that transforms novels from PDF to high-quality, multi-voice audiobooks. It follows KISS principles and emphasizes deterministic, reproducible outputs.

## Documents in This Section

### 🎯 [Project Vision & Goals](VISION.md)

**New document** - The "why" behind this project

- Problem statement and motivation
- Target users and use cases
- Success criteria and goals

### 📋 [System Context](CONTEXT.md)

**Core document** - Technical environment and constraints

- Hardware requirements (WSL2, GPU, etc.)
- Development machine setup
- Performance targets and limitations

### 🏛️ [Project Principles (KISS)](KISS.md)

**Foundation document** - Core tenets and policies

- Keep It Simple, Simple philosophy
- Local-first approach
- TDD and spec-first development

### 🏗️ [High-Level Architecture](ARCHITECTURE.md)

**Technical overview** - System design and data flow

- Pipeline stages (ingestion → annotation → rendering)
- Component relationships
- Current vs. future architecture

## Architecture at a Glance

```mermaid
graph LR
    subgraph "Phase 0 ✅"
        PDF[📕 PDF] --> Extract[🔍 Extract]
        Extract --> Chapters[📚 Chapters]
    end
    
    subgraph "Phase 1 🚧"
        Chapters --> Segment[✂️ Segment]
        Segment --> Annotate[🏷️ Annotate]
    end
    
    subgraph "Phase 2-3 ⏳"
        Annotate --> Cast[🎭 Cast]
        Cast --> Render[🎙️ TTS]
        Render --> Master[🎵 Master]
    end
```text

## How to Navigate

- **New to the project?** → Start with [Project Vision](VISION.md)
- **Setting up development?** → Read [System Context](CONTEXT.md)
- **Understanding principles?** → Review [KISS Policy](KISS.md)
- **Ready for technical details?** → Dive into [Architecture](ARCHITECTURE.md)

## Related Sections

- 📝 [Specifications](../02-specifications/README.md) - Detailed technical specs
- 🎨 [Diagrams](../04-diagrams/README.md) - Visual architecture documentation  
- 📈 [Development Journey](../05-development/journey/README.md) - How we got here

---

*Part of [Documentation Index](../README.md)*
