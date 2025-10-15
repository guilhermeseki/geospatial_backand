# app/services/geoserver.py
import textwrap  # Add this with other imports
import httpx
import os
from fastapi import HTTPException
from urllib.parse import urlencode
from pathlib import Path
import logging
from datetime import datetime
from app.config.settings import settings
logger = logging.getLogger(__name__)
import asyncio
import xarray as xr
import sys
import platform



class GeoServerService:
    def __init__(self):
        self.port = settings.GEOSERVER_PORT
        self.base_url = f"http://{settings.GEOSERVER_HOST}:{self.port}/geoserver"
        self.auth = (settings.GEOSERVER_ADMIN_USER, settings.GEOSERVER_ADMIN_PASSWORD)
        self.workspace = settings.GEOSERVER_WORKSPACE
        self.data_dir = settings.NETCDF_DATA_DIR
        self.timeout = 30  # Can be moved to settings if needed
        self.max_retries = 3
        logger.info(f"GeoServer configured at {self.base_url}")
        # Debug output
        print(f"GeoServer URL: {self.base_url}")
        print(f"Workspace: {self.workspace}")
        print(f"NetCDF Data Directory: {self.data_dir}")

    def get_geoserver_accessible_path(self, netcdf_path: Path) -> str:
        """
        Convert WSL paths to Windows paths for GeoServer.
        On Linux, just return the absolute path.
        """
        if platform.system() == "Linux" and "microsoft" in platform.release().lower():
            # WSL detected: /mnt/d/... -> D:\...
            parts = netcdf_path.parts
            if parts[1].lower() == "mnt":
                drive = parts[2].upper()  # 'd'
                rest = Path(*parts[3:])
                return f"{drive}:\\" + str(rest).replace("/", "\\")
        return str(netcdf_path)


    async def _create_workspace(self):
        """Create workspace if it doesn't exist"""
        async with httpx.AsyncClient(auth=self.auth) as client:
            response = await client.get(
                f"{self.base_url}/rest/workspaces/{self.workspace}"
            )
           
            if response.status_code == 404:
                create_res = await client.post(
                    f"{self.base_url}/rest/workspaces",
                    headers={"Content-Type": "application/json"},
                    json={"workspace": {"name": self.workspace}}
                )
                create_res.raise_for_status()
    async def _create_coverage_store(self, store_name: str, source: str):
        """Create coverage store if it doesn't exist or wrong type"""
        async with httpx.AsyncClient(auth=self.auth) as client:
            response = await client.get(
                f"{self.base_url}/rest/workspaces/{self.workspace}/coveragestores/{store_name}"
            )
            if response.status_code == 200:
                store_info = response.json().get('coverageStore', {})
                if store_info.get('type') == 'ImageMosaic':
                    return # Exists and correct, keep it
                else:
                    # Wrong type, delete
                    delete_res = await client.delete(
                        f"{self.base_url}/rest/workspaces/{self.workspace}/coveragestores/{store_name}?recurse=true"
                    )
                    delete_res.raise_for_status()
            # Create
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
                        "url": f"file:{self.data_dir}/{source}/"
                    }
                }
            )
            if create_res.status_code not in (200, 201):
                raise HTTPException(
                    status_code=502,
                    detail=f"Failed to create coverage store: {create_res.text}"
                )
    async def _publish_layer(self, store_name: str, layer_name: str):
        """Publish the layer in GeoServer (with temporal support)"""
        async with httpx.AsyncClient(auth=self.auth) as client:
            # First create the basic coverage
            response = await client.post(
                f"{self.base_url}/rest/workspaces/{self.workspace}/coveragestores/{store_name}/coverages",
                headers={"Content-Type": "application/json"},
                json={
                    "coverage": {
                        "name": layer_name,
                        "nativeName": layer_name,
                        "title": layer_name,
                        "enabled": True
                    }
                }
            )
            if response.status_code not in (200, 201):
                raise HTTPException(
                    status_code=502,
                    detail=f"Failed to publish layer: {response.text}"
                )
            # Then enable time dimension
            time_config = {
                "coverage": {
                    "metadata": {
                        "entry": [{
                            "@key": "time",
                            "dimensionInfo": {
                                "enabled": True,
                                "presentation": "LIST",
                                "resolution": "1 day"
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


    async def _ensure_mosaic_config(self, source_name: str):
        """Ensure GeoServer mosaic config files exist, with automatic time detection."""
        #if source_name == "chirps_final":
        #    schema_name="precip"
        data_dir = Path(self.data_dir) / source_name
        data_dir.mkdir(exist_ok=True, mode=0o755)
        netcdf_files = sorted(data_dir.glob(f"{source_name}_latam_*.nc"))
        if not netcdf_files:
            raise RuntimeError(f"No NetCDF files found in {data_dir} to detect time attribute")
        ds_path = netcdf_files[0]
        with xr.open_dataset(ds_path) as ds:
            time_attr = "time" if "time" in ds.coords else "ingestion"
        configs = {
            "indexer.properties": textwrap.dedent(f"""
                TimeAttribute={time_attr}
                Caching=false
                EnableTimeFilter=true
                AbsolutePath=true
                PropertyCollectors=TimestampFileNameExtractorSPI[timeregex](time)
            """),
            "timeregex.properties": textwrap.dedent(f"""
                regex={source_name}_latam_([0-9]{{8}})\\.nc
                format=yyyyMMdd
            """),
            f"{source_name}_aux.xml": textwrap.dedent(f"""
                <Indexer>
                  <coverages>
                    <coverage>
                      <schema name="{source_name}">
                        <attributes>the_geom:Polygon,imageindex:Integer,time:java.util.Date</attributes>
                      </schema>
                      <name>{source_name}</name>
                    </coverage>
                  </coverages>
                </Indexer>
            """)
        }
        for filename, content in configs.items():
            filepath = data_dir / filename
            if not filepath.exists():
                filepath.write_text(content.strip())
                filepath.chmod(0o644)
                print(f"Created {filepath}")
            else:
                print(f"Skipped existing file {filepath}")
        required_files = ["indexer.properties", "timeregex.properties", f"{source_name}_aux.xml"]
        if not all((data_dir / f).exists() for f in required_files):
            raise RuntimeError(f"Missing mosaic config files in {data_dir}")

    async def ensure_layer_exists(self, source: str, date: str) -> str:
        """
        Ensure mosaic layer exists and add new NetCDF file incrementally.
        Handles WSL/Windows paths and Linux paths automatically.
        """
        try:
            await self._ensure_mosaic_config(source)

            file_date = date.replace("-", "")
            netcdf_file = f"{source}_latam_{file_date}.nc"
            netcdf_path = Path(self.data_dir) / source / netcdf_file
            if not netcdf_path.exists():
                raise FileNotFoundError(f"NetCDF file not found: {netcdf_path}")

            store_name = f"{source}_mosaic"
            layer_name = source

            await self._create_workspace()
            await self._create_coverage_store(store_name, source)

            netcdf_parent = self.get_geoserver_accessible_path(netcdf_path.parent)
            async with httpx.AsyncClient(auth=self.auth) as client:
                post_resp = await client.post(
                    f"{self.base_url}/rest/workspaces/{self.workspace}/coveragestores/{store_name}/external.imagemosaic",
                    headers={"Content-Type": "text/plain"},
                    content=f"file:{netcdf_parent}/"
                )
                post_resp.raise_for_status()
                print(f"Indexed NetCDF directory: {netcdf_parent}")

            await self._publish_layer(store_name, layer_name)
            return f"{self.workspace}:{layer_name}"

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to ensure mosaic layer exists: {str(e)}"
            )


    async def get_wms_url(self, layer: str, bbox: str, time: str = None, size: str = "800x600"):
        """Generate WMS URL with time support"""
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
            "styles": "precipitation_style"
        }
       
        if time:
            # Convert date to ISO format if needed
            if len(time) == 10: # YYYY-MM-DD
                time += "T00:00:00Z"
            params["time"] = time
           
        return f"{self.base_url}/wms?{urlencode(params)}"
    async def check_geoserver_alive(self) -> bool:
        """Proper GeoServer health check that:
        - Handles authentication
        - Follows redirects
        - Validates both web and REST endpoints
        - Provides detailed logging
        """
        test_cases = [
            {
                "url": f"{self.base_url}/web/",
                "name": "Web Interface",
                "accept_status": [200, 302] # Accept both success and redirect
            },
            {
                "url": f"{self.base_url}/rest/about/version",
                "name": "REST API",
                "accept_status": [200] # Must return 200
            }
        ]
        for attempt in range(1, self.max_retries + 1):
            try:
                async with httpx.AsyncClient(
                    auth=self.auth, # Critical for REST API
                    timeout=self.timeout,
                    follow_redirects=True # Essential for web interface
                ) as client:
                    for test in test_cases:
                        try:
                            response = await client.get(test["url"])
                            if response.status_code not in test["accept_status"]:
                                logger.warning(
                                    f"GeoServer {test['name']} check failed (attempt {attempt}): "
                                    f"Status {response.status_code} (expected {test['accept_status']})"
                                )
                                break
                            logger.debug(f"GeoServer {test['name']} check passed")
                        except Exception as e:
                            logger.warning(
                                f"GeoServer {test['name']} connection failed (attempt {attempt}): {str(e)}"
                            )
                            break
                    else:
                        # All tests passed
                        return True
               
                if attempt < self.max_retries:
                    await asyncio.sleep(2 ** attempt) # Exponential backoff
                   
            except Exception as e:
                logger.error(f"GeoServer health check error (attempt {attempt}): {str(e)}")
                if attempt < self.max_retries:
                    await asyncio.sleep(2 ** attempt)
       
        return False
    # Run this once to clean up old configuration
    async def cleanup_old_stores(self):
        """Clean up any existing stores before migration"""
        async with httpx.AsyncClient(auth=self.auth) as client:
            # Delete mosaic store if exists
            await client.delete(
                f"{self.base_url}/rest/workspaces/{self.workspace}/coveragestores/chirps_final_mosaic?recurse=true"
            )
            # Delete any netcdf_* stores
            stores_res = await client.get(
                f"{self.base_url}/rest/workspaces/{self.workspace}/coveragestores.json"
            )
            for store in stores_res.json().get('coverageStores', {}).get('coverageStore', []):
                if store['name'].startswith('netcdf_'):
                    await client.delete(
                        f"{self.base_url}/rest/workspaces/{self.workspace}/coveragestores/{store['name']}?recurse=true"
                    )