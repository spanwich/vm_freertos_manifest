# QEMU Memory Hex Dump Capture Guide

## Overview

The enhanced memory pattern debugging toolkit now includes comprehensive hex dump capture capabilities. This allows you to save raw QEMU memory dumps to files during pattern painting for detailed analysis.

## 🎯 Quick Start

### 1. Single Hex Dump Capture
```bash
# Start QEMU with monitor interface (in one terminal)
cd /home/konton-otome/phd
./run_qemu_debug.sh

# Capture hex dumps (in another terminal)
python3 capture_hex_dumps.py
```

### 2. Continuous Hex Dump Capture
```bash
# Capture hex dumps every 15 seconds
python3 capture_hex_dumps.py --continuous --interval 15
```

### 3. Using the Enhanced Memory Analyzer
```bash
# Single analysis with hex dumps
python3 qemu_memory_analyzer.py --save-hex --output analysis.txt

# Continuous monitoring with hex dumps
python3 qemu_memory_analyzer.py --continuous --save-hex --interval 20

# Hex dumps only (no analysis)
python3 qemu_memory_analyzer.py --hex-only
```

## 📁 Generated Files

### Hex Dump Files
Each memory region generates a timestamped hex dump file:

```
hex_dump_guest_base_20250815_164530.txt    # Guest VM base (0x40000000)
hex_dump_stack_20250815_164530.txt         # Stack region (0x41000000)
hex_dump_data_20250815_164530.txt          # Data region (0x41200000)  
hex_dump_heap_20250815_164530.txt          # Heap region (0x41400000)
hex_dump_pattern_20250815_164530.txt       # Pattern region (0x42000000)
registers_20250815_164530.txt              # CPU registers
```

### Continuous Mode Files
In continuous mode, files include cycle numbers:
```
hex_dump_stack_20250815_164530_cycle001.txt
hex_dump_stack_20250815_164530_cycle002.txt
hex_dump_stack_20250815_164530_cycle003.txt
```

## 🔍 Hex Dump File Format

Each hex dump file contains:

```
# QEMU Memory Hex Dump
# Generated: 2025-08-15 16:45:30
# Address: 0x41000000
# Size: 256 words (1024 bytes)
# Format: wx
# Description: Stack region - Expected: 0xdeadbeef
# Command: x/256wx 0x41000000
#============================================================

0x41000000:  0xdeadbeef 0xdeadbeef 0xdeadbeef 0xdeadbeef
0x41000010:  0xdeadbeef 0xdeadbeef 0xdeadbeef 0xdeadbeef
0x41000020:  0xdeadbeef 0xdeadbeef 0xdeadbeef 0xdeadbeef
...

# End of dump
```

## 🔬 Analysis Workflow

### Step 1: Start FreeRTOS with Memory Pattern Painting
```bash
# Ensure you're using the debug binary
cd /home/konton-otome/phd/freertos_vexpress_a9
./build_debug.sh debug

# Update seL4 to use debug binary (if needed)
# Edit camkes-vm-examples/projects/vm-examples/apps/Arm/vm_freertos/CMakeLists.txt
```

### Step 2: Launch QEMU with Monitor
```bash
# Start QEMU (this will run the memory pattern painting FreeRTOS)
./run_qemu_debug.sh
```

### Step 3: Capture Hex Dumps During Pattern Painting
```bash
# Option A: Single capture
python3 capture_hex_dumps.py

# Option B: Continuous capture to see patterns evolve
python3 capture_hex_dumps.py --continuous --interval 10
```

### Step 4: Analyze Captured Dumps

#### Manual Inspection
```bash
# View a hex dump
cat hex_dump_stack_20250815_164530.txt

# Compare between cycles
diff hex_dump_stack_20250815_164530_cycle001.txt hex_dump_stack_20250815_164530_cycle002.txt

# Search for specific patterns
grep "0xdeadbeef" hex_dump_stack_*.txt
```

#### Automated Analysis
```bash
# Analyze patterns programmatically
python3 -c "
import re
with open('hex_dump_stack_20250815_164530.txt', 'r') as f:
    content = f.read()
    deadbeef_count = len(re.findall(r'0xdeadbeef', content))
    print(f'Found {deadbeef_count} instances of 0xdeadbeef pattern')
"
```

## 🎯 Expected Memory Patterns

### Stack Region (0x41000000)
- **Expected Pattern**: `0xdeadbeef`
- **Size**: 256 words (1024 bytes)
- **Success**: 90%+ pattern matches

### Data Region (0x41200000)  
- **Expected Pattern**: `0x12345678`
- **Size**: 256 words (1024 bytes)
- **Success**: 90%+ pattern matches

### Heap Region (0x41400000)
- **Expected Pattern**: `0xcafebabe`
- **Size**: 256 words (1024 bytes)
- **Success**: 90%+ pattern matches

### Pattern Region (0x42000000)
- **Expected Pattern**: `0x55aa55aa` + dynamic patterns
- **Size**: 1024 words (4096 bytes)
- **Success**: Pattern variations for instruction tracing

## 🔧 Command Reference

### QEMU Monitor Commands
```
# Connect to monitor
telnet 127.0.0.1 55555

# Manual memory inspection
(qemu) x/32wx 0x41000000  # Stack region
(qemu) x/32wx 0x41200000  # Data region
(qemu) x/32wx 0x41400000  # Heap region
(qemu) x/32wx 0x42000000  # Pattern region
(qemu) info registers     # CPU state
```

### Python Scripts
```bash
# Quick hex dump capture
python3 capture_hex_dumps.py

# Full analysis with hex dumps
python3 qemu_memory_analyzer.py --save-hex

# Continuous monitoring
python3 qemu_memory_analyzer.py --continuous --save-hex --interval 15

# Complete workflow
python3 memory_debug_workflow.py --all
```

## 🔍 Troubleshooting

### Connection Issues
```bash
# Check if QEMU monitor is running
netstat -an | grep 55555

# Test monitor connection
echo "info registers" | nc 127.0.0.1 55555
```

### No Pattern Painting Detected
```bash
# Check FreeRTOS output (should show pattern painting messages)
# Look for: "=== MEMORY PATTERN PAINTING TASK ==="

# Verify debug binary is being used
ls -la camkes-vm-examples/projects/vm-examples/apps/Arm/vm_freertos/qemu-arm-virt/freertos_debug_image.bin
```

### Pattern Mismatches
```bash
# Check if patterns are being painted
grep -E "0x(deadbeef|12345678|cafebabe|55aa55aa)" hex_dump_*.txt

# Compare with expected patterns
python3 qemu_memory_analyzer.py --hex-only
```

## 📊 Example Analysis

### Pattern Verification Script
```python
#!/usr/bin/env python3
import glob
import re

def analyze_hex_dumps():
    patterns = {
        'stack': '0xdeadbeef',
        'data': '0x12345678', 
        'heap': '0xcafebabe',
        'pattern': '0x55aa55aa'
    }
    
    for pattern_name, pattern_value in patterns.items():
        files = glob.glob(f'hex_dump_{pattern_name}_*.txt')
        
        for file in files:
            with open(file, 'r') as f:
                content = f.read()
                matches = len(re.findall(pattern_value, content))
                print(f"{file}: {matches} pattern matches")

if __name__ == "__main__":
    analyze_hex_dumps()
```

## 🎉 Success Indicators

✅ **Working Memory Mapping**: Pattern files show 90%+ expected patterns  
✅ **Active Pattern Painting**: FreeRTOS debug messages in QEMU output  
✅ **Dynamic Patterns**: Pattern region shows evolving values  
✅ **Register Consistency**: CPU registers show expected execution state  

The hex dump capture functionality provides the raw data needed to verify that the FreeRTOS memory pattern painting methodology is working correctly and that seL4 VM memory mappings are functioning as expected.