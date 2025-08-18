#!/usr/bin/env python3
"""
Quick Hex Dump Capture Script for Memory Pattern Debugging

This script connects to a running QEMU instance and captures hex dumps
of all memory regions during pattern painting.

Usage:
    python3 capture_hex_dumps.py [--continuous] [--interval 15]
"""

import argparse
import sys
import time
from qemu_memory_analyzer import QEMUMonitor, MemoryPatternAnalyzer

def capture_single_hex_dumps():
    """Capture a single set of hex dumps"""
    print("🔗 Connecting to QEMU monitor...")
    monitor = QEMUMonitor("127.0.0.1", 55555)
    
    if not monitor.connect():
        print("❌ Failed to connect to QEMU monitor")
        print("Make sure QEMU is running with: -monitor tcp:127.0.0.1:55555,server,nowait")
        return False
    
    try:
        analyzer = MemoryPatternAnalyzer(monitor)
        
        print("📸 Capturing hex dumps from all memory regions...")
        hex_files = analyzer.save_all_region_hex_dumps()
        
        print(f"\n✅ Successfully saved {len(hex_files)} hex dump files:")
        for region, filename in hex_files.items():
            print(f"  📄 {region:12}: {filename}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during capture: {e}")
        return False
    finally:
        monitor.close()

def capture_continuous_hex_dumps(interval: int = 15):
    """Capture hex dumps continuously"""
    print(f"🔗 Starting continuous hex dump capture (interval: {interval}s)")
    monitor = QEMUMonitor("127.0.0.1", 55555)
    
    if not monitor.connect():
        print("❌ Failed to connect to QEMU monitor")
        return False
    
    try:
        analyzer = MemoryPatternAnalyzer(monitor)
        cycle = 0
        
        while True:
            print(f"\n📸 Capture Cycle {cycle} ({time.strftime('%H:%M:%S')})")
            
            hex_files = analyzer.save_all_region_hex_dumps(cycle)
            
            print(f"  ✅ Saved {len(hex_files)} files for cycle {cycle}")
            
            cycle += 1
            
            print(f"⏳ Waiting {interval} seconds for next capture...")
            time.sleep(interval)
    
    except KeyboardInterrupt:
        print(f"\n⏹️  Capture stopped by user after {cycle} cycles")
        return True
    except Exception as e:
        print(f"❌ Error during continuous capture: {e}")
        return False
    finally:
        monitor.close()

def main():
    parser = argparse.ArgumentParser(description='Capture QEMU Memory Hex Dumps')
    parser.add_argument('--continuous', '-c', action='store_true', 
                       help='Continuous capture mode')
    parser.add_argument('--interval', type=int, default=15,
                       help='Interval between captures in seconds (default: 15)')
    
    args = parser.parse_args()
    
    print("🔬 QEMU Memory Hex Dump Capture Tool")
    print("=" * 40)
    
    if args.continuous:
        success = capture_continuous_hex_dumps(args.interval)
    else:
        success = capture_single_hex_dumps()
    
    if success:
        print("\n🎉 Hex dump capture completed successfully!")
        print("\n📋 What to do with the hex dumps:")
        print("  1. Compare patterns across different cycles")
        print("  2. Verify memory pattern painting is working")
        print("  3. Check for memory corruption or unexpected changes")
        print("  4. Correlate with FreeRTOS debug output")
        print("\n💡 Tip: Use 'diff' to compare hex dumps between cycles")
    else:
        print("\n❌ Hex dump capture failed")
        sys.exit(1)

if __name__ == "__main__":
    main()