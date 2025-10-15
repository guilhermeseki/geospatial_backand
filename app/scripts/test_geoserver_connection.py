#!/usr/bin/env python3
import asyncio
from app.services.geoserver import GeoServerService

async def main():
    print("Testing GeoServer connection...")
    gs = GeoServerService()
    
    if await gs.check_geoserver_alive():
        print("✅ GeoServer is reachable")
        # Add more manual tests here
    else:
        print("❌ Connection failed")

if __name__ == "__main__":
    asyncio.run(main())