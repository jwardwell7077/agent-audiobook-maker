#!/bin/bash
# Environment Validation Script for ABM Two-Agent System
# This script checks that all required environment variables and services are properly configured

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() { echo -e "${BLUE}$1${NC}"; }
print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }

echo "🧪 ABM Two-Agent System - Environment Validation"
echo "================================================="
echo ""

# Load environment variables
if [ -f .env ]; then
    source .env
    print_success "Environment file (.env) loaded"
else
    print_error "No .env file found - please create one from .env.example"
    exit 1
fi

# Check required environment variables
print_status "🔍 Checking environment variables..."

required_vars=(
    "DATABASE_URL"
    "OLLAMA_BASE_URL" 
    "OLLAMA_PRIMARY_MODEL"
    "DIALOGUE_CLASSIFIER_USE_AI_FALLBACK"
    "DATA_CHARACTERS_PATH"
)

missing_vars=()
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        missing_vars+=("$var")
        print_error "Missing required variable: $var"
    else
        print_success "$var = ${!var}"
    fi
done

if [ ${#missing_vars[@]} -gt 0 ]; then
    print_error "Missing ${#missing_vars[@]} required environment variables"
    exit 1
fi

# Check directory structure
print_status "📁 Checking directory structure..."
required_dirs=(
    "data"
    "data/characters" 
    "data/annotations"
    "data/clean"
    "logs"
    "database/init"
)

for dir in "${required_dirs[@]}"; do
    if [ ! -d "$dir" ]; then
        print_warning "Creating missing directory: $dir"
        mkdir -p "$dir"
    fi
    print_success "Directory exists: $dir"
done

# Test database connection (if PostgreSQL is running)
print_status "🗄️  Testing database connection..."
if command -v psql &> /dev/null; then
    if psql "$DATABASE_URL" -c "SELECT 1;" &> /dev/null; then
        print_success "Database connection successful"
        
        # Check if tables exist
        table_count=$(psql "$DATABASE_URL" -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';" 2>/dev/null | xargs)
        if [ "$table_count" -gt 0 ]; then
            print_success "Database schema initialized ($table_count tables found)"
        else
            print_warning "Database connected but no tables found - may need schema initialization"
        fi
    else
        print_warning "Database connection failed - make sure PostgreSQL is running"
        print_status "   Start with: docker-compose up -d db"
    fi
else
    print_warning "psql not found - cannot test database connection"
fi

# Test Ollama connection
print_status "🤖 Testing Ollama connection..."
if command -v curl &> /dev/null; then
    if curl -sf "${OLLAMA_BASE_URL}/api/tags" &> /dev/null; then
        print_success "Ollama API accessible"
        
        # Check if required models are available
        models=$(curl -s "${OLLAMA_BASE_URL}/api/tags" | grep -o '"name":"[^"]*"' | cut -d'"' -f4 || echo "")
        if echo "$models" | grep -q "$OLLAMA_PRIMARY_MODEL"; then
            print_success "Primary model available: $OLLAMA_PRIMARY_MODEL"
        else
            print_warning "Primary model not found: $OLLAMA_PRIMARY_MODEL"
            print_status "   Install with: ollama pull $OLLAMA_PRIMARY_MODEL"
        fi
    else
        print_warning "Ollama API not accessible at $OLLAMA_BASE_URL"
        print_status "   Start Ollama with: ollama serve"
    fi
else
    print_warning "curl not found - cannot test Ollama connection"
fi

# Summary
echo ""
print_status "📋 Environment Summary:"
echo "  Database: $DATABASE_URL"
echo "  Ollama: $OLLAMA_BASE_URL"  
echo "  Primary Model: $OLLAMA_PRIMARY_MODEL"
echo "  Data Path: $DATA_CHARACTERS_PATH"
echo "  Debug Mode: $DEBUG_MODE"
echo ""

if [ ${#missing_vars[@]} -eq 0 ]; then
    print_success "🎉 Environment validation complete - ready for two-agent system!"
    echo ""
    print_status "Next steps:"
    echo "  1. Start PostgreSQL: docker-compose up -d db"
    echo "  2. Start Ollama: ollama serve"
    echo "  3. Pull models: ollama pull $OLLAMA_PRIMARY_MODEL" 
    echo "  4. Run agent implementations"
else
    print_error "Environment validation failed - please fix missing variables"
    exit 1
fi
