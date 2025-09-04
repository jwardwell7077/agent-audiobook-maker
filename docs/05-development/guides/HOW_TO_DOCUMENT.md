# How to Document - Agent Audiobook Maker

> **Purpose**: Complete guide for creating, organizing, and maintaining documentation in the Agent Audiobook Maker project.

This guide explains our documentation structure, standards, templates, and best practices to help you contribute effectively to the project's knowledge base.

## Documentation Philosophy

### Core Principles

- **User-Centric**: Documentation serves different audiences with different needs
- **Hierarchical Organization**: Information is organized in logical, navigable sections
- **Living Documentation**: Docs evolve with the codebase and stay current
- **Self-Service**: Users should find answers without asking questions
- **Quality Over Quantity**: Better to have fewer, excellent docs than many poor ones

### Documentation-First Approach

1. **Design documents** before coding major features
2. **Update docs** with every code change that affects user experience
3. **Test documentation** - ensure examples work and instructions are clear
4. **Review docs** as part of the code review process

## Documentation Structure

### 6-Section Hierarchy

Our documentation follows a 6-section structure designed for different user types and needs:

```text
docs/
├── README.md                    # Main documentation index
├── GETTING_STARTED.md          # New contributor onboarding
├── 01-project-overview/        # Vision, architecture, context
├── 02-specifications/          # Technical requirements
├── 03-implementation/          # How the system is built
├── 04-diagrams/                # Visual documentation
├── 05-development/             # Contributor resources
└── 06-appendices/              # Reference materials
```text

### Section Purposes

| Section | Purpose | Audience | Content Types |
|---------|---------|----------|---------------|
| **01-Project Overview** | Understanding the project | All stakeholders | Vision, architecture, context |
| **02-Specifications** | What needs to be built | Developers, architects | API specs, data schemas, requirements |
| **03-Implementation** | How it's being built | Developers | Code organization, approaches, examples |
| **04-Diagrams** | Visual system understanding | Technical roles | Architecture, workflows, state machines |
| **05-Development** | Contributing to the project | Contributors | Processes, guidelines, journey docs |
| **06-Appendices** | Reference and troubleshooting | All users | Glossary, troubleshooting, resources |

## What to Document Where

### 01-Project Overview

**When to use**: Documenting high-level concepts, vision, or system architecture.

**File Types**:

- `README.md` - Section overview and navigation
- `VISION.md` - Project purpose, goals, and strategic direction
- `ARCHITECTURE.md` - System design and component relationships
- `CONTEXT.md` - Background, history, and decision context

**Examples**:

- Why does this project exist?
- What problem are we solving?
- How do the major components work together?
- What are our design principles?

### 02-Specifications

**When to use**: Documenting technical requirements, contracts, and detailed specifications.

**Subsections**:

- `data-schemas/` - Data structure definitions and schemas
- `components/` - Individual component specifications
- `advanced/` - Complex features and quality requirements

**File Types**:

- `*_SPEC.md` - Detailed technical specifications
- `*_SCHEMA.md` - Data structure definitions
- `README.md` files - Section navigation and overviews

**Examples**:

- API endpoint specifications
- Data structure definitions
- Component behavior requirements
- Quality gate definitions
- Advanced feature specifications

### 03-Implementation

**When to use**: Documenting how the system is actually built and organized.

**Subsections**:

- `langflow/` - Current LangFlow-based implementation
- `multi-agent/` - Future multi-agent system approach
- `examples/` - Working code samples and integration examples

**File Types**:

- `README.md` - Implementation approach overviews
- Component documentation and guides
- Example code and tutorials
- Integration guides

**Examples**:

- How to set up LangFlow components
- Code organization patterns
- Implementation decisions and trade-offs
- Working examples and tutorials

### 04-Diagrams

**When to use**: Creating visual representations of system concepts.

**File Types**:

- `*.mmd` - Mermaid diagram files
- `README.md` - Diagram index and usage guide

**Diagram Categories**:

- **Architecture** - System overview and component relationships
- **Workflows** - Process flows and data pipelines
- **State Machines** - Component behavior and state transitions
- **UML** - Class diagrams and relationships

**Examples**:

- System architecture diagrams
- Data flow diagrams
- Component interaction diagrams
- State machine diagrams

### 05-Development

**When to use**: Documenting contributor processes, project evolution, and development resources.

**Subsections**:

- `guides/` - Process documentation and how-to guides
- `journey/` - Project evolution and lessons learned
- `planning/` - Roadmaps and strategic planning
- `templates/` - Documentation templates

**File Types**:

- `CONTRIBUTING.md` - Contribution guidelines and processes
- Process guides and how-to documents
- Roadmaps and planning documents
- Project retrospectives and lessons learned

**Examples**:

- How to contribute code
- Development workflow and standards
- Project evolution and decisions
- Future roadmaps and plans

### 06-Appendices

**When to use**: Creating reference materials and troubleshooting resources.

**File Types**:

- `GLOSSARY.md` - Term definitions and vocabulary
- `TROUBLESHOOTING.md` - Problem-solving guide
- `REFERENCES.md` - External resources and citations

**Examples**:

- Technical term definitions
- Common problems and solutions
- External learning resources
- Tool documentation links

## File Naming Conventions

### Naming Patterns

- **Descriptive names**: `COMPONENT_SPECIFICATION.md` not `spec.md`
- **ALL_CAPS for major docs**: `README.md`, `CONTRIBUTING.md`, `ARCHITECTURE.md`
- **snake_case for technical docs**: `pdf_to_text_spec.md`, `quality_gate_spec.md`
- **Consistent suffixes**: `*_SPEC.md`, `*_SCHEMA.md`, `*_GUIDE.md`

### File Type Conventions

| Type | Naming Pattern | Example | Purpose |
|------|----------------|---------|---------|
| **Index** | `README.md` | `02-specifications/README.md` | Section navigation |
| **Specification** | `*_SPEC.md` | `SECTION_CLASSIFIER_SPEC.md` | Technical requirements |
| **Schema** | `*_SCHEMA.md` | `ANNOTATION_SCHEMA.md` | Data structure definitions |
| **Guide** | `*_GUIDE.md` | `SETUP_GUIDE.md` | How-to instructions |
| **Template** | `*_TEMPLATE.md` | `DESIGN_SPEC_TEMPLATE.md` | Reusable document templates |

## Documentation Templates

### Section README Template

Use this template for section index files:

```markdown
# Section Name

> **Purpose**: Brief description of what this section contains.

This section contains [description of content type and audience].

## Quick Navigation

| Category | Purpose | Files |
|----------|---------|-------|
| 📂 **Category** | What it contains | `file1.md`, `file2.md` |

## Contents

### 📋 [Document Name](#document-template)
**Brief description of what this document contains**

Key information about what users will find:
- Bullet point 1
- Bullet point 2  
- Bullet point 3

*Use this when [specific use case].*

## Related Sections

- 🔗 [Related Section](#related-section) - Why it's related
- 🔗 [Another Section](#another-related) - Connection explanation

---

*Part of [Documentation Index](../../README.md)*
```text

### Technical Specification Template

Use this for detailed technical specifications:

```markdown
# Component/Feature Name Specification

> **Purpose**: [One sentence describing what this specifies]

## Overview

Brief description of the component/feature and its role in the system.

## Requirements

### Functional Requirements
- **FR1**: [Requirement description]
- **FR2**: [Another requirement]

### Non-Functional Requirements  
- **NFR1**: Performance requirements
- **NFR2**: Quality requirements

## API/Interface Specification

### Input Format
```json
{
  "example": "input format"
}
```text

### Output Format

```json
{
  "example": "output format"
}
```text

## Behavior Specification

Detailed description of how the component should behave.

## Error Handling

How the component handles various error conditions.

## Testing Requirements

How to validate that the implementation meets the specification.

## Related Documents (examples)

- Related Spec (example)
- Implementation Guide (example)

```markdown
# Implementation: [Component/Feature Name]

> **Purpose**: [How this implementation works and why]

## Overview

Brief description of the implementation approach.

## Architecture

### Components

- **Component 1**: What it does
- **Component 2**: What it does

### Data Flow

Description or diagram of how data flows through the implementation.

## Setup and Usage

### Prerequisites

- Requirement 1
- Requirement 2

### Installation

```bash
# Step-by-step commands
```text

### Basic Usage

```python
# Example code
```text

## Advanced Features

Details about advanced capabilities.

## Troubleshooting

Common issues and solutions.

## Performance Considerations

Important performance notes and optimization tips.

## Reference Documents

- Specification (example)
- Examples (example)

### Implementation Guide Template

Use this for implementation documentation:

```markdown
# Implementation: [Component/Feature Name]

> **Purpose**: [How this implementation works and why]

## Overview

Brief description of the implementation approach.

## Architecture

### Components

- **Component 1**: What it does
- **Component 2**: What it does

### Data Flow

Description or diagram of how data flows through the implementation.

## Setup and Usage

### Prerequisites

- Requirement 1
- Requirement 2

### Installation

```bash
# Step-by-step commands
```text

### Configuration

```python
# Example code
```text

## Implementation Features

Details about advanced capabilities.

## Issue Resolution

Common issues and solutions.

## Performance Notes

Important performance notes and optimization tips.

## Links

- Specification (example)
- Examples (example)

## Documentation Standards

### Markdown Standards

**Required Elements**:

- **Purpose statement** - Every document starts with `> **Purpose**: ...`
- **Clear headings** - Use proper heading hierarchy (H1 → H2 → H3)
- **Navigation aids** - Breadcrumbs, cross-references, "Related Sections"
- **Examples** - Include code examples and practical usage
- **Context** - Explain why, not just what

**Formatting Requirements**:

- **Line length**: Aim for 80 characters, max 120
- **Blank lines**: Around headings, lists, and code blocks
- **Code blocks**: Always specify language (`python`, `bash`, `json`)
- **Links**: Use descriptive text, not bare URLs
- **Lists**: Consistent formatting with blank lines around

### Content Standards

**Writing Guidelines**:

- **Active voice**: "The system processes data" not "Data is processed"
- **Present tense**: "The component returns results" not "will return"
- **Specific examples**: Show real code, real data, real scenarios
- **User perspective**: Write for the person who needs to use this information

**Structure Guidelines**:

- **Start with overview**: What is this and why does it matter?
- **Provide context**: How does this fit into the bigger picture?
- **Include examples**: Show practical usage
- **Add troubleshooting**: Anticipate common problems
- **Link related content**: Help users find connected information

### Quality Checklist

Before submitting documentation:

- [ ] **Purpose is clear** - Reader understands why this document exists
- [ ] **Audience is appropriate** - Content matches the intended users
- [ ] **Examples work** - Code samples execute successfully
- [ ] **Links are valid** - All internal and external links work
- [ ] **Navigation is complete** - Breadcrumbs and cross-references included
- [ ] **Formatting is consistent** - Follows project markdown standards
- [ ] **Content is current** - Reflects the actual current state of the system

## Maintenance Workflow

### When to Update Documentation

**Required Updates**:

- **New features** - Document capabilities, usage, and integration
- **API changes** - Update specifications and examples
- **Process changes** - Revise workflow and contribution guides
- **Architecture changes** - Update diagrams and system documentation

**Recommended Updates**:

- **Bug fixes** - Add to troubleshooting if generally applicable
- **Performance improvements** - Update performance notes
- **New examples** - Add to relevant implementation guides
- **Learning experiences** - Add to lessons learned

### Update Process

1. **Identify affected documents** - What docs need updates?
2. **Update content** - Make necessary changes
3. **Update cross-references** - Fix any broken links
4. **Test examples** - Ensure code samples still work
5. **Review navigation** - Verify section READMEs are current
6. **Commit with good message** - Describe what changed and why

### Documentation Review

**Self-Review Checklist**:

- Does this explain things clearly to someone new to the project?
- Are there sufficient examples and practical guidance?
- Is the navigation helpful for finding related information?
- Does the content match the current reality of the system?

**Peer Review Focus**:

- Clarity and completeness for the target audience
- Accuracy of technical content and examples
- Consistency with existing documentation standards
- Quality of organization and navigation

## Tools and Automation

### Linting and Quality

**Markdown Linting**:

```bash
# Run markdown linter (requires npm/npx)
npx markdownlint-cli docs/ --fix

# Check specific files
npx markdownlint-cli docs/README.md
```text

**Quality Checks**:

- Link validation - Ensure all links work
- Example validation - Test that code samples execute
- Consistency checks - Verify formatting and structure

### Diagram Creation

**Mermaid Diagrams**:

- Use Mermaid for all diagrams to ensure version control and consistency
- Store as `.mmd` files in appropriate diagram categories
- Include diagram purpose and context in surrounding documentation

**Diagram Tools**:

- VS Code Mermaid Preview extension
- Online Mermaid editor (mermaid.live)
- GitHub automatic Mermaid rendering

### Documentation Automation

**Automated Tasks** (when available):

- Link checking in CI/CD
- Markdown linting in pull requests
- Diagram generation and validation
- Documentation completeness metrics

## Getting Help

### Resources

- **Templates**: Use files in `docs/05-development/templates/`
- **Examples**: Look at existing well-documented sections
- **Style Guide**: This document and existing documentation patterns
- **Glossary**: `docs/06-appendices/GLOSSARY.md` for term definitions

### Questions and Support

- **Structure questions**: How should I organize this information?
- **Audience questions**: Who is this documentation for?
- **Standards questions**: What format or template should I use?
- **Process questions**: How do I update cross-references?

*Create GitHub issues with the "documentation" label for questions and suggestions.*

---

*Part of [Development Guides](README.md) | [Documentation Index](../../README.md)*

## Mermaid diagrams: authoring and embedding

This project uses Mermaid for diagrams. Follow these rules to avoid GitHub rendering errors and flaky parsing.

### When creating standalone diagram files (`*.mmd` in `docs/04-diagrams/**`)

- Store RAW Mermaid DSL only. Do NOT wrap in a code fence.
  - First non-comment line must be the diagram directive, e.g. `flowchart LR` or `classDiagram`.
- Keep comments on their own lines using `%%`.
- Examples:

  - Flowchart file:
    
    flowchart LR
      PDF[PDF file] -->|"PyMuPDF / fitz"| EXTRACT[Extract pages]
      EXTRACT --> CLEAN[Normalize & clean]
      CLEAN --> TXT[Write .txt]
    
  - Class diagram file:
    
    classDiagram
      direction TB
      Component <|-- ABMChapterVolumeLoader
      ABMCacheManager ..> ABMTTSRenderer : caches
    

### When embedding diagrams inside Markdown (`.md`)

- Use a single fenced block with the language `mermaid`.
- Put the directive (`flowchart LR`, `classDiagram`, etc.) as the first line inside the fence.
- Do not nest fences or add blank lines immediately after ```mermaid.
- Example:
  
  ```mermaid
  flowchart LR
    A --> B
  ```

### GitHub-specific pitfalls and fixes

- Parentheses and special characters in edge labels can break parsing.
  - Prefer to avoid `(` and `)` in labels; if needed, wrap the label in double quotes: `-->|"Call (fitz)"|`.
  - Safer alternative: replace with `/` or `-` (e.g., `PyMuPDF / fitz`).
- Don’t use `mermaid.radar` or custom fence languages—only `mermaid` is supported by GitHub.
- Don’t duplicate diagram directives (e.g., avoid `classDiagram` on two consecutive lines).
- Class diagram relations use UML arrows, not flowchart link syntax:
  - Dependency: `..>`
  - Realization: `..|>`
  - Inheritance: `<|--`
  - Aggregation: `o--`
  - Composition: `*--`
  - Association: `-->` or `--`
  - Do NOT use `-.->` (that’s a flowchart dotted link). Use `..>` in class diagrams instead.
- Edge label syntax for flowcharts:
  - `A -->|text| B` or `A -- text --> B`
  - Quote labels if they include punctuation: `A -->|"Link (v1)"| B`
- Keep a direction line for readability in large diagrams: `direction TB` or `direction LR` (class diagrams only).

### Validation and tests

- We include unit tests to validate Mermaid syntax and catch regressions.
  - Run just the Mermaid tests:

    pytest tests/unit_tests/test_mermaid_*.py -q

- Locally preview in VS Code with a Mermaid extension, or use the project’s validator where available.

### Naming and organization

- Place flow/process diagrams under `docs/04-diagrams/flows/`.
- Place UML class diagrams under `docs/04-diagrams/uml/`.
- Architecture/system overviews under `docs/04-diagrams/architecture/`.
- Use `snake_case` filenames that reflect content, e.g., `pdf_to_text_flow.mmd`, `langflow_uml.mmd`.

### Quick checklist (before committing)

- No code fences in `.mmd` files.
- First line is the correct directive.
- No duplicate directives.
- Labels with punctuation are quoted or simplified.
- Class diagram uses UML arrows (e.g., `..>`), not flowchart dotted links.
- File is placed in the correct subfolder and named descriptively.
