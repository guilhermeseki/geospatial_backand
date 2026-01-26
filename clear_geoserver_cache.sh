#!/bin/bash
# Clear GeoServer caches without restarting

GEOSERVER_URL="http://localhost:8080/geoserver"
GEOSERVER_USER="admin"
GEOSERVER_PASS="todosabordo25!"

echo "🔄 Clearing GeoServer caches..."

# Reset all caches
echo "  → Resetting all caches..."
curl -s -u ${GEOSERVER_USER}:${GEOSERVER_PASS} -X POST "${GEOSERVER_URL}/rest/reset"
echo " ✓"

# Reload configuration
echo "  → Reloading configuration..."
curl -s -u ${GEOSERVER_USER}:${GEOSERVER_PASS} -X POST "${GEOSERVER_URL}/rest/reload"
echo " ✓"

# Reset specific coverage stores (optional)
if [ "$1" != "" ]; then
    echo "  → Resetting coverage store: $1..."
    WORKSPACE=$(echo $1 | cut -d: -f1)
    STORE=$(echo $1 | cut -d: -f2)
    curl -s -u ${GEOSERVER_USER}:${GEOSERVER_PASS} -X POST \
      "${GEOSERVER_URL}/rest/workspaces/${WORKSPACE}/coveragestores/${STORE}/reset"
    echo " ✓"
fi

echo "✅ GeoServer caches cleared!"
