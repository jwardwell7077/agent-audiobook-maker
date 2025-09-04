# Glossary

> **Purpose**: Comprehensive definitions of technical terms, concepts, and acronyms used throughout the Agent Audiobook Maker project.

This glossary provides clear definitions for all specialized terminology used in documentation, code, and project discussions.

## Core Concepts

### Agent Audiobook Maker (ABM)

The complete system for converting text content into structured annotations suitable for audiobook production. Consists of ingestion, classification, structuring, and annotation pipelines.

### Annotation Pipeline

The multi-stage process that transforms raw text into richly annotated content with speaker identification, dialogue/narration classification, and metadata generation.

### Audiobook Production

The process of converting written text into spoken audio content, typically involving text-to-speech synthesis, voice acting, or narrator recording.

### Chapter Segmentation

The process of identifying and extracting individual chapters from book content, including chapter boundaries, titles, and content classification.

### Chapterizer (Legacy)

Historical component previously responsible for detecting chapter boundaries and structuring book content. The redesign derives chapter structure directly from the Section Classifier outputs (`chapters_section.json`).

### Dialogue Detection

The automated identification of spoken dialogue within text, typically using punctuation patterns, formatting cues, and linguistic analysis.

### Multi-Agent System (MAS)

An architectural pattern where multiple specialized AI agents collaborate to accomplish complex tasks, with each agent having specific roles and capabilities.

### Narration

Non-dialogue text content in books, including descriptive passages, internal thoughts, scene setting, and authorial commentary.

### Pipeline

A sequence of processing stages where the output of one stage becomes the input to the next, allowing complex transformations through modular components.

### Quality Gate

A validation checkpoint in the processing pipeline that ensures output meets specified quality standards before proceeding to the next stage.

### Section Classification

The process of identifying and categorizing different parts of a book (table of contents, chapters, appendices, etc.) for appropriate processing.

### Segmentation

The process of breaking text into smaller, meaningful units (sentences, utterances, or semantic chunks) for targeted processing.

### Speaker Attribution

The process of identifying which character or narrator is responsible for specific utterances in dialogue-rich content.

### Structured JSON

The standardized data format used to represent processed book content, including hierarchical organization and rich metadata.

### Text-to-Speech (TTS)

Technology that converts written text into spoken audio, often used in audiobook production and accessibility applications.

### Utterance

A single unit of speech or text, typically representing one complete thought, sentence, or speaking turn in dialogue.

## Technology Stack

### CrewAI

A Python framework for building and orchestrating multi-agent systems, designed for complex workflows requiring agent collaboration.

### LangChain

A framework for developing applications powered by language models, providing tools for chains, agents, and memory systems.

### LangFlow

A visual, low-code platform for building LangChain applications through a drag-and-drop interface, used for rapid prototyping.

### LangGraph

A library for building stateful, multi-actor applications with language models, providing graph-based workflow orchestration.

### LangSmith

A developer platform for debugging, testing, evaluating, and monitoring LLM applications and agents.

### Large Language Model (LLM)

AI models trained on vast amounts of text data to understand and generate human-like text, used for various NLP tasks.

### Natural Language Processing (NLP)

A field of AI focused on enabling computers to understand, interpret, and generate human language.

### Python Virtual Environment (venv)

An isolated Python environment that allows project-specific dependencies without affecting the system Python installation.

### Redis

An in-memory data structure store used for caching, session storage, and real-time data management in multi-agent systems.

### Vector Store

A database optimized for storing and querying high-dimensional vectors, commonly used for semantic search and retrieval.

## Development Terms

### API (Application Programming Interface)

A set of protocols and tools for building software applications, defining how components should interact.

### Continuous Integration (CI)

A development practice where code changes are automatically tested and integrated into the main codebase frequently.

### Docker

A platform for developing, shipping, and running applications in lightweight, portable containers.

### FSM (Finite State Machine)

A computational model used to design and represent systems with a finite number of states and defined transitions between them.

### Git

A distributed version control system for tracking changes in source code during software development.

### JSON (JavaScript Object Notation)

A lightweight, text-based data interchange format that's easy for humans to read and write.

### JSONL (JSON Lines)

A format for storing structured data where each line is a valid JSON object, commonly used for streaming data processing.

### Makefile

A build automation tool that uses a file containing rules and dependencies to control the compilation and build process.

### Markdown

A lightweight markup language with plain text formatting syntax, commonly used for documentation.

### pytest

A testing framework for Python that makes it easy to write simple and scalable test cases.

### REST API

An architectural style for web services that uses standard HTTP methods and stateless communication.

### UML (Unified Modeling Language)

A standardized modeling language used to visualize the design of software systems.

### YAML (YAML Ain't Markup Language)

A human-readable data serialization standard commonly used for configuration files.

## Data Formats

### CSV (Comma-Separated Values)

A simple file format for tabular data where values are separated by commas.

### Mermaid

A syntax for creating diagrams and flowcharts from text, commonly used in documentation.

### PDF (Portable Document Format)

A file format that preserves document formatting across different platforms and devices.

### Plain Text

Simple text format containing only readable characters without any special formatting or metadata.

### TSV (Tab-Separated Values)

Similar to CSV but uses tab characters as delimiters between data fields.

## Quality Assurance

### Automated Testing

The use of software tools to run tests automatically, providing rapid feedback on code changes.

### Code Coverage

A metric that measures the percentage of code executed during testing, indicating test completeness.

### Code Review

The process of systematically examining source code changes before they're merged into the main codebase.

### Integration Testing

Testing that verifies the interaction between different components or systems works correctly.

### Linting

The process of running a program that analyzes source code for potential errors, bugs, and stylistic issues.

### Unit Testing

Testing individual components or functions in isolation to ensure they work correctly.

## Audiobook Domain

### Audio Format

The technical specification for digital audio files (WAV, MP3, FLAC, etc.), including sample rate, bit depth, and compression.

### Audiobook Standards

Industry specifications for audiobook production, including chapter divisions, metadata requirements, and quality guidelines.

### Chapter Markers

Timestamp-based navigation points in audio files that allow listeners to jump between book sections.

### Dialogue Tag

Textual indicators that identify who is speaking in written dialogue (e.g., "he said," "she whispered").

### Metadata

Descriptive information about content, including title, author, genre, publication date, and technical specifications.

### Narrator Instructions

Special annotations in text that provide guidance for voice actors or TTS systems about pronunciation, emphasis, or delivery.

### Point of View (POV)

The narrative perspective from which a story is told (first person, third person limited, omniscient, etc.).

### Prosody

The rhythm, stress, and intonation patterns in speech that convey meaning and emotion.

### Sound Effects (SFX)

Audio elements added to enhance the listening experience, such as background sounds, music, or special audio cues.

### Voice Acting

The performance art of using voice to portray characters and convey narrative content in audio productions.

## Acronyms & Abbreviations

- **ABM** - Agent Audiobook Maker
- **AI** - Artificial Intelligence
- **API** - Application Programming Interface
- **CI/CD** - Continuous Integration/Continuous Deployment
- **CLI** - Command Line Interface
- **CSV** - Comma-Separated Values
- **FSM** - Finite State Machine
- **JSON** - JavaScript Object Notation
- **JSONL** - JSON Lines
- **LLM** - Large Language Model
- **MAS** - Multi-Agent System
- **ML** - Machine Learning
- **NLP** - Natural Language Processing
- **PDF** - Portable Document Format
- **POV** - Point of View
- **QA** - Quality Assurance
- **REST** - Representational State Transfer
- **SFX** - Sound Effects
- **TTS** - Text-to-Speech
- **UI** - User Interface
- **UML** - Unified Modeling Language
- **URL** - Uniform Resource Locator
- **UUID** - Universally Unique Identifier
- **YAML** - YAML Ain't Markup Language

## Usage Notes

### Context Sensitivity

Many terms may have different meanings in different contexts. This glossary provides definitions as they apply specifically to the Agent Audiobook Maker project.

### Version Awareness

Technology definitions reflect current versions as of project creation. Some tools and frameworks may evolve beyond these descriptions.

### Audience Considerations

Definitions are written for technical contributors but should be accessible to domain experts from audiobook production backgrounds.

______________________________________________________________________

*Part of [Appendices](README.md) | [Documentation Index](../README.md)*
