#create_precipitation_style.py

import httpx
import os
from pathlib import Path
from app.config.settings import settings
import logging

logger = logging.getLogger(__name__)

# Define paths and GeoServer details
SLD_FILE_PATH = Path("/media/guilherme/Workwork/geospatial_backend/data/precipitation_style.sld")
GEOSERVER_REST_URL = f"http://{settings.GEOSERVER_HOST}:{settings.GEOSERVER_PORT}/geoserver/rest"
GEOSERVER_AUTH = (settings.GEOSERVER_ADMIN_USER, settings.GEOSERVER_ADMIN_PASSWORD)
WORKSPACE = settings.GEOSERVER_WORKSPACE
LAYER_NAME = "chirps_final_mosaic"
STYLE_NAME = "precipitation_style"

# SLD content for precipitation style
SLD_CONTENT = """<?xml version="1.0" encoding="UTF-8"?>
<StyledLayerDescriptor version="1.0.0" xmlns="http://www.opengis.net/sld" xmlns:ogc="http://www.opengis.net/ogc">
  <NamedLayer>
    <Name>precipitation_style</Name>
    <UserStyle>
      <Title>Precipitation Style</Title>
      <FeatureTypeStyle>
        <Rule>
          <RasterSymbolizer>
            <Opacity>1.0</Opacity>
            <ColorMap>
              <ColorMapEntry color="#0000FF" quantity="0" label="No Data" opacity="0"/>
              <ColorMapEntry color="#00FF00" quantity="10" label="Low"/>
              <ColorMapEntry color="#FFFF00" quantity="50" label="Medium"/>
              <ColorMapEntry color="#FF0000" quantity="100" label="High"/>
            </ColorMap>
          </RasterSymbolizer>
        </Rule>
      </FeatureTypeStyle>
    </UserStyle>
  </NamedLayer>
</StyledLayerDescriptor>
"""

def create_sld_file():
    """Create the precipitation_style.sld file."""
    try:
        os.makedirs(SLD_FILE_PATH.parent, exist_ok=True)
        with open(SLD_FILE_PATH, "w") as f:
            f.write(SLD_CONTENT)
        os.chmod(SLD_FILE_PATH, 0o664)
        logger.info(f"Created SLD file: {SLD_FILE_PATH}")
    except Exception as e:
        logger.error(f"Failed to create SLD file: {str(e)}")
        raise

async def upload_style_to_geoserver():
    """Upload the SLD file to GeoServer via REST API."""
    async with httpx.AsyncClient(auth=GEOSERVER_AUTH) as client:
        # Check if style exists
        response = await client.get(f"{GEOSERVER_REST_URL}/styles/{STYLE_NAME}")
        if response.status_code == 200:
            logger.info(f"Style {STYLE_NAME} already exists, updating...")
            # Update existing style
            headers = {"Content-Type": "application/vnd.ogc.sld+xml"}
            response = await client.put(
                f"{GEOSERVER_REST_URL}/styles/{STYLE_NAME}",
                content=SLD_CONTENT,
                headers=headers
            )
        else:
            # Create new style
            headers = {"Content-Type": "application/xml"}
            style_xml = f"""
            <style>
                <name>{STYLE_NAME}</name>
                <filename>{STYLE_NAME}.sld</filename>
            </style>
            """
            response = await client.post(
                f"{GEOSERVER_REST_URL}/styles",
                content=style_xml,
                headers=headers
            )
            if response.status_code == 201:
                logger.info(f"Created style {STYLE_NAME}")
                # Upload SLD content
                headers = {"Content-Type": "application/vnd.ogc.sld+xml"}
                response = await client.put(
                    f"{GEOSERVER_REST_URL}/styles/{STYLE_NAME}",
                    content=SLD_CONTENT,
                    headers=headers
                )
        if response.status_code not in (200, 201):
            logger.error(f"Failed to upload style: {response.text}")
            raise Exception(f"Style upload failed: {response.status_code}")

async def assign_style_to_layer():
    """Assign the style to the chirps_final_mosaic layer."""
    async with httpx.AsyncClient(auth=GEOSERVER_AUTH) as client:
        # Get current layer configuration
        response = await client.get(
            f"{GEOSERVER_REST_URL}/workspaces/{WORKSPACE}/layers/{LAYER_NAME}"
        )
        if response.status_code != 200:
            logger.error(f"Layer {LAYER_NAME} not found: {response.text}")
            raise Exception("Layer not found")

        # Update layer to set default style
        layer_xml = f"""
        <layer>
            <defaultStyle>
                <name>{STYLE_NAME}</name>
            </defaultStyle>
        </layer>
        """
        headers = {"Content-Type": "application/xml"}
        response = await client.put(
            f"{GEOSERVER_REST_URL}/workspaces/{WORKSPACE}/layers/{LAYER_NAME}",
            content=layer_xml,
            headers=headers
        )
        if response.status_code == 200:
            logger.info(f"Assigned style {STYLE_NAME} to layer {WORKSPACE}:{LAYER_NAME}")
        else:
            logger.error(f"Failed to assign style: {response.text}")
            raise Exception(f"Style assignment failed: {response.status_code}")

async def main():
    """Main function to create and implement the style."""
    try:
        create_sld_file()
        await upload_style_to_geoserver()
        await assign_style_to_layer()
        logger.info("Successfully created and implemented precipitation_style")
    except Exception as e:
        logger.error(f"Failed to implement style: {str(e)}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())