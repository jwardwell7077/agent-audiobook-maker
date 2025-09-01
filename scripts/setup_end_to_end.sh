#!/bin/bash
# Setup script for LangFlow end-to-end components (Unified)

set -e

echo "🚀 Setting up LangFlow End-to-End Components..."

# Define paths
REPO_ROOT="/home/jon/repos/agent-audiobook-maker"
LANGFLOW_COMPONENTS_DIR="$REPO_ROOT/src/abm/lf_components/audiobook"

# Ensure components directory exists
mkdir -p "$LANGFLOW_COMPONENTS_DIR"
echo "📁 Component Directory: $LANGFLOW_COMPONENTS_DIR"

# List components
echo "📝 Available Components:"
echo "  ✅ ABMChapterLoader - Unified loader (chapters/chapter/blocks)"
echo "  ✅ ABMBlockIterator - Batch processing management"
echo "  ✅ ABMDialogueClassifier - Agent 1"
echo "  ✅ ABMSpeakerAttribution - Agent 2"
echo "  ✅ ABMResultsAggregator - Results collection and validation"
echo "  ✅ ABM Results → Utterances - Normalizer"
echo "  ✅ ABMAggregatedJsonlWriter - Aggregated JSONL output"
echo "  ✅ ABMCastingDirector - Voice assignment"
echo "  ✅ ABMCharacterDataCollector - Stats/collection"

# Check component files
echo ""
echo "🔍 Checking Component Files:"
components=(
    "abm_chapter_loader.py"
    "abm_block_iterator.py"
    "abm_dialogue_classifier.py"
    "abm_speaker_attribution.py"
    "abm_results_aggregator.py"
    "abm_results_to_utterances.py"
    "abm_aggregated_jsonl_writer.py"
    "abm_casting_director.py"
    "abm_character_data_collector.py"
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
        chapter_count=$(python3 - <<'PY'
import json,sys
try:
        with open(sys.argv[1]) as f:
                data = json.load(f)
        print(len(data.get('chapters', [])))
except Exception:
        print(0)
PY
"$DATA_DIR/chapters.json")
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

# Check database connection (optional)
echo ""
echo "💾 Checking Database Connection:"
if command -v docker-compose >/dev/null 2>&1; then
    if docker-compose ps db 2>/dev/null | grep -q "Up"; then
        echo "  ✅ PostgreSQL database is running"
        if docker-compose exec -T db psql -U abm_user -d audiobook_maker -c "SELECT 1;" &>/dev/null; then
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

# LangFlow tips
echo ""
echo "🌊 LangFlow Setup:"
echo "  📍 Start LangFlow with: ./scripts/run_langflow.sh"
echo "  🌐 Access at: http://localhost:7860"
echo ""
echo "📋 Component Configuration (Loader):"
echo "  📖 ABM Chapter Loader:"
echo "    - book_name: mvs"
echo "    - chapter_index: 1"
echo "    - base_data_dir: $REPO_ROOT/data/clean"
echo "    - context_sentences: 2"
echo ""

# Data access setup
echo "🔗 Data Access Setup:"
echo "  Option 1 (Recommended): Use absolute paths in components"
echo "  Option 2: Create symbolic link:"
echo "    ln -s $REPO_ROOT/data ~/.langflow/audiobook_data"
echo ""

# Connection diagram reminder
echo "📊 Connection Diagram:"
echo "  View: docs/diagrams/langflow-two-agent-pipeline.mmd"
echo "  Flow: ABM Chapter Loader → Iterator → Agent1 → Agent2 → Aggregator → Results→Utterances → Aggregated JSONL Writer"
echo ""

echo "🎉 Setup complete! Ready for end-to-end processing."
echo ""
echo "🚀 Next Steps:"
echo "  1. Start LangFlow: ./scripts/run_langflow.sh"
echo "  2. Load components in LangFlow UI"
echo "  3. Import flow examples/langflow/abm_full_pipeline.v15.json (optional)"
echo "  4. Process Chapter 1 of MVS book"
