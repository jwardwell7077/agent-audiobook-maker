# Mermaid Test File

Testing different Mermaid syntax variations to see what renders on GitHub.

## Test 1: Basic Flowchart (No Emoji)

```mermaid
flowchart TD
    A[Start] --> B[Process]
    B --> C[End]
```

## Test 2: Flowchart with Simple Text Labels

```mermaid
flowchart LR
    PDF[PDF Files] --> Text[Text Processing]
    Text --> JSON[JSON Output]
```

## Test 3: Sequence Diagram

```mermaid
sequenceDiagram
    participant User
    participant System
    User->>System: Request
    System->>User: Response
```

## Test 4: Graph with Subgraphs (Simple)

```mermaid
graph TB
    subgraph Input
        A[File A]
        B[File B]
    end
    subgraph Output
        C[Result C]
    end
    A --> C
    B --> C
```

## Test 5: State Diagram

```mermaid
stateDiagram-v2
    [*] --> Idle
    Idle --> Processing
    Processing --> Complete
    Complete --> [*]
```

## Test 6: Class Diagram

```mermaid
classDiagram
    class Animal {
        +name: string
        +makeSound()
    }
    class Dog {
        +breed: string
        +bark()
    }
    Animal <|-- Dog
```

## Test 7: With Quotes in Labels

```mermaid
flowchart TD
    A["Start Process"] --> B["Process Data"]
    B --> C["End Process"]
```

## Test 8: Complex Flowchart (Our Architecture Style)

```mermaid
flowchart LR
    subgraph Dev["Local Development"]
        CLI["CLI Tools"]
        PDF[("PDF Input")]
        TXT[("Text Output")]
    end
    
    subgraph Process["Processing"]
        Parser["Text Parser"]
        Annotate["Annotation Engine"]
    end
    
    CLI --> PDF
    PDF --> TXT
    TXT --> Parser
    Parser --> Annotate
```

---

**Test Results**: Check which of these render properly on GitHub and which show "Error rendering embedded code".
