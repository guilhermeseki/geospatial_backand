#!/bin/bash

# check_setup.sh
# Script to verify Prefect and GeoServer setup for chirps_daily_flow
# Usage: bash check_setup.sh
# Run in Conda environment: source /home/guilherme/miniconda3/bin/activate horus

# Configuration (update for cloud deployment)
CONDA_ENV="/home/guilherme/miniconda3/envs/horus"
PROJECT_DIR="/media/guilherme/Workwork/geospatial_backend"
PREFECT_API_URL="http://localhost:4200/api"
GEOSERVER_HOST="localhost"  # Update for cloud GeoServer host
GEOSERVER_PORT="8080"      # Update for cloud GeoServer port
GEOSERVER_ADMIN_USER=$(python -c 'from app.config.settings import settings; print(settings.GEOSERVER_ADMIN_USER)' 2>/dev/null || echo "admin")
GEOSERVER_ADMIN_PASSWORD=$(python -c 'from app.config.settings import settings; print(settings.GEOSERVER_ADMIN_PASSWORD)' 2>/dev/null || echo "your_password")
GEOSERVER_URL="http://$GEOSERVER_HOST:$GEOSERVER_PORT/geoserver/rest"
GEOSERVER_WORKSPACE=$(python -c 'from app.config.settings import settings; print(settings.GEOSERVER_WORKSPACE)' 2>/dev/null)
DATA_DIR=$(python -c 'from app.config.settings import settings; print(settings.DATA_DIR)' 2>/dev/null || echo "/media/guilherme/Workwork/geospatial_backend/data")
RAW_DIR="$DATA_DIR/raw"
CHIRPS_FINAL_DIR="$DATA_DIR/chirps_final"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "\n${YELLOW}0. Checking settings variables${NC}"
if [ -z "$DATA_DIR" ]; then
    echo -e "${RED}DATA_DIR is empty${NC}"
    exit 1
else
    echo -e "${GREEN}DATA_DIR: $DATA_DIR${NC}"
fi
if [ -z "$GEOSERVER_HOST" ]; then
    echo -e "${RED}GEOSERVER_HOST is empty${NC}"
    exit 1
else
    echo -e "${GREEN}GEOSERVER_HOST: $GEOSERVER_HOST${NC}"
fi
if [ -z "$GEOSERVER_PORT" ] || ! [[ "$GEOSERVER_PORT" =~ ^[0-9]+$ ]]; then
    echo -e "${RED}GEOSERVER_PORT is empty or invalid${NC}"
    exit 1
else
    echo -e "${GREEN}GEOSERVER_PORT: $GEOSERVER_PORT${NC}"
fi
if [ -z "$GEOSERVER_ADMIN_USER" ]; then
    echo -e "${RED}GEOSERVER_ADMIN_USER is empty${NC}"
    exit 1
else
    echo -e "${GREEN}GEOSERVER_ADMIN_USER: $GEOSERVER_ADMIN_USER${NC}"
fi
if [ -z "$GEOSERVER_ADMIN_PASSWORD" ]; then
    echo -e "${RED}GEOSERVER_ADMIN_PASSWORD is empty${NC}"
    exit 1
else
    echo -e "${GREEN}GEOSERVER_ADMIN_PASSWORD: [hidden]${NC}"
fi
if [ -z "$GEOSERVER_WORKSPACE" ]; then
    echo -e "${RED}GEOSERVER_WORKSPACE is empty${NC}"
    exit 1
else
    echo -e "${GREEN}GEOSERVER_WORKSPACE: $GEOSERVER_WORKSPACE${NC}"
fi

echo "Checking Prefect and GeoServer setup for chirps_daily_flow..."

# 1. Check Conda environment
echo -e "\n${YELLOW}1. Checking Conda environment${NC}"
if [ -f "$CONDA_ENV/bin/prefect" ]; then
    echo -e "${GREEN}Conda environment found at $CONDA_ENV${NC}"
    source /home/guilherme/miniconda3/bin/activate horus
    PREFECT_VERSION=$(prefect version | grep Version | awk '{print $2}')
    if [ "$PREFECT_VERSION" = "3.4.14" ]; then
        echo -e "${GREEN}Prefect version 3.4.14 confirmed${NC}"
    else
        echo -e "${RED}Unexpected Prefect version: $PREFECT_VERSION (expected 3.4.14)${NC}"
        exit 1
    fi
else
    echo -e "${RED}Conda environment not found at $CONDA_ENV${NC}"
    echo "Please create and install dependencies:"
    echo "conda create -n horus python=3.13"
    echo "source $CONDA_ENV/bin/activate"
    echo "pip install prefect rioxarray rasterio xarray fsspec requests pandas"
    exit 1
fi

# 2. Check Prefect server
echo -e "\n${YELLOW}2. Checking Prefect server on port 4200${NC}"
if curl -s "$PREFECT_API_URL/health" | grep -q "true"; then
    echo -e "${GREEN}Prefect server is healthy at $PREFECT_API_URL${NC}"
else
    echo -e "${RED}Prefect server is not running or unreachable at $PREFECT_API_URL${NC}"
    echo "Trying to start server..."
    prefect server start &
    sleep 5
    if curl -s "$PREFECT_API_URL/health" | grep -q "true"; then
        echo -e "${GREEN}Prefect server started successfully${NC}"
    else
        echo -e "${RED}Failed to start Prefect server${NC}"
        echo "Check if port 4200 is in use:"
        sudo lsof -i :4200
        exit 1
    fi
fi
# Check server process
SERVER_PID=$(sudo lsof -i :4200 | grep LISTEN | awk '{print $2}' | head -1)
if [ -n "$SERVER_PID" ]; then
    echo -e "${GREEN}Prefect server process found (PID: $SERVER_PID)${NC}"
else
    echo -e "${YELLOW}No process found on port 4200; server may be running externally${NC}"
fi

# 3. Check prefect-agent.service
echo -e "\n${YELLOW}3. Checking prefect-agent.service${NC}"
if sudo systemctl is-active prefect-agent.service | grep -q "active"; then
    echo -e "${GREEN}prefect-agent.service is active${NC}"
else
    echo -e "${RED}prefect-agent.service is not active${NC}"
    echo "Starting prefect-agent.service..."
    sudo systemctl restart prefect-agent.service
    sleep 2
    if sudo systemctl is-active prefect-agent.service | grep -q "active"; then
        echo -e "${GREEN}prefect-agent.service started successfully${NC}"
    else
        echo -e "${RED}Failed to start prefect-agent.service${NC}"
        echo "Recent logs:"
        journalctl -u prefect-agent.service -b -n 20
        exit 1
    fi
fi

# 4. Check work pool
echo -e "\n${YELLOW}4. Checking default work pool${NC}"
if prefect work-pool ls | grep -q "default"; then
    echo -e "${GREEN}Default work pool exists${NC}"
else
    echo -e "${YELLOW}Default work pool not found, creating...${NC}"
    prefect work-pool create default --type process
    if prefect work-pool ls | grep -q "default"; then
        echo -e "${GREEN}Default work pool created${NC}"
    else
        echo -e "${RED}Failed to create default work pool${NC}"
        exit 1
    fi
fi

# 5. Check directories
echo -e "\n${YELLOW}5. Checking directories${NC}"
if [ -d "$RAW_DIR" ]; then
    echo -e "${GREEN}Raw directory exists: $RAW_DIR${NC}"
else
    echo -e "${YELLOW}Raw directory not found, creating: $RAW_DIR${NC}"
    sudo mkdir -p "$RAW_DIR"
    sudo chown geoserver:geoserver "$RAW_DIR"
    sudo chmod 755 "$RAW_DIR"
fi
if [ -d "$CHIRPS_FINAL_DIR" ]; then
    echo -e "${GREEN}Chirps final directory exists: $CHIRPS_FINAL_DIR${NC}"
else
    echo -e "${YELLOW}Chirps final directory not found, creating: $CHIRPS_FINAL_DIR${NC}"
    sudo mkdir -p "$CHIRPS_FINAL_DIR"
    sudo chown geoserver:geoserver "$CHIRPS_FINAL_DIR"
    sudo chmod 755 "$CHIRPS_FINAL_DIR"
fi
# Check permissions
RAW_PERMS=$(ls -ld "$RAW_DIR" | awk '{print $1, $3, $4}')
CHIRPS_PERMS=$(ls -ld "$CHIRPS_FINAL_DIR" | awk '{print $1, $3, $4}')
if [[ "$RAW_PERMS" == *"geoserver geoserver"* && "$CHIRPS_PERMS" == *"geoserver geoserver"* ]]; then
    echo -e "${GREEN}Directory permissions correct (owned by geoserver:geoserver)${NC}"
else
    echo -e "${YELLOW}Fixing directory permissions...${NC}"
    sudo chown -R geoserver:geoserver "$RAW_DIR" "$CHIRPS_FINAL_DIR"
    sudo chmod -R 755 "$RAW_DIR" "$CHIRPS_FINAL_DIR"
fi
# Ensure guilherme has access
if groups guilherme | grep -q "geoserver"; then
    echo -e "${GREEN}User guilherme is in geoserver group${NC}"
else
    echo -e "${YELLOW}Adding guilherme to geoserver group${NC}"
    sudo usermod -aG geoserver guilherme
fi

# 6. Check GeoServer indexer files
echo -e "\n${YELLOW}6. Checking GeoServer indexer files${NC}"
if [ -f "$CHIRPS_FINAL_DIR/indexer.properties" ] && [ -f "$CHIRPS_FINAL_DIR/timeregex.properties" ]; then
    echo -e "${GREEN}Indexer files found: $CHIRPS_FINAL_DIR/{indexer.properties,timeregex.properties}${NC}"
else
    echo -e "${RED}Indexer files missing in $CHIRPS_FINAL_DIR${NC}"
    echo "Ensure GeoServerService creates indexer.properties and timeregex.properties"
    exit 1
fi

# 7. Test GeoServer connectivity
echo -e "\n${YELLOW}7. Testing GeoServer connectivity${NC}"
GEOSERVER_TEST_URL="$GEOSERVER_URL/about/version"
if curl -s -u "$GEOSERVER_ADMIN_USER:$GEOSERVER_ADMIN_PASSWORD" "$GEOSERVER_TEST_URL" | grep -q "GeoServer"; then
    echo -e "${GREEN}GeoServer is reachable at $GEOSERVER_TEST_URL${NC}"
else
    echo -e "${RED}GeoServer is not reachable at $GEOSERVER_TEST_URL${NC}"
    echo "Check GEOSERVER_HOST, GEOSERVER_PORT, and credentials in settings"
    exit 1
fi

# 8. Test GeoServer reindex
echo -e "\n${YELLOW}8. Testing GeoServer reindex${NC}"
TEST_TIFF="$CHIRPS_FINAL_DIR/chirps_final_latam_20250825.tif"
REINDEX_URL="$GEOSERVER_URL/workspaces/$GEOSERVER_WORKSPACE/coveragestores/chirps_final_mosaic/external.imagemosaic"
echo -e "$GEOSERVER_ADMIN_USER:$GEOSERVER_ADMIN_PASSWORD"
if curl -s -u "$GEOSERVER_ADMIN_USER:$GEOSERVER_ADMIN_PASSWORD" -X POST -H "Content-Type: text/plain" -d "file://$TEST_TIFF" "$REINDEX_URL" | grep -q "200\|201"; then
    echo -e "${GREEN}GeoServer reindex test successful${NC}"
else
    echo -e "${RED}GeoServer reindex test failed${NC}"
    echo "Check GeoServer logs or try manually:"
    echo "curl -u $GEOSERVER_ADMIN_USER:**** -X POST -H 'Content-Type: text/plain' -d 'file://$TEST_TIFF' $REINDEX_URL"
fi

# 9. Test manual flow run
echo -e "\n${YELLOW}9. Testing manual flow run${NC}"
export PREFECT_API_URL=http://localhost:4200/api
if prefect run deployment chirps-daily; then
    echo -e "${GREEN}Manual flow run successful${NC}"
else
    echo -e "${RED}Manual flow run failed${NC}"
    echo "Check dashboard at http://localhost:4200 or logs:"
    journalctl -u prefect-agent.service -b -n 20
    exit 1
fi

echo -e "\n${GREEN}Setup check completed successfully${NC}"