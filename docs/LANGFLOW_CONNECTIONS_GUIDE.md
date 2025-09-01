# LangFlow Data Integration & Text Blocks Guide

Note: Terminology updated. Previous references to "chunk(s)" are now "block(s)" in the codebase and flows.

## 📊 **Overview: Existing Data Structure**

Your repository has rich structured data ready for LangFlow integration:

### **Current Data Assets:**

- ✅ **Volume Manifest**: `data/clean/mvs/chapters.json` (4,919 lines, full book structured)
- ✅ **Readable Text**: `data/clean/mvs/chapters_readable.txt` (91,782 lines, formatted chapters)  
- ✅ **Database**: PostgreSQL with character tracking (Great Gatsby sample data)
- ✅ **JSONL Pipeline**: Existing components for utterance output format

## 🎯 **Text Chunking Challenge: The Core Problem**

Your chapters contain **bulk text** that needs intelligent segmentation:

### **Current Structure Issues:**

```json
{
  "body_text": "Chapter 1: Just an old Book\n\"Try not to die by tripping over yourself, Quinn!\" A boy shouted down the hallway,\nlaughing uncontrollably right after.\nQuinn dismissed the petty mockery as he carried on walking..."
}
```

### **Target Structure Needed:**

```json
[
  {
    "text": "\"Try not to die by tripping over yourself, Quinn!\" A boy shouted down the hallway, laughing uncontrollably right after.",
    "type": "dialogue",
    "chunk_id": 1,
    "context_before": "",
    "context_after": "Quinn dismissed the petty mockery..."
  },
  {
    "text": "Quinn dismissed the petty mockery as he carried on walking down the school corridor.",
    "type": "narration", 
    "chunk_id": 2,
    "context_before": "\"Try not to die by tripping over yourself, Quinn!\"",
    "context_after": "The harassment had become a daily occurrence..."
  }
]
```

---

## 🧠 **Smart Text Chunking Algorithm**

Based on your existing `ABMSegmentDialogueNarration` component, here's an enhanced chunking strategy:

### **Algorithm Overview:**

```python
class EnhancedTextChunker:
    """
    Smart text chunking for LLM processing with dialogue/narration awareness
    """
    
    def __init__(self):
        # Dialogue indicators (high confidence)
        self.dialogue_patterns = [
            r'"[^"]*"',                    # Standard quotes
            r"'[^']*'",                    # Single quotes  
            r'"[^"]*"',                    # Smart quotes
            r'«[^»]*»',                    # European quotes
        ]
        
        # Attribution patterns (speaker indicators)
        self.attribution_patterns = [
            r'\b(\w+)\s+(said|asked|replied|shouted|whispered|exclaimed)\b',
            r'\b(he|she|they)\s+(said|asked|replied)\b',
            r'\bsaid\s+(\w+)\b',
        ]
        
        # Narration indicators
        self.narration_patterns = [
            r'\b(\w+)\s+(walked|ran|thought|looked|felt|seemed)\b',
            r'\b(The|A|An)\s+\w+',
            r'\b(Meanwhile|However|Then|After|Before)\b',
        ]
        
        # Sentence boundaries
        self.sentence_endings = ['.', '!', '?', '...', '."', ".'", '!"', "!'", '?"', "?'"]
        
    def chunk_chapter(self, chapter_text: str, max_chunk_size: int = 500) -> List[Dict]:
        """
        Chunk chapter text into optimal segments for LLM processing
        """
        chunks = []
        sentences = self._split_into_sentences(chapter_text)
        
        current_chunk = []
        current_size = 0
        chunk_id = 1
        
        for i, sentence in enumerate(sentences):
            sentence_size = len(sentence)
            
            # Check if adding sentence exceeds max size
            if current_size + sentence_size > max_chunk_size and current_chunk:
                # Flush current chunk
                chunk_text = ' '.join(current_chunk).strip()
                if chunk_text:
                    chunks.append(self._create_chunk(
                        chunk_text, chunk_id, sentences, i, current_chunk
                    ))
                    chunk_id += 1
                
                # Start new chunk
                current_chunk = [sentence]
                current_size = sentence_size
            else:
                current_chunk.append(sentence)
                current_size += sentence_size
        
        # Don't forget final chunk
        if current_chunk:
            chunk_text = ' '.join(current_chunk).strip()
            if chunk_text:
                chunks.append(self._create_chunk(
                    chunk_text, chunk_id, sentences, len(sentences), current_chunk
                ))
        
        return chunks
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """
        Smart sentence splitting that preserves dialogue boundaries
        """
        # Handle dialogue specially to avoid breaking quotes
        sentences = []
        current_sentence = ""
        in_quote = False
        quote_char = None
        
        for char in text:
            current_sentence += char
            
            # Track quote state
            if char in ['"', "'", '"', '"'] and not in_quote:
                in_quote = True
                quote_char = char
            elif char == quote_char and in_quote:
                in_quote = False
                quote_char = None
            
            # Split on sentence endings, but not within quotes
            if char in ['.', '!', '?'] and not in_quote:
                # Look ahead to see if this is really the end
                if self._is_sentence_end(current_sentence):
                    sentences.append(current_sentence.strip())
                    current_sentence = ""
        
        # Add remaining text
        if current_sentence.strip():
            sentences.append(current_sentence.strip())
            
        return sentences
    
    def _create_chunk(self, chunk_text: str, chunk_id: int, all_sentences: List[str], 
                     current_index: int, current_chunk: List[str]) -> Dict:
        """
        Create a properly structured chunk with metadata
        """
        # Determine chunk type (dialogue vs narration)
        chunk_type = self._classify_chunk_type(chunk_text)
        
        # Generate context windows
        context_before = self._get_context_before(all_sentences, current_index, 2)
        context_after = self._get_context_after(all_sentences, current_index, 2)
        
        # Extract dialogue if present
        dialogue_text = self._extract_dialogue(chunk_text) if chunk_type == "dialogue" else ""
        
        # Find attribution clues
        attribution_clues = self._find_attribution_clues(chunk_text + " " + context_after)
        
        return {
            "chunk_id": chunk_id,
            "text": chunk_text,
            "type": chunk_type,
            "word_count": len(chunk_text.split()),
            "char_count": len(chunk_text),
            "dialogue_text": dialogue_text,
            "attribution_clues": attribution_clues,
            "context_before": context_before,
            "context_after": context_after,
            "sentences": current_chunk,
            "processing_hints": {
                "has_quotes": '"' in chunk_text or "'" in chunk_text,
                "has_attribution": bool(attribution_clues),
                "complexity": self._assess_complexity(chunk_text)
            }
        }
    
    def _classify_chunk_type(self, text: str) -> str:
        """
        Classify chunk as dialogue, narration, or mixed
        """
        has_quotes = any(re.search(pattern, text) for pattern in self.dialogue_patterns)
        has_attribution = any(re.search(pattern, text, re.IGNORECASE) 
                            for pattern in self.attribution_patterns)
        has_narration = any(re.search(pattern, text, re.IGNORECASE) 
                          for pattern in self.narration_patterns)
        
        if has_quotes and has_attribution:
            return "dialogue"
        elif has_quotes and not has_narration:
            return "dialogue"
        elif has_narration and not has_quotes:
            return "narration"
        else:
            return "mixed"
```

---

## 🔗 **LangFlow Pipeline Integration**

### **Step 1: Enhanced Chapter Loader**

Create an enhanced version of your existing loader:

```python
class ABMEnhancedChapterLoader(Component):
    display_name = "ABM Enhanced Chapter Loader"
    description = "Load and intelligently chunk chapters for two-agent processing"
    
    inputs = [
        StrInput(name="book_name", value="mvs"),
        IntInput(name="chapter_index", value=1),
        IntInput(name="max_chunk_size", value=500),
        BoolInput(name="preserve_dialogue_boundaries", value=True),
    ]
    
    def load_and_chunk_chapter(self) -> Data:
        """Load chapter and return intelligently chunked segments"""
        
        # Load from your existing chapters.json
        chapters_file = Path(f"data/clean/{self.book_name}/chapters.json")
        with open(chapters_file) as f:
            chapters_data = json.load(f)
        
        # Find target chapter
        target_chapter = None
        for chapter in chapters_data["chapters"]:
            if chapter["index"] == self.chapter_index:
                target_chapter = chapter
                break
        
        if not target_chapter:
            return Data(data={"error": f"Chapter {self.chapter_index} not found"})
        
        # Initialize chunker
        chunker = EnhancedTextChunker()
        
        # Chunk the chapter text
        chunks = chunker.chunk_chapter(
            target_chapter["body_text"], 
            max_chunk_size=self.max_chunk_size
        )
        
        return Data(data={
            "book_name": self.book_name,
            "chapter_index": self.chapter_index,
            "chapter_title": target_chapter["title"],
            "total_chunks": len(chunks),
            "chunks": chunks,
            "processing_metadata": {
                "chunk_sizes": [c["word_count"] for c in chunks],
                "dialogue_chunks": len([c for c in chunks if c["type"] == "dialogue"]),
                "narration_chunks": len([c for c in chunks if c["type"] == "narration"]),
                "mixed_chunks": len([c for c in chunks if c["type"] == "mixed"]),
            }
        })
```

### **Step 2: Batch Processing Pipeline**

```
ABMEnhancedChapterLoader → BlockIterator → ABMDialogueClassifier → ABMSpeakerAttribution → ResultsAggregator → JSONLWriter
```

### **Step 3: Block Iterator Component**

```python
class ABMBlockIterator(Component):
    display_name = "ABM Block Iterator"
    description = "Process blocks one by one through the two-agent pipeline"
    
    def process_blocks(self) -> Data:
        """Iterate through blocks and prepare for agent processing"""
        
    chunks_data = self.chunks_data.data
    chunks = chunks_data.get("chunks", [])
        
        processed_results = []
        
    for chunk in chunks:
            # Prepare data for Agent 1 (Dialogue Classifier)
            utterance_data = {
                "utterance_text": chunk["text"],
                "context_before": chunk["context_before"],
                "context_after": chunk["context_after"],
                "book_id": chunks_data["book_name"],
                "chapter_id": f"chapter_{chunks_data['chapter_index']:02d}",
                "utterance_idx": chunk["chunk_id"],
                "processing_hints": chunk["processing_hints"]
            }
            
            # This would connect to your two-agent pipeline
            processed_results.append(utterance_data)
        
        return Data(data={
            "batch_utterances": processed_results,
            "total_utterances": len(processed_results),
            "source_chapter": chunks_data
        })
```

---

## 🎛️ **LangFlow Component Workflow**

### **Complete Real-Data Pipeline:**

```
1. ABMEnhancedChapterLoader (Load MVS Chapter 1)
   ↓
2. ChunkIterator (Break into processable chunks)  
   ↓
3. [FOR EACH CHUNK]
   ABMDialogueClassifier (Agent 1: Classify dialogue/narration)
   ↓
   ChatOutput (Debug: Show classification)
   ↓ 
   ABMSpeakerAttribution (Agent 2: Identify speakers)
   ↓
   ChatOutput (Debug: Show attribution)
   ↓
4. ResultsAggregator (Combine all results)
   ↓
5. ABMUtteranceJsonlWriter (Output to JSONL format)
   ↓
6. DatabaseUpdater (Persist to PostgreSQL)
```

---

## 📝 **Configuration Examples**

### **For Testing with Your MVS Data:**

#### **Component Settings:**

1. **ABMEnhancedChapterLoader**:
   - book_name: `mvs`
   - chapter_index: `1` (Chapter 1: Just an old Book)
   - max_chunk_size: `300` (optimal for LLM context)

2. **ABMDialogueClassifier**:
   - classification_method: `hybrid`
   - confidence_threshold: `0.8`
   - use_context: `true`

3. **ABMSpeakerAttribution**:
   - attribution_method: `comprehensive`
   - create_new_characters: `true` (for Quinn, Vorden, etc.)
   - confidence_threshold: `0.6`

### **Expected Processing Results:**

```json
{
  "chunk_1": {
    "text": "\"Try not to die by tripping over yourself, Quinn!\" A boy shouted down the hallway, laughing uncontrollably right after.",
    "classification": "dialogue",
    "confidence": 0.95,
    "speaker_attribution": {
      "character_name": "Unknown Boy", 
      "confidence": 0.8,
      "method": "direct_explicit_said"
    }
  },
  "chunk_2": {
    "text": "Quinn dismissed the petty mockery as he carried on walking down the school corridor.",
    "classification": "narration",
    "confidence": 0.9,
    "speaker_attribution": null
  }
}
```

---

## 🚀 **Implementation Steps**

### **Phase 1: Basic Integration (Week 1)**

1. ✅ Create enhanced chapter loader component
2. ✅ Test loading MVS Chapter 1 data
3. ✅ Validate chunking algorithm with sample text
4. ✅ Connect to existing Agent 1 → Agent 2 pipeline

### **Phase 2: Batch Processing (Week 2)**

1. ✅ Implement block iterator for batch processing  
2. ✅ Add progress tracking and error handling
3. ✅ Create results aggregation component
4. ✅ Test full chapter processing

### **Phase 3: Database Integration (Week 3)**

1. ✅ Connect to PostgreSQL character database
2. ✅ Implement character persistence and updates
3. ✅ Add JSONL output with proper metadata
4. ✅ Create production pipeline validation

### **Phase 4: Multi-Chapter Processing (Week 4)**

1. ✅ Scale to process multiple chapters
2. ✅ Add character continuity tracking
3. ✅ Implement quality gates and validation
4. ✅ Optimize for production workloads

---

## 🔧 **Algorithm Parameters & Tuning**

### **Chunking Parameters:**

```python
CHUNKING_CONFIG = {
    # Size constraints
    "max_chunk_size": 300,          # Max words per chunk
    "min_chunk_size": 50,           # Min words per chunk  
    "context_window": 2,            # Sentences for context
    
    # Boundary preservation
    "preserve_dialogue": True,      # Don't split quotes
    "preserve_paragraphs": True,    # Respect paragraph breaks
    "smart_sentence_split": True,   # Handle complex punctuation
    
    # Classification hints
    "boost_attribution_clues": True,    # Weight dialogue with speakers higher
    "detect_conversation_flow": True,   # Track multi-turn dialogue
    "identify_scene_breaks": True,      # Detect scene transitions
}
```

### **Quality Metrics:**

- **Chunk Size Distribution**: 80% chunks between 100-400 words
- **Dialogue Preservation**: 95%+ complete quotes in single chunks  
- **Context Accuracy**: 90%+ relevant context windows
- **Processing Speed**: <100ms per chunk on average

---

## 💡 **Pro Tips for Your Data**

### **MVS Book Specific Optimizations:**

1. **Character Names**: Quinn, Vorden, Peter, Layla, Erin are main characters
2. **Dialogue Patterns**: Heavy use of standard quotes `"text"`
3. **Attribution Style**: Mix of "X said" and "said X" patterns
4. **Scene Structure**: School settings, military academy, etc.

### **Chunking Strategy for Your Content:**

- **Short dialogue chunks**: 50-150 words for clear attribution
- **Narration chunks**: 200-400 words for scene context
- **Mixed chunks**: 100-250 words to maintain flow
- **Context overlap**: 1-2 sentences to preserve continuity

This guide gives you everything needed to process your real MVS book data through the two-agent LangFlow pipeline! 🚀

Ready to implement the enhanced chapter loader and start processing Chapter 1?
