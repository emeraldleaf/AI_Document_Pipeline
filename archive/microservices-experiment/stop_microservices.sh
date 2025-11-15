#!/bin/bash
#
# AI Document Pipeline - Stop Script
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

COMPOSE_FILE="docker-compose-microservices.yml"

echo -e "${BLUE}"
echo "╔════════════════════════════════════════════════════════════╗"
echo "║   Stopping AI Document Pipeline                           ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo -e "${NC}\n"

# Parse command line arguments
REMOVE_VOLUMES=false
if [ "$1" = "--remove-data" ] || [ "$1" = "-v" ]; then
    REMOVE_VOLUMES=true
    echo -e "${YELLOW}⚠ WARNING: This will delete all data (volumes)!${NC}"
    read -p "Are you sure? (yes/no): " -r
    if [[ ! $REPLY =~ ^[Yy]es$ ]]; then
        echo "Cancelled."
        exit 0
    fi
fi

echo -e "${BLUE}[$(date +%H:%M:%S)]${NC} Stopping services..."

if [ "$REMOVE_VOLUMES" = true ]; then
    docker-compose -f "$COMPOSE_FILE" down -v
    echo -e "${GREEN}✓${NC} All services stopped and data removed"
else
    docker-compose -f "$COMPOSE_FILE" down
    echo -e "${GREEN}✓${NC} All services stopped (data preserved)"
fi

echo ""
echo "Services stopped successfully!"
echo ""
echo "To start again:"
echo "  ./start_microservices.sh"
echo ""
echo "To remove all data:"
echo "  ./stop_microservices.sh --remove-data"
echo ""
