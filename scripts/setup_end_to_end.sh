#!/bin/bash
# Setup script for LangFlow end-to-end components

set -e

echo "🚀 Setting up LangFlow End-to-End Components..."

# Define paths
REPO_ROOT="/home/jon/repos/audio-book-maker-lg"
LANGFLOW_COMPONENTS_DIR="$REPO_ROOT/src/abm/lf_components/audiobook"

# Ensure components directory exists
mkdir -p "$LANGFLOW_COMPONENTS_DIR"

echo "📁 Component Directory: $LANGFLOW_COMPONENTS_DIR"

# List all new components
echo "📝 Available Components:"
echo "  ✅ ABMEnhancedChapterLoader - Smart chapter loading and chunking"
echo "  ✅ ABMBlockIterator - Batch processing management" 
echo "  ✅ ABMResultsAggregator - Results collection and validation"
echo "  ✅ ABMDialogueClassifier - Agent 1 (existing)"
echo "  ✅ ABMSpeakerAttribution - Agent 2 (existing)"
echo "  ✅ ABMUtteranceJsonlWriter - JSONL output (existing)"

# Check if components exist
echo ""
echo "🔍 Checking Component Files:"

components=(
    "abm_enhanced_chapter_loader.py"
    "abm_chunk_iterator.py" 
    "abm_results_aggregator.py"
    "abm_dialogue_classifier.py"
    "abm_speaker_attribution.py"
    "abm_utterance_jsonl_writer.py"
)

for component in "${components[@]}"; do
    if [ -f "$LANGFLOW_COMPONENTS_DIR/$component" ]; then
        echo "  ✅ $component"
    else
        echo "  ❌ $component - MISSING"
    fi
done

# Check data directory
echo ""
echo "📚 Checking Data Directory:"
DATA_DIR="$REPO_ROOT/data/clean/mvs"

if [ -d "$DATA_DIR" ]; then
    echo "  ✅ Data directory exists: $DATA_DIR"
    
    if [ -f "$DATA_DIR/chapters.json" ]; then
        echo "  ✅ chapters.json found"
        
        # Get chapter count
        chapter_count=$(python3 -c "
import json
with open('$DATA_DIR/chapters.json') as f:
    data = json.load(f)
    print(len(data.get('chapters', [])))
" 2>/dev/null || echo "0")
        
        echo "  📖 Available chapters: $chapter_count"
    else
        echo "  ❌ chapters.json not found"
    fi
    
    if [ -f "$DATA_DIR/chapters_readable.txt" ]; then
        echo "  ✅ chapters_readable.txt found"
    else
        echo "  ❌ chapters_readable.txt not found"
    fi
else
    echo "  ❌ Data directory not found: $DATA_DIR"
fi

# Check database connection
echo ""
echo "💾 Checking Database Connection:"
if command -v docker-compose &> /dev/null; then
    if docker-compose ps db 2>/dev/null | grep -q "Up"; then
        echo "  ✅ PostgreSQL database is running"
        
        # Test connection
        if docker-compose exec -T db psql -U abm_user -d audiobook_maker -c "SELECT COUNT(*) FROM characters;" &>/dev/null; then
            echo "  ✅ Database connection successful"
        else
            echo "  ⚠️ Database running but connection failed"
        fi
    else
        echo "  ❌ PostgreSQL database is not running"
        echo "      Run: docker-compose up -d db"
    fi
else
    echo "  ⚠️ docker-compose not found, skipping database check"
fi

# Check LangFlow
echo ""
echo "🌊 LangFlow Setup:"
echo "  📍 Start LangFlow with: ./scripts/run_langflow.sh"
echo "  🌐 Access at: http://localhost:7860"
echo ""
echo "📋 Component Configuration:"
echo "  📖 Enhanced Chapter Loader:"
echo "    - book_name: mvs"
echo "    - chapter_index: 1"
echo "    - base_data_dir: /home/jon/repos/audio-book-maker-lg/data/clean"
echo ""
echo "  🎭 Dialogue Classifier:"  
echo "    - classification_method: hybrid"
echo "    - confidence_threshold: 0.8"
echo ""
echo "  👥 Speaker Attribution:"
echo "    - attribution_method: comprehensive"
echo "    - confidence_threshold: 0.6"
echo "    - create_new_characters: true"
echo ""

# Data access setup
echo "🔗 Data Access Setup:"
echo "  Option 1 (Recommended): Use absolute paths in components"
echo "  Option 2: Create symbolic link:"
echo "    ln -s /home/jon/repos/audio-book-maker-lg/data ~/.langflow/audiobook_data"
echo ""

# Connection diagram reminder
echo "📊 Connection Diagram:"
echo "  View: temp/langflow-end-to-end-connections.mmd"
echo "  Flow: Enhanced Loader → Iterator → Agent1 → Agent2 → Aggregator → JSONL Writer"
echo ""

echo "🎉 Setup complete! Ready for end-to-end processing."
echo ""
echo "🚀 Next Steps:"
echo "  1. Start LangFlow: ./scripts/run_langflow.sh"
echo "  2. Load components in LangFlow UI"
echo "  3. Follow connection diagram in temp/langflow-end-to-end-connections.mmd"
echo "  4. Process Chapter 1 of MVS book"
