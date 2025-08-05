import httpx
import os
import aiofiles
from urllib.parse import urlencode
from fastapi import HTTPException

class GeoServerService:
    def __init__(self):
        self.url = "http://localhost:8080/geoserver/wms"
        self.rest_url = "http://localhost:8080/geoserver/rest"
        self.credentials = ("admin", "geoserver")
        self.workspace = "precipitation_ws"
        self.mosaic_base_dir = "/data/mosaics"

    async def generate_map_url(self, lat, lon, source, date, zoom, width, height):
        layer_name = await self.ensure_mosaic(source, date)
        params = {
            "service": "WMS",
            "version": "1.1.1",
            "request": "GetMap",
            "layers": f"{self.workspace}:{layer_name}",
            "bbox": f"{lon-0.1},{lat-0.1},{lon+0.1},{lat+0.1}",
            "width": width,
            "height": height,
            "srs": "EPSG:4326",
            "format": "image/png",
            "time": date,
        }
        return f"{self.url}?{urlencode(params)}"

#    async def ensure_mosaic(self, source: str, date: str) -> str:
    async def ensure_mosaic_and_harvest(source: str, date: str) -> str:
        store_name = f"{source}_mosaic"
        layer_name = store_name
        mosaic_dir = os.path.join(MOSAIC_BASE_DIR, source)
        os.makedirs(mosaic_dir, exist_ok=True)
        
        # TODO: Replace with actual function to get NetCDF bytes
        netcdf_content = b""  # e.g., await get_netcdf_bytes(source, date)
        
        netcdf_filename = f"precip_{date.replace('-', '')}.nc"
        netcdf_path = os.path.join(mosaic_dir, netcdf_filename)
        
        if not os.path.exists(netcdf_path):
            async with aiofiles.open(netcdf_path, 'wb') as f:
                await f.write(netcdf_content)
        
        async with httpx.AsyncClient(auth=(GEOSERVER_USERNAME, GEOSERVER_PASSWORD)) as client:
            response = await client.get(f"{GEOSERVER_REST_URL}/workspaces/{WORKSPACE}/coveragestores/{store_name}")
            if response.status_code != 200:
                headers = {"Content-Type": "text/xml"}
                data = f"""<coverageStore>
                    <name>{store_name}</name>
                    <type>ImageMosaic</type>
                    <enabled>true</enabled>
                    <workspace>{WORKSPACE}</workspace>
                    <url>file:{mosaic_dir}</url>
                </coverageStore>"""
                response = await client.post(f"{GEOSERVER_REST_URL}/workspaces/{WORKSPACE}/coveragestores", headers=headers, content=data)
                if response.status_code != 201:
                    raise HTTPException(status_code=500, detail="Failed to create mosaic store")
        
        headers = {"Content-Type": "text/plain"}
        harvest_data = f"file://{netcdf_path}"
        async with httpx.AsyncClient(auth=(GEOSERVER_USERNAME, GEOSERVER_PASSWORD)) as client:
            response = await client.post(f"{GEOSERVER_REST_URL}/workspaces/{WORKSPACE}/coveragestores/{store_name}/external.imagemosaic", headers=headers, content=harvest_data)
            if response.status_code not in (200, 201):
                raise HTTPException(status_code=500, detail="Failed to harvest granule")
        
        return layer_name