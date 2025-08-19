# ARM Exception Vector Table Analysis: Linux vs seL4 Hypervisor

## Problem Statement

FreeRTOS fails with **Page Fault at PC: 0x8** when running under seL4 VM hypervisor. Analysis shows this is the ARM Software Interrupt (SWI) vector address, indicating a missing or misconfigured ARM exception vector table.

## Root Cause Analysis

### FreeRTOS Context Switch Failure
- Location: `vPortRestoreTaskContext()` in `portASM.S:199`
- Instruction: `BX R1` where R1 = 0x8
- Expected: R1 should contain valid function address
- Actual: R1 contains ARM SWI vector address (0x8)

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

## Apple-to-Apple Comparison Plan

### Setup 1: Linux KVM Reference
```bash
# Boot Linux with KVM on identical QEMU ARM virt platform
qemu-system-arm -M virt -cpu cortex-a15 -m 512M \
  -kernel linux-kernel \
  -initrd minimal-rootfs \
  -append "console=ttyAMA0" \
  -nographic

# Inside Linux: Load FreeRTOS and examine vector table at 0x0-0x1C
```

### Setup 2: seL4 VM (Current Failing Case)
```bash
# Your existing seL4 + CAmkES VM setup
cd camkes-vm-examples/build
./simulate
# FreeRTOS fails: Page fault at PC: 0x8
```

## Comparison Points

### 1. ARM Exception Vector Configuration
**Test Script:**
```c
// Read ARM exception vectors
uint32_t *vectors = (uint32_t*)0x0;
for(int i = 0; i < 8; i++) {
    printf("Vector 0x%02x: 0x%08x\n", i*4, vectors[i]);
}
```

**Expected Difference:**
- **Linux:** Valid instruction addresses at each vector
- **seL4:** Unmapped memory or invalid values at 0x8

### 2. VBAR (Vector Base Address Register) 
**Test Code:**
```c
uint32_t vbar;
asm volatile("mrc p15, 0, %0, c12, c0, 0" : "=r"(vbar));
printf("VBAR = 0x%08x\n", vbar);
```

**Expected Difference:**
- **Linux:** VBAR properly configured to valid vector table
- **seL4:** VBAR may point to unmapped or incorrect location

### 3. Memory Mapping at Low Addresses
**Test:** Check if addresses 0x0-0x1C are mapped and accessible

### 4. Guest Exception Handling Setup
**Test:** Verify if hypervisor provides exception vector support to guest

## Implementation Strategy

### Phase 1: Linux Reference Implementation (1 day)
1. **Setup Linux KVM:** Boot minimal Linux on QEMU ARM virt
2. **Create FreeRTOS Loader:** 
   - Load FreeRTOS binary to 0x40000000
   - Setup ARM exception vectors
   - Jump to FreeRTOS entry point
3. **Capture State:** 
   - Vector table content at 0x0-0x1C
   - VBAR register value
   - Memory mapping status

### Phase 2: Vector Table Comparison (1 day)
1. **Compare Vector Content:** Side-by-side analysis of 0x0-0x1C
2. **Identify Missing Vectors:** Determine what seL4 VM lacks
3. **Document Differences:** Create detailed comparison report

### Phase 3: seL4 VM Fix (2-3 days)
1. **Implement Vector Support:** Configure seL4 VM to provide ARM exception vectors
2. **Test Integration:** Verify FreeRTOS progresses past 0x8 fault
3. **Validate Solution:** Ensure proper exception handling

## Quick Verification Commands

### For Linux KVM Setup:
```bash
# Check if vectors are mapped
devmem 0x0 32
devmem 0x4 32  
devmem 0x8 32  # This should contain valid instruction
devmem 0xC 32

# Check VBAR register (if accessible from userspace)
# May need kernel module for privileged register access
```

### For seL4 VM Debug:
```bash
# Add debug output to FreeRTOS before failure
# In vPortRestoreTaskContext():
# Print R1 value before BX R1 instruction
# Print memory content at 0x8
```

## Expected Results

### Successful Linux KVM Run:
```
Vector 0x00: 0x????????  (Reset handler address)
Vector 0x04: 0x????????  (Undefined instruction handler) 
Vector 0x08: 0x????????  (SWI handler address) ← Valid address
Vector 0x0C: 0x????????  (Prefetch abort handler)
...
VBAR = 0x????????
FreeRTOS boots successfully past context switch
```

### Current seL4 VM Failure:
```
Vector 0x00: 0x00000000  (Unmapped/zero)
Vector 0x04: 0x00000000  (Unmapped/zero)
Vector 0x08: 0x00000000  (Unmapped/zero) ← Causes page fault
Vector 0x0C: 0x00000000  (Unmapped/zero)
...
VBAR = 0x????????
FreeRTOS fails: Page fault at PC: 0x8
```

## Success Criteria

1. **Clear Identification:** Document exact vector table differences
2. **Root Cause Confirmation:** Prove 0x8 fault is due to missing SWI vector
3. **Solution Implementation:** Configure seL4 VM to provide ARM exception vectors
4. **Functional Verification:** FreeRTOS successfully starts first task

## Timeline

- **Day 1:** Linux KVM setup and vector analysis
- **Day 2:** Side-by-side comparison and documentation  
- **Day 3-4:** seL4 VM vector table implementation
- **Day 5:** Testing and validation

This focused comparison will provide definitive evidence for what seL4 VM needs to properly support FreeRTOS exception handling.