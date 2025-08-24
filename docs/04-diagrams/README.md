# Documentation Diagrams

> **Purpose**: Visual representations of system architecture, workflows, and component interactions.

This section contains all the technical diagrams that illustrate how the Agent Audiobook Maker system works, from high-level architecture to detailed component behaviors.

## Quick Navigation

| Diagram Type | Purpose | Files |
|-------------|---------|-------|
| 🏗️ **Architecture** | System overview and component relationships | `high_level_architecture.mmd` |
| 🔄 **Workflows** | Data processing pipelines | `pdf_to_text_flow.mmd` |
| 🤖 **Components** | Individual component behavior | `chapterizer_fsm.mmd`, `section_classifier_fsm.mmd` |
| 📊 **Data Models** | Schema and structure diagrams | `structured_json_schema.mmd` |
| 🧠 **State Machines** | Finite state machine behaviors | `quality_gate_fsm.mmd` |

## Architecture Diagrams

### 🏗️ [High-Level Architecture](high_level_architecture.mmd)

System overview showing major components and data flow

- **Purpose**: Executive summary of system design
- **Audience**: Stakeholders, new developers, architects
- **Level**: 30,000-foot view
- **Key Elements**: Major subsystems, external dependencies, data stores

```mermaid
%%{display}%%
graph TB
    subgraph "Input Processing"
        PDF[PDF Files] --> PdfToText[PDF to Text]
        TXT[Text Files] --> TextProcessor[Text Processing]
    end
    
    subgraph "Content Analysis"
        TextProcessor --> Classifier[Section Classifier]
        PdfToText --> Classifier
        Classifier --> Chapterizer[Chapter Structure]
    end
    
    subgraph "Annotation Pipeline"  
        Chapterizer --> Segmenter[Dialogue/Narration]
        Segmenter --> Annotator[Metadata Generation]
    end
    
    subgraph "Output & Quality"
        Annotator --> QualityGate[Quality Assurance]
        QualityGate --> Output[Structured JSON/JSONL]
    end
```text

> This is a simplified representation – see full diagram for implementation details.

## Workflow Diagrams

### 📄 [PDF to Text Flow](pdf_to_text_flow.mmd)

**Detailed workflow for PDF ingestion and text extraction**

- **Process**: PDF → Text extraction → Validation → Storage
- **Error handling**: Malformed PDFs, encoding issues, layout problems
- **Quality gates**: Text quality validation, formatting preservation
- **Output**: Clean text files ready for annotation

### 📝 [TXT to JSON Processing](txt_to_json_spec.mmd)

**Text file to structured annotation workflow**

- **Process**: Text → Classification → Segmentation → Annotation
- **Components**: Section classifier, chapterizer, dialogue segmenter
- **Quality control**: Validation at each stage
- **Output**: Structured JSON with rich metadata

## Component State Machines

### 📚 [Chapterizer FSM](chapterizer_fsm.mmd)

**Finite state machine for chapter detection and structuring**

**States:**

- `SCANNING` - Looking for chapter boundaries
- `CHAPTER_START` - Found potential chapter beginning  
- `CONTENT_PROCESSING` - Processing chapter content
- `VALIDATION` - Validating chapter structure
- `COMPLETE` - Chapter successfully processed

**Triggers:**

- Chapter markers (numbers, titles, formatting)
- Content boundaries (page breaks, whitespace)
- Validation results (pass/fail)

### 🔍 [Section Classifier FSM](section_classifier_fsm.mmd)

**State machine for classifying different text sections**

**States:**

- `ANALYSIS` - Analyzing text characteristics
- `TOC_DETECTION` - Looking for table of contents  
- `CHAPTER_CLASSIFICATION` - Identifying chapter content
- `METADATA_EXTRACTION` - Extracting book metadata
- `FINAL_CLASSIFICATION` - Assigning final labels

**Classifications:**

- Table of Contents, Chapter Content, Index, Appendix
- Front Matter, Back Matter, Bibliography
- Footnotes, Headers, Page Numbers

### ✅ [Quality Gate FSM](quality_gate_fsm.mmd)

**State machine for quality assurance workflows**

**States:**

- `INTAKE` - Receiving content for validation
- `AUTOMATED_CHECKS` - Running automated quality rules
- `SCORING` - Calculating quality metrics
- `HUMAN_REVIEW` - Flagged for manual review (if needed)
- `APPROVED` - Passed all quality gates
- `REJECTED` - Failed validation, needs rework

**Quality Metrics:**

- Segmentation accuracy, speaker consistency
- Annotation completeness, metadata quality
- Format compliance, schema validation

## UML Diagrams  

### 🔧 [Component UML](pdf_to_text_uml.mmd)

**Class diagrams for PDF processing components**

- **Classes**: PDFReader, TextExtractor, QualityValidator
- **Interfaces**: ITextProcessor, IQualityGate, IFileHandler
- **Relationships**: Inheritance, composition, dependencies
- **Methods**: Key public APIs and data transformations

### 📊 [Data Model UML](structured_json_schema.mmd)

**Entity relationship diagrams for data schemas**

- **Entities**: Book, Chapter, Utterance, Speaker, Annotation
- **Relationships**: One-to-many, many-to-many mappings
- **Attributes**: Required fields, optional metadata, constraints
- **Inheritance**: Base classes and specialized types

## Data Flow Diagrams

### 🔄 Processing Pipeline

```mermaid
%%{display}%%
sequenceDiagram
    participant Input as Input Files
    participant Processor as Text Processor
    participant Classifier as Section Classifier  
    participant Chapterizer as Chapter Structure
    participant Annotator as Annotation Engine
    participant Output as Structured Output
    
    Input->>Processor: Raw text/PDF
    Processor->>Classifier: Clean text
    Classifier->>Chapterizer: Classified sections
    Chapterizer->>Annotator: Chapter structure  
    Annotator->>Output: Annotated JSONL
```text

### 🔍 Quality Assurance Flow

```mermaid
%%{display}%%
graph LR
    A[Raw Output] --> B{Automated QA}
    B -->|Pass| C[Approved]
    B -->|Fail| D[Human Review]
    D -->|Approve| C
    D -->|Reject| E[Rework]
    E --> A
```text

## Diagram Maintenance

### File Formats

- **Mermaid (.mmd)**: Primary format for all diagrams
- **Renderable**: Can be viewed in GitHub, VS Code, documentation sites
- **Version controlled**: Text-based format tracks changes clearly

### Updating Diagrams

1. **Edit .mmd files** directly in VS Code with Mermaid extension
2. **Test rendering** before committing changes
3. **Update documentation** if diagram changes affect specifications
4. **Coordinate with code** - ensure diagrams match implementation

### Viewing Diagrams

- **GitHub**: Automatically renders Mermaid in README files
- **VS Code**: Install Mermaid preview extension
- **Documentation site**: Hugo/MkDocs with Mermaid plugin
- **Online**: Copy to mermaid.live for quick viewing

## Contributing New Diagrams

### When to Create Diagrams

- **New major feature** - Architecture impact
- **Complex workflow** - Multi-step processes  
- **State machine** - Component behavior
- **Data relationships** - Schema changes

### Diagram Standards

- **Consistent styling** - Use established color schemes
- **Clear labels** - Descriptive node and edge labels
- **Appropriate level** - Match audience and purpose
- **Documentation** - Include purpose and context

### Review Process

1. **Create diagram** in appropriate category
2. **Add to this index** with description and purpose  
3. **Link from specifications** where relevant
4. **Test rendering** in multiple viewers
5. **Get feedback** from domain experts

## Related Sections

- 🏗️ [Architecture](../../01-project-overview/ARCHITECTURE.md) - What these diagrams illustrate
- 📋 [Specifications](../../02-specifications/README.md) - Requirements these diagrams support
- 🔧 [Implementation](../../03-implementation/README.md) - Code that implements these designs
- 📝 [Data Schemas](../data-schemas/README.md) - Detailed schema documentation

---

*Part of [Documentation Index](../../README.md)*
