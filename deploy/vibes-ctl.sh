#!/bin/bash
# Vibes Control Script
# ====================
# Safe management of the vibes stack with project protection

set -e
cd "$(dirname "$0")"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Find all project containers
get_project_containers() {
    docker ps -a --filter "name=vibes-project-" --format "{{.Names}}\t{{.Status}}" 2>/dev/null | grep -v "vibes-project-manager" || true
}

# Count running project containers
count_projects() {
    get_project_containers | wc -l
}

case "$1" in
    start)
        echo -e "${GREEN}Starting Vibes stack...${NC}"
        docker compose up -d
        echo -e "${GREEN}Vibes is running!${NC}"
        ;;

    stop)
        echo -e "${YELLOW}Stopping Vibes stack (preserving project containers)...${NC}"
        # Stop core services but NOT project containers
        docker compose stop caddy frontend dashboard hpts warp redis postgres project-manager
        echo -e "${GREEN}Core services stopped. Project containers preserved.${NC}"
        ;;

    restart)
        echo -e "${YELLOW}Restarting Vibes stack...${NC}"
        docker compose restart
        echo -e "${GREEN}Vibes restarted!${NC}"
        ;;

    rebuild)
        echo -e "${YELLOW}Rebuilding and restarting Vibes stack...${NC}"
        echo ""
        echo -e "${YELLOW}[1/3] Rebuilding images...${NC}"
        docker compose build
        echo ""
        echo -e "${YELLOW}[2/3] Restarting core services...${NC}"
        docker compose up -d
        echo ""
        PROJECT_COUNT=$(count_projects)
        if [ "$PROJECT_COUNT" -gt 0 ]; then
            echo -e "${YELLOW}[3/3] Updating $PROJECT_COUNT project container(s)...${NC}"
            for container in $(get_project_containers | cut -f1); do
                project_id="${container#vibes-project-}"
                echo "  Recreating $container..."
                docker stop "$container" 2>/dev/null || true
                docker rm "$container" 2>/dev/null || true
                # Start via project-manager to recreate with new image
                curl -s -X POST "http://localhost:3009/projects/$project_id/start" > /dev/null 2>&1 || true
            done
        else
            echo -e "${YELLOW}[3/3] No project containers to update.${NC}"
        fi
        echo ""
        echo -e "${GREEN}Vibes rebuilt and running!${NC}"
        ;;

    update-projects)
        PROJECT_COUNT=$(count_projects)
        if [ "$PROJECT_COUNT" -eq 0 ]; then
            echo "No project containers to update."
            exit 0
        fi
        echo -e "${YELLOW}Updating $PROJECT_COUNT project container(s) with latest image...${NC}"
        for container in $(get_project_containers | cut -f1); do
            project_id="${container#vibes-project-}"
            echo "  Recreating $container..."
            docker stop "$container" 2>/dev/null || true
            docker rm "$container" 2>/dev/null || true
            curl -s -X POST "http://localhost:3009/projects/$project_id/start" > /dev/null 2>&1 || true
        done
        echo -e "${GREEN}Project containers updated!${NC}"
        ;;

    down)
        PROJECT_COUNT=$(count_projects)
        if [ "$PROJECT_COUNT" -gt 0 ]; then
            echo -e "${YELLOW}╔════════════════════════════════════════════════════════════╗${NC}"
            echo -e "${YELLOW}║  WARNING: Found $PROJECT_COUNT project container(s)                        ║${NC}"
            echo -e "${YELLOW}╚════════════════════════════════════════════════════════════╝${NC}"
            echo ""
            echo "Project containers:"
            get_project_containers | while read line; do
                echo "  - $line"
            done
            echo ""
            echo -e "${RED}Taking down the stack will orphan these containers!${NC}"
            echo ""
            read -p "Options: [k]eep projects & stop core only, [d]elete all, [c]ancel? " choice
            case "$choice" in
                k|K)
                    echo -e "${YELLOW}Stopping core services only...${NC}"
                    docker compose stop
                    echo -e "${GREEN}Core services stopped. Project containers preserved.${NC}"
                    echo "Run 'docker start <container>' to restart projects later."
                    ;;
                d|D)
                    echo -e "${RED}Removing all containers including projects...${NC}"
                    # First remove project containers
                    get_project_containers | cut -f1 | xargs -r docker rm -f 2>/dev/null || true
                    # Then take down the stack
                    docker compose down
                    echo -e "${GREEN}All containers removed.${NC}"
                    ;;
                *)
                    echo "Cancelled."
                    exit 0
                    ;;
            esac
        else
            echo -e "${YELLOW}No project containers found. Taking down stack...${NC}"
            docker compose down
            echo -e "${GREEN}Stack is down.${NC}"
        fi
        ;;

    status)
        echo -e "${GREEN}=== Vibes Stack Status ===${NC}"
        echo ""
        echo "Core Services:"
        docker compose ps --format "table {{.Name}}\t{{.Status}}" 2>/dev/null || echo "  Not running"
        echo ""
        PROJECT_COUNT=$(count_projects)
        if [ "$PROJECT_COUNT" -gt 0 ]; then
            echo "Project Containers ($PROJECT_COUNT):"
            get_project_containers | while read line; do
                echo "  $line"
            done
        else
            echo "Project Containers: None"
        fi
        ;;

    projects)
        echo -e "${GREEN}=== Project Containers ===${NC}"
        PROJECT_COUNT=$(count_projects)
        if [ "$PROJECT_COUNT" -gt 0 ]; then
            get_project_containers
        else
            echo "No project containers found."
        fi
        ;;

    clean-projects)
        PROJECT_COUNT=$(count_projects)
        if [ "$PROJECT_COUNT" -eq 0 ]; then
            echo "No project containers to clean."
            exit 0
        fi
        echo -e "${YELLOW}Found $PROJECT_COUNT project container(s):${NC}"
        get_project_containers | while read line; do
            echo "  - $line"
        done
        echo ""
        read -p "Remove all project containers? [y/N] " confirm
        if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
            get_project_containers | cut -f1 | xargs -r docker rm -f
            echo -e "${GREEN}Project containers removed.${NC}"
        else
            echo "Cancelled."
        fi
        ;;

    *)
        echo "Vibes Control Script"
        echo ""
        echo "Usage: $0 <command>"
        echo ""
        echo "Commands:"
        echo "  start            Start the Vibes stack"
        echo "  stop             Stop core services (preserve projects)"
        echo "  restart          Restart all services"
        echo "  rebuild          Rebuild images + restart + update projects"
        echo "  down             Take down stack (with project protection)"
        echo "  status           Show stack and project status"
        echo "  projects         List project containers"
        echo "  update-projects  Recreate projects with latest image"
        echo "  clean-projects   Remove all project containers"
        echo ""
        ;;
esac
