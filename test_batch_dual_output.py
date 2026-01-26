#!/usr/bin/env python3
"""
Test dual-output format (summary + details) for batch analysis.
"""
import requests
import pandas as pd
from io import BytesIO
import zipfile

BASE_URL = "http://localhost:8000"
ENDPOINT = f"{BASE_URL}/batch_analysis/points"

# Create test data
test_data = {
    "local": ["Brasília"],
    "latitude": [-15.8],
    "longitude": [-47.9]
}

df = pd.DataFrame(test_data)

print("=" * 80)
print("Testing Dual-Output Format (Summary + Details)")
print("=" * 80)

# Test 1: XLSX with temperature (should have events)
print("\n📊 Test 1: XLSX format with Temperature Max")
print("-" * 80)

xlsx_buffer = BytesIO()
df.to_excel(xlsx_buffer, index=False, engine='openpyxl')
xlsx_buffer.seek(0)

files = {'file': ('test_temp.xlsx', xlsx_buffer, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
data = {
    'variable_type': 'temp_max',
    'source': 'temp_max',
    'threshold': 30.0,
    'start_date': '2024-01-01',
    'end_date': '2024-12-31',
    'consecutive_days': 1
}

try:
    response = requests.post(ENDPOINT, files=files, data=data, timeout=120)

    if response.status_code == 200:
        print("✅ Success!")

        # Save and read XLSX
        with open('test_temp_analise.xlsx', 'wb') as f:
            f.write(response.content)

        print(f"\nFile saved: test_temp_analise.xlsx")

        # Read both sheets
        df_summary = pd.read_excel(BytesIO(response.content), sheet_name='Resumo')
        df_details = pd.read_excel(BytesIO(response.content), sheet_name='Detalhes')

        print(f"\n📋 Summary Sheet ({len(df_summary)} rows):")
        print(df_summary.to_string(index=False))

        print(f"\n📋 Details Sheet ({len(df_details)} rows, showing first 10):")
        print(df_details.head(10).to_string(index=False))

        # Check datetime format
        if not df_details.empty:
            print(f"\n✓ Date column type: {df_details['data_evento'].dtype}")

    else:
        print(f"❌ Error: {response.status_code}")
        print(response.text)

except Exception as e:
    print(f"❌ Error: {e}")

# Test 2: CSV (ZIP) format
print("\n\n📊 Test 2: CSV format (ZIP with 2 files)")
print("-" * 80)

csv_buffer = BytesIO()
df.to_csv(csv_buffer, index=False, encoding='utf-8')
csv_buffer.seek(0)

files = {'file': ('test_temp.csv', csv_buffer, 'text/csv')}

try:
    response = requests.post(ENDPOINT, files=files, data=data, timeout=120)

    if response.status_code == 200:
        print("✅ Success!")

        # Save ZIP file
        with open('test_temp_analise.zip', 'wb') as f:
            f.write(response.content)

        print(f"\nFile saved: test_temp_analise.zip")

        # Extract and read CSVs
        with zipfile.ZipFile(BytesIO(response.content)) as zf:
            print(f"\nZIP contents: {zf.namelist()}")

            # Read summary
            with zf.open('test_temp_resumo.csv') as f:
                df_summary = pd.read_csv(f)
                print(f"\n📋 Summary CSV ({len(df_summary)} rows):")
                print(df_summary.to_string(index=False))

            # Read details
            with zf.open('test_temp_detalhes.csv') as f:
                df_details = pd.read_csv(f)
                print(f"\n📋 Details CSV ({len(df_details)} rows, showing first 10):")
                print(df_details.head(10).to_string(index=False))

                # Check date format
                if not df_details.empty:
                    print(f"\n✓ First date value: {df_details['data_evento'].iloc[0]}")
                    print(f"✓ Date column type: {df_details['data_evento'].dtype}")
    else:
        print(f"❌ Error: {response.status_code}")
        print(response.text)

except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "=" * 80)
print("Tests complete!")
print("=" * 80)
