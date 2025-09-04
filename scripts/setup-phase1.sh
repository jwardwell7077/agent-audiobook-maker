#!/bin/bash
# ABM Setup - Phase 1: External Foundation Setup
# This script sets up all external infrastructure dependencies

set -e

echo "🚀 ABM Setup - Phase 1: External Foundation Setup"
echo "============================================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}$1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check prerequisites
print_status "🔍 Checking prerequisites..."

if ! command -v docker &> /dev/null; then
    print_error "Docker is required but not installed"
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    print_error "Docker Compose is required but not installed"
    exit 1
fi

print_success "Docker and Docker Compose are available"

# Create necessary directories
print_status "📁 Creating directory structure..."
mkdir -p data/characters
mkdir -p data/annotations
mkdir -p data/clean
mkdir -p logs
print_success "Directory structure created"

# Start core services (PostgreSQL)
print_status "🗄️  Starting PostgreSQL database..."
docker compose up -d db

# Wait for database to be healthy
print_status "⏳ Waiting for PostgreSQL to be ready..."
timeout=60
counter=0
while ! docker compose exec db pg_isready -U abm_user -d audiobook_maker &> /dev/null; do
    sleep 2
    counter=$((counter + 2))
    if [ $counter -ge $timeout ]; then
        print_error "PostgreSQL failed to start within $timeout seconds"
        docker compose logs db
        exit 1
    fi
    echo "   Waiting for PostgreSQL... (${counter}s/${timeout}s)"
done
print_success "PostgreSQL is ready and healthy"

# Verify database schema
print_status "🔍 Verifying database schema..."
TABLES=$(docker compose exec db psql -U abm_user -d audiobook_maker -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';")
if [ "${TABLES// /}" -gt 0 ]; then
    print_success "Database schema initialized successfully ($TABLES tables created)"
else
    print_error "Database schema initialization failed"
    exit 1
fi

# Start Ollama (optional, with profile)
print_status "🤖 Starting Ollama service..."
if docker compose --profile ollama up -d ollama; then
    print_success "Ollama service started"

    # Wait for Ollama to be ready
    print_status "⏳ Waiting for Ollama to initialize..."
    timeout=120
    counter=0
    while ! curl -sf http://localhost:11434/api/tags &> /dev/null; do
        sleep 5
        counter=$((counter + 5))
        if [ $counter -ge $timeout ]; then
            print_warning "Ollama initialization timeout - you may need to pull models manually"
            break
        fi
        echo "   Waiting for Ollama API... (${counter}s/${timeout}s)"
    done

    if [ $counter -lt $timeout ]; then
        print_success "Ollama is ready"

        # Run model setup
        print_status "📥 Setting up Ollama models..."
        if docker compose exec ollama /bin/bash -c "$(cat scripts/setup-ollama.sh)"; then
            print_success "Ollama models configured successfully"
        else
            print_warning "Ollama model setup encountered issues - you can run setup manually later"
        fi
    fi
else
    print_warning "Ollama service failed to start - continuing without it"
    print_warning "You can start Ollama later with: docker compose --profile ollama up -d"
fi

# Optional: Start pgAdmin
read -p "🔧 Do you want to start pgAdmin for database management? (y/n): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_status "🔧 Starting pgAdmin..."
    docker compose --profile admin up -d pgadmin
    print_success "pgAdmin started at http://localhost:8080"
    print_status "   Default login: admin@audiobook-maker.local / admin"
fi

# Show service status
print_status "📊 Service Status Summary:"
echo ""
docker compose ps

echo ""
print_success "🎉 Phase 1: External Foundation Setup Complete!"
echo ""
echo "📋 Infrastructure Ready:"
echo "  🗄️  PostgreSQL Database: localhost:5432"
echo "      - Database: audiobook_maker"
echo "      - User: abm_user"
echo "      - Schema: legacy tables created"
echo ""
if docker compose ps ollama | grep -q "Up"; then
    echo "  🤖 Ollama LLM Service: localhost:11434"
    echo "      - Models: llama3.2:3b, phi3:mini, dialogue-classifier"
    echo "      - Ready for AI fallback classification"
    echo ""
fi
if docker compose ps pgadmin | grep -q "Up"; then
    echo "  🔧 pgAdmin: http://localhost:8080"
    echo "      - Database management interface"
    echo ""
fi
echo "🚀 Ready for Phase 2: Agent Implementation!"
echo ""
echo "📚 Next Steps:"
echo "  1. Implement Agent 1: Dialogue Classifier"
echo "  2. Implement Agent 2: Speaker Attribution"
echo "  3. Test end-to-end workflow"
echo ""
print_status "Use 'docker compose logs [service]' to view service logs"
print_status "Use 'docker compose down' to stop all services"
