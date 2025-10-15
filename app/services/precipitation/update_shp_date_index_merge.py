from osgeo import ogr
from pathlib import Path
from datetime import datetime
import re
import shutil

# === CONFIG ===
mosaic_dir = Path("/mnt/workwork/geoserver_data/merge")
shapefile_name = "merge.shp"
old_shp = mosaic_dir / shapefile_name
fixed_shp = mosaic_dir / "merge_fixed.shp"

# Function to extract date from filename (string with YYYYMMDD)
def extract_date_from_string(text):
    match = re.search(r"(\d{8})", text)
    if match:
        return datetime.strptime(match.group(1), "%Y%m%d")
    return None

# Open original shapefile
driver = ogr.GetDriverByName("ESRI Shapefile")
source_ds = driver.Open(str(old_shp), 0)
source_layer = source_ds.GetLayer()

# Remove existing fixed shapefile if it exists
if fixed_shp.exists():
    driver.DeleteDataSource(str(fixed_shp))

# Create new shapefile
target_ds = driver.CreateDataSource(str(fixed_shp))
target_layer = target_ds.CreateLayer("merge_fixed", geom_type=ogr.wkbPolygon)

# Define fields
target_layer.CreateField(ogr.FieldDefn("location", ogr.OFTString))

ingestion_field = ogr.FieldDefn("ingestion", ogr.OFTString)
ingestion_field.SetWidth(20)
target_layer.CreateField(ingestion_field)

# Copy all features and set ingestion date from location field
for feature in source_layer:
    new_feature = ogr.Feature(target_layer.GetLayerDefn())

    location_val = feature.GetField("location")
    new_feature.SetField("location", location_val)

    # Extract ingestion date from the location filename
    ingestion_date = extract_date_from_string(location_val)
    if ingestion_date:
        new_feature.SetField("ingestion", ingestion_date.strftime("%Y-%m-%d"))
    else:
        new_feature.SetField("ingestion", "")  # leave blank if not found

    # Copy geometry
    geom = feature.GetGeometryRef()
    new_feature.SetGeometry(geom.Clone())

    target_layer.CreateFeature(new_feature)
    new_feature = None

source_ds = None
target_ds = None

# Preserve .prj if it exists
prj_file = old_shp.with_suffix(".prj")
if prj_file.exists():
    shutil.copy(prj_file, mosaic_dir / "merge_fixed.prj")

# Remove old shapefile components except .prj
for ext in [".shp", ".shx", ".dbf", ".cpg"]:
    old_file = old_shp.with_suffix(ext)
    if old_file.exists():
        old_file.unlink()

# Rename fixed shapefile components to original name
for ext in [".shp", ".shx", ".dbf", ".prj", ".cpg"]:
    fixed_file = fixed_shp.with_suffix(ext)
    if fixed_file.exists():
        fixed_file.rename(mosaic_dir / f"merge{ext}")

print("Shapefile updated: ingestion field extracted from location values.")
