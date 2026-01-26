#!/usr/bin/env python3
"""
Create example input/output files for batch analysis documentation.
"""
import pandas as pd
from io import BytesIO

print("Creating example files...")
print("=" * 80)

# Create INPUT example
input_data = {
    "local": ["Brasília", "São Paulo", "Rio de Janeiro"],
    "latitude": [-15.8, -23.5, -22.9],
    "longitude": [-47.9, -46.6, -43.2]
}

df_input = pd.DataFrame(input_data)
df_input.to_excel("example_input.xlsx", index=False)
df_input.to_csv("example_input.csv", index=False)

print("✓ Created example_input.xlsx")
print("✓ Created example_input.csv")
print()
print("INPUT TABLE:")
print(df_input.to_string(index=False))
print()

# Create OUTPUT example - Summary
summary_data = {
    "local": ["Brasília", "São Paulo", "Rio de Janeiro"],
    "latitude": [-15.8, -23.5, -22.9],
    "longitude": [-47.9, -46.6, -43.2],
    "variavel": ["Temperatura Máxima", "Temperatura Máxima", "Temperatura Máxima"],
    "fonte": ["TEMP_MAX", "TEMP_MAX", "TEMP_MAX"],
    "periodo": ["01/01/2024-31/12/2024", "01/01/2024-31/12/2024", "01/01/2024-31/12/2024"],
    "limiar": [35.0, 35.0, 35.0],
    "numero_eventos": [3, 1, 5],
    "eventos/ano": [2.99, 1.00, 4.99]
}

df_summary = pd.DataFrame(summary_data)

# Create OUTPUT example - Details
details_data = {
    "local": ["Brasília", "Brasília", "Brasília", "São Paulo", "Rio de Janeiro",
              "Rio de Janeiro", "Rio de Janeiro", "Rio de Janeiro", "Rio de Janeiro"],
    "latitude": [-15.8, -15.8, -15.8, -23.5, -22.9, -22.9, -22.9, -22.9, -22.9],
    "longitude": [-47.9, -47.9, -47.9, -46.6, -43.2, -43.2, -43.2, -43.2, -43.2],
    "variavel": ["Temperatura Máxima"] * 9,
    "fonte": ["TEMP_MAX"] * 9,
    "data_evento": pd.to_datetime([
        "2024-01-15", "2024-02-22", "2024-09-10",
        "2024-03-05",
        "2024-01-08", "2024-01-12", "2024-02-18", "2024-02-25", "2024-11-30"
    ]),
    "valor_evento": [36.2, 37.1, 35.8, 35.4, 38.5, 36.7, 39.2, 37.8, 40.1]
}

df_details = pd.DataFrame(details_data)

# Create XLSX output example
with pd.ExcelWriter("example_output.xlsx", engine='openpyxl') as writer:
    df_summary.to_excel(writer, sheet_name='Resumo', index=False)
    df_details.to_excel(writer, sheet_name='Detalhes', index=False)

print("✓ Created example_output.xlsx (with Resumo and Detalhes sheets)")
print()

print("=" * 80)
print("OUTPUT TABLE - SHEET 1: Resumo (Summary)")
print("=" * 80)
print(df_summary.to_string(index=False))
print()

print("=" * 80)
print("OUTPUT TABLE - SHEET 2: Detalhes (Details)")
print("=" * 80)
print(df_details.to_string(index=False))
print()

print("=" * 80)
print("Files created successfully!")
print("=" * 80)
print()
print("You can now open these files in Excel:")
print("  - example_input.xlsx (input format)")
print("  - example_output.xlsx (output format with 2 sheets)")
