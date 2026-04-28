#!/usr/bin/env python3
"""
IRIS System Monitor v2 -- Run in a second terminal while testing echo_iris.py
Shows CPU, RAM, temperature, and swap usage in real time.

Usage: python3 iris_monitor.py
"""

import subprocess
import time
import os

def get_cpu_temp():
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            temp = int(f.read().strip()) / 1000
            return f"{temp:.1f}C"
    except:
        return "N/A"

def get_memory():
    with open("/proc/meminfo", "r") as f:
        lines = f.readlines()
    info = {}
    for line in lines:
        parts = line.split()
        info[parts[0].rstrip(":")] = int(parts[1])
    
    total = info["MemTotal"] / 1024
    available = info["MemAvailable"] / 1024
    used = total - available
    swap_total = info["SwapTotal"] / 1024
    swap_free = info["SwapFree"] / 1024
    swap_used = swap_total - swap_free
    
    return total, used, available, swap_total, swap_used

def get_cpu_usage():
    try:
        result = subprocess.run(
            ["grep", "cpu ", "/proc/stat"],
            capture_output=True, text=True
        )
        parts = result.stdout.split()
        idle = int(parts[4])
        total = sum(int(x) for x in parts[1:])
        return idle, total
    except:
        return 0, 1

def make_bar(percent, width=20):
    filled = int(width * percent / 100)
    return "[" + "#" * filled + "-" * (width - filled) + "]"

def main():
    print("  IRIS System Monitor v2")
    print("=" * 46)
    
    prev_idle, prev_total = get_cpu_usage()
    time.sleep(0.5)
    
    while True:
        # CPU usage
        curr_idle, curr_total = get_cpu_usage()
        idle_delta = curr_idle - prev_idle
        total_delta = curr_total - prev_total
        if total_delta > 0:
            cpu_pct = 100.0 * (1.0 - idle_delta / total_delta)
        else:
            cpu_pct = 0.0
        prev_idle, prev_total = curr_idle, curr_total
        
        # Temperature
        temp = get_cpu_temp()
        
        # Memory
        total, used, available, swap_total, swap_used = get_memory()
        ram_pct = (used / total) * 100
        
        # Temperature as percent for bar (0-100C range)
        temp_val = float(temp.replace("C", "")) if temp != "N/A" else 0
        temp_pct = min(temp_val, 100)
        
        # Warning flags
        warnings = []
        if ram_pct > 85:
            warnings.append("!! RAM CRITICAL !!")
        elif ram_pct > 70:
            warnings.append("! RAM HIGH !")
        
        if temp_val > 80:
            warnings.append("!! TEMP CRITICAL !!")
        elif temp_val > 70:
            warnings.append("! TEMP HIGH !")
        
        if swap_used > 100:
            warnings.append("! SWAPPING (SLOW) !")
        
        # Display
        os.system("clear")
        print("  IRIS System Monitor v2")
        print("=" * 46)
        print(f"  CPU:   {cpu_pct:5.1f}%  {make_bar(cpu_pct)}")
        print(f"  Temp:  {temp}  {make_bar(temp_pct)}")
        print(f"  RAM:   {used:.0f} / {total:.0f} MB ({ram_pct:.0f}%)")
        print(f"         {make_bar(ram_pct)}")
        print(f"  Swap:  {swap_used:.0f} / {swap_total:.0f} MB")
        print(f"  Free:  {available:.0f} MB available")
        print("=" * 46)
        
        if warnings:
            for w in warnings:
                print(f"  >>> {w}")
        else:
            print("  Status: OK")
        
        print("=" * 46)
        print("  WHAT THESE MEAN:")
        print("  CPU   Normal to hit 99% during LLM")
        print("        inference. Will not cause crash.")
        print("  Temp  Stay under 80C. Above = throttle.")
        print("        85C = auto shutdown risk.")
        print("  RAM   Most important number. Above 85%")
        print("        = crash risk. Above 70% = caution.")
        print("  Swap  If above 0, Pi is using disk as")
        print("        RAM. System will feel very slow.")
        print("  Free  RAM available for new tasks.")
        print("        Under 500MB = danger zone.")
        
        time.sleep(2)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nMonitor stopped.")
