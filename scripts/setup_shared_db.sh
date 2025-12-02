#!/bin/bash
# Helper script to set up shared database configuration

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

echo "=========================================="
echo "🔧 Shared Database Setup Helper"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Check if .env exists
if [ ! -f .env ]; then
    print_warning ".env file not found. Creating from template..."
    if [ -f "PRODUCTION_ENV_TEMPLATE" ]; then
        cp PRODUCTION_ENV_TEMPLATE .env
    else
        print_warning "No template found. Please create .env manually."
        exit 1
    fi
fi

echo "Choose your shared database setup:"
echo ""
echo "1) Docker Compose on this machine (expose to network)"
echo "2) Use existing cloud database (Railway, Supabase, etc.)"
echo "3) Use local PostgreSQL server"
echo "4) Just show current DATABASE_URL"
echo ""
read -p "Enter choice [1-4]: " choice

case $choice in
    1)
        echo ""
        print_info "Setting up Docker Compose database..."
        
        # Check if Docker is running
        if ! command -v docker &> /dev/null; then
            print_warning "Docker not found. Please install Docker first."
            exit 1
        fi
        
        # Start database
        print_info "Starting PostgreSQL database..."
        docker-compose up -d db
        
        # Wait for database to be ready
        print_info "Waiting for database to be ready..."
        sleep 5
        
        # Get local IP address
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            LOCAL_IP=$(ifconfig | grep "inet " | grep -v 127.0.0.1 | head -1 | awk '{print $2}')
        else
            # Linux
            LOCAL_IP=$(hostname -I | awk '{print $1}')
        fi
        
        if [ -z "$LOCAL_IP" ]; then
            print_warning "Could not determine local IP. Using localhost."
            DB_URL="postgresql://postgres:postgres@localhost:5432/rag_brain"
        else
            print_success "Local IP: $LOCAL_IP"
            DB_URL="postgresql://postgres:postgres@$LOCAL_IP:5432/rag_brain"
        fi
        
        # Update .env
        if grep -q "^DATABASE_URL=" .env; then
            sed -i.bak "s|^DATABASE_URL=.*|DATABASE_URL=$DB_URL|" .env
        else
            echo "DATABASE_URL=$DB_URL" >> .env
        fi
        
        print_success "Updated .env with DATABASE_URL"
        echo ""
        print_info "On other machines, use this DATABASE_URL:"
        echo "  ${GREEN}$DB_URL${NC}"
        echo ""
        print_info "To initialize schema, run:"
        echo "  ${GREEN}psql \"$DB_URL\" < db_schema.sql${NC}"
        ;;
        
    2)
        echo ""
        read -p "Enter your database connection string: " DB_URL
        
        # Validate format
        if [[ ! "$DB_URL" =~ ^postgresql:// ]]; then
            print_warning "Invalid format. Should start with 'postgresql://'"
            exit 1
        fi
        
        # Update .env
        if grep -q "^DATABASE_URL=" .env; then
            sed -i.bak "s|^DATABASE_URL=.*|DATABASE_URL=$DB_URL|" .env
        else
            echo "DATABASE_URL=$DB_URL" >> .env
        fi
        
        print_success "Updated .env with cloud database URL"
        echo ""
        print_info "Test connection:"
        echo "  ${GREEN}psql \"$DB_URL\" -c \"SELECT version();\"${NC}"
        echo ""
        print_info "Initialize schema:"
        echo "  ${GREEN}psql \"$DB_URL\" < db_schema.sql${NC}"
        ;;
        
    3)
        echo ""
        read -p "Enter database host IP or hostname: " DB_HOST
        read -p "Enter database port [5432]: " DB_PORT
        DB_PORT=${DB_PORT:-5432}
        read -p "Enter database name [rag_brain]: " DB_NAME
        DB_NAME=${DB_NAME:-rag_brain}
        read -p "Enter username [postgres]: " DB_USER
        DB_USER=${DB_USER:-postgres}
        read -sp "Enter password: " DB_PASS
        echo ""
        
        DB_URL="postgresql://$DB_USER:$DB_PASS@$DB_HOST:$DB_PORT/$DB_NAME"
        
        # Test connection
        print_info "Testing connection..."
        if psql "$DB_URL" -c "SELECT version();" &> /dev/null; then
            print_success "Connection successful!"
        else
            print_warning "Connection test failed. Please check credentials."
            exit 1
        fi
        
        # Update .env
        if grep -q "^DATABASE_URL=" .env; then
            sed -i.bak "s|^DATABASE_URL=.*|DATABASE_URL=$DB_URL|" .env
        else
            echo "DATABASE_URL=$DB_URL" >> .env
        fi
        
        print_success "Updated .env with local PostgreSQL URL"
        echo ""
        print_info "Initialize schema:"
        echo "  ${GREEN}psql \"$DB_URL\" < db_schema.sql${NC}"
        ;;
        
    4)
        echo ""
        if grep -q "^DATABASE_URL=" .env; then
            CURRENT_URL=$(grep "^DATABASE_URL=" .env | cut -d'=' -f2-)
            print_info "Current DATABASE_URL:"
            echo "  ${GREEN}$CURRENT_URL${NC}"
        else
            print_warning "DATABASE_URL not found in .env"
        fi
        ;;
        
    *)
        print_warning "Invalid choice"
        exit 1
        ;;
esac

echo ""
print_info "Next steps:"
echo "  1. Copy this .env file to your other machine(s)"
echo "  2. Initialize schema: psql \"\$DATABASE_URL\" < db_schema.sql"
echo "  3. Start the server: ./START_LOCAL.sh"
echo ""
print_success "Setup complete!"


