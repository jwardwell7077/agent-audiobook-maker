# \[DEPRECATED\] UML Class Diagram: Two-Agent Character Tracking System

> Deprecated terminology. See spans-first two-stage components for current
> UML where available. This document is preserved for historical reference.

## Overview

This document provides the complete UML class diagram for the two-agent dialogue classification and speaker attribution system, showing all classes, relationships, and database entities.

## Core System Classes

```mermaid
classDiagram
    %% Database Entity Classes
    class Character {
        +int id
        +int book_id
        +string canonical_name
        +string display_name
        +JSONB aliases
        +int first_appearance_segment_id
        +string character_type
        +JSONB profile
        +datetime created_at
        +datetime updated_at
        +validate_aliases() bool
        +add_alias(name: string, type: string) void
        +get_all_names() list[string]
        +update_profile(data: dict) void
    }

    class CharacterTextSegment {
        +int id
        +int character_id
        +int utterance_id
        +string segment_type
        +string relationship
        +string context_before
        +string context_after
        +float confidence_score
        +JSONB context_data
        +datetime created_at
        +validate_relationship() bool
        +get_context_window() dict
    }

    class Utterance {
        +int id
        +int book_id
        +int chapter_id
        +string text
        +int position_in_chapter
        +string dialogue_classification
        +float dialogue_confidence
        +int speaker_character_id
        +float speaker_confidence
        +datetime processed_by_agents
        +is_processed() bool
        +set_classification(type: string, confidence: float) void
        +set_speaker(character_id: int, confidence: float) void
    }

    class Book {
        +int id
        +string title
        +string author
        +JSONB metadata
        +get_characters() list[Character]
        +get_chapters() list[Chapter]
    }

    class Chapter {
        +int id
        +int book_id
        +int index
        +string title
        +string body_text
        +get_utterances() list[Utterance]
        +get_character_appearances() dict
    }

    %% Agent Classes
    class HybridDialogueClassifier {
        +HeuristicEngine heuristic_engine
        +AgentEngine agent_engine
        +ClassificationConfig config
        +classify_segment(segment: ContextWindow) ClassificationResult
        +should_use_agent(segment: string) bool
        +get_classification_confidence(result: dict) float
        -apply_heuristics(segment: string) HeuristicResult
        -apply_agent_classification(window: ContextWindow) AgentResult
        -combine_results(heuristic: dict, agent: dict) ClassificationResult
    }

    class SpeakerAttributionAgent {
        +CharacterDatabase character_db
        +AttributionEngine attribution_engine
        +ContextAnalyzer context_analyzer
        +attribute_speaker(segment: DialogueSegment, context: ContextWindow) AttributionResult
        +lookup_character(name: string, book_id: int) Character|None
        +create_character(name: string, book_id: int) Character
        +resolve_speaker_ambiguity(candidates: list) AttributionResult
        -extract_names_from_segment(text: string) list[string]
        -analyze_dialogue_tags(text: string) dict
        -determine_speaker_role(name: string, position: string) string
    }

    class CharacterProfileBuilder {
        +ProfileAggregator aggregator
        +RelationshipDetector relationship_detector
        +build_profile(character_id: int) CharacterProfile
        +update_profile(character_id: int, segments: list) void
        +detect_relationships(character_id: int) dict
        -analyze_dialogue_patterns(segments: list) dict
        -extract_character_traits(segments: list) dict
        -compute_speaking_statistics(segments: list) dict
    }

    %% Data Processing Classes
    class ContextWindow {
        +int target_segment_id
        +string target_text
        +list[string] context_before
        +list[string] context_after
        +list[string] prev_classifications
        +int estimated_tokens
        +int memory_footprint
        +build_context_prompt() string
        +validate_window_size() bool
    }

    class ContextWindowLoader {
        +DatabasePool db_pool
        +int batch_size
        +int memory_limit
        +load_batch(book_id: int) list[ContextWindow]
        +estimate_memory_usage(windows: list) int
        -build_context_query() string
        -validate_context_integrity(window: ContextWindow) bool
    }

    class ClassificationResult {
        +int segment_id
        +string classification
        +float confidence
        +string method
        +string reasoning
        +dict metadata
        +validate_result() bool
        +to_database_record() dict
    }

    class AttributionResult {
        +int segment_id
        +int character_id
        +string character_name
        +float confidence
        +string attribution_method
        +list[dict] alternative_candidates
        +dict context_evidence
        +validate_attribution() bool
        +get_best_candidate() dict
    }

    %% Engine Classes
    class HeuristicEngine {
        +list[Pattern] dialogue_patterns
        +list[Pattern] narration_patterns
        +PatternMatcher matcher
        +classify(text: string) HeuristicResult
        +get_confidence_score(matches: list) float
        -match_dialogue_patterns(text: string) list[Match]
        -match_narration_patterns(text: string) list[Match]
        -compute_pattern_strength(matches: list) float
    }

    class AgentEngine {
        +LLMInterface llm
        +PromptTemplate template
        +ClassificationConfig config
        +classify_with_context(window: ContextWindow) AgentResult
        +batch_classify(windows: list[ContextWindow]) list[AgentResult]
        -build_classification_prompt(window: ContextWindow) string
        -parse_llm_response(response: string) AgentResult
        -validate_classification(result: dict) bool
    }

    class AttributionEngine {
        +NameExtractor name_extractor
        +DialogueAnalyzer dialogue_analyzer
        +ContextAnalyzer context_analyzer
        +extract_speaker_candidates(segment: string) list[string]
        +analyze_dialogue_structure(text: string) dict
        +determine_attribution_confidence(evidence: dict) float
        -parse_dialogue_tags(text: string) list[dict]
        -identify_addressees(text: string) list[string]
        -compute_attribution_score(candidate: string, evidence: dict) float
    }

    class CharacterDatabase {
        +DatabasePool db_pool
        +CharacterCache cache
        +lookup_character(name: string, book_id: int) Character|None
        +create_character(data: dict) Character
        +update_character_profile(character_id: int, profile: dict) void
        +get_character_aliases(character_id: int) list[string]
        +resolve_name_conflicts(names: list, book_id: int) list[Character]
        -normalize_character_name(name: string) string
        -check_alias_matches(name: string, character: Character) bool
        -update_character_cache(character: Character) void
    }

    %% Processing Pipeline Classes
    class TwoAgentProcessor {
        +HybridDialogueClassifier dialogue_classifier
        +SpeakerAttributionAgent speaker_agent
        +CharacterProfileBuilder profile_builder
        +ContextWindowLoader window_loader
        +DatabaseManager db_manager
        +process_book(book_id: int) ProcessingResult
        +process_batch(windows: list[ContextWindow]) BatchResult
        -coordinate_agent_processing(windows: list) dict
        -update_database_batch(results: list) void
        -validate_processing_results(results: dict) bool
    }

    class DatabaseManager {
        +DatabasePool connection_pool
        +TransactionManager transaction_manager
        +batch_update_utterances(updates: list) bool
        +batch_create_character_segments(segments: list) bool
        +commit_character_profiles(profiles: dict) bool
        +rollback_failed_processing(batch_id: string) bool
        -validate_database_constraints(data: dict) bool
        -optimize_batch_queries(queries: list) list
    }

    %% Relationships
    Character ||--o{ CharacterTextSegment : has
    Utterance ||--o{ CharacterTextSegment : referenced_by
    Character ||--o{ Utterance : spoken_by
    Book ||--o{ Character : contains
    Book ||--o{ Chapter : contains
    Chapter ||--o{ Utterance : contains

    HybridDialogueClassifier *-- HeuristicEngine
    HybridDialogueClassifier *-- AgentEngine
    SpeakerAttributionAgent *-- AttributionEngine
    SpeakerAttributionAgent *-- CharacterDatabase
    CharacterProfileBuilder *-- ProfileAggregator
    TwoAgentProcessor *-- HybridDialogueClassifier
    TwoAgentProcessor *-- SpeakerAttributionAgent
    TwoAgentProcessor *-- CharacterProfileBuilder
    TwoAgentProcessor *-- ContextWindowLoader
    TwoAgentProcessor *-- DatabaseManager

    ContextWindowLoader ..> ContextWindow : creates
    HybridDialogueClassifier ..> ClassificationResult : produces
    SpeakerAttributionAgent ..> AttributionResult : produces
    CharacterDatabase ..> Character : manages
```

## Key Class Relationships

### Composition Relationships

- **TwoAgentProcessor** owns and coordinates all processing components
- **HybridDialogueClassifier** contains both heuristic and agent engines
- **SpeakerAttributionAgent** contains attribution logic and character database access

### Association Relationships

- **Character** has many **CharacterTextSegment** records
- **Utterance** can be associated with one **Character** as speaker
- **Book** contains multiple **Character** and **Chapter** entities

### Dependency Relationships

- **ContextWindowLoader** creates **ContextWindow** objects
- **HybridDialogueClassifier** produces **ClassificationResult** objects
- **SpeakerAttributionAgent** produces **AttributionResult** objects

## Interface Definitions

### LLMInterface

```python
class LLMInterface(ABC):
    @abstractmethod
    def classify(self, prompt: str, context: dict) -> dict:
        pass
    
    @abstractmethod
    def batch_classify(self, prompts: list[str]) -> list[dict]:
        pass
```

### DatabasePool

```python
class DatabasePool(ABC):
    @abstractmethod
    async def acquire(self) -> Connection:
        pass
    
    @abstractmethod
    async def execute_batch(self, queries: list[str]) -> list[dict]:
        pass
```

## Class Interaction Patterns

### Processing Flow Pattern

1. **TwoAgentProcessor** loads context windows via **ContextWindowLoader**
1. **HybridDialogueClassifier** processes segments using heuristics or agents
1. **SpeakerAttributionAgent** attributes speakers for dialogue segments
1. **CharacterProfileBuilder** updates character profiles
1. **DatabaseManager** persists all results in batches

### Error Handling Pattern

- All processing classes implement validation methods
- Results include confidence scores for quality assessment
- Database operations are wrapped in transactions with rollback capability

### Caching Pattern

- **CharacterDatabase** maintains in-memory cache of frequently accessed characters
- **ContextWindowLoader** implements memory limit checks to prevent overflow
- **ProfileAggregator** caches computed statistics for performance

This UML diagram provides the complete class structure for implementing the two-agent character tracking system with proper separation of concerns and clear interface definitions.
