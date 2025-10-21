import httpx
from fastapi import HTTPException
from urllib.parse import urlencode
from pathlib import Path
import logging
import textwrap
import subprocess
import time
from app.config.settings import get_settings
import asyncio
import platform

settings = get_settings()
logger = logging.getLogger(__name__)

def is_success(status_code: int) -> bool:
    return status_code in (200, 201, 202)

# --- New: SLD Creation Function ---
def create_precipitation_sld(path: Path):
    sld_content = textwrap.dedent("""
    <StyledLayerDescriptor version="1.0.0"
        xsi:schemaLocation="http://www.opengis.net/sld StyledLayerDescriptor.xsd"
        xmlns="http://www.opengis.net/sld"
        xmlns:ogc="http://www.opengis.net/ogc"
        xmlns:xlink="http://www.w3.org/1999/xlink"
        xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
      <NamedLayer>
        <Name>precipitation_style</Name>
        <UserStyle>
          <Title>Precipitation Style - Custom Colorbar</Title>
          <FeatureTypeStyle>
            <Rule>
              <RasterSymbolizer>
                <ColorMap>

                  <!-- boundaries & colors -->
                  <ColorMapEntry color="#FFFFFF" quantity="0" label="0" opacity="0"/> <!-- white -->
                  <ColorMapEntry color="#50D0D0" quantity="1" label="1"/> <!-- (0.3137,0.8157,0.8157) -->
                  <ColorMapEntry color="#00FFFF" quantity="2.5" label="2.5"/> <!-- cyan -->
                  <ColorMapEntry color="#00E080" quantity="5" label="5"/> <!-- (0,0.878,0.502) -->
                  <ColorMapEntry color="#00C000" quantity="7.5" label="7.5"/> <!-- green -->
                  <ColorMapEntry color="#CCE000" quantity="10" label="10"/> <!-- yellow-green -->
                  <ColorMapEntry color="#FFFF00" quantity="15" label="15"/> <!-- yellow -->
                  <ColorMapEntry color="#FFA000" quantity="20" label="20"/> <!-- orange -->
                  <ColorMapEntry color="#FF0000" quantity="30" label="30"/> <!-- red -->
                  <ColorMapEntry color="#FF2080" quantity="40" label="40"/> <!-- pinkish -->
                  <ColorMapEntry color="#F041FF" quantity="50" label="50"/> <!-- violet -->
                  <ColorMapEntry color="#8020FF" quantity="70" label="70"/> <!-- purple -->
                  <ColorMapEntry color="#4040FF" quantity="100" label="100"/> <!-- blue -->
                  <ColorMapEntry color="#202080" quantity="150" label="150"/> <!-- dark blue -->
                  <ColorMapEntry color="#202020" quantity="200" label="200"/> <!-- dark gray -->
                  <ColorMapEntry color="#808080" quantity="250" label="250"/> <!-- gray -->
                  <ColorMapEntry color="#E0E0E0" quantity="300" label="300"/> <!-- light gray -->
                  <ColorMapEntry color="#EED4BC" quantity="400" label="400"/> <!-- beige -->
                  <ColorMapEntry color="#DAA675" quantity="500" label="500"/> <!-- brown -->
                  <ColorMapEntry color="#A06C3C" quantity="600" label="600"/> <!-- dark brown -->
                  <ColorMapEntry color="#663300" quantity="750" label="750"/> <!-- very dark brown -->

                </ColorMap>
              </RasterSymbolizer>
            </Rule>
          </FeatureTypeStyle>
        </UserStyle>
      </NamedLayer>
    </StyledLayerDescriptor>

    """).strip()

    path.write_text(sld_content)
    path.chmod(0o644)
    return path


class GeoServerService:
    def __init__(self):
        self.base_url = f"http://{settings.GEOSERVER_HOST}:{settings.GEOSERVER_PORT}/geoserver"
        self.auth = (settings.GEOSERVER_ADMIN_USER, settings.GEOSERVER_ADMIN_PASSWORD)
        self.workspace = settings.GEOSERVER_WORKSPACE
        self.layer = settings.GEOSERVER_LAYER
        self.data_dir = settings.DATA_DIR
        self.timeout = 30
        self.max_retries = 3
        logger.info(f"GeoServer configured at {self.base_url}")

    async def reindex_time(self) -> bool:
        """
        Reindex ImageMosaic time dimension.
        Steps:
        1. Delete old index files
        2. Restart GeoServer
        3. Recalculate ImageMosaic index
        4. Update shapefile date index
        """
        try:
            # Step 1 — Delete old index files (.fix, .idx, etc.)
            index_path = Path(self.data_dir) / "merge"
            for ext in ["fix", "idx", "properties", "xml"]:
                file = index_path / f"merge.{ext}"
                if file.exists():
                    file.unlink()
                    logger.info(f"Deleted index file: {file}")

            # Step 2 — Restart GeoServer
            logger.info("Restarting GeoServer...")
            subprocess.run(["sudo", "systemctl", "restart", "geoserver"], check=True)
            logger.info("GeoServer restarted. Waiting 15 seconds...")
            await asyncio.sleep(15)  # Use async sleep in async function

            # Step 3 — Recalculate ImageMosaic index
            reindex_url = (
                f"{self.base_url}/rest/workspaces/{self.workspace}"
                f"/coveragestores/merge/external.imagemosaic?recalculate=all"
            )
            async with httpx.AsyncClient(auth=self.auth, timeout=self.timeout) as client:
                logger.info(f"Calling reindex URL: {reindex_url}")
                response = await client.post(reindex_url)
                if not is_success(response.status_code):
                    logger.error(f"Failed to reindex: {response.status_code} {response.text}")
                    return False
                logger.info("ImageMosaic reindex request submitted successfully.")

            # Step 4 — Update shapefile index (if needed)
            # Uncomment if you have this function:
            # logger.info("Updating shapefile date index...")
            # update_shp_date_index_chirps()

            return True
        except Exception as e:
            logger.error(f"Error in reindex_time: {e}", exc_info=True)
            return False

    def get_geoserver_accessible_path(self, path: Path) -> str:
        if platform.system() == "Linux" and "microsoft" in platform.release().lower():
            parts = path.parts
            if parts[1].lower() == "mnt":
                drive = parts[2].upper()
                rest = Path(*parts[3:])
                return f"{drive}:\\" + str(rest).replace("/", "\\")
        return str(path)

    # --- Upload SLD ---
    async def upload_sld(self, sld_path: Path, style_name: str):
        async with httpx.AsyncClient(auth=self.auth) as client:
            headers = {"Content-Type": "application/vnd.ogc.sld+xml"}
            url = f"{self.base_url}/rest/styles?name={style_name}"
            response = await client.post(url, headers=headers, content=sld_path.read_bytes())
            if not is_success(response.status_code):  # Fixed: was checking if IS success
                raise HTTPException(
                    status_code=502,
                    detail=f"Failed to upload SLD {style_name}: {response.text}"
                )
            logger.info(f"SLD {style_name} uploaded successfully")

    async def ensure_layer_exists(self, source: str, date: str = None) -> str:
        """
        If you want to create a new mosaic, add at least two .tif files 
        with different dates in the folder, then restart FastAPI.
        """
        try:
            data_dir = Path(self.data_dir) / source
            tif_files = sorted(data_dir.glob(f"{source}_latam_*.tif"))
            if not tif_files:
                raise FileNotFoundError(f"No GeoTIFF files found in {data_dir}")

            if date:
                file_date = date.replace("-", "")
                geotiff_file = data_dir / f"{source}_latam_{file_date}.tif"
                if not geotiff_file.exists():
                    geotiff_file = tif_files[0]
            else:
                geotiff_file = tif_files[0]

            # --- Ensure mosaic config files exist ---
            indexer_props = data_dir / "indexer.properties"

            if not indexer_props.exists():
                indexer_props.write_text(
                    "TimeAttribute=timestamp\n"
                    "Schema=*the_geom:Polygon,location:String,timestamp:java.util.Date\n"
                    "PropertyCollectors=TimestampFileNameExtractorSPI[timeregex](timestamp)\n"
                    f"timeregex=.*_(\\d{8})\\.tif\n"
                    "timeformat=yyyyMMdd\n"
                )
                logger.info(f"Created {indexer_props}")

            store_name = f"{source}_mosaic"
            layer_name = f"{source}_mosaic"
            native_name = source

            try:
                await self._create_workspace()
            except Exception as e:
                logger.error("Failed to create workspace", exc_info=True)
                raise

            try:
                await self._create_coverage_store(store_name, source)
            except Exception as e:
                logger.error("Failed to create coverage store", exc_info=True)
                raise

            try:
                await self._publish_layer(store_name, layer_name, native_name=native_name)
            except Exception as e:
                logger.error("Failed to publish layer or enable time dimension", exc_info=True)
                raise

            sld_file = Path(self.data_dir) / "precipitation_style.sld"
            if not sld_file.exists():
                create_precipitation_sld(sld_file)
            await self.upload_sld(sld_file, style_name="precipitation_style")

            async with httpx.AsyncClient(auth=self.auth) as client:
                url = f"{self.base_url}/rest/layers/{self.workspace}:{layer_name}"
                payload = {"layer": {"defaultStyle": {"name": "precipitation_style"}}}
                response = await client.put(url, headers={"Content-Type": "application/json"}, json=payload)
                if not is_success(response.status_code):  # Fixed: was checking if IS success
                    logger.warning(f"Failed to apply SLD to {layer_name}: {response.text}")

            logger.info(f"Layer {layer_name} ensured with {geotiff_file.name}")
            return f"{self.workspace}:{layer_name}"

        except Exception as e:
            logger.error(f"Error in ensure_layer_exists: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to ensure layer exists: {str(e)}")

    async def _create_workspace(self):
        async with httpx.AsyncClient(auth=self.auth) as client:
            response = await client.get(f"{self.base_url}/rest/workspaces/{self.workspace}")
            if response.status_code == 404:
                create_res = await client.post(
                    f"{self.base_url}/rest/workspaces",
                    headers={"Content-Type": "application/json"},
                    json={"workspace": {"name": self.workspace}}
                )
                create_res.raise_for_status()

    async def _create_coverage_store(self, store_name: str, source: str):
        async with httpx.AsyncClient(auth=self.auth) as client:
            response = await client.get(
                f"{self.base_url}/rest/workspaces/{self.workspace}/coveragestores/{store_name}"
            )
            if response.status_code == 200:
                return  # already exists

            create_res = await client.post(
                f"{self.base_url}/rest/workspaces/{self.workspace}/coveragestores",
                params={"configure": "all"},
                headers={"Content-Type": "application/json"},
                json={
                    "coverageStore": {
                        "name": store_name,
                        "type": "ImageMosaic",
                        "enabled": True,
                        "workspace": {"name": self.workspace},
                        "url": f"file:{self.get_geoserver_accessible_path(Path(self.data_dir) / source)}/"
                    }
                }
            )
            if not is_success(create_res.status_code):  # Fixed: was checking if IS success
                raise HTTPException(
                    status_code=502,
                    detail=f"Failed to create coverage store: {create_res.text}"
                )

    async def _publish_layer(self, store_name: str, layer_name: str, native_name: str = None):
        if native_name is None:
            native_name = layer_name.replace("_mosaic", "")

        async with httpx.AsyncClient(auth=self.auth) as client:
            response = await client.get(
                f"{self.base_url}/rest/workspaces/{self.workspace}/coveragestores/{store_name}/coverages/{layer_name}"
            )
            if response.status_code == 200:
                return

            response = await client.post(
                f"{self.base_url}/rest/workspaces/{self.workspace}/coveragestores/{store_name}/coverages",
                headers={"Content-Type": "application/json"},
                json={
                    "coverage": {
                        "name": layer_name,
                        "nativeName": native_name,
                        "title": layer_name,
                        "enabled": True,
                        "srs": "EPSG:4326",
                        "nativeCRS": "EPSG:4326"
                    }
                }
            )
            if not is_success(response.status_code):  # Fixed: was checking if IS success
                raise HTTPException(
                    status_code=502,
                    detail=f"Failed to publish layer: {response.text}"
                )

            # Enable time dimension
            time_config = {
                "coverage": {
                    "metadata": {
                        "entry": [{
                            "@key": "time",
                            "dimensionInfo": {
                                "enabled": True,
                                "presentation": "LIST",
                                "resolution": "1 day",
                                "defaultValue": "NEAREST"
                            }
                        }]
                    }
                }
            }
            time_response = await client.put(
                f"{self.base_url}/rest/workspaces/{self.workspace}/coveragestores/{store_name}/coverages/{layer_name}",
                headers={"Content-Type": "application/json"},
                json=time_config
            )
            time_response.raise_for_status()

    async def get_wms_url(self, layer: str, bbox: str, time: str = None, size: str = "800x600"):
        params = {
            "service": "WMS",
            "version": "1.3.0",
            "request": "GetMap",
            "layers": layer,
            "bbox": bbox,
            "width": size.split("x")[0],
            "height": size.split("x")[1],
            "srs": "EPSG:4326",
            "format": "image/png",
            "styles": "precipitation_style",
            "transparent": "true"
        }
        if time:
            if len(time) == 10:
                time += "T00:00:00Z"
            params["time"] = time
        return f"{self.base_url}/wms?{urlencode(params)}"

    async def check_geoserver_alive(self) -> bool:
        """Check if GeoServer is responsive"""
        try:
            async with httpx.AsyncClient(auth=self.auth, timeout=5) as client:
                response = await client.get(f"{self.base_url}/rest/about/version.json")
                return response.status_code == 200
        except Exception as e:
            logger.warning(f"GeoServer health check failed: {e}")
            return False