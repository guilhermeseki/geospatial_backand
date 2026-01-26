#!/usr/bin/env python3
"""
Download ECV Climatology (1991-2020) for temperature and humidity
Simple script without Prefect to avoid database issues
"""
import cdsapi
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))
from app.config.settings import get_settings

def download_ecv(variable, origin="era5_land"):
    """Download ECV climatology for a variable"""
    settings = get_settings()
    
    # Output directory
    raw_dir = Path(settings.DATA_DIR) / "raw" / "ecv_climatology"
    raw_dir.mkdir(parents=True, exist_ok=True)
    
    # Output filename
    var_short = variable.replace("surface_air_", "").replace("_for_0_to_7cm_layer", "")
    output_file = raw_dir / f"ecv_{var_short}_{origin}_climatology_1991_2020.grib"
    
    if output_file.exists():
        print(f"✓ Already downloaded: {output_file}")
        return output_file
    
    print("=" * 80)
    print(f"Downloading: {variable}")
    print(f"Origin: {origin}")
    print("=" * 80)
    
    # Build request
    request = {
        "variable": [variable],
        "origin": [origin],
        "product_type": ["climatology"],
        "climate_reference_period": ["1991_2020"],
        "month": [
            "01", "02", "03", "04", "05", "06",
            "07", "08", "09", "10", "11", "12"
        ]
    }
    
    print("Request:", request)
    print()
    
    try:
        client = cdsapi.Client()
        print("Submitting to CDS API...")
        result = client.retrieve("ecv-for-climate-change", request)
        result.download(str(output_file))
        
        size_mb = output_file.stat().st_size / 1024 / 1024
        print(f"✓ Downloaded: {output_file}")
        print(f"  Size: {size_mb:.2f} MB")
        return output_file
        
    except Exception as e:
        print(f"✗ Download failed: {e}")
        if output_file.exists():
            output_file.unlink()
        raise

if __name__ == "__main__":
    print("ECV CLIMATOLOGY DOWNLOAD (1991-2020)")
    print("=" * 80)
    print()

    variables = [
        "surface_air_temperature",
        "surface_air_relative_humidity"
    ]

    for i, var in enumerate(variables, 1):
        print(f"\n[{i}/{len(variables)}] Processing: {var}")
        try:
            # Try ERA5-Land first, fallback to ERA5 if it fails
            try:
                download_ecv(var, origin="era5_land")
            except Exception as e:
                if "400" in str(e):
                    print("  ERA5-Land not available, trying ERA5...")
                    download_ecv(var, origin="era5")
                else:
                    raise
            print()
        except Exception as e:
            print(f"ERROR: {e}")
            continue
    
    print("\n" + "=" * 80)
    print("DOWNLOADS COMPLETE")
    print("=" * 80)
