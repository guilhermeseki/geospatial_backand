#!/usr/bin/env python3
"""
Analyze GLM FED data by Brazilian mesoregions.

This script:
1. Downloads mesoregion boundaries from IBGE
2. Loads existing GLM FED GeoTIFF files
3. Calculates statistics for each mesoregion
4. Creates a summary report
"""

import geopandas as gpd
import rasterio
import numpy as np
import pandas as pd
from pathlib import Path
from rasterstats import zonal_stats
import matplotlib.pyplot as plt
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def download_mesoregion_boundaries(output_dir: Path):
    """
    Download Brazil mesoregion boundaries from IBGE.

    Returns:
        GeoDataFrame with mesoregion boundaries
    """
    logger.info("Downloading mesoregion boundaries from IBGE...")

    # IBGE official mesoregion boundaries (2020)
    url = "https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais/malhas_municipais/municipio_2020/Brasil/BR/BR_Mesorregioes_2020.zip"

    try:
        mesoregions = gpd.read_file(url)
        logger.info(f"✓ Loaded {len(mesoregions)} mesoregions")

        # Save locally for future use
        output_file = output_dir / "mesoregions.geojson"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        mesoregions.to_file(output_file, driver='GeoJSON')
        logger.info(f"✓ Saved to {output_file}")

        return mesoregions

    except Exception as e:
        logger.error(f"Failed to download from IBGE: {e}")
        logger.info("Trying alternative source...")

        # Alternative: try simplified version
        try:
            url_alt = "https://raw.githubusercontent.com/tbrugz/geodata-br/master/geojson/geojs-100-meso.json"
            mesoregions = gpd.read_file(url_alt)
            logger.info(f"✓ Loaded {len(mesoregions)} mesoregions from alternative source")

            output_file = output_dir / "mesoregions.geojson"
            output_file.parent.mkdir(parents=True, exist_ok=True)
            mesoregions.to_file(output_file, driver='GeoJSON')

            return mesoregions
        except Exception as e2:
            logger.error(f"Alternative source also failed: {e2}")
            raise


def analyze_glm_by_mesoregion(
    geotiff_dir: Path,
    mesoregions: gpd.GeoDataFrame,
    output_dir: Path
):
    """
    Calculate GLM FED statistics for each mesoregion.

    Args:
        geotiff_dir: Directory containing GLM FED GeoTIFF files
        mesoregions: GeoDataFrame with mesoregion boundaries
        output_dir: Directory to save results
    """
    logger.info("="*80)
    logger.info("ANALYZING GLM FED BY MESOREGION")
    logger.info("="*80)

    # Find all GeoTIFF files
    geotiff_files = sorted(list(geotiff_dir.glob("glm_fed_*.tif")))
    logger.info(f"Found {len(geotiff_files)} GeoTIFF files")

    if not geotiff_files:
        logger.error("No GeoTIFF files found!")
        return None

    # Use a sample of files (every 7 days to reduce processing time)
    sample_files = geotiff_files[::7]
    logger.info(f"Using {len(sample_files)} files for analysis (every 7 days)")

    results = []

    for idx, geotiff_file in enumerate(sample_files, 1):
        logger.info(f"Processing {idx}/{len(sample_files)}: {geotiff_file.name}")

        try:
            # Extract date from filename
            date_str = geotiff_file.stem.split('_')[-1]
            file_date = datetime.strptime(date_str, '%Y%m%d')

            # Calculate zonal statistics
            stats = zonal_stats(
                mesoregions,
                str(geotiff_file),
                stats=['mean', 'max', 'sum', 'count'],
                nodata=np.nan,
                all_touched=True
            )

            # Add to results
            for meso_idx, meso_stats in enumerate(stats):
                if meso_stats['count'] is not None and meso_stats['count'] > 0:
                    result = {
                        'date': file_date,
                        'mesoregion_id': meso_idx,
                        'mean_fed': meso_stats.get('mean', 0),
                        'max_fed': meso_stats.get('max', 0),
                        'total_fed': meso_stats.get('sum', 0),
                        'pixel_count': meso_stats['count']
                    }
                    results.append(result)

        except Exception as e:
            logger.error(f"Failed to process {geotiff_file.name}: {e}")
            continue

    if not results:
        logger.error("No results generated!")
        return None

    # Convert to DataFrame
    df = pd.DataFrame(results)
    logger.info(f"✓ Generated {len(df)} result rows")

    # Add mesoregion names
    mesoregions['mesoregion_id'] = range(len(mesoregions))

    # Determine name column (varies by source)
    name_col = None
    for col in ['NM_MESO', 'name', 'NOME', 'nome']:
        if col in mesoregions.columns:
            name_col = col
            break

    if name_col:
        df = df.merge(
            mesoregions[['mesoregion_id', name_col]].rename(columns={name_col: 'mesoregion_name'}),
            on='mesoregion_id',
            how='left'
        )

    # Calculate summary statistics per mesoregion
    summary = df.groupby('mesoregion_id').agg({
        'mean_fed': ['mean', 'std', 'max'],
        'max_fed': ['mean', 'max'],
        'total_fed': 'sum'
    }).round(2)

    summary.columns = ['_'.join(col).strip() for col in summary.columns.values]

    if name_col:
        summary = summary.merge(
            mesoregions[['mesoregion_id', name_col]].rename(columns={name_col: 'mesoregion_name'}),
            left_index=True,
            right_on='mesoregion_id',
            how='left'
        )
        summary = summary.set_index('mesoregion_name')

    # Sort by mean activity
    summary = summary.sort_values('mean_fed_mean', ascending=False)

    logger.info("\n" + "="*80)
    logger.info("TOP 20 MESOREGIONS BY LIGHTNING ACTIVITY")
    logger.info("="*80)
    print(summary.head(20))

    # Save results
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save detailed results
    csv_file = output_dir / f"glm_fed_by_mesoregion_detailed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    df.to_csv(csv_file, index=False)
    logger.info(f"✓ Saved detailed results to {csv_file}")

    # Save summary
    summary_file = output_dir / f"glm_fed_by_mesoregion_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    summary.to_csv(summary_file)
    logger.info(f"✓ Saved summary to {summary_file}")

    # Create visualization
    create_visualization(summary, mesoregions, output_dir)

    return summary


def create_visualization(summary: pd.DataFrame, mesoregions: gpd.GeoDataFrame, output_dir: Path):
    """
    Create visualization of GLM FED by mesoregion.
    """
    logger.info("Creating visualizations...")

    fig, axes = plt.subplots(1, 2, figsize=(20, 8))

    # Bar chart of top 20 mesoregions
    ax1 = axes[0]
    top20 = summary.head(20).copy()
    top20 = top20.reset_index()

    name_col = 'mesoregion_name' if 'mesoregion_name' in top20.columns else top20.columns[0]

    y_pos = np.arange(len(top20))
    ax1.barh(y_pos, top20['mean_fed_mean'], color='steelblue')
    ax1.set_yticks(y_pos)
    ax1.set_yticklabels(top20[name_col], fontsize=8)
    ax1.invert_yaxis()
    ax1.set_xlabel('Mean Lightning Activity (events per pixel)', fontsize=10)
    ax1.set_title('Top 20 Mesoregions by Lightning Activity', fontsize=12, fontweight='bold')
    ax1.grid(axis='x', alpha=0.3)

    # Map visualization
    ax2 = axes[1]

    # Merge summary data with geometries
    mesoregions_plot = mesoregions.copy()
    mesoregions_plot['mesoregion_id'] = range(len(mesoregions_plot))

    if 'mesoregion_id' in summary.reset_index().columns:
        mesoregions_plot = mesoregions_plot.merge(
            summary.reset_index()[['mesoregion_id', 'mean_fed_mean']],
            on='mesoregion_id',
            how='left'
        )

    if 'mean_fed_mean' in mesoregions_plot.columns:
        mesoregions_plot.plot(
            column='mean_fed_mean',
            cmap='YlOrRd',
            legend=True,
            ax=ax2,
            edgecolor='black',
            linewidth=0.3,
            legend_kwds={'label': 'Mean Lightning Activity (events/pixel)'}
        )
    else:
        mesoregions_plot.plot(ax=ax2, edgecolor='black', facecolor='lightgray')

    ax2.set_title('Lightning Activity by Mesoregion', fontsize=12, fontweight='bold')
    ax2.axis('off')

    plt.tight_layout()

    output_file = output_dir / f"glm_fed_mesoregion_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    logger.info(f"✓ Saved visualization to {output_file}")
    plt.close()


if __name__ == "__main__":
    from app.config.settings import get_settings

    settings = get_settings()

    # Specific mesoregion codes to analyze
    MESOREGION_CODES = [
        2702, 2503, 2603, 2403, 2802, 3505, 3503, 3510, 3304, 1501,
        3504, 2502, 3507, 3111, 3203, 3106, 2402, 1303, 3303, 5203,
        2103, 2903, 5002, 4102, 4303, 4105, 4304, 2906, 2202, 2306,
        5104, 4108, 5301, 2901, 4205, 3511, 2305, 3103, 4388, 4377,
        2703, 5003, 5204, 2104, 2404, 1102, 2803, 3202, 3514, 3512,
        1101, 1502, 3509, 2504, 2604, 3107, 1503, 4110, 2303, 4305,
        2605, 2905, 3515, 3306, 2904, 5102, 1504, 4302, 2301, 3101,
        3201, 3301, 5201, 4101, 4301, 1301, 4202, 2302, 4103, 3102,
        1401, 1601, 3302, 5202, 2101, 5101, 2201, 4104, 1701, 4201,
        3109, 2102, 4106, 2401, 1702, 5001, 3506, 3508, 3502, 4203,
        2701, 2501, 2601, 2801, 2304, 5105, 1506, 4109, 2204, 4307,
        1302, 5004, 5103, 1505, 4107, 2203, 4306, 1304, 2907, 4206,
        2307, 1402, 1602, 3204, 3305, 5205, 2105, 3110, 2602, 3501,
        3105, 1202, 4204, 1201, 3104, 3513, 3108, 2902, 3112
    ]

    geotiff_dir = Path(settings.DATA_DIR) / "glm_fed"
    output_dir = Path("/opt/geospatial_backend/analysis_results")
    shapefile_dir = Path("/opt/geospatial_backend/data/shapefiles")

    # Check if mesoregion boundaries exist locally
    local_mesoregions = shapefile_dir / "mesoregions.geojson"

    if local_mesoregions.exists():
        logger.info(f"Loading mesoregions from {local_mesoregions}")
        mesoregions = gpd.read_file(local_mesoregions)
    else:
        mesoregions = download_mesoregion_boundaries(shapefile_dir)

    logger.info(f"Mesoregions columns: {mesoregions.columns.tolist()}")
    logger.info(f"Mesoregions CRS: {mesoregions.crs}")

    # Filter to only requested mesoregions
    code_col = None
    for col in ['CD_GEOCME', 'cd_geocme', 'geocodigo', 'codigo']:
        if col in mesoregions.columns:
            code_col = col
            break

    if code_col:
        logger.info(f"Using code column: {code_col}")
        mesoregions[code_col] = mesoregions[code_col].astype(int)
        mesoregions = mesoregions[mesoregions[code_col].isin(MESOREGION_CODES)]
        logger.info(f"Filtered to {len(mesoregions)} mesoregions")
    else:
        logger.warning(f"Could not find code column. Available columns: {mesoregions.columns.tolist()}")

    # Ensure WGS84
    if mesoregions.crs != "EPSG:4326":
        logger.info("Converting to WGS84...")
        mesoregions = mesoregions.to_crs("EPSG:4326")

    # Run analysis
    summary = analyze_glm_by_mesoregion(geotiff_dir, mesoregions, output_dir)

    if summary is not None:
        logger.info("\n" + "="*80)
        logger.info("✓ ANALYSIS COMPLETE!")
        logger.info("="*80)
        logger.info(f"Results saved to: {output_dir}")
