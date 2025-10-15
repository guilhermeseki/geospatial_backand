#!/usr/bin/env python3
import shapefile
from datetime import datetime
import os

# Path to your shapefile
shp_path = '/opt/geoserver/data_dir/chirps_final/chirps_final.shp'

def fix_shapefile_timestamps(shp_path):
    # Read the shapefile
    sf = shapefile.Reader(shp_path)
    
    # Create a new shapefile with same schema
    new_sf = shapefile.Writer(shp_path.replace('.shp', '_fixed.shp'), shapeType=sf.shapeType)
    
    # Copy fields from original
    for field in sf.fields[1:]:  # Skip first field (deletion flag)
        new_sf.field(*field)
    
    # Add timestamp field if it doesn't exist
    field_names = [field[0] for field in sf.fields[1:]]
    if 'timestamp' not in field_names:
        new_sf.field('timestamp', 'D')  # 'D' for Date field
    
    # Process each record
    for i, shape_record in enumerate(sf.iterShapeRecords()):
        shape = shape_record.shape
        record = shape_record.record
        
        # Extract date from filename
        location = record[field_names.index('location')]
        date_str = location.split('_latam_')[1].split('.tif')[0]
        
        # Convert to datetime object
        date_obj = datetime.strptime(date_str, '%Y%m%d')
        
        # Copy all existing fields
        new_record = list(record)
        
        # Add timestamp (as datetime object for shapefile writer)
        if 'timestamp' not in field_names:
            new_record.append(date_obj)
        else:
            # Replace existing null timestamp
            timestamp_idx = field_names.index('timestamp')
            new_record[timestamp_idx] = date_obj
        
        # Write shape and record
        new_sf.shape(shape)
        new_sf.record(*new_record)
    
    # Close the new shapefile
    new_sf.close()
    print(f"Fixed shapefile created: {shp_path.replace('.shp', '_fixed.shp')}")

def replace_shapefile():
    # Backup original
    base_path = '/opt/geoserver/data_dir/chirps_final/chirps_final'
    files_to_backup = ['.shp', '.dbf', '.shx', '.prj']
    
    for ext in files_to_backup:
        if os.path.exists(base_path + ext):
            os.rename(base_path + ext, base_path + ext + '.bak')
    
    # Rename fixed files
    fixed_base = '/opt/geoserver/data_dir/chirps_final/chirps_final_fixed'
    for ext in files_to_backup:
        if os.path.exists(fixed_base + ext):
            os.rename(fixed_base + ext, base_path + ext)

if __name__ == "__main__":
    # Install required library if needed
    # try:
    #     import shapefile
    # except ImportError:
    #     print("Installing pyshp...")
    #     os.system("pip install pyshp")
    #     import shapefile
    
    fix_shapefile_timestamps(shp_path)
    replace_shapefile()
    print("Shapefile timestamps fixed successfully!")