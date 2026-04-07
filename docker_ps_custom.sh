#!/bin/bash

# Custom docker ps with monitoring ports from labels

echo "CONTAINER                       STATUS              HEALTH          MONITORING PORT"
echo "────────────────────────────────────────────────────────────────────────────────────"

docker ps -a --filter "name=katzenschreck" --format "{{.Names}}|{{.Status}}|{{.ID}}" | while IFS='|' read -r name status id; do
    # Get health status
    health=$(docker inspect --format='{{.State.Health.Status}}' "$id" 2>/dev/null || echo "none")
    
    # Get monitoring port from label
    port=$(docker inspect --format='{{index .Config.Labels "katzenschreck.monitoring.port"}}' "$id" 2>/dev/null)
    if [ -z "$port" ] || [ "$port" = "<no value>" ]; then
        port="N/A"
    fi
    
    # Truncate status if too long
    status_short=$(echo "$status" | cut -c1-20)
    
    # Color-code health
    case "$health" in
        "healthy")
            health_display="✅ healthy"
            ;;
        "unhealthy")
            health_display="❌ unhealthy"
            ;;
        "starting")
            health_display="🔄 starting"
            ;;
        *)
            health_display="⚪ $health"
            ;;
    esac
    
    printf "%-30s  %-20s %-15s %s\n" "$name" "$status_short" "$health_display" "$port"
done
