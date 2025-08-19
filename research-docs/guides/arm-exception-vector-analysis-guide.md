# ARM Exception Vector Analysis Guide
## Using Existing Debug Tools for Linux vs seL4 Hypervisor Comparison

**Date**: 2025-01-18  
**Purpose**: Step-by-step guide to analyze ARM exception vector differences causing Page Fault at PC: 0x8  
**Tools Used**: Existing debug scripts (`run_qemu_debug.sh`, `qemu_memory_analyzer.py`)

---

## Overview

This guide provides practical steps to use our existing debug tools to investigate why FreeRTOS fails with "Page Fault at PC: 0x8" under seL4 VM but works under Linux hypervisors. The failure occurs at the ARM Software Interrupt (SWI) vector address.

## Background: The Problem

**Issue**: FreeRTOS reaches `vPortRestoreTaskContext()` but fails with Page Fault at PC: 0x8  
**Location**: `portASM.S:199` - `BX R1` where R1 = 0x8  
**Root Cause**: ARM exception vector table at 0x0-0x1C not properly configured by seL4 VM

### ARM Exception Vector Layout
```
0x00: Reset Vector
0x04: Undefined Instruction  
0x08: Software Interrupt (SWI/SVC) ← FAILURE POINT
0x0C: Prefetch Abort
0x10: Data Abort
0x14: Reserved
0x18: IRQ
0x1C: FIQ
```

---

## Phase 1: Analyze seL4 VM Exception Vector State

### Step 1: Start seL4 VM with Debug Monitor

```bash
cd /home/konton-otome/phd/camkes-vm-examples/build

# Activate Python environment
source ../../sel4-dev-env/bin/activate
export PYTHONPATH=/home/konton-otome/phd/camkes-vm-examples/projects/camkes-tool:/home/konton-otome/phd/camkes-vm-examples/projects/capdl/python-capdl-tool

# Build if needed
ninja

# Start seL4 VM with debug monitor using our existing debug script
cd /home/konton-otome/phd
./run_qemu_debug.sh
```

### Step 2: Capture Exception Vector State

In another terminal, connect to the QEMU monitor:

```bash
cd /home/konton-otome/phd

# Use our existing memory analyzer to connect
python3 qemu_memory_analyzer.py --monitor-port 55555 --hex-only
```

Or manually connect:
```bash
telnet 127.0.0.1 55555
```

### Step 3: Examine ARM Exception Vectors

**Critical Commands** (run in QEMU monitor):
```
# Check exception vectors (0x0-0x1C)
x/8wx 0x0

# Check memory mapping around exception vectors  
info mtree

# Check CPU registers
info registers

# Check memory protection for low addresses
x/1wx 0x0
x/1wx 0x4  
x/1wx 0x8    # This should cause the failure
x/1wx 0xC
```

### Step 4: Document seL4 VM Vector State

**Expected Results for seL4 VM (Current Failing State)**:
```
(qemu) x/8wx 0x0
0x00000000: 0x00000000 0x00000000 0x00000000 0x00000000
0x00000010: 0x00000000 0x00000000 0x00000000 0x00000000
```
This shows unmapped/zero values causing the Page Fault at 0x8.

---

## Phase 2: Analyze Reference ARM Linux Environment

### Step 5: Create Simple ARM Linux Reference

Since we have ARM cross-compilation tools, create a minimal ARM Linux setup:

```bash
cd /home/konton-otome/phd/linux_vm_comparison

# Cross-compile the vector analyzer for ARM
arm-linux-gnueabi-gcc -o vector_analyzer_arm -static vector_analyzer.c

# Create minimal Linux kernel + initramfs approach
# Option 1: Use pre-built Debian ARM images
wget http://http.us.debian.org/debian/dists/bookworm/main/installer-armhf/current/images/netboot/vmlinuz
wget http://http.us.debian.org/debian/dists/bookworm/main/installer-armhf/current/images/netboot/initrd.gz

# Option 2: Build minimal BusyBox initramfs (recommended)
mkdir -p minimal_linux && cd minimal_linux
```

### Step 6: Boot ARM Linux with Identical Platform

```bash
# Boot Linux on same QEMU ARM virt platform as seL4
qemu-system-arm \
  -M virt \
  -cpu cortex-a15 \
  -m 512M \
  -kernel vmlinuz \
  -initrd initrd.gz \
  -append "console=ttyAMA0,38400 rdinit=/bin/sh" \
  -nographic \
  -monitor tcp:127.0.0.1:55556,server,nowait
```

### Step 7: Analyze Linux Exception Vectors

Connect to Linux QEMU monitor:
```bash
telnet 127.0.0.1 55556
```

**Critical Commands for Linux**:
```
# Check exception vectors - should show valid addresses
x/8wx 0x0

# Check VBAR register
info registers | grep -i vbar

# Check memory tree
info mtree
```

**Expected Results for Linux (Working State)**:
```
(qemu) x/8wx 0x0  
0x00000000: 0x???????? 0x???????? 0x???????? 0x????????
0x00000010: 0x???????? 0x???????? 0x???????? 0x????????
```
Should show valid instruction addresses, particularly at 0x8.

---

## Phase 3: Enhanced seL4 VM Analysis Using Existing Tools

### Step 8: Add Vector Analysis to FreeRTOS Debug Code

Modify `/home/konton-otome/phd/freertos_vexpress_a9/Source/main.c` to add vector analysis:

```c
void debug_arm_vectors() {
    uart_puts("=== ARM Exception Vector Analysis ===\r\n");
    
    // Check if we can read exception vectors
    volatile uint32_t *vectors = (volatile uint32_t*)0x0;
    
    for(int i = 0; i < 8; i++) {
        uart_puts("Vector 0x");
        uart_hex(i*4);
        uart_puts(": ");
        
        // Try to read vector - may fault if unmapped
        uint32_t vector_value = 0;
        __try {
            vector_value = vectors[i];
            uart_puts("0x");
            uart_hex(vector_value);
        } __except {
            uart_puts("UNMAPPED/FAULT");
        }
        
        // Add description
        if (i == 0) uart_puts(" (Reset)");
        else if (i == 1) uart_puts(" (Undefined Instruction)"); 
        else if (i == 2) uart_puts(" (SWI/SVC) ← CRITICAL");
        else if (i == 3) uart_puts(" (Prefetch Abort)");
        else if (i == 4) uart_puts(" (Data Abort)");
        else if (i == 5) uart_puts(" (Reserved)");
        else if (i == 6) uart_puts(" (IRQ)");
        else if (i == 7) uart_puts(" (FIQ)");
        
        uart_puts("\r\n");
    }
    
    // Try to read VBAR register
    uint32_t vbar = 0;
    __asm__ volatile("mrc p15, 0, %0, c12, c0, 0" : "=r"(vbar));
    uart_puts("VBAR = 0x");
    uart_hex(vbar);
    uart_puts("\r\n");
}

// Add to main() before vTaskStartScheduler()
int main() {
    // ... existing initialization ...
    
    debug_arm_vectors();  // Add this line
    
    uart_puts("Starting FreeRTOS scheduler...\r\n");
    vTaskStartScheduler();  // Will fail at vPortRestoreTaskContext
    
    return 0;
}
```

### Step 9: Rebuild and Test Enhanced seL4 VM

```bash
cd /home/konton-otome/phd/freertos_vexpress_a9
./build_debug.sh

# Copy updated binary to seL4 VM build
cp Build/freertos_image.bin /home/konton-otome/phd/camkes-vm-examples/build/

# Rebuild seL4 system with updated FreeRTOS
cd /home/konton-otome/phd/camkes-vm-examples/build
ninja

# Test with debug output
cd /home/konton-otome/phd
./run_qemu_debug.sh --trace
```

### Step 10: Use Memory Analyzer for Vector Region

While seL4 VM is running:

```bash
# Use our memory analyzer to specifically check vector region
python3 qemu_memory_analyzer.py --monitor-port 55555 --save-hex

# Or create custom analysis for vectors
python3 -c "
import sys
sys.path.append('.')
from qemu_memory_analyzer import QEMUMonitor

monitor = QEMUMonitor('127.0.0.1', 55555)
if monitor.connect():
    print('=== ARM Exception Vector Analysis ===')
    
    # Check exception vector region
    vectors = monitor.dump_memory(0x0, 8, 'wx')
    for i, val in enumerate(vectors):
        addr = i * 4
        print(f'Vector 0x{addr:02x}: 0x{val:08x}')
    
    # Save detailed hex dump of vector region
    monitor.save_hex_dump_to_file(0x0, 32, 'arm_exception_vectors.txt', 'wx', 'ARM Exception Vector Table')
    
    monitor.close()
    print('Vector analysis complete!')
"
```

---

## Phase 4: Comparison and Analysis

### Step 11: Compare Results

Create comparison table using our debug output:

| Address | Exception Type | Linux KVM | seL4 VM | Status |
|---------|----------------|-----------|---------|---------|
| 0x00 | Reset | 0x???????? | 0x00000000 | ❌ Missing |
| 0x04 | Undefined | 0x???????? | 0x00000000 | ❌ Missing |
| **0x08** | **SWI/SVC** | **0x????????** | **0x00000000** | **❌ CRITICAL** |
| 0x0C | Prefetch Abort | 0x???????? | 0x00000000 | ❌ Missing |
| ... | ... | ... | ... | ... |

### Step 12: Root Cause Identification

Based on comparison, confirm that:
1. **Linux KVM**: Provides complete exception vector table at 0x0-0x1C
2. **seL4 VM**: Does NOT provide exception vectors for guest
3. **FreeRTOS Issue**: Tries to jump to SWI handler at 0x8 but finds unmapped memory

---

## Phase 5: seL4 VM Configuration Fix

### Step 13: Configure seL4 VM Exception Vector Support

Edit `/home/konton-otome/phd/camkes-vm-examples/projects/vm-examples/apps/Arm/vm_freertos/qemu-arm-virt/devices.camkes`:

```c
assembly {
    configuration {
        // Add exception vector mapping
        vm0.untyped_mmios = [
            "0x0:12",          // Exception vectors (4KB at 0x0) ← ADD THIS
            "0x8040000:12",    // GIC Virtual CPU interface  
            "0x40000000:29",   // Guest RAM region (512MB)
            "0x09000000:12",   // UART MMIO region
        ];
        
        // Configure vector region in address config
        vm0.vm_address_config = {
            "ram_base" : "0x40000000",
            "ram_paddr_base" : "0x40000000", 
            "ram_size" : "0x20000000",
            "dtb_addr" : "0x4F000000",
            "initrd_addr" : "0x4D700000", 
            "kernel_entry_addr" : "0x40000000"
        };
    }
}
```

### Step 14: Test Fixed Configuration

```bash
cd /home/konton-otome/phd/camkes-vm-examples/build
ninja clean && ninja

# Test with debug monitoring
cd /home/konton-otome/phd
./run_qemu_debug.sh

# In another terminal, check vectors now work
python3 qemu_memory_analyzer.py --monitor-port 55555 --hex-only
```

**Expected Results After Fix**:
```
Vector 0x08: 0x????????  (Valid SWI handler address)
FreeRTOS successfully starts first task!
```

---

## Step 15: Validation and Documentation

### Success Criteria:
1. ✅ ARM exception vectors properly mapped at 0x0-0x1C
2. ✅ SWI vector at 0x8 contains valid handler address
3. ✅ FreeRTOS successfully executes past `vPortRestoreTaskContext()`  
4. ✅ First task creation and scheduling works

### Documentation:
- Save all hex dumps from both Linux and seL4 VM
- Document exact configuration changes needed
- Create reproducible test procedure
- Update CLAUDE.md with solution

---

## Tools Reference

**Existing Debug Scripts**:
- `run_qemu_debug.sh` - Starts seL4 VM with monitor interface
- `qemu_memory_analyzer.py` - Automated memory analysis and hex dumps
- `capture_hex_dumps.py` - Memory snapshot capture
- `analyze_snapshots.py` - Memory pattern analysis

**Key Monitor Commands**:
- `x/8wx 0x0` - Examine exception vectors
- `info registers` - Check CPU state  
- `info mtree` - Memory tree mapping
- `x/32wx 0x40000000` - Check guest base

**Expected Timeline**: 2-3 days to complete full analysis and implement fix.

This guide leverages our existing sophisticated debug infrastructure to systematically identify and resolve the ARM exception vector configuration issue causing the Page Fault at 0x8.