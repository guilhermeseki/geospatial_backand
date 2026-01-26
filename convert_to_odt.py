#!/usr/bin/env python3
"""
Converter o arquivo TXT para ODT (LibreOffice Writer)
"""

from odf.opendocument import OpenDocumentText
from odf.style import Style, TextProperties, ParagraphProperties, TableColumnProperties, TableProperties
from odf.text import P, H, Span
from odf.table import Table, TableColumn, TableRow, TableCell
from odf import teletype
import re

def create_odt_from_txt(txt_file, odt_file):
    """Convert TXT to ODT with formatting"""

    # Create document
    doc = OpenDocumentText()

    # Define styles
    # Bold style
    bold_style = Style(name="Bold", family="text")
    bold_style.addElement(TextProperties(fontweight="bold"))
    doc.styles.addElement(bold_style)

    # Heading 1
    h1_style = Style(name="Heading1", family="paragraph")
    h1_style.addElement(TextProperties(fontsize="18pt", fontweight="bold"))
    h1_style.addElement(ParagraphProperties(margintop="0.5cm", marginbottom="0.3cm"))
    doc.styles.addElement(h1_style)

    # Heading 2
    h2_style = Style(name="Heading2", family="paragraph")
    h2_style.addElement(TextProperties(fontsize="14pt", fontweight="bold"))
    h2_style.addElement(ParagraphProperties(margintop="0.3cm", marginbottom="0.2cm"))
    doc.styles.addElement(h2_style)

    # Monospace (for tables and code)
    mono_style = Style(name="Monospace", family="text")
    mono_style.addElement(TextProperties(fontfamily="Courier New"))
    doc.styles.addElement(mono_style)

    # Table style
    table_style = Style(name="Table1", family="table")
    table_style.addElement(TableProperties(width="16cm", align="center"))
    doc.automaticstyles.addElement(table_style)

    # Read input file
    with open(txt_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    in_table = False
    table_lines = []

    for line in lines:
        line = line.rstrip('\n')

        # Check if line is a table delimiter
        if line.startswith('┌') or line.startswith('├') or line.startswith('└'):
            if line.startswith('┌'):
                in_table = True
                table_lines = []
            elif line.startswith('└'):
                in_table = False
                # Process table
                if table_lines:
                    add_table_to_doc(doc, table_lines)
                table_lines = []
            continue

        if in_table:
            if line.startswith('│'):
                table_lines.append(line)
            continue

        # Empty line
        if not line.strip():
            p = P()
            doc.text.addElement(p)
            continue

        # Separator line
        if line.startswith('────'):
            p = P()
            doc.text.addElement(p)
            continue

        # Heading
        if line.startswith('==='):
            continue  # Skip separator

        # Check next line for heading
        if line and not line.startswith(' '):
            # Could be a heading
            if '🖥️' in line or '☁️' in line or '💰' in line or '📊' in line or '🎯' in line or '💻' in line or '⚡' in line or '🎓' in line or '📞' in line:
                h = H(outlinelevel=1, stylename=h1_style)
                h.addText(line)
                doc.text.addElement(h)
                continue

        # Bullet points
        if line.startswith('•'):
            p = P()
            p.addText(line)
            doc.text.addElement(p)
            continue

        # Check for bold text (between **)
        if '**' in line or ':' in line and not line.startswith(' '):
            # Section headers or bold text
            p = P()
            parts = re.split(r'(\*\*.*?\*\*)', line)
            for part in parts:
                if part.startswith('**') and part.endswith('**'):
                    span = Span(stylename=bold_style)
                    span.addText(part[2:-2])
                    p.addElement(span)
                else:
                    p.addText(part)
            doc.text.addElement(p)
            continue

        # Regular paragraph
        p = P()
        p.addText(line)
        doc.text.addElement(p)

    # Save document
    doc.save(odt_file)
    print(f"✅ Documento ODT criado: {odt_file}")

def add_table_to_doc(doc, table_lines):
    """Add a table to the document"""
    if not table_lines:
        return

    # Parse table
    rows = []
    for line in table_lines:
        cells = [cell.strip() for cell in line.split('│')[1:-1]]
        if cells:
            rows.append(cells)

    if not rows:
        return

    # Create table
    table = Table()

    # Add columns
    num_cols = len(rows[0])
    for _ in range(num_cols):
        table.addElement(TableColumn())

    # Add rows
    for row_data in rows:
        row = TableRow()
        for cell_data in row_data:
            cell = TableCell()
            p = P()
            p.addText(cell_data)
            cell.addElement(p)
            row.addElement(cell)
        table.addElement(row)

    doc.text.addElement(table)

    # Add spacing after table
    p = P()
    doc.text.addElement(p)

def main():
    txt_file = '/opt/geospatial_backend/Comparacao_Hardware_vs_Nuvem_v2.txt'
    odt_file = '/opt/geospatial_backend/Comparacao_Hardware_vs_Nuvem.odt'

    print("🚀 Convertendo TXT para ODT (LibreOffice)...")
    create_odt_from_txt(txt_file, odt_file)
    print(f"📄 Arquivo criado: {odt_file}")
    print("\nAgora você pode abrir com:")
    print(f"  libreoffice {odt_file}")

if __name__ == '__main__':
    main()
