#!/bin/bash
# Fix GLM layer time dimension to use "List" mode instead of "Nearest"
# This prevents GeoServer from returning nearest date when exact date doesn't exist

GEOSERVER_URL="http://localhost:8080/geoserver"
WORKSPACE="glm_ws"
LAYER="glm_fed"
USER="admin"
PASS="todosabordo25!"

echo "Configuring time dimension for ${WORKSPACE}:${LAYER}"
echo "Setting to List mode (discrete values only)"

# Update layer with time dimension configuration
curl -v -u ${USER}:${PASS} \
  -X PUT \
  -H "Content-Type: application/json" \
  "${GEOSERVER_URL}/rest/workspaces/${WORKSPACE}/coveragestores/${LAYER}/coverages/${LAYER}" \
  -d '{
    "coverage": {
      "enabled": true,
      "metadata": {
        "entry": [
          {
            "@key": "time",
            "dimensionInfo": {
              "enabled": true,
              "presentation": "LIST",
              "units": "ISO8601",
              "defaultValue": {
                "strategy": "MINIMUM"
              },
              "nearestMatchEnabled": false
            }
          }
        ]
      }
    }
  }'

echo ""
echo "Time dimension configured!"
echo "Test with: curl 'http://localhost:8080/geoserver/glm_ws/wms?...' "
