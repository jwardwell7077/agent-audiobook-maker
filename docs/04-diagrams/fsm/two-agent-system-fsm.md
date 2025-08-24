# Two-Agent System Finite State Machine Specifications

## Processing State Machine Overview

The two-agent system operates through a series of well-defined states that govern dialogue classification, speaker attribution, and character database management.

## Main Processing FSM

```mermaid
stateDiagram-v2
    [*] --> Initializing : Start Processing
    
    Initializing --> LoadingSegments : System Ready
    LoadingSegments --> SegmentReady : Segments Loaded
    LoadingSegments --> LoadError : Loading Failed
    
    LoadError --> [*] : Abort Processing
    
    SegmentReady --> BuildingContext : Create Context Window
    BuildingContext --> ContextReady : Window Built
    BuildingContext --> ContextError : Window Build Failed
    
    ContextError --> SegmentReady : Retry with Next Segment
    
    ContextReady --> ClassifyingDialogue : Begin Classification
    
    state ClassifyingDialogue {
        [*] --> HeuristicAnalysis
        
        HeuristicAnalysis --> ClearDialogue : Quote + Dialogue Tag
        HeuristicAnalysis --> ClearNarration : Descriptive Text
        HeuristicAnalysis --> RequiresAI : Ambiguous Pattern
        
        ClearDialogue --> [*] : Heuristic Result
        ClearNarration --> [*] : Heuristic Result
        
        RequiresAI --> AIProcessing : Context Analysis Needed
        AIProcessing --> AIComplete : AI Classification Done
        AIProcessing --> AIError : AI Processing Failed
        
        AIComplete --> [*] : AI Result
        AIError --> [*] : Fallback Result
    }
    
    ClassifyingDialogue --> DialogueClassified : Classification Complete
    
    DialogueClassified --> CheckDialogueType : Evaluate Result
    
    state CheckDialogueType {
        [*] --> choice_state
        choice_state --> DialogueDetected : Dialogue/Mixed
        choice_state --> NarrationDetected : Narration Only
    }
    
    DialogueDetected --> AttributingSpeaker : Speaker Attribution Needed
    NarrationDetected --> CollectingContext : Context Collection
    
    state AttributingSpeaker {
        [*] --> DatabaseLookup
        
        DatabaseLookup --> CharacterFound : Match in Database
        DatabaseLookup --> NoCharacterMatch : No Match Found
        
        CharacterFound --> AnalyzingRole : Determine Speaker/Addressee
        NoCharacterMatch --> CreatingCharacter : New Character Detected
        
        CreatingCharacter --> CharacterCreated : Character Record Created
        CharacterCreated --> AnalyzingRole : Proceed with Role Analysis
        
        AnalyzingRole --> SpeakerIdentified : Speaker Role Confirmed
        AnalyzingRole --> AddresseeIdentified : Addressee Role Confirmed
        AnalyzingRole --> AmbiguousRole : Role Unclear
        
        SpeakerIdentified --> [*] : Attribution Complete
        AddresseeIdentified --> [*] : Attribution Complete
        AmbiguousRole --> [*] : Store Multiple Options
    }
    
    state CollectingContext {
        [*] --> AnalyzingNarration
        
        AnalyzingNarration --> CharacterMentions : Characters Referenced
        AnalyzingNarration --> SceneDescription : Scene Context
        AnalyzingNarration --> ActionDescription : Character Actions
        
        CharacterMentions --> LinkingMentions : Associate with Characters
        SceneDescription --> StoringContext : Store Scene Data
        ActionDescription --> LinkingActions : Associate Actions
        
        LinkingMentions --> [*] : Mentions Linked
        StoringContext --> [*] : Context Stored
        LinkingActions --> [*] : Actions Linked
    }
    
    AttributingSpeaker --> UpdatingDatabase : Update Character Records
    CollectingContext --> UpdatingDatabase : Update Context Data
    
    state UpdatingDatabase {
        [*] --> UpdatingCharacterTable : Update Character Records
        UpdatingCharacterTable --> UpdatingTextSegments : Create Text Associations
        UpdatingTextSegments --> UpdatingUtterances : Update Utterance Records
        UpdatingUtterances --> UpdatingProfiles : Update Character Profiles
        UpdatingProfiles --> [*] : Database Update Complete
    }
    
    UpdatingDatabase --> ProcessingComplete : Segment Processing Done
    ProcessingComplete --> CheckMoreSegments : Check Processing Queue
    
    state CheckMoreSegments {
        [*] --> choice_more
        choice_more --> SegmentReady : More Segments Available
        choice_more --> AllComplete : No More Segments
    }
    
    AllComplete --> [*] : Processing Finished
```

## Dialogue Classification FSM Detail

```mermaid
stateDiagram-v2
    [*] --> ReceiveSegment : New Segment Input
    
    ReceiveSegment --> ExtractingFeatures : Parse Text Features
    
    state ExtractingFeatures {
        [*] --> CheckQuotes : Look for Quote Marks
        CheckQuotes --> CheckDialogueTags : Look for Speech Tags
        CheckDialogueTags --> CheckSpeechIndicators : Look for Speech Verbs
        CheckSpeechIndicators --> CheckContextClues : Analyze Context
        CheckContextClues --> [*] : Feature Extraction Done
    }
    
    ExtractingFeatures --> ApplyingHeuristics : Use Rule-Based Logic
    
    state ApplyingHeuristics {
        [*] --> QuoteAnalysis
        
        QuoteAnalysis --> HasClearQuotes : "Text" + said/asked
        QuoteAnalysis --> HasPartialQuotes : "Text" without tag
        QuoteAnalysis --> NoQuotes : No quotation marks
        
        HasClearQuotes --> HighConfidenceDialogue : Clear Dialogue Pattern
        HasPartialQuotes --> MediumConfidenceDialogue : Likely Dialogue
        NoQuotes --> NarrativeAnalysis : Check for Narration
        
        NarrativeAnalysis --> HasDescriptive : Action/Setting Description
        NarrativeAnalysis --> HasReported : Reported Speech
        NarrativeAnalysis --> Ambiguous : Unclear Pattern
        
        HasDescriptive --> HighConfidenceNarration : Clear Narration
        HasReported --> MediumConfidenceDialogue : Indirect Speech
        Ambiguous --> RequiresAI : Need AI Analysis
        
        HighConfidenceDialogue --> [*] : Heuristic Classification
        MediumConfidenceDialogue --> [*] : Heuristic Classification
        HighConfidenceNarration --> [*] : Heuristic Classification
        RequiresAI --> [*] : Send to AI Agent
    }
    
    ApplyingHeuristics --> CheckConfidence : Evaluate Confidence Level
    
    state CheckConfidence {
        [*] --> confidence_check
        confidence_check --> HighConfidence : Confidence > 0.9
        confidence_check --> MediumConfidence : 0.7 < Confidence ≤ 0.9
        confidence_check --> LowConfidence : Confidence ≤ 0.7
    }
    
    HighConfidence --> ClassificationComplete : Accept Heuristic Result
    MediumConfidence --> ClassificationComplete : Accept with Flag
    LowConfidence --> AIClassification : Requires AI Analysis
    
    state AIClassification {
        [*] --> PrepareContext : Build Context Window
        PrepareContext --> InvokeAI : Call LLM with Context
        InvokeAI --> AIProcessing : AI Analysis in Progress
        
        AIProcessing --> AISuccess : AI Classification Complete
        AIProcessing --> AITimeout : AI Request Timeout
        AIProcessing --> AIError : AI Processing Error
        
        AISuccess --> [*] : Return AI Result
        AITimeout --> [*] : Return Fallback Result
        AIError --> [*] : Return Fallback Result
    }
    
    AIClassification --> ClassificationComplete : AI Analysis Done
    ClassificationComplete --> [*] : Classification Ready
```

## Speaker Attribution FSM Detail

```mermaid
stateDiagram-v2
    [*] --> ReceiveDialogue : Dialogue Segment Input
    
    ReceiveDialogue --> ExtractingNames : Parse Character Names
    
    state ExtractingNames {
        [*] --> TokenizeText : Split into Tokens
        TokenizeText --> IdentifyNames : Find Potential Names
        IdentifyNames --> NormalizeNames : Standardize Name Forms
        NormalizeNames --> [*] : Names Extracted
    }
    
    ExtractingNames --> DatabaseLookup : Query Character Database
    
    state DatabaseLookup {
        [*] --> ExactNameSearch : Search by Exact Name
        
        ExactNameSearch --> NameFound : Direct Match
        ExactNameSearch --> NoExactMatch : No Direct Match
        
        NoExactMatch --> AliasSearch : Search Aliases
        AliasSearch --> AliasFound : Alias Match
        AliasSearch --> NoAliasMatch : No Alias Match
        
        NoAliasMatch --> FuzzySearch : Fuzzy Name Matching
        FuzzySearch --> FuzzyFound : Similar Name Found
        FuzzySearch --> NoMatch : No Similar Names
        
        NameFound --> [*] : Character Located
        AliasFound --> [*] : Character Located
        FuzzyFound --> [*] : Character Located
        NoMatch --> [*] : No Character Found
    }
    
    DatabaseLookup --> EvaluateMatches : Process Search Results
    
    state EvaluateMatches {
        [*] --> match_evaluation
        match_evaluation --> SingleMatch : One Character Found
        match_evaluation --> MultipleMatches : Multiple Candidates
        match_evaluation --> NoMatches : No Character Found
    }
    
    SingleMatch --> AnalyzeRole : Determine Speaker Role
    MultipleMatches --> DisambiguateCharacters : Resolve Ambiguity
    NoMatches --> CreateNewCharacter : Add New Character
    
    state DisambiguateCharacters {
        [*] --> ContextAnalysis : Analyze Surrounding Context
        ContextAnalysis --> ScenePresence : Check Scene Context
        ScenePresence --> SelectBestMatch : Choose Most Likely
        SelectBestMatch --> [*] : Character Resolved
    }
    
    state CreateNewCharacter {
        [*] --> ExtractCharacterInfo : Gather Character Data
        ExtractCharacterInfo --> CreateRecord : Add to Database
        CreateRecord --> InitializeProfile : Set Up Profile
        InitializeProfile --> [*] : Character Created
    }
    
    DisambiguateCharacters --> AnalyzeRole : Character Resolved
    CreateNewCharacter --> AnalyzeRole : New Character Ready
    
    state AnalyzeRole {
        [*] --> ParseDialogueStructure : Analyze Text Structure
        
        ParseDialogueStructure --> IdentifySpeakerTags : Look for "said X"
        ParseDialogueStructure --> AnalyzeQuotePosition : Check Quote Placement
        ParseDialogueStructure --> ExamineAddressing : Look for "Hey X"
        
        IdentifySpeakerTags --> SpeakerTagFound : Tag Indicates Speaker
        IdentifySpeakerTags --> NoSpeakerTag : No Clear Tag
        
        AnalyzeQuotePosition --> NameAfterQuote : Name follows quote
        AnalyzeQuotePosition --> NameInQuote : Name within quote
        AnalyzeQuotePosition --> NameBeforeQuote : Name precedes quote
        
        ExamineAddressing --> DirectAddress : "Hey [Name]"
        ExamineAddressing --> NoDirectAddress : No Addressing Found
        
        SpeakerTagFound --> ConfirmSpeaker : High Confidence Speaker
        NameAfterQuote --> ConfirmSpeaker : Likely Speaker
        NameBeforeQuote --> ConfirmSpeaker : Possible Speaker
        
        NameInQuote --> ConfirmAddressee : Likely Addressee
        DirectAddress --> ConfirmAddressee : Clear Addressee
        
        NoSpeakerTag --> ContextualAnalysis : Need Context
        NoDirectAddress --> ContextualAnalysis : Need Context
        
        ContextualAnalysis --> InferFromContext : Use Conversation Flow
        InferFromContext --> ProbableSpeaker : Context Suggests Speaker
        InferFromContext --> ProbableAddressee : Context Suggests Addressee
        InferFromContext --> AmbiguousRole : Role Unclear
        
        ConfirmSpeaker --> [*] : Speaker Identified
        ConfirmAddressee --> [*] : Addressee Identified
        ProbableSpeaker --> [*] : Speaker Probable
        ProbableAddressee --> [*] : Addressee Probable
        AmbiguousRole --> [*] : Role Ambiguous
    }
    
    AnalyzeRole --> UpdateAssociations : Create Character-Text Links
    
    state UpdateAssociations {
        [*] --> CreateTextSegmentLink : Link Character to Text
        CreateTextSegmentLink --> UpdateCharacterStats : Update Statistics
        UpdateCharacterStats --> UpdateCharacterProfile : Enhance Profile
        UpdateCharacterProfile --> [*] : Associations Updated
    }
    
    UpdateAssociations --> [*] : Attribution Complete
```

## Character Database Management FSM

```mermaid
stateDiagram-v2
    [*] --> DatabaseRequest : Incoming Database Operation
    
    DatabaseRequest --> RequestType : Determine Operation Type
    
    state RequestType {
        [*] --> operation_type
        operation_type --> CreateCharacter : New Character Request
        operation_type --> UpdateCharacter : Update Character Request
        operation_type --> SearchCharacter : Character Search Request
        operation_type --> DeleteCharacter : Delete Character Request
    }
    
    CreateCharacter --> ValidateCharacterData : Check Input Data
    UpdateCharacter --> ValidateUpdateData : Check Update Data
    SearchCharacter --> ExecuteSearch : Perform Search
    DeleteCharacter --> ValidateDeleteRequest : Check Delete Permissions
    
    state ValidateCharacterData {
        [*] --> CheckRequiredFields : Validate Required Data
        CheckRequiredFields --> NameValidation : Check Name Format
        NameValidation --> DuplicateCheck : Check for Duplicates
        DuplicateCheck --> ValidationPassed : Data Valid
        DuplicateCheck --> DuplicateFound : Duplicate Detected
        
        ValidationPassed --> [*] : Validation Success
        DuplicateFound --> [*] : Validation Failed
    }
    
    state ValidateUpdateData {
        [*] --> CheckCharacterExists : Verify Character ID
        CheckCharacterExists --> CharacterExists : Character Found
        CheckCharacterExists --> CharacterNotFound : Character Missing
        
        CharacterExists --> ValidateChanges : Check Update Data
        ValidateChanges --> UpdateValid : Changes Valid
        ValidateChanges --> UpdateInvalid : Invalid Changes
        
        CharacterNotFound --> [*] : Update Failed
        UpdateValid --> [*] : Update Ready
        UpdateInvalid --> [*] : Update Failed
    }
    
    state ExecuteSearch {
        [*] --> PrepareQuery : Build Search Query
        PrepareQuery --> RunQuery : Execute Database Query
        RunQuery --> ProcessResults : Process Query Results
        ProcessResults --> [*] : Search Complete
    }
    
    ValidateCharacterData --> ExecuteCreate : Create Character Record
    ValidateUpdateData --> ExecuteUpdate : Update Character Record
    ExecuteSearch --> ReturnResults : Return Search Results
    ValidateDeleteRequest --> ExecuteDelete : Delete Character Record
    
    state ExecuteCreate {
        [*] --> StartTransaction : Begin Database Transaction
        StartTransaction --> InsertCharacter : Insert Character Record
        InsertCharacter --> InitializeProfile : Create Initial Profile
        InitializeProfile --> CreateIndexes : Update Search Indexes
        CreateIndexes --> CommitTransaction : Commit Changes
        CommitTransaction --> [*] : Character Created
    }
    
    state ExecuteUpdate {
        [*] --> StartUpdateTransaction : Begin Update Transaction
        StartUpdateTransaction --> UpdateCharacterRecord : Modify Character Data
        UpdateCharacterRecord --> UpdateProfile : Update Profile Data
        UpdateProfile --> UpdateIndexes : Refresh Indexes
        UpdateIndexes --> CommitUpdate : Commit Changes
        CommitUpdate --> [*] : Update Complete
    }
    
    ExecuteCreate --> DatabaseOperationComplete : Operation Success
    ExecuteUpdate --> DatabaseOperationComplete : Operation Success
    ReturnResults --> DatabaseOperationComplete : Operation Success
    ExecuteDelete --> DatabaseOperationComplete : Operation Success
    
    DatabaseOperationComplete --> [*] : Database Operation Done
```

## Error Handling FSM

```mermaid
stateDiagram-v2
    [*] --> NormalProcessing : System Operating
    
    NormalProcessing --> ErrorDetected : Error Occurs
    
    state ErrorDetected {
        [*] --> ClassifyError : Determine Error Type
        
        ClassifyError --> DatabaseError : Database Connection Lost
        ClassifyError --> AIServiceError : AI Service Unavailable
        ClassifyError --> ValidationError : Data Validation Failed
        ClassifyError --> TimeoutError : Processing Timeout
        ClassifyError --> UnknownError : Unclassified Error
    }
    
    DatabaseError --> DatabaseRecovery : Attempt Database Recovery
    AIServiceError --> AIRecovery : Attempt AI Service Recovery
    ValidationError --> ValidationRecovery : Handle Validation Error
    TimeoutError --> TimeoutRecovery : Handle Timeout
    UnknownError --> GenericRecovery : Generic Error Handling
    
    state DatabaseRecovery {
        [*] --> CheckConnection : Test Database Connection
        CheckConnection --> ConnectionOK : Connection Restored
        CheckConnection --> ConnectionFailed : Connection Still Down
        
        ConnectionOK --> RetryOperation : Retry Failed Operation
        ConnectionFailed --> WaitAndRetry : Wait Before Retry
        
        RetryOperation --> OperationSuccess : Operation Succeeded
        RetryOperation --> OperationFailed : Operation Still Fails
        
        WaitAndRetry --> CheckConnection : Test Connection Again
        
        OperationSuccess --> [*] : Recovery Complete
        OperationFailed --> [*] : Recovery Failed
    }
    
    state AIRecovery {
        [*] --> CheckAIService : Test AI Service
        CheckAIService --> AIServiceOK : Service Available
        CheckAIService --> AIServiceDown : Service Unavailable
        
        AIServiceOK --> RetryAIOperation : Retry AI Request
        AIServiceDown --> UseFallback : Use Heuristic Fallback
        
        RetryAIOperation --> AISuccess : AI Request Succeeded
        RetryAIOperation --> AIStillFailed : AI Still Failing
        
        UseFallback --> FallbackComplete : Fallback Used
        
        AISuccess --> [*] : Recovery Complete
        AIStillFailed --> UseFallback : Fall Back to Heuristics
        FallbackComplete --> [*] : Recovery with Fallback
    }
    
    state ValidationRecovery {
        [*] --> AnalyzeValidationFailure : Examine Failed Data
        AnalyzeValidationFailure --> DataCorrectable : Data Can Be Fixed
        AnalyzeValidationFailure --> DataUncorrectable : Data Cannot Be Fixed
        
        DataCorrectable --> CorrectData : Apply Data Corrections
        CorrectData --> RetryValidation : Re-validate Data
        
        RetryValidation --> ValidationPassed : Data Now Valid
        RetryValidation --> ValidationStillFailed : Still Invalid
        
        DataUncorrectable --> SkipRecord : Skip Invalid Record
        ValidationStillFailed --> SkipRecord : Cannot Correct
        
        ValidationPassed --> [*] : Recovery Complete
        SkipRecord --> [*] : Recovery with Skip
    }
    
    DatabaseRecovery --> EvaluateRecovery : Check Recovery Success
    AIRecovery --> EvaluateRecovery : Check Recovery Success
    ValidationRecovery --> EvaluateRecovery : Check Recovery Success
    TimeoutRecovery --> EvaluateRecovery : Check Recovery Success
    GenericRecovery --> EvaluateRecovery : Check Recovery Success
    
    state EvaluateRecovery {
        [*] --> recovery_evaluation
        recovery_evaluation --> RecoverySuccessful : Error Resolved
        recovery_evaluation --> RecoveryPartial : Partial Recovery
        recovery_evaluation --> RecoveryFailed : Recovery Failed
    }
    
    RecoverySuccessful --> NormalProcessing : Resume Normal Operation
    RecoveryPartial --> DegradedMode : Continue with Reduced Functionality
    RecoveryFailed --> SystemShutdown : Initiate Graceful Shutdown
    
    state DegradedMode {
        [*] --> ReducedFunctionality : Operating with Limitations
        ReducedFunctionality --> AttemptFullRecovery : Retry Full Recovery
        AttemptFullRecovery --> FullRecoverySuccess : Full Functionality Restored
        AttemptFullRecovery --> StillDegraded : Still in Degraded Mode
        
        FullRecoverySuccess --> [*] : Return to Normal
        StillDegraded --> ReducedFunctionality : Continue Degraded
    }
    
    DegradedMode --> NormalProcessing : Full Recovery Achieved
    
    SystemShutdown --> [*] : System Terminated
```

## State Transition Conditions

### Classification State Transitions

| From State | To State | Condition | Action |
|------------|----------|-----------|---------|
| SegmentReady | ClassifyingDialogue | Segment has text content | Initialize context window |
| HeuristicAnalysis | ClearDialogue | Quotes + dialogue tags detected | Set confidence > 0.9 |
| HeuristicAnalysis | RequiresAI | No clear patterns | Queue for AI processing |
| AIProcessing | AIComplete | LLM returns result | Store AI confidence score |
| DialogueClassified | AttributingSpeaker | Classification = dialogue/mixed | Extract character names |
| DialogueClassified | CollectingContext | Classification = narration | Analyze character mentions |

### Attribution State Transitions

| From State | To State | Condition | Action |
|------------|----------|-----------|---------|
| DatabaseLookup | CharacterFound | Exact/alias match found | Load character record |
| DatabaseLookup | NoCharacterMatch | No matches in database | Prepare character creation |
| AnalyzingRole | SpeakerIdentified | "said [Name]" pattern | Create speaker association |
| AnalyzingRole | AddresseeIdentified | "[Name]," within quotes | Create addressee association |
| AnalyzingRole | AmbiguousRole | Multiple role indicators | Store all possibilities |

### Database State Transitions

| From State | To State | Condition | Action |
|------------|----------|-----------|---------|
| ValidateCharacterData | ExecuteCreate | All validations pass | Begin database transaction |
| ValidateCharacterData | ValidationFailed | Required fields missing | Return validation errors |
| ExecuteCreate | DatabaseOperationComplete | Transaction commits successfully | Update indexes |
| ExecuteUpdate | DatabaseOperationComplete | Update transaction succeeds | Refresh character cache |

### Error Recovery Conditions

| Error Type | Recovery Action | Success Condition | Fallback Action |
|------------|----------------|-------------------|-----------------|
| Database Connection | Retry connection | Connection restored | Use local cache |
| AI Service Timeout | Retry with smaller batch | Response received | Use heuristic classification |
| Validation Failure | Correct data format | Data passes validation | Skip invalid record |
| Memory Exhaustion | Clear processing cache | Memory usage normal | Reduce batch size |

## Performance Considerations

### State Machine Optimization

1. **Batch State Transitions**: Group similar operations to reduce state machine overhead
2. **Parallel FSM Execution**: Run multiple FSMs concurrently for different segments
3. **State Caching**: Cache frequently accessed states to reduce computation
4. **Early Exit Conditions**: Implement fast paths for common scenarios

### Memory Management

1. **State Cleanup**: Ensure proper cleanup when exiting states
2. **Context Window Limits**: Restrict context window size to prevent memory bloat
3. **Profile Data Pruning**: Limit character profile data growth
4. **Error State Recovery**: Implement memory recovery in error states

This FSM specification provides comprehensive state management for the two-agent dialogue classification and speaker attribution system, ensuring robust and predictable operation under all conditions.
