#!/usr/bin/env python3
import psutil
import time
import sys

PID = 723119
peak_ram = 0
print(f"Monitoring PID {PID} for peak RAM usage (30 iterations, 10-second intervals)")
print(f"{'Time':10s} | {'Current RAM (GB)':16s} | {'Peak RAM (GB)':14s} | {'System RAM':12s}")
print("-" * 70)

for i in range(30):
    try:
        process = psutil.Process(PID)
        mem_info = process.memory_info()
        current_ram_gb = mem_info.rss / (1024**3)

        if current_ram_gb > peak_ram:
            peak_ram = current_ram_gb

        sys_mem = psutil.virtual_memory()
        sys_ram_gb = sys_mem.used / (1024**3)

        timestamp = time.strftime("%H:%M:%S")
        print(f"{timestamp:10s} | {current_ram_gb:14.2f} GB | {peak_ram:12.2f} GB | {sys_ram_gb:10.2f} GB")

        time.sleep(10)
    except psutil.NoSuchProcess:
        print("Process ended")
        break
    except Exception as e:
        print(f"Error: {e}")
        break

print("-" * 70)
print(f"PEAK RAM USAGE: {peak_ram:.2f} GB")
