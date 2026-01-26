"""
Location upload and validation endpoints.

Handles bulk upload of geographic points via XLSX/CSV files
with validation for Brazilian territory.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, status
from fastapi.responses import JSONResponse
from typing import Dict, List, Any
import logging

from app.utils.xlsx_validation import validate_geographic_points

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/locations", tags=["locations"])


@router.post(
    "/validate",
    response_model=Dict[str, List[Dict]],
    responses={
        200: {
            "description": "Todas as linhas são válidas",
            "content": {
                "application/json": {
                    "example": {
                        "valid_rows": [
                            {"local": "São Paulo", "latitude": -23.5505, "longitude": -46.6333},
                            {"local": "Rio de Janeiro", "latitude": -22.9068, "longitude": -43.1729}
                        ],
                        "invalid_rows": []
                    }
                }
            }
        },
        400: {
            "description": "Erro no formato do arquivo, codificação ou estrutura",
            "content": {
                "application/json": {
                    "examples": {
                        "missing_columns": {
                            "summary": "Colunas faltando",
                            "value": {"detail": "Faltam colunas obrigatórias: latitude. Colunas esperadas: local, latitude, longitude"}
                        },
                        "encoding_error": {
                            "summary": "Erro de codificação",
                            "value": {"detail": "Falha ao ler arquivo CSV com qualquer codificação suportada"}
                        },
                        "empty_file": {
                            "summary": "Arquivo vazio",
                            "value": {"detail": "Arquivo enviado está vazio"}
                        }
                    }
                }
            }
        },
        422: {
            "description": "Arquivo válido mas contém dados inválidos",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "As linhas 3,4 estão com erro!",
                        "valid_rows": [
                            {"local": "São Paulo", "latitude": -23.5505, "longitude": -46.6333}
                        ],
                        "invalid_rows": [
                            {
                                "_row_number": 3,
                                "local": "Caracas",
                                "latitude": 10.4806,
                                "longitude": -66.9036,
                                "failure_reason": "Latitude 10.4806 está fora do território brasileiro (intervalo válido: -33.7683 a 5.2711)"
                            },
                            {
                                "_row_number": 4,
                                "local": "Cidade",
                                "latitude": None,
                                "longitude": -46.6333,
                                "failure_reason": "Campo 'latitude' está ausente ou vazio"
                            }
                        ]
                    }
                }
            }
        },
        500: {
            "description": "Erro interno do servidor",
            "content": {
                "application/json": {
                    "example": {"detail": "Erro ao processar arquivo: unexpected error"}
                }
            }
        }
    }
)
async def validate_location_file(
    file: UploadFile = File(..., description="XLSX or CSV file containing location data (columns: local, latitude, longitude)")
) -> Dict[str, List[Dict]]:
    """
    Validate geographic points from an uploaded XLSX or CSV file.

    **Required file format:**
    - File types: .xlsx, .xls, or .csv
    - Required columns (case-insensitive): local, latitude, longitude
    - All coordinates must fall within Brazil's boundaries

    **Brazilian boundaries:**
    - Latitude: -33.7683 to 5.2711
    - Longitude: -73.9870 to -34.7937

    **HTTP Status Codes:**
    - `200 OK`: All rows are valid
    - `400 Bad Request`: File format error, encoding error, or missing required columns
    - `422 Unprocessable Entity`: File is valid but contains invalid data rows
    - `500 Internal Server Error`: Unexpected server error

    **Returns:**
    - `valid_rows`: List of valid location entries
    - `invalid_rows`: List of invalid entries with failure reasons

    **Example XLSX/CSV structure:**
    ```
    local           | latitude  | longitude
    São Paulo       | -23.5505  | -46.6333
    Rio de Janeiro  | -22.9068  | -43.1729
    Brasília        | -15.7942  | -47.8822
    ```

    **Example response (200 - all valid):**
    ```json
    {
      "valid_rows": [
        {"local": "São Paulo", "latitude": -23.5505, "longitude": -46.6333},
        {"local": "Rio de Janeiro", "latitude": -22.9068, "longitude": -43.1729}
      ],
      "invalid_rows": []
    }
    ```

    **Example response (422 - some invalid rows):**
    ```json
    {
      "detail": "As linhas 3,5 estão com erro!",
      "valid_rows": [
        {"local": "São Paulo", "latitude": -23.5505, "longitude": -46.6333}
      ],
      "invalid_rows": [
        {
          "_row_number": 3,
          "local": "Missing Field",
          "latitude": null,
          "longitude": -46.6333,
          "failure_reason": "Campo 'latitude' está ausente ou vazio"
        },
        {
          "_row_number": 5,
          "local": "Caracas",
          "latitude": 10.4806,
          "longitude": -66.9036,
          "failure_reason": "Latitude 10.4806 está fora do território brasileiro (intervalo válido: -33.7683 a 5.2711)"
        }
      ]
    }
    ```

    **Example response (400 - file error):**
    ```json
    {
      "detail": "Faltam colunas obrigatórias: latitude. Colunas esperadas: local, latitude, longitude"
    }
    ```
    """
    logger.info(f"Validating uploaded file: {file.filename}")

    # Check file extension
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No filename provided"
        )

    if not file.filename.lower().endswith(('.xlsx', '.xls', '.csv')):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format: {file.filename}. Only XLSX and CSV files are accepted."
        )

    try:
        # Read file content
        file_content = await file.read()

        if len(file_content) == 0:
            raise HTTPException(
                status_code=400,
                detail="Arquivo enviado está vazio"
            )

        # Validate the geographic points
        result = validate_geographic_points(file_content, file.filename)

        # Log summary
        valid_count = len(result['valid_rows'])
        invalid_count = len(result['invalid_rows'])
        logger.info(
            f"Validation complete for {file.filename}: "
            f"{valid_count} valid, {invalid_count} invalid"
        )

        # Check if validation failed due to file/structure errors
        # These errors don't have _row_number field
        if invalid_count > 0 and valid_count == 0:
            # Check if it's a structural error (no _row_number field)
            first_error = result['invalid_rows'][0]
            if '_row_number' not in first_error:
                # File-level or structural error - return 400
                raise HTTPException(
                    status_code=400,
                    detail=first_error['failure_reason']
                )

        # If there are any invalid rows (data validation errors), return 422
        if invalid_count > 0:
            # Get list of row numbers with errors
            error_rows = [str(row.get('_row_number', '?')) for row in result['invalid_rows']]
            error_rows_str = ','.join(error_rows)

            return JSONResponse(
                content={
                    "detail": f"As linhas {error_rows_str} estão com erro!",
                    "valid_rows": result['valid_rows'],
                    "invalid_rows": result['invalid_rows']
                },
                status_code=422
            )

        # All rows valid - return 200
        return JSONResponse(
            content=result,
            status_code=200
        )

    except HTTPException:
        # Re-raise HTTP exceptions
        raise

    except Exception as e:
        logger.error(f"Error validating file {file.filename}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao processar arquivo: {str(e)}"
        )


@router.post("/upload")
async def upload_locations(
    file: UploadFile = File(..., description="XLSX or CSV file containing location data")
) -> Dict:
    """
    Validate and save geographic points from an uploaded file.

    This endpoint validates the uploaded file and would typically:
    1. Validate all entries
    2. Store valid entries in the database
    3. Return summary of successful/failed entries

    **Note:** Currently returns validation results. Database integration pending.

    See `/locations/validate` for detailed format requirements.
    """
    logger.info(f"Processing location upload: {file.filename}")

    # For now, just validate the file
    # TODO: Add database integration to actually save valid locations
    file_content = await file.read()
    result = validate_geographic_points(file_content, file.filename)

    valid_count = len(result['valid_rows'])
    invalid_count = len(result['invalid_rows'])

    if invalid_count > 0 and valid_count == 0:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "No valid locations found in file",
                "invalid_rows": result['invalid_rows']
            }
        )

    return {
        "message": f"Successfully validated {valid_count} locations",
        "summary": {
            "valid_count": valid_count,
            "invalid_count": invalid_count,
            "total_processed": valid_count + invalid_count
        },
        "valid_rows": result['valid_rows'],
        "invalid_rows": result['invalid_rows']
    }
