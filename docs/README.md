# Agent Audiobook Maker Documentation

> **Comprehensive documentation for the Agent Audiobook Maker project - your complete guide to understanding, developing, and contributing to the system.**

Welcome to the documentation hub! This project transforms raw text into structured audiobook annotations using AI agents and workflow orchestration.

## 🚀 Quick Start

### New to the Project?

- 📖 **[Getting Started Guide](GETTING_STARTED.md)** - Essential onboarding for new contributors
- 🎯 **[Project Overview](01-project-overview/README.md)** - Understand the vision and architecture
- 🔧 **[Development Setup](05-development/README.md)** - Get your environment ready

### Need Something Specific?

- 📋 **Specifications** → [02-specifications/](02-specifications/README.md)
- 🛠️ **Implementation** → [03-implementation/](03-implementation/README.md)  
- 📊 **Diagrams** → [04-diagrams/](04-diagrams/README.md)
- 🔍 **Troubleshooting** → [06-appendices/TROUBLESHOOTING.md](06-appendices/TROUBLESHOOTING.md)

## 📚 Documentation Structure

Our documentation is organized into 6 main sections designed for different needs and audiences:

| Section | Purpose | Audience | Key Content |
|---------|---------|----------|-------------|
| **[📋 01-Project Overview](01-project-overview/README.md)** | Vision, architecture, and context | All stakeholders | Vision, architecture, project context |
| **[📝 02-Specifications](02-specifications/README.md)** | Technical requirements and contracts | Developers, architects | API specs, data schemas, components |
| **[🔧 03-Implementation](03-implementation/README.md)** | How the system is built | Developers | LangFlow, multi-agent approaches |
| **[📊 04-Diagrams](04-diagrams/README.md)** | Visual representations | All technical roles | Architecture, workflows, state machines |
| **[👥 05-Development](05-development/README.md)** | Contributor resources | Contributors, maintainers | Processes, journey, roadmaps |
| **[📚 06-Appendices](06-appendices/README.md)** | Reference materials | All users | Glossary, troubleshooting, resources |

## 🎯 Find What You Need

### By Role

#### 🆕 New Contributor

1. [Getting Started](GETTING_STARTED.md) - Setup and onboarding
2. [Contributing Guide](05-development/guides/CONTRIBUTING.md) - Process and standards
3. [Architecture Overview](01-project-overview/ARCHITECTURE.md) - System understanding

#### 💻 Developer

1. [Component Specifications](02-specifications/components/README.md) - What to build
2. [LangFlow Implementation](03-implementation/langflow/README.md) - Current approach
3. [Data Schemas](02-specifications/data-schemas/README.md) - Data structures

#### 🏗️ Architect  

1. [System Architecture](01-project-overview/ARCHITECTURE.md) - High-level design
2. [Multi-Agent Roadmap](05-development/planning/MULTI_AGENT_ROADMAP.md) - Future direction
3. [Diagrams Collection](04-diagrams/README.md) - Visual documentation

#### 📖 Domain Expert

1. [Project Vision](01-project-overview/VISION.md) - Business understanding
2. [Quality Specifications](02-specifications/advanced/QUALITY_GATE_SPEC.md) - Standards
3. [Troubleshooting](06-appendices/TROUBLESHOOTING.md) - Problem solving

### By Task

#### 🔍 Understanding the System

- [Project Vision](01-project-overview/VISION.md) - Why this exists
- [Architecture](01-project-overview/ARCHITECTURE.md) - How it's designed
- [Component Diagrams](04-diagrams/README.md) - Visual system overview

#### 🛠️ Building Features

- [Component Specs](02-specifications/components/README.md) - Requirements
- [Data Schemas](02-specifications/data-schemas/README.md) - Data contracts
- [Implementation Guide](03-implementation/README.md) - Technical approaches

#### 🐛 Solving Problems

- [Troubleshooting Guide](06-appendices/TROUBLESHOOTING.md) - Common solutions
- [Development Issues](05-development/README.md#troubleshooting) - Dev-specific problems
- [Glossary](06-appendices/GLOSSARY.md) - Term definitions

#### 📈 Planning & Strategy

- [Development Journey](05-development/journey/README.md) - Project evolution
- [Multi-Agent Roadmap](05-development/planning/MULTI_AGENT_ROADMAP.md) - Future plans
- [Lessons Learned](05-development/journey/LESSONS_LEARNED.md) - Experience insights

## 🔥 Recent Updates

### Latest Changes

- ✅ **Two-Agent System Architecture** - Complete technical specifications for dialogue classification and speaker attribution
- ✅ **Database-Driven Character Management** - PostgreSQL schema for character profiles and voice casting
- ✅ Complete documentation reorganization into logical 6-section structure
- ✅ LangFlow component implementation with full UI integration
- ✅ Multi-agent system architecture planning and roadmap
- ✅ Comprehensive troubleshooting and reference materials

### What's New

- **Two-Agent System**: Hybrid dialogue classifier and speaker attribution agents with database integration
- **Character Database**: PostgreSQL-based character profiling for voice casting decisions  
- **LangFlow Components**: Production-ready audiobook processing components
- **Quality Gates**: Automated validation and error detection systems  
- **Multi-Agent Planning**: Detailed roadmap for production architecture
- **Documentation Reorganization**: Professional knowledge base structure

## 🚀 Getting Started Paths

### 👋 I'm New Here

```text
📖 GETTING_STARTED.md → 🎯 Project Overview → 🔧 Development Setup
```text

### 💻 I Want to Contribute

```text
🤝 CONTRIBUTING.md → 🏗️ Architecture → 📝 Component Specs → 🛠️ Implementation
```text

### 🔍 I Need to Solve a Problem

```text
🚨 TROUBLESHOOTING.md → 📚 Glossary → 🏠 Relevant Section
```text

### 📊 I Want to Understand the System

```text
🎯 Vision → 🏗️ Architecture → 📊 Diagrams → 📋 Specifications
```text

## 💡 Pro Tips

### Documentation Navigation

- 🍞 **Follow the breadcrumbs** - Each page shows its location in the hierarchy
- 🔗 **Use cross-references** - Related sections are linked throughout
- 📑 **Start with section READMEs** - They provide comprehensive overviews
- 🔍 **Check the glossary** - Unknown terms are defined in appendices

### Contributing to Docs

- 📝 **Update cross-references** when moving or renaming files  
- 🎯 **Add content to appropriate sections** based on audience and purpose
- 📋 **Update section README files** when adding new documents
- 🔄 **Maintain the breadcrumb navigation** in all pages

## 🏗️ System Overview

The Agent Audiobook Maker is a sophisticated text processing pipeline that transforms raw books into richly annotated content suitable for audiobook production. The system has evolved from simple segmentation to a comprehensive two-agent architecture:

- **📄 Text Ingestion**: PDF and text file processing with quality validation
- **🔍 Content Analysis**: Chapter detection, structure classification, quality assessment
- **✂️ Intelligent Segmentation**: Advanced two-agent system for dialogue/narration classification and speaker attribution
- **🗄️ Character Database**: PostgreSQL-driven character profiling and voice casting preparation
- **🤖 AI-Powered Annotation**: Rich metadata generation with confidence scoring and quality metrics
- **🎯 Quality Assurance**: Automated validation and human-in-the-loop workflows

**Current Status**: Phase 1+ (Two-Agent Architecture) - Hybrid classification with database integration  
**Next Phase**: Phase 2 (Multi-Agent System) - Advanced orchestration and production deployment

**Two-Agent System Features**:

- Hybrid dialogue classification (heuristic + AI fallback)  
- Database-driven speaker attribution with character tracking
- Confidence scoring for quality assurance
- Character profile building for voice casting decisions

---

## 📞 Need Help?

- 🔍 **Search this documentation** - Use your browser's find function
- 📚 **Check the glossary** - [06-appendices/GLOSSARY.md](06-appendices/GLOSSARY.md)
- 🛠️ **Try troubleshooting** - [06-appendices/TROUBLESHOOTING.md](06-appendices/TROUBLESHOOTING.md)
- 💬 **Ask questions** - Create an issue in the GitHub repository

### Happy documenting! 🎉
