"""
Runner script for downloading ECV (Essential Climate Variables) climatology data.

This script downloads monthly climatology data (1991-2020 reference period)
for Brazil from the Copernicus Climate Data Store.

Available variables:
- surface_air_temperature: Monthly temperature climatology
- surface_air_relative_humidity: Monthly humidity climatology
- volumetric_soil_moisture_for_0_to_7cm_layer: Monthly soil moisture climatology
- precipitation: Monthly precipitation climatology

Usage:
    # Download temperature climatology with ERA5 (0.25° resolution)
    python app/run_ecv_climatology.py

    # Download all variables
    python app/run_ecv_climatology.py --all

    # Download specific variable with ERA5-Land (0.1° resolution)
    python app/run_ecv_climatology.py --variable surface_air_relative_humidity --origin era5_land

    # Download using 1981-2010 reference period
    python app/run_ecv_climatology.py --reference-period 1981_2010
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.workflows.data_processing.ecv_climatology_flow import (
    download_ecv_climatology_flow,
    ECV_VARIABLE_MAPPING
)


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Download ECV monthly climatology data for Brazil",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download temperature climatology (default)
  python app/run_ecv_climatology.py

  # Download all available variables
  python app/run_ecv_climatology.py --all

  # Download specific variable with high resolution
  python app/run_ecv_climatology.py --variable precipitation --origin era5_land

  # Download humidity with 1981-2010 reference period
  python app/run_ecv_climatology.py --variable surface_air_relative_humidity --reference-period 1981_2010

  # Don't clip to Brazil (download full bbox)
  python app/run_ecv_climatology.py --no-clip

  # Keep raw GRIB files (don't cleanup)
  python app/run_ecv_climatology.py --no-cleanup
        """
    )

    parser.add_argument(
        "--variable",
        type=str,
        default="surface_air_temperature",
        choices=list(ECV_VARIABLE_MAPPING.keys()),
        help="ECV variable to download (default: surface_air_temperature)"
    )

    parser.add_argument(
        "--origin",
        type=str,
        default="era5",
        choices=["era5", "era5_land"],
        help="Data source: era5 (0.25°) or era5_land (0.1°) (default: era5)"
    )

    parser.add_argument(
        "--product-type",
        type=str,
        default="climatology",
        choices=["climatology", "monthly_mean", "anomaly"],
        help="Product type (default: climatology)"
    )

    parser.add_argument(
        "--reference-period",
        type=str,
        default="1991_2020",
        choices=["1981_2010", "1991_2020"],
        help="Climate reference period (default: 1991_2020)"
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help="Download all available variables (ignores --variable)"
    )

    parser.add_argument(
        "--no-clip",
        action="store_true",
        help="Don't clip to Brazil boundary (download full bbox)"
    )

    parser.add_argument(
        "--no-cleanup",
        action="store_true",
        help="Keep raw GRIB files after processing"
    )

    args = parser.parse_args()

    # Determine which variables to download
    if args.all:
        variables = list(ECV_VARIABLE_MAPPING.keys())
        print(f"Downloading all {len(variables)} ECV variables:")
        for var in variables:
            print(f"  - {var}")
    else:
        variables = [args.variable]
        print(f"Downloading single variable: {args.variable}")

    print(f"\nConfiguration:")
    print(f"  Origin: {args.origin}")
    print(f"  Product type: {args.product_type}")
    print(f"  Reference period: {args.reference_period}")
    print(f"  Clip to Brazil: {not args.no_clip}")
    print(f"  Cleanup raw files: {not args.no_cleanup}")
    print("=" * 80)

    # Download each variable
    for i, variable in enumerate(variables, 1):
        if len(variables) > 1:
            print(f"\n[{i}/{len(variables)}] Processing: {variable}")
            print("=" * 80)

        try:
            download_ecv_climatology_flow(
                variable=variable,
                origin=args.origin,
                product_type=args.product_type,
                reference_period=args.reference_period,
                clip_to_brazil=not args.no_clip,
                cleanup=not args.no_cleanup
            )
        except Exception as e:
            print(f"ERROR processing {variable}: {e}")
            if not args.all:
                # If downloading single variable, exit on error
                raise
            else:
                # If downloading all, continue to next variable
                print(f"Continuing to next variable...")
                continue

    print("\n" + "=" * 80)
    print("✓ ALL DOWNLOADS COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
