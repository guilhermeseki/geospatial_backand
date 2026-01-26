# app/api/routers/batch_analysis.py
"""
Batch analysis endpoints for processing multiple locations from uploaded files.

Supports:
- Point-based batch analysis (current)
- Circle area batch analysis (future)
- Polygon batch analysis (future)
"""
import logging
import asyncio
import traceback
from io import BytesIO
import zipfile

import pandas as pd
from fastapi import APIRouter, HTTPException, File, UploadFile, Form
from fastapi.responses import StreamingResponse

from app.services.climate_data import get_dataset
from app.utils.xlsx_validation import validate_geographic_points

# Import internal trigger calculation helpers
from app.api.routers.precipitation import _query_point_data_sync as _query_precipitation_sync
from app.api.routers.temperature import _query_temperature_point_data_sync as _query_temperature_sync
from app.api.routers.wind import _query_wind_point_data_sync as _query_wind_sync
from app.api.routers.lightning import _query_lightning_point_data_sync as _query_lightning_sync

# Import schema classes
from app.api.schemas.precipitation import TriggerRequest as PrecipTriggerRequest
from app.api.schemas.era5 import ERA5TriggerRequest
from app.api.schemas.wind import WindTriggerRequest
from app.api.schemas.lightning import LightningTriggerRequest


router = APIRouter(prefix="/batch_analysis", tags=["Batch Analysis"])
logger = logging.getLogger(__name__)


# Variable name mapping for output file
VARIABLE_NAMES = {
    "precipitation": "Precipitação",
    "temp_max": "Temperatura Máxima",
    "temp_min": "Temperatura Mínima",
    "temp_mean": "Temperatura Média",
    "wind": "Vento",
    "lightning": "Raios"
}

def _get_variable_display_name(variable_type: str, source: str) -> str:
    """Get display name for variable, handling new 'temperature' variable_type."""
    if variable_type == "temperature":
        # For new temperature format, use source to get display name
        return VARIABLE_NAMES.get(source, source)
    else:
        # For old format, use variable_type directly
        return VARIABLE_NAMES.get(variable_type, variable_type)


def _get_source_display_name(variable_type: str, source: str) -> str:
    """
    Get display name for data source based on variable type.

    Rules:
    - Temperature (temp_max, temp_min, temp_mean, temperature): always ERA5
    - Wind: always ERA5
    - Precipitation: CHIRPS or MERGE (based on user selection)
    - Lightning: always GOES-19
    """
    if variable_type in ["temp_max", "temp_min", "temp_mean", "temperature"]:
        return "ERA5"
    elif variable_type == "wind":
        return "ERA5"
    elif variable_type == "precipitation":
        return source.upper()  # CHIRPS or MERGE
    elif variable_type == "lightning":
        return "GOES-19"
    else:
        return source.upper()


def _determine_trigger_type(variable_type: str, source: str = None, user_trigger_type: str = None) -> str:
    """
    Determine the trigger type based on variable type and source.

    Rules:
    - temp_max or temperature+temp_max: always "above" (heat events)
    - temp_min or temperature+temp_min: always "below" (cold events)
    - temp_mean or temperature+temp_mean: user specifies, default "above"
    - precipitation/wind/lightning: always "above"
    """
    # Handle new "temperature" variable_type with source
    if variable_type == "temperature":
        if source == "temp_max":
            return "above"
        elif source == "temp_min":
            return "below"
        elif source == "temp_mean":
            return user_trigger_type or "above"

    # Handle old format
    if variable_type == "temp_max":
        return "above"
    elif variable_type == "temp_min":
        return "below"
    elif variable_type == "temp_mean":
        return user_trigger_type or "above"
    else:
        # precipitation, wind, lightning
        return "above"


def _get_data_category(variable_type: str) -> str:
    """Map variable type to data category for get_dataset()."""
    if variable_type == "precipitation":
        return "precipitation"
    elif variable_type in ["temp_max", "temp_min", "temp_mean", "temperature"]:
        return "temperature"
    elif variable_type == "wind":
        return "wind"
    elif variable_type == "lightning":
        return "lightning"
    else:
        raise ValueError(f"Unknown variable type: {variable_type}")


async def _calculate_trigger_for_point(
    variable_type: str,
    source: str,
    lat: float,
    lon: float,
    start_date: str,
    end_date: str,
    threshold: float,
    trigger_type: str,
    consecutive_days: int
) -> dict:
    """
    Calculate trigger exceedances for a single point.

    Calls internal helper functions directly for better performance in batch mode.
    Returns dict with 'n_exceedances' and 'exceedances' list.
    Returns {'n_exceedances': 0, 'exceedances': []} on error.
    """
    try:
        # Get dataset
        data_category = _get_data_category(variable_type)
        historical_ds = get_dataset(data_category, source)

        if historical_ds is None:
            logger.error(f"Dataset not loaded for {data_category}/{source}")
            return {'n_exceedances': 0, 'exceedances': []}

        # Build request object and call internal helper
        if variable_type == "precipitation":
            request = PrecipTriggerRequest(
                source=source,
                lat=lat,
                lon=lon,
                start_date=start_date,
                end_date=end_date,
                trigger=threshold,
                consecutive_days=consecutive_days
            )
            result = await asyncio.to_thread(
                _query_precipitation_sync,
                historical_ds,
                request,
                True  # is_trigger
            )

        elif variable_type in ["temp_max", "temp_min", "temp_mean", "temperature"]:
            # For new "temperature" variable_type, use source; for old types, use variable_type
            temp_source = source if variable_type == "temperature" else variable_type
            request = ERA5TriggerRequest(
                source=temp_source,
                lat=lat,
                lon=lon,
                start_date=start_date,
                end_date=end_date,
                trigger=threshold,
                trigger_type=trigger_type,
                consecutive_days=consecutive_days
            )
            result = await asyncio.to_thread(
                _query_temperature_sync,
                historical_ds,
                request,
                temp_source,  # variable_name
                True  # is_trigger
            )

        elif variable_type == "wind":
            request = WindTriggerRequest(
                source=source,
                lat=lat,
                lon=lon,
                start_date=start_date,
                end_date=end_date,
                trigger=threshold,
                consecutive_days=consecutive_days
            )
            result = await asyncio.to_thread(
                _query_wind_sync,
                historical_ds,
                request,
                True  # is_trigger
            )

        elif variable_type == "lightning":
            request = LightningTriggerRequest(
                source=source,
                lat=lat,
                lon=lon,
                start_date=start_date,
                end_date=end_date,
                trigger=threshold,
                consecutive_days=consecutive_days
            )
            result = await asyncio.to_thread(
                _query_lightning_sync,
                historical_ds,
                request,
                True  # is_trigger
            )

        else:
            raise ValueError(f"Unknown variable type: {variable_type}")

        # Return full result with exceedances list
        return {
            'n_exceedances': result.get("n_exceedances", 0),
            'exceedances': result.get("exceedances", [])
        }

    except Exception as e:
        logger.error(f"Error calculating trigger for {variable_type} at ({lat}, {lon}): {e}")
        logger.error(traceback.format_exc())
        # Return empty result on error instead of failing entire batch
        return {'n_exceedances': 0, 'exceedances': []}


def _calculate_events_per_year(num_events: int, start_date: str, end_date: str) -> float:
    """Calculate average events per year."""
    try:
        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)
        days = (end - start).days + 1
        years = days / 365.25

        if years > 0:
            return round(num_events / years, 2)
        else:
            return 0.0
    except Exception as e:
        logger.error(f"Error calculating events/year: {e}")
        return 0.0


def _format_period(start_date: str, end_date: str) -> str:
    """Format period as DD/MM/YYYY-DD/MM/YYYY."""
    try:
        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)
        return f"{start.strftime('%d/%m/%Y')}-{end.strftime('%d/%m/%Y')}"
    except Exception as e:
        logger.error(f"Error formatting period: {e}")
        return f"{start_date}-{end_date}"


@router.post("/points")
async def batch_point_analysis(
    file: UploadFile = File(..., description="CSV or XLSX file with columns: local, latitude, longitude"),
    variable_type: str = Form(...),
    source: str = Form(...),
    threshold: float = Form(...),
    start_date: str = Form(...),
    end_date: str = Form(...),
    consecutive_days: int = Form(1),
    trigger_type: str = Form(None)
):
    """
    Perform batch trigger analysis for multiple point locations.

    **Input File Format:**
    - CSV or XLSX file
    - Required columns: `local`, `latitude`, `longitude`
    - File must contain valid points within Brazil

    **Parameters:**
    - `variable_type`: precipitation, temperature, wind, lightning
    - `source`: Data source
        - precipitation: chirps or merge
        - temperature: temp_max, temp_min, or temp_mean
        - wind: wind_speed
        - lightning: glm_fed
    - `threshold`: Threshold value for trigger detection
    - `start_date`: Analysis start date (YYYY-MM-DD)
    - `end_date`: Analysis end date (YYYY-MM-DD)
    - `consecutive_days`: Minimum consecutive days (default: 1)
    - `trigger_type`: Optional, only for temperature with source=temp_mean - "above" or "below" (default: above)

    **Output:**
    - Same format as input (CSV → CSV, XLSX → XLSX)
    - Filename: `{original_name}_analise.{ext}`
    - Columns:
        1. `local` (original)
        2. `latitude` (original)
        3. `longitude` (original)
        4. `variavel` (e.g., "Precipitação")
        5. `fonte` (e.g., "CHIRPS")
        6. `periodo` (e.g., "01/01/2015-01/01/2025")
        7. `limiar` (threshold value)
        8. `dias_consecutivos` (only if > 1)
        9. `numero_eventos` (count of exceedances)
        10. `eventos/ano` (average per year)

    **Trigger Type Logic:**
    - temperature with source=temp_max: always "above" (detects heat events)
    - temperature with source=temp_min: always "below" (detects cold events)
    - temperature with source=temp_mean: user specifies "above" or "below"
    - precipitation/wind/lightning: always "above"

    **Examples:**
    ```bash
    # Precipitation example
    curl -X POST "http://localhost:8000/batch_analysis/points" \\
      -F "file=@locations.xlsx" \\
      -F "variable_type=precipitation" \\
      -F "source=chirps" \\
      -F "threshold=50.0" \\
      -F "start_date=2015-01-01" \\
      -F "end_date=2025-01-01" \\
      -F "consecutive_days=1"

    # Temperature example
    curl -X POST "http://localhost:8000/batch_analysis/points" \\
      -F "file=@locations.xlsx" \\
      -F "variable_type=temperature" \\
      -F "source=temp_max" \\
      -F "threshold=28.0" \\
      -F "start_date=2024-01-01" \\
      -F "end_date=2024-12-31" \\
      -F "consecutive_days=3"
    ```
    """
    try:
        # Read uploaded file
        file_content = await file.read()
        filename = file.filename

        # Validate file format and points
        logger.info(f"Validating uploaded file: {filename}")
        validation_result = validate_geographic_points(file_content, filename)

        if not validation_result["valid_rows"]:
            raise HTTPException(
                status_code=400,
                detail=f"No valid locations found in file. Errors: {validation_result['invalid_rows']}"
            )

        valid_locations = validation_result["valid_rows"]
        logger.info(f"Found {len(valid_locations)} valid locations")

        # Determine trigger type
        determined_trigger_type = _determine_trigger_type(variable_type, source, trigger_type)

        # Process each location
        summary_rows = []
        details_rows = []

        for idx, location in enumerate(valid_locations):
            logger.info(f"Processing location {idx+1}/{len(valid_locations)}: {location['local']}")

            trigger_result = await _calculate_trigger_for_point(
                variable_type=variable_type,
                source=source,
                lat=location["latitude"],
                lon=location["longitude"],
                start_date=start_date,
                end_date=end_date,
                threshold=threshold,
                trigger_type=determined_trigger_type,
                consecutive_days=consecutive_days
            )

            num_events = trigger_result['n_exceedances']
            exceedances = trigger_result['exceedances']

            events_per_year = _calculate_events_per_year(num_events, start_date, end_date)
            period_str = _format_period(start_date, end_date)

            # Build summary row
            summary_row = {
                "local": location["local"],
                "latitude": location["latitude"],
                "longitude": location["longitude"],
                "variavel": _get_variable_display_name(variable_type, source),
                "fonte": _get_source_display_name(variable_type, source),
                "periodo": period_str,
                "limiar": threshold,
                "numero_eventos": num_events,
                "eventos/ano": events_per_year
            }

            # Add dias_consecutivos only if > 1
            if consecutive_days > 1:
                summary_row["dias_consecutivos"] = consecutive_days
            else:
                summary_row["dias_consecutivos"] = ""

            summary_rows.append(summary_row)

            # Build details rows (one per exceedance)
            for exc in exceedances:
                detail_row = {
                    "local": location["local"],
                    "latitude": location["latitude"],
                    "longitude": location["longitude"],
                    "variavel": _get_variable_display_name(variable_type, source),
                    "fonte": _get_source_display_name(variable_type, source),
                    "data_evento": exc['date'],
                    "valor_evento": exc['value']
                }
                details_rows.append(detail_row)

        # Create summary DataFrame
        if consecutive_days > 1:
            summary_columns = [
                "local", "latitude", "longitude", "variavel", "fonte",
                "periodo", "limiar", "dias_consecutivos", "numero_eventos", "eventos/ano"
            ]
        else:
            summary_columns = [
                "local", "latitude", "longitude", "variavel", "fonte",
                "periodo", "limiar", "numero_eventos", "eventos/ano"
            ]
            # Remove dias_consecutivos column if not used
            for r in summary_rows:
                r.pop("dias_consecutivos", None)

        df_summary = pd.DataFrame(summary_rows, columns=summary_columns)

        # Create details DataFrame
        details_columns = ["local", "latitude", "longitude", "variavel", "fonte", "data_evento", "valor_evento"]
        df_details = pd.DataFrame(details_rows, columns=details_columns)

        # Determine output format and filename
        original_name = filename.rsplit(".", 1)[0]
        file_extension = filename.rsplit(".", 1)[1].lower()

        output_buffer = BytesIO()

        if file_extension in ["xlsx", "xls"]:
            # XLSX: Create file with 2 sheets (Resumo + Detalhes)
            output_filename = f"{original_name}_analise.xlsx"

            # Convert data_evento to Excel datetime for details sheet
            if not df_details.empty:
                df_details['data_evento'] = pd.to_datetime(df_details['data_evento'])

            with pd.ExcelWriter(output_buffer, engine='openpyxl') as writer:
                df_summary.to_excel(writer, sheet_name='Resumo', index=False)
                df_details.to_excel(writer, sheet_name='Detalhes', index=False)

            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            logger.info(f"XLSX: Returning {len(summary_rows)} summary rows + {len(details_rows)} detail rows")

        elif file_extension == "csv":
            # CSV: Create ZIP with 2 files (resumo.csv + detalhes.csv)
            output_filename = f"{original_name}_analise.zip"

            # Convert data_evento to datetime for CSV as well (Excel recognizes ISO format)
            if not df_details.empty:
                df_details['data_evento'] = pd.to_datetime(df_details['data_evento'])

            with zipfile.ZipFile(output_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Summary CSV with UTF-8 BOM for Excel compatibility
                summary_csv = BytesIO()
                df_summary.to_csv(summary_csv, index=False, encoding='utf-8-sig')
                zipf.writestr(f"{original_name}_resumo.csv", summary_csv.getvalue())

                # Details CSV (datetime in ISO format: YYYY-MM-DD) with UTF-8 BOM
                details_csv = BytesIO()
                df_details.to_csv(details_csv, index=False, encoding='utf-8-sig')
                zipf.writestr(f"{original_name}_detalhes.csv", details_csv.getvalue())

            media_type = "application/zip"
            logger.info(f"ZIP: Returning {len(summary_rows)} summary rows + {len(details_rows)} detail rows")

        else:
            raise HTTPException(status_code=400, detail="Unsupported file format")

        output_buffer.seek(0)

        # Return file as download
        return StreamingResponse(
            output_buffer,
            media_type=media_type,
            headers={
                "Content-Disposition": f"attachment; filename={output_filename}"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in batch point analysis: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Batch analysis failed: {str(e)}")


@router.options("/points")
async def options_batch_points():
    """OPTIONS endpoint for CORS preflight - /points"""
    return {}
