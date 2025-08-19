# Linux KVM FreeRTOS Comparison Setup

**Purpose**: Set up Linux KVM to run the same FreeRTOS binary and capture ARM exception vector state for hypervisor comparison

**Date**: 2025-01-18

---

## Overview

To complete our hypervisor comparison, we need to run the same FreeRTOS binary under Linux KVM and capture memory snapshots showing the ARM exception vector table at addresses 0x0-0x1C.

**Hypothesis to Test**: Linux KVM provides ARM exception vectors at 0x0-0x1C, while seL4 VM does not.

---

## Linux KVM Setup Requirements

### 1. Host System Requirements
```bash
# Check KVM support
lscpu | grep Virtualization
cat /proc/cpuinfo | grep vmx    # Intel VT-x
cat /proc/cpuinfo | grep svm    # AMD-V

# Check KVM kernel modules
lsmod | grep kvm
```

### 2. Install KVM and QEMU Tools
```bash
sudo apt update
sudo apt install -y qemu-kvm qemu-system-arm qemu-utils virtinst virt-manager libvirt-daemon-system libvirt-clients bridge-utils

# Add user to KVM group
sudo usermod -aG kvm $USER
sudo usermod -aG libvirt $USER

# Verify KVM installation
kvm-ok
```

### 3. ARM KVM Support Check
```bash
# Check if ARM KVM is available
ls /dev/kvm
cat /sys/module/kvm/parameters/ignore_msrs

# For ARM64 host (if needed)
sudo apt install qemu-system-aarch64
```

---

## FreeRTOS Binary Preparation

### 1. Use Existing Working FreeRTOS Binary
```bash
# Location of working FreeRTOS binary from seL4 testing
FREERTOS_BINARY="/home/konton-otome/phd/freertos_vexpress_a9/Build/freertos_image.bin"

# Verify binary exists and check format
ls -la "$FREERTOS_BINARY"
file "$FREERTOS_BINARY"
hexdump -C "$FREERTOS_BINARY" | head -20
```

### 2. Create KVM-Compatible Binary if Needed
```bash
# If binary needs conversion for KVM
cp "$FREERTOS_BINARY" /home/konton-otome/phd/freertos_kvm.bin

# Check entry point and load address
readelf -h "$FREERTOS_BINARY" 2>/dev/null || echo "Raw binary - no ELF headers"
```

---

## Linux KVM QEMU Configuration

### 1. Basic KVM Launch Script
Create `/home/konton-otome/phd/run_freertos_linux_kvm.sh`:

```bash
#!/bin/bash
# Linux KVM FreeRTOS launcher with debugging support

set -e

echo "=========================================="
echo "  Linux KVM FreeRTOS Debug Mode"
echo "  For ARM Exception Vector Comparison"
echo "=========================================="

# Configuration
FREERTOS_BINARY="/home/konton-otome/phd/freertos_vexpress_a9/Build/freertos_image.bin"
GDB_PORT=1235  # Different from seL4 (1234) 
MONITOR_PORT=55556  # Different from seL4 (55555)
TRACE_FILE="/home/konton-otome/phd/linux_kvm_trace.log"

echo "Configuration:"
echo "  FreeRTOS Binary: $FREERTOS_BINARY"
echo "  GDB Server: tcp::$GDB_PORT"
echo "  Monitor: tcp:127.0.0.1:$MONITOR_PORT"
echo "  Trace File: $TRACE_FILE"
echo ""

# Check if binary exists
if [ ! -f "$FREERTOS_BINARY" ]; then
    echo "ERROR: FreeRTOS binary not found: $FREERTOS_BINARY"
    exit 1
fi

echo "🚀 Starting Linux KVM with FreeRTOS..."
echo ""
echo "Debugging interfaces available:"
echo "1. GDB Server: Connect with: gdb-multiarch"
echo "   (gdb) target remote :$GDB_PORT"
echo ""
echo "2. Monitor Interface: telnet 127.0.0.1 $MONITOR_PORT"
echo "   (qemu) x/8wx 0x0    # Check exception vectors"
echo "   (qemu) info registers"
echo "   (qemu) info mtree"
echo ""

# KVM-specific QEMU command
echo "QEMU KVM Command Line:"
echo "qemu-system-arm -enable-kvm -M virt -cpu host -m 2048M -nographic \\"
echo "  -kernel $FREERTOS_BINARY \\"
echo "  -gdb tcp::$GDB_PORT \\"
echo "  -monitor tcp:127.0.0.1:$MONITOR_PORT,server,nowait"
echo ""

echo "Press Ctrl+C to stop QEMU"
echo "Starting in 3 seconds..."
sleep 3

# Run QEMU with KVM acceleration
exec qemu-system-arm \
    -enable-kvm \
    -M virt \
    -cpu host \
    -m 2048M \
    -nographic \
    -kernel "$FREERTOS_BINARY" \
    -gdb tcp::$GDB_PORT \
    -monitor tcp:127.0.0.1:$MONITOR_PORT,server,nowait \
    -d exec,cpu,guest_errors,int \
    -D "$TRACE_FILE" \
    "$@"
```

### 2. Alternative Non-KVM Version (for compatibility)
Create `/home/konton-otome/phd/run_freertos_linux_qemu.sh`:

```bash
#!/bin/bash
# Standard QEMU ARM (without KVM) for comparison

set -e

echo "=========================================="
echo "  Linux QEMU ARM FreeRTOS Debug Mode"
echo "  (Without KVM acceleration)"
echo "=========================================="

FREERTOS_BINARY="/home/konton-otome/phd/freertos_vexpress_a9/Build/freertos_image.bin"
GDB_PORT=1235
MONITOR_PORT=55556
TRACE_FILE="/home/konton-otome/phd/linux_qemu_trace.log"

# Use Cortex-A15 (same as working seL4 setup for fair comparison)
exec qemu-system-arm \
    -M virt \
    -cpu cortex-a15 \
    -m 2048M \
    -nographic \
    -kernel "$FREERTOS_BINARY" \
    -gdb tcp::$GDB_PORT \
    -monitor tcp:127.0.0.1:$MONITOR_PORT,server,nowait \
    -d exec,cpu,guest_errors,int,mmu \
    -D "$TRACE_FILE" \
    "$@"
```

---

## Memory Snapshot Comparison

### 1. Linux KVM Memory Analysis Script
Create `/home/konton-otome/phd/capture_linux_kvm_vectors.py`:

```python
#!/usr/bin/env python3
"""
Linux KVM ARM Exception Vector Analysis
Captures memory snapshots from Linux KVM for comparison with seL4 VM
"""

import telnetlib
import time
import json
from datetime import datetime

class LinuxKVMAnalyzer:
    def __init__(self, monitor_host='127.0.0.1', monitor_port=55556):
        self.monitor_host = monitor_host
        self.monitor_port = monitor_port
        self.tn = None

    def connect(self):
        """Connect to QEMU monitor interface"""
        try:
            self.tn = telnetlib.Telnet(self.monitor_host, self.monitor_port, timeout=10)
            # Wait for QEMU prompt
            self.tn.read_until(b'(qemu) ', timeout=5)
            print(f"✅ Connected to Linux KVM QEMU monitor at {self.monitor_host}:{self.monitor_port}")
            return True
        except Exception as e:
            print(f"❌ Failed to connect to monitor: {e}")
            return False

    def execute_command(self, command):
        """Execute QEMU monitor command and return output"""
        if not self.tn:
            return None
        
        try:
            self.tn.write(f"{command}\n".encode())
            output = self.tn.read_until(b'(qemu) ', timeout=5)
            # Remove the command echo and prompt
            result = output.decode('utf-8', errors='ignore')
            lines = result.split('\n')[1:-1]  # Remove first (command) and last (prompt) lines
            return '\n'.join(lines)
        except Exception as e:
            print(f"❌ Command execution failed: {e}")
            return None

    def capture_exception_vectors(self):
        """Capture ARM exception vectors at 0x0-0x1C"""
        print("\n🔍 Analyzing ARM Exception Vectors in Linux KVM...")
        
        vectors = {}
        
        # Read exception vector table
        print("📋 Reading exception vector table at 0x0-0x1C:")
        vector_data = self.execute_command("x/8wx 0x0")
        print(vector_data)
        vectors['exception_table'] = vector_data
        
        # Read as instructions
        print("\n📋 Reading exception vectors as ARM instructions:")
        vector_instructions = self.execute_command("x/8i 0x0")
        print(vector_instructions)
        vectors['exception_instructions'] = vector_instructions
        
        # CPU registers
        print("\n📋 CPU Register State:")
        registers = self.execute_command("info registers")
        print(registers[:500] + "..." if len(registers) > 500 else registers)
        vectors['cpu_registers'] = registers
        
        # Memory tree
        print("\n📋 Memory Layout:")
        memory_tree = self.execute_command("info mtree")
        print(memory_tree[:800] + "..." if len(memory_tree) > 800 else memory_tree)
        vectors['memory_layout'] = memory_tree
        
        return vectors

    def save_snapshot(self, data, filename):
        """Save snapshot data to file"""
        snapshot = {
            'timestamp': datetime.now().isoformat(),
            'hypervisor': 'Linux KVM',
            'system': 'FreeRTOS ARM',
            'data': data
        }
        
        with open(filename, 'w') as f:
            json.dump(snapshot, f, indent=2)
        
        print(f"💾 Snapshot saved to: {filename}")

    def disconnect(self):
        """Disconnect from monitor"""
        if self.tn:
            self.tn.close()

def main():
    analyzer = LinuxKVMAnalyzer()
    
    if not analyzer.connect():
        print("❌ Cannot connect to Linux KVM monitor. Make sure QEMU is running with monitor enabled.")
        return
    
    try:
        # Capture exception vector data
        vector_data = analyzer.capture_exception_vectors()
        
        # Save snapshot
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"/home/konton-otome/phd/linux_kvm_exception_vectors_{timestamp}.json"
        analyzer.save_snapshot(vector_data, filename)
        
        print(f"\n✅ Linux KVM exception vector analysis complete!")
        print(f"📄 Data saved to: {filename}")
        
    except KeyboardInterrupt:
        print("\n🛑 Analysis interrupted by user")
    finally:
        analyzer.disconnect()

if __name__ == "__main__":
    main()
```

### 2. Comparison Analysis Script
Create `/home/konton-otome/phd/compare_hypervisor_vectors.py`:

```python
#!/usr/bin/env python3
"""
Hypervisor Exception Vector Comparison
Compares ARM exception vectors between Linux KVM and seL4 VM
"""

import json
import sys
from pathlib import Path

def load_snapshot(filename):
    """Load snapshot data from JSON file"""
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Failed to load {filename}: {e}")
        return None

def analyze_exception_vectors(data, hypervisor_name):
    """Analyze exception vector data"""
    print(f"\n📊 {hypervisor_name} Exception Vector Analysis:")
    print("=" * 50)
    
    exception_table = data.get('exception_table', '')
    
    # Check if vectors are accessible
    if 'Cannot access memory' in exception_table:
        print("❌ Exception vectors NOT accessible")
        print("🔍 Memory at 0x0-0x1C returns: 'Cannot access memory'")
        return False
    else:
        print("✅ Exception vectors ARE accessible")
        print("🔍 Memory at 0x0-0x1C contains valid data:")
        print(exception_table[:200] + "..." if len(exception_table) > 200 else exception_table)
        
        # Analyze instruction patterns
        instructions = data.get('exception_instructions', '')
        if instructions:
            print("\n📋 Exception Vector Instructions:")
            print(instructions[:300] + "..." if len(instructions) > 300 else instructions)
        
        return True

def compare_snapshots(linux_file, sel4_file):
    """Compare Linux and seL4 snapshots"""
    print("🔍 Loading snapshots for comparison...")
    
    linux_data = load_snapshot(linux_file)
    sel4_data = load_snapshot(sel4_file)
    
    if not linux_data or not sel4_data:
        print("❌ Failed to load snapshot data")
        return
    
    print(f"\n📅 Linux snapshot: {linux_data.get('timestamp', 'Unknown')}")
    print(f"📅 seL4 snapshot: {sel4_data.get('timestamp', 'Unknown')}")
    
    # Analyze each hypervisor
    linux_has_vectors = analyze_exception_vectors(linux_data['data'], "Linux KVM")
    sel4_has_vectors = analyze_exception_vectors(sel4_data['data'], "seL4 VM")
    
    # Comparison summary
    print("\n" + "="*60)
    print("🏁 HYPERVISOR COMPARISON SUMMARY")
    print("="*60)
    
    print(f"Linux KVM Exception Vectors:  {'✅ PRESENT' if linux_has_vectors else '❌ MISSING'}")
    print(f"seL4 VM Exception Vectors:    {'✅ PRESENT' if sel4_has_vectors else '❌ MISSING'}")
    
    if linux_has_vectors and not sel4_has_vectors:
        print("\n🎯 HYPOTHESIS CONFIRMED:")
        print("   • Linux KVM provides ARM exception vectors at 0x0-0x1C")
        print("   • seL4 VM does NOT provide ARM exception vectors")
        print("   • This explains why FreeRTOS fails with 'Page Fault at PC: 0x8' in seL4")
        print("   • FreeRTOS works in Linux KVM because SWI vector at 0x8 is accessible")
        
        return True
    elif not linux_has_vectors and not sel4_has_vectors:
        print("\n🤔 UNEXPECTED RESULT:")
        print("   • Both hypervisors lack exception vectors")
        print("   • Need to investigate why FreeRTOS works in Linux")
        
        return False
    elif linux_has_vectors and sel4_has_vectors:
        print("\n🤔 UNEXPECTED RESULT:")
        print("   • Both hypervisors have exception vectors")
        print("   • Need to investigate other causes of seL4 VM failure")
        
        return False
    else:
        print("\n🔍 INVESTIGATION NEEDED:")
        print("   • seL4 has vectors but Linux doesn't - unusual scenario")
        
        return False

def main():
    if len(sys.argv) != 3:
        print("Usage: python3 compare_hypervisor_vectors.py <linux_snapshot.json> <sel4_snapshot.json>")
        print("\nExample:")
        print("  python3 compare_hypervisor_vectors.py \\")
        print("    linux_kvm_exception_vectors_20250118_143022.json \\")
        print("    /home/konton-otome/phd/research-docs/analysis/sel4_vm_exception_vectors.json")
        return
    
    linux_file = sys.argv[1]
    sel4_file = sys.argv[2]
    
    # Verify files exist
    if not Path(linux_file).exists():
        print(f"❌ Linux snapshot file not found: {linux_file}")
        return
    
    if not Path(sel4_file).exists():
        print(f"❌ seL4 snapshot file not found: {sel4_file}")
        return
    
    # Perform comparison
    result = compare_snapshots(linux_file, sel4_file)
    
    if result:
        print("\n✅ Comparison analysis complete - hypothesis confirmed!")
    else:
        print("\n⚠️ Comparison complete - further investigation needed")

if __name__ == "__main__":
    main()
```

---

## Testing Workflow

### 1. Start Linux KVM with FreeRTOS
```bash
# Make scripts executable
chmod +x /home/konton-otome/phd/run_freertos_linux_kvm.sh
chmod +x /home/konton-otome/phd/run_freertos_linux_qemu.sh
chmod +x /home/konton-otome/phd/capture_linux_kvm_vectors.py
chmod +x /home/konton-otome/phd/compare_hypervisor_vectors.py

# Start Linux KVM (in one terminal)
cd /home/konton-otome/phd
./run_freertos_linux_kvm.sh

# Or if KVM not available, use standard QEMU
./run_freertos_linux_qemu.sh
```

### 2. Capture Linux Exception Vector Snapshot  
```bash
# In another terminal, capture Linux snapshot
cd /home/konton-otome/phd
python3 capture_linux_kvm_vectors.py
```

### 3. Compare with seL4 Results
```bash
# Find the latest Linux snapshot file
ls -la linux_kvm_exception_vectors_*.json

# Compare with our seL4 analysis (create seL4 snapshot file first if needed)
python3 compare_hypervisor_vectors.py \
  linux_kvm_exception_vectors_20250118_XXXXXX.json \
  research-docs/analysis/sel4_vm_exception_vectors.json
```

---

## Expected Results

### If Hypothesis is Correct:
**Linux KVM**:
```
(qemu) x/8wx 0x0
00000000: 0xea000010 0xea000020 0xea000030 0xea000040
00000010: 0xea000050 0xea000060 0xea000070 0xea000080
```
✅ Shows valid ARM branch instructions

**seL4 VM**:
```
(qemu) x/8wx 0x0  
00000000: Cannot access memory
```
❌ No memory access at exception vector addresses

### Analysis Outcome:
This would confirm that Linux KVM provides the ARM exception vector table that FreeRTOS expects, while seL4 VM does not - explaining why the Page Fault at PC: 0x8 occurs only in seL4.

---

## Files Created

1. `/home/konton-otome/phd/run_freertos_linux_kvm.sh` - Linux KVM launcher
2. `/home/konton-otome/phd/run_freertos_linux_qemu.sh` - Standard QEMU launcher  
3. `/home/konton-otome/phd/capture_linux_kvm_vectors.py` - Linux vector analyzer
4. `/home/konton-otome/phd/compare_hypervisor_vectors.py` - Comparison tool

**Next Step**: Execute this Linux setup to capture the comparison data and validate our seL4 VM root cause analysis.