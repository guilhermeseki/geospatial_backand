# Batch Point Analysis - Input/Output Examples

## Example Request

### Input File: `locations.xlsx`

| local          | latitude | longitude |
|----------------|----------|-----------|
| Brasília       | -15.8    | -47.9     |
| São Paulo      | -23.5    | -46.6     |
| Rio de Janeiro | -22.9    | -43.2     |

### Request Parameters

```json
{
  "variable_type": "temp_max",
  "source": "temp_max",
  "threshold": 35.0,
  "start_date": "2024-01-01",
  "end_date": "2024-12-31",
  "consecutive_days": 1
}
```

---

## Output: `locations_analise.xlsx`

### Sheet 1: "Resumo" (Summary)

| local          | latitude | longitude | variavel           | fonte    | periodo                    | limiar | numero_eventos | eventos/ano |
|----------------|----------|-----------|--------------------|----------|----------------------------|--------|----------------|-------------|
| Brasília       | -15.8    | -47.9     | Temperatura Máxima | TEMP_MAX | 01/01/2024-31/12/2024      | 35.0   | 3              | 2.99        |
| São Paulo      | -23.5    | -46.6     | Temperatura Máxima | TEMP_MAX | 01/01/2024-31/12/2024      | 35.0   | 1              | 1.00        |
| Rio de Janeiro | -22.9    | -43.2     | Temperatura Máxima | TEMP_MAX | 01/01/2024-31/12/2024      | 35.0   | 5              | 4.99        |

**Total:** 3 rows (one per location)

---

### Sheet 2: "Detalhes" (Details)

| local          | latitude | longitude | variavel           | fonte    | data_evento | valor_evento |
|----------------|----------|-----------|--------------------|----------|-------------|--------------|
| Brasília       | -15.8    | -47.9     | Temperatura Máxima | TEMP_MAX | 2024-01-15  | 36.2         |
| Brasília       | -15.8    | -47.9     | Temperatura Máxima | TEMP_MAX | 2024-02-22  | 37.1         |
| Brasília       | -15.8    | -47.9     | Temperatura Máxima | TEMP_MAX | 2024-09-10  | 35.8         |
| São Paulo      | -23.5    | -46.6     | Temperatura Máxima | TEMP_MAX | 2024-03-05  | 35.4         |
| Rio de Janeiro | -22.9    | -43.2     | Temperatura Máxima | TEMP_MAX | 2024-01-08  | 38.5         |
| Rio de Janeiro | -22.9    | -43.2     | Temperatura Máxima | TEMP_MAX | 2024-01-12  | 36.7         |
| Rio de Janeiro | -22.9    | -43.2     | Temperatura Máxima | TEMP_MAX | 2024-02-18  | 39.2         |
| Rio de Janeiro | -22.9    | -43.2     | Temperatura Máxima | TEMP_MAX | 2024-02-25  | 37.8         |
| Rio de Janeiro | -22.9    | -43.2     | Temperatura Máxima | TEMP_MAX | 2024-11-30  | 40.1         |

**Total:** 9 rows (one per exceedance event)

**Note:** `data_evento` column is in **Excel datetime format** - sortable and filterable!

---

## Example with Consecutive Days Filter

### Request with consecutive_days = 3

```json
{
  "variable_type": "precipitation",
  "source": "chirps",
  "threshold": 10.0,
  "start_date": "2024-01-01",
  "end_date": "2024-12-31",
  "consecutive_days": 3
}
```

### Output: Sheet 1 "Resumo"

| local          | latitude | longitude | variavel     | fonte  | periodo                    | limiar | dias_consecutivos | numero_eventos | eventos/ano |
|----------------|----------|-----------|--------------|--------|----------------------------|--------|-------------------|----------------|-------------|
| Brasília       | -15.8    | -47.9     | Precipitação | CHIRPS | 01/01/2024-31/12/2024      | 10.0   | 3                 | 15             | 14.97       |
| São Paulo      | -23.5    | -46.6     | Precipitação | CHIRPS | 01/01/2024-31/12/2024      | 10.0   | 3                 | 22             | 21.95       |
| Rio de Janeiro | -22.9    | -43.2     | Precipitação | CHIRPS | 01/01/2024-31/12/2024      | 10.0   | 3                 | 18             | 17.97       |

**Note:** `dias_consecutivos` column **only appears when > 1**

---

## CSV Format Output

When uploading a **CSV file**, you receive a **ZIP file** containing:

### File: `locations_analise.zip`

**Contents:**
- `locations_resumo.csv` - Summary table (same structure as Resumo sheet)
- `locations_detalhes.csv` - Details table (same structure as Detalhes sheet)

**Date format in CSV:** ISO format `YYYY-MM-DD` (Excel recognizes this as dates)

---

## Supported Variable Types

| variable_type | fonte         | Description                    | Trigger Type |
|---------------|---------------|--------------------------------|--------------|
| precipitation | chirps, merge | Daily precipitation (mm)       | above        |
| temp_max      | temp_max      | Daily maximum temperature (°C) | above        |
| temp_min      | temp_min      | Daily minimum temperature (°C) | below        |
| temp_mean     | temp_mean     | Daily mean temperature (°C)    | user choice  |
| wind          | era5          | Wind speed (m/s)               | above        |
| lightning     | glm_fed       | Lightning flash density        | above        |

---

## API Endpoint

```bash
POST http://localhost:8000/batch_analysis/points
```

**Form Data:**
- `file`: CSV/XLSX file (multipart/form-data)
- `variable_type`: One of the supported types
- `source`: Data source name
- `threshold`: Numeric threshold value
- `start_date`: Start date (YYYY-MM-DD)
- `end_date`: End date (YYYY-MM-DD)
- `consecutive_days`: Optional, default = 1
- `trigger_type`: Optional, only for temp_mean ("above" or "below")

**Example with curl:**

```bash
curl -X POST "http://localhost:8000/batch_analysis/points" \
  -F "file=@locations.xlsx" \
  -F "variable_type=temp_max" \
  -F "source=temp_max" \
  -F "threshold=35.0" \
  -F "start_date=2024-01-01" \
  -F "end_date=2024-12-31" \
  -F "consecutive_days=1"
```

**Response:**
- XLSX input → `locations_analise.xlsx` (Excel file with 2 sheets)
- CSV input → `locations_analise.zip` (ZIP with 2 CSV files)
