#!/usr/bin/env python3
"""
NDVI MODIS Data Download Script for 2024
Downloads MODIS NDVI data (250m, 16-day composites) for Latin America
With RAM monitoring
"""
from app.workflows.data_processing.ndvi_flow import ndvi_data_flow
from datetime import date
import psutil
import threading
import time

# Global flag to control monitoring
monitoring = True
max_ram_usage = 0

def monitor_ram():
    """Monitor RAM usage in background"""
    global monitoring, max_ram_usage
    print("\n🔍 RAM Monitoring started (updating every 10 seconds)...")
    print(f"{'Time':20s} | {'RAM Used (GB)':15s} | {'RAM %':10s} | {'Available (GB)':15s}")
    print("-" * 80)

    while monitoring:
        mem = psutil.virtual_memory()
        used_gb = mem.used / (1024**3)
        available_gb = mem.available / (1024**3)
        percent = mem.percent

        # Track max
        if used_gb > max_ram_usage:
            max_ram_usage = used_gb

        timestamp = time.strftime("%H:%M:%S")
        print(f"{timestamp:20s} | {used_gb:13.2f} GB | {percent:8.1f}% | {available_gb:13.2f} GB")

        # Warning if RAM usage is high
        if percent > 80:
            print(f"⚠️  WARNING: High RAM usage ({percent:.1f}%)")

        time.sleep(10)

if __name__ == "__main__":
    # Start RAM monitoring in background
    monitor_thread = threading.Thread(target=monitor_ram, daemon=True)
    monitor_thread.start()

    year = 2024
    year_start = date(year, 1, 1)
    year_end = date(year, 12, 31)

    print("="*80)
    print(f"MODIS NDVI DATA DOWNLOAD FOR {year}")
    print("="*80)
    print(f"Date range: {year_start} to {year_end}")
    print(f"Source: MODIS MOD13Q1.061 (250m resolution, 16-day composites)")
    print(f"Provider: Microsoft Planetary Computer (FREE!)")
    print(f"Region: Latin America")
    print("="*80)

    try:
        # Run the flow for 2024
        result = ndvi_data_flow(
            start_date=year_start,
            end_date=year_end,
            sources=['modis'],
            batch_days=16  # Smaller batches = fewer composites per request
        )

        print(f"\n✓ Year {year}: Processed {len(result)} files")

    except Exception as e:
        print(f"\n✗ Year {year} failed: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Stop monitoring
        monitoring = False
        time.sleep(1)  # Give monitor thread time to finish

        print("\n" + "="*80)
        print(f"RAM USAGE SUMMARY")
        print("="*80)
        mem = psutil.virtual_memory()
        print(f"Peak RAM usage: {max_ram_usage:.2f} GB")
        print(f"Final RAM usage: {mem.used / (1024**3):.2f} GB ({mem.percent:.1f}%)")
        print(f"Total RAM: {mem.total / (1024**3):.2f} GB")
        print("="*80)
