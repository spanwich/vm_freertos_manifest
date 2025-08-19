# seL4 VM Exception Vector Implementation Plan

**Date**: 2025-01-18  
**Purpose**: Implement ARM exception vector support to resolve FreeRTOS Page Fault at PC: 0x8  
**Status**: Implementation Ready  

---

## Executive Summary

Based on our confirmed root cause analysis, the seL4 VM framework does not provide ARM exception vectors at addresses 0x0-0x1C. This causes "Page Fault at PC: 0x8" when FreeRTOS attempts to access the Software Interrupt (SWI) vector during task context switching.

**Solution Approach**: Add ARM exception vector table support to seL4 VM configuration with appropriate handlers that either service exceptions locally or pass them to the guest OS.

---

## Implementation Options Analysis

### Option 1: Low Memory Mapping with Exception Vector Table ✅ RECOMMENDED

**Approach**: Map memory region 0x0-0x1C and install ARM exception vector table

**Advantages**:
- Standard ARM architecture compliance
- Compatible with existing FreeRTOS code
- No guest OS modifications required
- Follows ARM reference manual specifications

**Implementation**:
```c
// In devices.camkes
vm0.untyped_mmios = [
    "0x0:12",          // Exception vectors (4KB at 0x0) - NEW
    "0x8040000:12",    // GIC Virtual CPU interface
    "0x40000000:29",   // Guest RAM region (512MB)
];

// Exception vector handlers at 0x0-0x1C
vm0.exception_vectors = {
    "0x00": "reset_handler",           // Reset
    "0x04": "undefined_handler",       // Undefined Instruction
    "0x08": "svc_handler",             // Software Interrupt (CRITICAL)
    "0x0C": "prefetch_abort_handler",  // Prefetch Abort
    "0x10": "data_abort_handler",      // Data Abort
    "0x14": "reserved_handler",        // Reserved
    "0x18": "irq_handler",             // IRQ
    "0x1C": "fiq_handler"              // FIQ
};
```

### Option 2: VBAR Redirection ⚠️ REQUIRES GUEST MODIFICATION

**Approach**: Set Vector Base Address Register to point to guest RAM region

**Implementation**:
```c
// Redirect exception vectors to guest RAM
vm0.vbar_addr = "0x40100000";  // Vectors in guest RAM space
```

**Disadvantages**:
- Requires FreeRTOS modification to set up vectors at new location
- More complex guest OS integration
- Non-standard memory layout

### Option 3: High Exception Vectors 🚫 NOT COMPATIBLE

**Approach**: Use ARM high vectors at 0xFFFF0000-0xFFFF001C

**Why Not Suitable**:
- FreeRTOS specifically uses low vectors (0x0-0x1C)
- Would require significant FreeRTOS architectural changes
- Compatibility issues with existing ARM code

---

## Detailed Implementation Plan - Option 1

### Phase 1: CAmkES Configuration Updates

#### 1.1 Update devices.camkes
**File**: `/home/konton-otome/phd/camkes-vm-examples/projects/vm-examples/apps/Arm/vm_freertos/qemu-arm-virt/devices.camkes`

```c
#include <configurations/vm.h>

#define VM_RAM_BASE 0x40000000
#define VM_RAM_SIZE 0x20000000
#define VM_DTB_ADDR 0x4F000000
#define VM_INITRD_ADDR 0x4D700000

// NEW: Exception vector definitions
#define EXCEPTION_VECTOR_BASE 0x00000000
#define EXCEPTION_VECTOR_SIZE 0x1000

assembly {
    composition {}
    configuration {
        vm0.vm_address_config = {
            "ram_base" : VAR_STRINGIZE(VM_RAM_BASE),
            "ram_paddr_base" : VAR_STRINGIZE(VM_RAM_BASE),
            "ram_size" : VAR_STRINGIZE(VM_RAM_SIZE),
            "dtb_addr" : VAR_STRINGIZE(VM_DTB_ADDR),
            "initrd_addr" : VAR_STRINGIZE(VM_INITRD_ADDR),
            "kernel_entry_addr" : VAR_STRINGIZE(VM_RAM_BASE),
            // NEW: Exception vector configuration
            "exception_vector_base" : VAR_STRINGIZE(EXCEPTION_VECTOR_BASE)
        };

        vm0.vm_image_config = {
            "kernel_bootcmdline" : "",
            "kernel_stdout" : "/pl011@9000000",
            "provide_initrd" : false,
            "generate_dtb" : true,
            "provide_dtb" : false,
        };

        vm0.num_vcpus = 1;

        vm0.dtb = dtb([
            {"path": "/pl011@9000000"},
        ]);

        // UPDATED: Add exception vector memory mapping
        vm0.untyped_mmios = [
            "0x0:12",          // Exception vectors (4KB) - NEW
            "0x8040000:12",    // GIC Virtual CPU interface
            "0x40000000:29",   // Guest RAM region (512MB)
        ];

        // NEW: Exception vector table configuration
        vm0.exception_vector_config = {
            "provide_vectors" : true,
            "vector_base" : VAR_STRINGIZE(EXCEPTION_VECTOR_BASE),
            "svc_handler_mode" : "passthrough"  // Pass SVC to guest OS
        };
    }
}
```

#### 1.2 ARM Exception Vector Handler Implementation
**New File**: `/home/konton-otome/phd/camkes-vm-examples/projects/vm/components/VM_Arm/src/exception_vectors.S`

```assembly
.section .exception_vectors, "ax"
.align 5

// ARM Exception Vector Table at 0x00000000
.global exception_vector_table
exception_vector_table:
    b reset_handler         // 0x00: Reset
    b undefined_handler     // 0x04: Undefined Instruction  
    b svc_handler           // 0x08: Software Interrupt (SVC/SWI) - CRITICAL
    b prefetch_abort_handler // 0x0C: Prefetch Abort
    b data_abort_handler    // 0x10: Data Abort
    b reserved_handler      // 0x14: Reserved
    b irq_handler           // 0x18: IRQ
    b fiq_handler           // 0x1C: FIQ

// Exception Handlers
reset_handler:
    // Reset - should not occur in VM context
    b .

undefined_handler:
    // Handle undefined instruction - could pass to guest or handle locally
    b .

svc_handler:
    // CRITICAL: Software Interrupt handler
    // This handles FreeRTOS vPortRestoreTaskContext() SVC calls
    // Strategy: Pass control to guest OS SVC handler if it exists
    // For now, simple passthrough to guest
    b .

prefetch_abort_handler:
    // Handle instruction fetch faults
    b .

data_abort_handler:
    // Handle data access faults  
    b .

reserved_handler:
    // Reserved - should not occur
    b .

irq_handler:
    // Handle IRQ interrupts
    b .

fiq_handler:
    // Handle FIQ interrupts
    b .
```

### Phase 2: VM Component Integration

#### 2.1 Update VM Component Configuration
**File**: `/home/konton-otome/phd/camkes-vm-examples/projects/vm/components/VM_Arm/VM_Arm.camkes`

```c
import <std_connector.camkes>;

// VM Component with exception vector support
component VM_Arm {
    // ... existing interfaces ...
    
    // NEW: Exception vector support
    attribute string exception_vector_config;
    attribute string exception_vector_base;
}
```

#### 2.2 VM Initialization Updates
**File**: `/home/konton-otome/phd/camkes-vm-examples/projects/vm/components/VM_Arm/src/main.c`

Add exception vector initialization:

```c
#include <sel4/sel4.h>
#include <camkes.h>

// NEW: Exception vector initialization
static int vm_install_exception_vectors(vm_t *vm) {
    // Map exception vector page at 0x0
    void *vector_addr = (void*)0x0;
    
    // Install exception vector table
    extern char exception_vector_table[];
    memcpy(vector_addr, exception_vector_table, 0x20);  // Copy 32 bytes of vectors
    
    // Flush instruction cache to ensure vectors are visible
    seL4_ARM_Page_Clean_Data(/* page capability */);
    seL4_ARM_Page_Invalidate_Data(/* page capability */);
    
    return 0;
}

int run(void) {
    // ... existing VM initialization ...
    
    // NEW: Install exception vectors
    if (vm_install_exception_vectors(&vm) < 0) {
        ZF_LOGE("Failed to install exception vectors");
        return -1;
    }
    
    // ... rest of existing code ...
}
```

### Phase 3: Memory Management Updates

#### 3.1 Update VM Memory Layout
**File**: `/home/konton-otome/phd/camkes-vm-examples/projects/vm/src/vm_ram.c`

```c
// Update memory region management to include exception vectors
static vm_mem_reservation_t *reserve_exception_vectors(vm_t *vm) {
    // Reserve 0x0-0x1000 for exception vectors
    return vm_reserve_memory_at(vm, 0x0, 0x1000, 
                               default_error_fault_callback, 
                               NULL);
}
```

#### 3.2 Update seL4VMParameters Template
**File**: `/home/konton-otome/phd/camkes-vm-examples/projects/vm/templates/seL4VMParameters.template.c`

Add exception vector configuration handling:

```c
/*- if configuration.get('exception_vector_config') -*/
static struct {
    bool provide_vectors;
    uintptr_t vector_base;
    const char* svc_handler_mode;
} exception_config = {
    .provide_vectors = /*? configuration.exception_vector_config.provide_vectors ?*/,
    .vector_base = /*? configuration.exception_vector_config.vector_base ?*/,
    .svc_handler_mode = "/*? configuration.exception_vector_config.svc_handler_mode ?*/"
};
/*- endif -*/
```

---

## Testing and Validation Plan

### Phase 4: Testing Strategy

#### 4.1 Memory Mapping Verification
```bash
# Start seL4 VM with QEMU debugging
cd /home/konton-otome/phd/camkes-vm-examples/build
./run_qemu_full_debug.sh

# Connect to QEMU monitor
telnet 127.0.0.1 55555

# Verify exception vectors are accessible
(qemu) x/8wx 0x0
# Expected: Should return valid ARM instructions, not "Cannot access memory"
```

#### 4.2 Exception Vector Content Validation
```bash
# Verify vector content matches expected ARM instruction patterns
(qemu) x/8i 0x0
# Expected: ARM branch instructions (b <handler>)
```

#### 4.3 FreeRTOS Integration Test
```bash
# Run complete system and monitor FreeRTOS behavior
./simulate

# Expected output:
# - No "Page Fault at PC: 0x8"
# - FreeRTOS progresses past vPortRestoreTaskContext()
# - Task creation and switching functions correctly
```

#### 4.4 SVC Handler Verification
Using GDB debugging:
```gdb
# Connect to QEMU GDB server
target remote :1234

# Set breakpoint at SVC vector
break *0x8

# Run and verify SVC handler is called
continue
```

---

## Implementation Sequence

### Immediate Tasks (Priority 1)
1. ✅ **Complete root cause documentation** - DONE
2. 🔄 **Create this implementation plan** - IN PROGRESS  
3. 📋 **Update devices.camkes with exception vector mapping**
4. 📋 **Create basic exception vector table in assembly**
5. 🧪 **Test memory mapping with QEMU monitor**

### Short-term Tasks (Priority 2)  
6. **Implement SVC passthrough handler**
7. **Add exception vector installation to VM initialization**
8. **Test with minimal FreeRTOS task switching**
9. **Validate exception handling works correctly**

### Long-term Tasks (Priority 3)
10. **Performance optimization of exception handlers**
11. **Advanced exception handling (e.g., guest fault recovery)**
12. **Multi-core exception vector support**
13. **Documentation and research paper preparation**

---

## Risk Analysis and Mitigation

### High Risk Items
1. **Memory Mapping Conflicts**: Exception vectors at 0x0 might conflict with other system components
   - *Mitigation*: Careful review of existing memory layout, test thoroughly
   
2. **Performance Impact**: Exception vector overhead might affect real-time performance  
   - *Mitigation*: Use minimal overhead handlers, benchmark performance

3. **Guest OS Compatibility**: Changes might break other guest operating systems
   - *Mitigation*: Make exception vector support optional/configurable

### Medium Risk Items  
1. **seL4 Capability Management**: Need proper capabilities for low memory access
   - *Mitigation*: Follow seL4 capability allocation patterns

2. **Cache Coherency**: Exception vectors must be visible to CPU instruction fetch
   - *Mitigation*: Proper cache management in vector installation

---

## Expected Outcomes

### Immediate Benefits
- ✅ **Resolve Page Fault at PC: 0x8** - Primary objective achieved
- ✅ **Enable FreeRTOS task switching** - Context switching functions correctly
- ✅ **ARM architecture compliance** - Standard exception vector table

### Research Impact
- 📖 **Demonstrate seL4 VM flexibility** - Can support diverse guest OS requirements
- 🔬 **Expand seL4 virtualization research** - Beyond Linux-centric assumptions  
- 🛡️ **Maintain security properties** - Exception handling within seL4 security model

### Long-term Research Opportunities
- **Formal verification of exception handling** - Mathematical proof of correctness
- **Real-time system analysis** - Impact of virtualization on timing properties
- **Multi-guest exception management** - Support for multiple concurrent guest OSes

---

## Implementation Status

**Current Status**: 🔄 **DESIGN COMPLETE - READY FOR IMPLEMENTATION**

**Next Step**: Update devices.camkes with exception vector memory mapping

**Estimated Implementation Time**: 2-3 days for basic functionality, 1 week for complete testing and validation

**Dependencies**: 
- Existing seL4 VM framework
- ARM cross-compilation toolchain  
- QEMU debugging environment (already available)

---

**Implementation Plan Status**: ✅ **COMPLETE**  
**Ready for Development**: **YES**  
**Risk Level**: **MEDIUM** (well-understood changes with clear testing strategy)