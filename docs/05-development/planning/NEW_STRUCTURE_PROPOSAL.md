# Proposed Documentation Structure

## Current Issues

- Documents are mixed at the root level without clear categorization
- Hard to find related documents (specs, diagrams, progress updates)
- No clear navigation path for different user types (developers, contributors, users)

## Proposed Structure

```text
docs/
├── README.md                           # Main documentation index
├── GETTING_STARTED.md                  # Quick start guide
│
├── 01-project-overview/
│   ├── README.md                       # Overview index
│   ├── VISION.md                       # Project vision and goals
│   ├── CONTEXT.md                      # Current file - project context
│   ├── KISS.md                         # Current file - project principles
│   └── ARCHITECTURE.md                 # Current file - high-level architecture
│
├── 02-specifications/
│   ├── README.md                       # Specs index
│   ├── data-schemas/
│   │   ├── README.md
│   │   ├── STRUCTURED_JSON_SCHEMA.md
│   │   ├── ANNOTATION_SCHEMA.md
│   │   └── schemas/                    # JSON schema files
│   ├── components/
│   │   ├── README.md
│   │   ├── PDF_TO_TEXT_SPEC.md
│   │   ├── PDF_TO_TEXT_CLI_SPEC.md
│   │   ├── TXT_TO_JSON_SPEC.md
│   │   ├── SECTION_CLASSIFIER_SPEC.md
│   │   ├── CHAPTERIZER_SPEC.md
│   │   └── QUALITY_GATE_SPEC.md        # from design/
│   └── advanced/
│       ├── README.md
│       ├── ADVANCED_SPEAKER_ATTRIBUTION.md
│       └── MVP_SPECIFICATION.md
│
├── 03-implementation/
│   ├── README.md                       # Implementation index
│   ├── langflow/
│   │   ├── README.md
│   │   ├── LANGFLOW_COMPONENT_PLAN.md
│   │   ├── LANGFLOW_COMPONENT_SUCCESS.md
│   │   ├── LANGFLOW_COMPONENT_SUCCESS_CLEAN.md
│   │   └── COMPONENT_TEST_RESULTS.md
│   ├── multi-agent/
│   │   ├── README.md
│   │   ├── MULTI_AGENT_ROADMAP.md
│   │   └── LEARNING_PATH_MULTI_AGENT.md
│   └── examples/                       # Move from root
│
├── 04-diagrams/
│   ├── README.md                       # Diagram index with thumbnails/descriptions
│   ├── architecture/
│   │   ├── high_level_architecture.mmd
│   │   ├── langflow_architecture.mmd
│   │   └── quality_gate_architecture.mmd
│   ├── flows/
│   │   ├── pdf_to_text_flow.mmd
│   │   ├── langflow_fsm.mmd
│   │   ├── section_classifier.mmd
│   │   └── structured_json_schema.mmd
│   ├── state-machines/
│   │   ├── chapterizer_fsm.mmd
│   │   ├── section_classifier_fsm.mmd
│   │   └── quality_gate_fsm.mmd
│   └── uml/
│       ├── chapterizer_uml.mmd
│       ├── langflow_uml.mmd
│       ├── pdf_to_text_uml.mmd
│       ├── quality_gate_uml.mmd
│       └── section_classifier_uml.mmd
│
├── 05-development/
│   ├── README.md                       # Development index
│   ├── journey/
│   │   ├── README.md
│   │   ├── DEVELOPMENT_JOURNEY.md
│   │   ├── LESSONS_LEARNED.md
│   │   └── progress-updates/
│   │       ├── README.md
│   │       ├── PROGRESS_UPDATE_2025_08_23.md
│   │       ├── LANGFLOW_STATUS_UPDATE.md
│   │       └── QUALITY_GATE_SUCCESS.md
│   ├── templates/
│   │   ├── FULL_DESIGN_SPEC_TEMPLATE.md
│   │   └── TEST_PLAN_TEMPLATE.md
│   └── guides/
│       └── CONTRIBUTING.md             # Move from root
│
└── 06-appendices/
    ├── README.md
    ├── glossary.md                     # New - technical terms
    ├── troubleshooting.md              # New - common issues
    └── references.md                   # New - external links
```

## Benefits of This Structure

1. **Clear User Paths**: Different entry points for different needs
2. **Logical Grouping**: Related documents are co-located
3. **Scalable**: Easy to add new documents in appropriate sections
4. **Discoverable**: Each section has its own index/README
5. **Maintainable**: Clear ownership and update patterns

## Migration Strategy

1. Create new directory structure
2. Move files to new locations
3. Update all cross-references and links
4. Create comprehensive index files
5. Add navigation breadcrumbs
6. Test all links work correctly

## Index Files Strategy

Each major section will have:

- Overview of what's in that section
- Quick navigation to key documents
- Visual hierarchy (when appropriate)
- Status indicators (draft/stable/deprecated)
