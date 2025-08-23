# LangFlow Component Plan & Architecture

Last updated: 2025-08-23

## Diagrams

- **Architecture**: [diagrams/langflow_architecture.mmd](diagrams/langflow_architecture.mmd)
- **UML Class Structure**: [diagrams/langflow_uml.mmd](diagrams/langflow_uml.mmd)  
- **Finite State Machine**: [diagrams/langflow_fsm.mmd](diagrams/langflow_fsm.mmd)

## Executive Summary

This document outlines the strategy for leveraging LangFlow's built-in components versus building custom components for the audiobook maker pipeline. **Critical Note**: All existing LangFlow components in `lf_components/` are non-functional and require complete redesign/rewriting.

## Current State Assessment

### ❌ **Existing Components Status: NON-FUNCTIONAL**

All components in `lf_components/abm/` require complete redesign:

1. `ABMChapterVolumeLoader` - **Broken**
2. `ABMChapterSelector` - **Broken**
3. `ABMSegmentDialogueNarration` - **Broken**
4. `ABMUtteranceFilter` - **Broken**
5. `ABMUtteranceJSONLWriter` - **Broken**
6. `ABMPayloadLogger` - **Broken**

### ✅ **Project Foundation (Solid)**

- Structured JSON schemas (Volume Manifest v1.1, Annotation Schema v1-v4)
- Deterministic ingestion pipeline with hash-based caching
- Clear data contracts and artifact organization
- KISS-aligned architecture principles

## Component Strategy: Leverage vs Build

## 🔄 **LEVERAGE - Built-in LangFlow Components**

### **Data Loading & File Operations**

- **File Loader**: Read JSON chapter files, JSONL annotation files
- **Directory Loader**: Batch processing multiple chapters
- **JSON Loader**: Handle structured chapter data
- **Text Splitter**: Complement custom segmentation logic

**Rationale**: Standard file I/O operations don't need custom implementation.

### **Text Processing**

- **Text Length Filter**: Replace custom filtering logic in utterance processing
- **Text Regex**: Pattern matching for dialogue detection
- **Text Concatenator**: Join utterances, chapters for rendering

**Rationale**: Basic text operations are well-handled by built-in components.

### **LLM Integration**  

- **Ollama Component**: Direct integration for speaker attribution and QA agents
- **Chat Memory**: Maintain context across utterances within chapters
- **Prompt Template**: Structured prompts for speaker/emotion analysis

**Rationale**: Leverage mature LLM integration rather than building from scratch.

### **Data Transformation**

- **Data Transformer**: Convert between data formats
- **JSON Parser/Builder**: Construct annotation records
- **List Operations**: Filter, sort, map utterances

**Rationale**: Generic data manipulation shouldn't require custom code.

---

## 🛠️ **BUILD CUSTOM - Domain-Specific Components**

### **Phase 1: Core Pipeline (Redesign Required)**

#### **1. ABMChapterVolumeLoader** 🔄 **REDESIGN**

- **Purpose**: Load book metadata and chapters from structured JSON
- **Input**: `book_id`, `chapter_index` (optional)
- **Logic**: Parse volume manifest, extract chapter data with validation
- **Output**: Chapter payload with metadata + body text
- **Current Status**: Non-functional, needs complete rewrite

#### **2. ABMChapterSelector** 🔄 **REDESIGN**  

- **Purpose**: Select single chapter by index or title substring
- **Input**: Chapter payload, selection criteria
- **Logic**: Index-based or fuzzy title matching
- **Output**: Single chapter payload
- **Current Status**: Non-functional, needs complete rewrite

#### **3. ABMSegmentDialogueNarration** 🔄 **REDESIGN**

- **Purpose**: Split chapter text into dialogue/narration utterances
- **Input**: Chapter body text
- **Logic**: Sentence boundary detection + dialogue heuristics (quotes, speech patterns)
- **Output**: List of utterances with `is_dialogue` flags
- **Current Status**: Non-functional, needs complete rewrite
- **Enhancement**: Improve beyond naive line-based splitting

#### **4. ABMUtteranceJSONLWriter** 🔄 **REDESIGN**

- **Purpose**: Write utterances to JSONL following annotation schema
- **Input**: Utterance list with metadata
- **Logic**: Schema validation, deterministic file writing
- **Output**: JSONL file path + confirmation payload
- **Current Status**: Non-functional, needs complete rewrite

### **Phase 2: Multi-Agent Enhancement (New Components)**

#### **5. ABMAdvancedSpeakerAttributor** 🆕 **NEW - ENHANCED**

- **Purpose**: Multi-model ensemble speaker attribution for 95% F1 target
- **Input**: Enhanced utterances with context and character bible
- **Logic**: 4-model ensemble system:
  - Rule-based patterns (attribution phrases, action beats)
  - NER + Coreference resolution (SpanBERT-coref)
  - LLM-based complex attribution (Llama 3.1 8B)  
  - Character embedding similarity matching
- **Output**: Speaker labels + confidence scores + attribution reasoning
- **Performance Target**: >95% F1 score on test dataset
- **Dependencies**: Transformers, sentence-transformers, Ollama, cached embeddings

#### **6. ABMConversationStateManager** 🆕 **NEW**

- **Purpose**: Track conversation context and speaker turn-taking
- **Input**: Sequential utterances with speaker attributions
- **Logic**:
  - Active speaker tracking across dialogue sequences
  - Turn-taking pattern analysis
  - Character presence state management
- **Output**: Updated conversation state + likely next speaker predictions
- **Dependencies**: Conversation flow heuristics, character bible integration

#### **7. ABMEmotionClassifier** 🆕 **NEW**

- **Purpose**: Classify emotional tone of utterances  
- **Input**: Speaker-attributed utterances
- **Logic**: Local emotion model (CPU-based) + rule smoothing + context awareness
- **Output**: Emotion labels + confidence scores
- **Performance Target**: >65% macro-F1 score
- **Dependencies**: Local ML model, emotion taxonomy, character emotional profiles

#### **8. ABMQualityAssuranceAgent** 🆕 **NEW**  

- **Purpose**: Validate annotation quality and flag issues
- **Input**: Fully annotated utterances
- **Logic**: Rule-based validation + selective LLM spot checks
- **Output**: QA flags, warnings, confidence metrics
- **Dependencies**: Validation rules, quality thresholds

#### **8. ABMCharacterBibleBuilder** 🆕 **NEW**

- **Purpose**: Build character profiles for voice casting
- **Input**: Speaker-attributed chapters (multiple)
- **Logic**: Character frequency analysis, alias detection, trait extraction
- **Output**: Character profiles with metadata
- **Dependencies**: Character analysis heuristics

### **Phase 3: Audio Pipeline (New Components)**

#### **9. ABMProsodyGenerator** 🆕 **NEW**

- **Purpose**: Generate prosodic markup for natural speech
- **Input**: Emotion-tagged utterances + character profiles
- **Logic**: Rule-based prosody assignment (pitch, rate, intensity)
- **Output**: Prosody metadata for SSML generation
- **Dependencies**: Prosody rules engine

#### **10. ABMSSMLBuilder** 🆕 **NEW**

- **Purpose**: Build SSML for TTS rendering
- **Input**: Prosody-enhanced utterances + voice profile mappings
- **Logic**: Template-based SSML generation with voice tags
- **Output**: Renderable SSML files
- **Dependencies**: SSML templates, voice profile mapping

#### **11. ABMTTSRenderer** 🆕 **NEW**

- **Purpose**: Generate audio stems from SSML
- **Input**: SSML files + voice profile configurations
- **Logic**: XTTS v2 / Piper integration with GPU management
- **Output**: WAV audio stems with metadata
- **Dependencies**: XTTS v2, Piper, GPU resource management

#### **12. ABMAudioMaster** 🆕 **NEW**

- **Purpose**: Master individual stems into final audiobook
- **Input**: Chapter stems + mastering parameters
- **Logic**: EBU R128 loudness normalization, concatenation, quality gates
- **Output**: Mastered chapter audio + book master WAV
- **Dependencies**: pyloudnorm, audio processing libraries

### **Phase 4: Utility Components**

#### **13. ABMPayloadLogger** 🔄 **REDESIGN**

- **Purpose**: Debug/monitor payload flow through pipeline
- **Input**: Any payload + logging configuration
- **Logic**: Structured logging with payload previews
- **Output**: Pass-through payload + log entries
- **Current Status**: Non-functional, needs complete rewrite

#### **14. ABMPerformanceTracker** 🆕 **NEW**

- **Purpose**: Monitor and report speaker attribution performance metrics
- **Input**: Gold standard annotations + predictions
- **Logic**: Calculate F1, precision, recall by speaker, conversation type, confidence levels  
- **Output**: Performance metrics dashboard + improvement recommendations
- **Performance Target**: Track progress toward 95% F1 goal
- **Dependencies**: Evaluation datasets, statistical analysis tools

#### **15. ABMCacheManager** 🆕 **NEW**

- **Purpose**: Manage hash-based caching across pipeline
- **Input**: Content + parameters + cache keys
- **Logic**: SHA256 hashing, cache hit/miss logic, invalidation
- **Output**: Cached results or cache miss signals
- **Dependencies**: File system cache, hash computation

---

## 🔄 **Pipeline Workflows**

### **Workflow 1: Annotation Pipeline**

```mermaid
flowchart LR
    A[Built-in File Loader] --> B[ABMChapterVolumeLoader]
    B --> C[ABMChapterSelector] 
    C --> D[ABMSegmentDialogueNarration]
    D --> E[ABMSpeakerAttributionAgent]
    E --> F[ABMEmotionClassifier]
    F --> G[ABMQualityAssuranceAgent]
    G --> H[Built-in JSON Builder]
    H --> I[ABMUtteranceJSONLWriter]
```

### **Workflow 2: Audio Generation Pipeline**

```mermaid
flowchart LR
    A[Built-in JSONL Loader] --> B[ABMCharacterBibleBuilder]
    B --> C[ABMProsodyGenerator]
    C --> D[ABMSSMLBuilder] 
    D --> E[ABMTTSRenderer]
    E --> F[Built-in File Operations]
    F --> G[ABMAudioMaster]
```

---

## 📋 **Implementation Roadmap**

### **Sprint 1: Foundation Rebuild**

- **Week 1-2**: Redesign and rebuild core Phase 1 components
  - [ ] ABMChapterVolumeLoader (complete rewrite)
  - [ ] ABMChapterSelector (complete rewrite)
  - [ ] ABMSegmentDialogueNarration (complete rewrite)
  - [ ] ABMUtteranceJSONLWriter (complete rewrite)
- **Week 3**: Integration testing of rebuilt components
- **Week 4**: Documentation and example flows

### **Sprint 2: Multi-Agent Enhancement**  

- **Week 1**: ABMSpeakerAttributionAgent + Ollama integration
- **Week 2**: ABMEmotionClassifier with local models
- **Week 3**: ABMQualityAssuranceAgent with validation rules
- **Week 4**: ABMCharacterBibleBuilder for character profiling

### **Sprint 3: Audio Pipeline**

- **Week 1-2**: Prosody and SSML generation components
- **Week 3**: TTS integration (XTTS v2 / Piper)
- **Week 4**: Audio mastering and final pipeline testing

### **Sprint 4: Production Readiness**

- **Week 1**: Performance optimization and GPU resource management
- **Week 2**: Comprehensive error handling and recovery
- **Week 3**: Production deployment and monitoring
- **Week 4**: Documentation and user guides

---

## 🎯 **Success Criteria**

### **Phase 1 Complete**

- [ ] All 4 core components functional and tested
- [ ] End-to-end segmentation pipeline working
- [ ] Hash-based caching implemented and verified
- [ ] JSONL output matches annotation schema v1

### **Phase 2 Complete**  

- [ ] Speaker attribution >80% accuracy on test set
- [ ] Emotion classification >65% macro F1 score
- [ ] Character bible generation working
- [ ] QA flags catching major annotation issues

### **Phase 3 Complete**

- [ ] SSML generation producing valid markup
- [ ] TTS rendering working with XTTS v2/Piper
- [ ] Audio mastering meeting EBU R128 standards
- [ ] End-to-end book generation under 2 hours locally

---

## ⚠️ **Risk Mitigation**

| Risk | Impact | Mitigation |
|------|---------|------------|
| Component rebuild takes longer than expected | Delayed timeline | Start with simplest components; parallel development where possible |
| LangFlow API changes break integration | Technical debt | Pin LangFlow version; abstract LangFlow-specific code |
| GPU resource contention in TTS | Poor performance | Implement queuing system; fallback to CPU TTS |
| Audio quality regressions | User experience | Comprehensive audio quality gates; A/B testing |

---

## 🔗 **Related Documentation**

- [Architecture Overview](ARCHITECTURE.md)
- [Annotation Schema](ANNOTATION_SCHEMA.md)
- [Multi-Agent Roadmap](MULTI_AGENT_ROADMAP.md)
- [Structured JSON Schema](STRUCTURED_JSON_SCHEMA.md)
- [KISS Principles](KISS.md)

---

## 📝 **Notes**

- This plan assumes LangFlow environment is properly configured with all dependencies
- All custom components must follow KISS principles and maintain deterministic behavior
- Hash-based caching strategy must be implemented consistently across all components
- Audio pipeline components should be designed with GPU resource management in mind

Last updated: 2025-08-23
