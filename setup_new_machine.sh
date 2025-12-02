#!/bin/bash
# Setup script for Mini-RAG on a new machine
# This script sets up the project dependencies and environment

set -e  # Exit on error

echo "=========================================="
echo "🔧 Mini-RAG Setup Script"
echo "=========================================="
echo ""

# Get the directory where the script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print colored output
print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "  → $1"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Step 1: Check for required dependencies
echo "Step 1: Checking dependencies..."
echo ""

MISSING_DEPS=0

if command_exists python3; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    print_success "Python 3 found: $PYTHON_VERSION"
else
    print_error "Python 3 not found. Please install Python 3.8+"
    MISSING_DEPS=1
fi

if command_exists node; then
    NODE_VERSION=$(node --version)
    print_success "Node.js found: $NODE_VERSION"
else
    print_error "Node.js not found. Please install Node.js 16+"
    MISSING_DEPS=1
fi

if command_exists npm; then
    NPM_VERSION=$(npm --version)
    print_success "npm found: $NPM_VERSION"
else
    print_error "npm not found. Please install npm"
    MISSING_DEPS=1
fi

# Check for PostgreSQL (optional but recommended)
if command_exists psql; then
    print_success "PostgreSQL client found"
    print_info "You can use a local PostgreSQL database or a remote one"
elif command_exists docker; then
    print_warning "PostgreSQL client not found, but Docker is available"
    print_info "You can use Docker Compose to run PostgreSQL"
else
    print_warning "PostgreSQL not found. You'll need to set up a database separately"
    print_info "Options: Install PostgreSQL locally, use Docker, or use a cloud database"
fi

if [ $MISSING_DEPS -eq 1 ]; then
    echo ""
    print_error "Missing required dependencies. Please install them and run this script again."
    exit 1
fi

echo ""
echo "Step 2: Setting up Python environment..."
echo ""

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    print_info "Creating Python virtual environment..."
    python3 -m venv venv
    print_success "Virtual environment created"
else
    print_success "Virtual environment already exists"
fi

# Activate virtual environment
print_info "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
print_info "Upgrading pip..."
pip install --upgrade pip --quiet

# Install Python dependencies
print_info "Installing Python dependencies (this may take a few minutes)..."
if pip install -r requirements.txt --quiet; then
    print_success "Python dependencies installed"
else
    print_error "Failed to install Python dependencies"
    exit 1
fi

echo ""
echo "Step 3: Setting up frontend..."
echo ""

# Install Node.js dependencies
cd frontend-react
print_info "Installing Node.js dependencies (this may take a few minutes)..."
if npm install --silent; then
    print_success "Node.js dependencies installed"
else
    print_error "Failed to install Node.js dependencies"
    exit 1
fi

# Build frontend
print_info "Building frontend..."
if npm run build; then
    print_success "Frontend built successfully"
else
    print_error "Failed to build frontend"
    exit 1
fi

cd ..

echo ""
echo "Step 4: Setting up environment file..."
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    if [ -f "PRODUCTION_ENV_TEMPLATE" ]; then
        print_info "Creating .env from PRODUCTION_ENV_TEMPLATE..."
        cp PRODUCTION_ENV_TEMPLATE .env
        print_success ".env file created"
    elif [ -f "env.template" ]; then
        print_info "Creating .env from env.template..."
        cp env.template .env
        print_success ".env file created"
    else
        print_warning "No template found. Creating basic .env file..."
        cat > .env << EOF
# Google OAuth Credentials
GOOGLE_CLIENT_ID=your-google-client-id-here
GOOGLE_CLIENT_SECRET=your-google-client-secret-here

# Secret key for JWT token signing
# Generate with: python3 -c "import secrets; print(secrets.token_urlsafe(32))"
SECRET_KEY=your-secret-key-here

# Database connection (optional - for user management and persistence)
# DATABASE_URL=postgresql://rag_user:password@localhost:5432/rag_brain

# Local development mode (bypasses authentication)
LOCAL_MODE=true
ALLOW_INSECURE_DEFAULTS=true

# OpenAI API Key (required for LLM functionality)
OPENAI_API_KEY=your-openai-api-key-here

# Anthropic API Key (optional - for Claude models)
# ANTHROPIC_API_KEY=your-anthropic-api-key-here
EOF
        print_success ".env file created"
    fi
    
    echo ""
    print_warning "IMPORTANT: You need to edit .env with your actual credentials:"
    print_info "  - Google OAuth credentials (if using Google login)"
    print_info "  - SECRET_KEY (generate a new one)"
    print_info "  - DATABASE_URL (if using PostgreSQL)"
    print_info "  - OPENAI_API_KEY (required for LLM features)"
    print_info "  - ANTHROPIC_API_KEY (optional, for Claude)"
    echo ""
    print_info "For local development, LOCAL_MODE=true is already set"
else
    print_success ".env file already exists"
fi

echo ""
echo "Step 5: Database setup..."
echo ""

# Check if DATABASE_URL is set in .env
if grep -q "^DATABASE_URL=" .env 2>/dev/null && ! grep -q "^DATABASE_URL=$" .env 2>/dev/null && ! grep -q "^#.*DATABASE_URL=" .env 2>/dev/null; then
    print_info "DATABASE_URL found in .env"
    
    # Check if we can connect (optional check)
    if command_exists psql; then
        print_info "You can initialize the database schema with:"
        print_info "  psql \$DATABASE_URL < db_schema.sql"
    fi
    
    if command_exists docker && [ -f "docker-compose.yml" ]; then
        print_info "Or use Docker Compose:"
        print_info "  docker-compose up -d"
        print_info "  docker exec -i mini-rag-db psql -U postgres -d rag_brain < db_schema.sql"
    fi
else
    print_warning "DATABASE_URL not configured in .env"
    print_info "For local development without a database, the app will use LOCAL_MODE"
    print_info "To set up a database later, edit .env and add DATABASE_URL"
fi

echo ""
echo "=========================================="
echo "✅ Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Edit .env file with your credentials:"
echo "   ${YELLOW}nano .env${NC}  (or use your preferred editor)"
echo ""
echo "2. (Optional) Set up database:"
echo "   - If using Docker: ${YELLOW}docker-compose up -d${NC}"
echo "   - Initialize schema: ${YELLOW}psql \$DATABASE_URL < db_schema.sql${NC}"
echo ""
echo "3. Start the server:"
echo "   ${YELLOW}./START_LOCAL.sh${NC}"
echo ""
echo "   Or manually:"
echo "   ${YELLOW}source venv/bin/activate${NC}"
echo "   ${YELLOW}python3 -m uvicorn server:app --host 0.0.0.0 --port 8000 --reload${NC}"
echo ""
echo "4. Open your browser:"
echo "   ${GREEN}http://localhost:8000/app${NC}"
echo ""
echo "For more information, see README.md"
echo ""


