#!/bin/bash

# Show all katzenschreck containers with their monitoring ports and health status

echo "🐱 Katzenschreck Containers"
echo "═════════════════════════════════════════════════════════════════════════════════════"
printf "%-30s %-15s %-10s %-10s %-20s\n" "CONTAINER" "CAMERA" "PORT" "NETWORK" "HEALTH"
echo "─────────────────────────────────────────────────────────────────────────────────────"

# Get all katzenschreck containers
CONTAINERS=$(docker ps -a --filter "name=katzenschreck" --format "{{.Names}}")

if [ -z "$CONTAINERS" ]; then
    echo "No katzenschreck containers found."
    exit 0
fi

for CONTAINER in $CONTAINERS; do
    # Get camera name from label
    CAMERA=$(docker inspect --format='{{index .Config.Labels "katzenschreck.camera.name"}}' "$CONTAINER" 2>/dev/null || echo "N/A")
    
    # Get monitoring port from label
    PORT=$(docker inspect --format='{{index .Config.Labels "katzenschreck.monitoring.port"}}' "$CONTAINER" 2>/dev/null || echo "N/A")
    
    # Get network mode from label or inspect
    NETWORK=$(docker inspect --format='{{index .Config.Labels "katzenschreck.network.mode"}}' "$CONTAINER" 2>/dev/null || echo "")
    if [ -z "$NETWORK" ] || [ "$NETWORK" = "<no value>" ]; then
        # Fallback: check actual network mode
        NETWORK=$(docker inspect --format='{{range $net, $conf := .NetworkSettings.Networks}}{{$net}}{{end}}' "$CONTAINER" 2>/dev/null || echo "N/A")
    fi
    
    # Get health status
    HEALTH=$(docker inspect --format='{{.State.Health.Status}}' "$CONTAINER" 2>/dev/null || echo "no healthcheck")
    
    # Get container status
    STATUS=$(docker inspect --format='{{.State.Status}}' "$CONTAINER" 2>/dev/null || echo "unknown")
    
    # Color code health status
    case "$HEALTH" in
        "healthy")
            HEALTH_COLOR="✅ $HEALTH"
            ;;
        "unhealthy")
            HEALTH_COLOR="❌ $HEALTH"
            ;;
        "starting")
            HEALTH_COLOR="🔄 $HEALTH"
            ;;
        *)
            HEALTH_COLOR="⚠️  $HEALTH"
            ;;
    esac
    
    # Add status to container name
    if [ "$STATUS" != "running" ]; then
        CONTAINER="$CONTAINER ($STATUS)"
    fi
    
    printf "%-30s %-15s %-10s %-10s %-20s\n" "$CONTAINER" "$CAMERA" "$PORT" "$NETWORK" "$HEALTH_COLOR"
done

echo "═════════════════════════════════════════════════════════════════════════════════════"
echo ""
echo "💡 Quick access:"

for CONTAINER in $CONTAINERS; do
    STATUS=$(docker inspect --format='{{.State.Status}}' "$CONTAINER" 2>/dev/null)
    if [ "$STATUS" = "running" ]; then
        PORT=$(docker inspect --format='{{index .Config.Labels "katzenschreck.monitoring.port"}}' "$CONTAINER" 2>/dev/null || echo "8080")
        echo "   $CONTAINER: http://localhost:$PORT"
    fi
done
