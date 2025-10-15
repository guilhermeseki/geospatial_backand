#!/bin/bash

# check_settings.sh
# Script to verify GeoServer and data directory settings from app.config.settings
# Usage: bash check_settings.sh
# Run in Conda environment: source /home/guilherme/miniconda3/bin/activate horus

# Configuration
CONDA_ENV="/home/guilherme/miniconda3/envs/horus"
PROJECT_DIR="/media/guilherme/Workwork/geospatial_backend"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "Checking settings from app.config.settings..."

# 1. Check Conda environment
echo -e "\n${YELLOW}1. Checking Conda environment${NC}"
if [ -f "$CONDA_ENV/bin/python" ]; then
    echo -e "${GREEN}Conda environment found at $CONDA_ENV${NC}"
    source /home/guilherme/miniconda3/bin/activate horus
else
    echo -e "${RED}Conda environment not found at $CONDA_ENV${NC}"
    echo "Please create and activate: conda create -n horus python=3.13"
    exit 1
fi

# 2. Retrieve settings
echo -e "\n${YELLOW}2. Retrieving settings${NC}"
DATA_DIR=$(python -c 'from app.config.settings import settings; print(settings.DATA_DIR)' 2>/dev/null)
GEOSERVER_HOST=$(python -c 'from app.config.settings import settings; print(settings.GEOSERVER_HOST)' 2>/dev/null)
GEOSERVER_PORT=$(python -c 'from app.config.settings import settings; print(settings.GEOSERVER_PORT)' 2>/dev/null)
GEOSERVER_ADMIN_USER=$(python -c 'from app.config.settings import settings; print(settings.GEOSERVER_ADMIN_USER)' 2>/dev/null)
GEOSERVER_ADMIN_PASSWORD=$(python -c 'from app.config.settings import settings; print(settings.GEOSERVER_ADMIN_PASSWORD)' 2>/dev/null)
GEOSERVER_WORKSPACE=$(python -c 'from app.config.settings import settings; print(settings.GEOSERVER_WORKSPACE)' 2>/dev/null)

# 3. Validate settings
echo -e "\n${YELLOW}3. Validating settings${NC}"
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

# 4. Test GeoServer connectivity
echo -e "\n${YELLOW}4. Testing GeoServer connectivity${NC}"
GEOSERVER_URL="http://$GEOSERVER_HOST:$GEOSERVER_PORT/geoserver/rest"
GEOSERVER_TEST_URL="$GEOSERVER_URL/about/version"
if curl -s -u "$GEOSERVER_ADMIN_USER:$GEOSERVER_ADMIN_PASSWORD" "$GEOSERVER_TEST_URL" | grep -q "GeoServer"; then
    echo -e "${GREEN}GeoServer is reachable at $GEOSERVER_TEST_URL${NC}"
else
    echo -e "${RED}GeoServer is not reachable at $GEOSERVER_TEST_URL${NC}"
    echo "Check GEOSERVER_HOST, GEOSERVER_PORT, and credentials in app.config.settings"
    exit 1
fi

# 5. Check directories
echo -e "\n${YELLOW}5. Checking directories${NC}"
RAW_DIR="$DATA_DIR/raw"
CHIRPS_FINAL_DIR="$DATA_DIR/chirps_final"
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

echo -e "\n${GREEN}Settings check completed successfully${NC}"
