# FreeRTOS Hypervisor Integration Guides

## Overview

This directory contains comprehensive guides for running FreeRTOS under different hypervisor environments, along with debugging and analysis methodologies.

## 📋 **Primary Hypervisor Guides**

### 1. freertos-linux-qemu-setup-guide.md ✅ **RECOMMENDED FOR WORKING FREERTOS**
**Complete Linux QEMU Setup Guide**

- **Status**: ✅ **FULLY WORKING**
- **Purpose**: Run FreeRTOS successfully with complete task scheduler support
- **Key Feature**: No "Page Fault at PC: 0x8" errors
- **Target**: Developers wanting immediate FreeRTOS functionality
- **Contents**:
  - Quick start commands
  - Step-by-step setup instructions
  - Debugging interface configuration
  - Success verification procedures
  - Troubleshooting common issues

### 2. freertos-sel4-vm-complete-setup-guide.md ⚠️ **RESEARCH VERSION**
**Complete seL4 VM Integration Guide**

- **Status**: ⚠️ **PARTIAL - Known Limitations**
- **Purpose**: FreeRTOS integration with formally verified seL4 microkernel
- **Known Issue**: "Page Fault at PC: 0x8" prevents task scheduling
- **Target**: Researchers working on secure virtualization
- **Contents**:
  - seL4/CAmkES environment setup
  - FreeRTOS binary integration
  - Memory layout configuration
  - Current limitations and workarounds
  - Complete CAmkES configuration reference

## 📊 **Analysis and Debugging Guides**

### arm-exception-vector-analysis-guide.md
**ARM Exception Vector Debug Methodology**

- **Purpose**: Step-by-step debugging approach for exception vector issues
- **Target**: Researchers analyzing hypervisor compatibility
- **Contents**:
  - Database snapshot recording procedures
  - Memory analysis techniques
  - Exception vector verification
  - Root cause identification methods

### linux-kvm-freertos-comparison-setup.md
**Hypervisor Comparison Setup**

- **Purpose**: Set up Linux KVM environment for hypervisor comparison
- **Target**: Researchers performing comparative analysis
- **Contents**:
  - Linux KVM configuration
  - Evidence collection procedures
  - Memory access verification
  - Comparison methodology

## 📁 **Supporting Documentation**

### DATABASE_SNAPSHOT_GUIDE.md
**Database-Backed Memory Analysis**

- **Purpose**: Advanced memory debugging using database recording
- **Target**: Users needing sophisticated memory analysis
- **Contents**:
  - Database system setup
  - Memory snapshot recording
  - SQL-based analysis queries
  - Pattern analysis techniques

### detailed-debugging-steps.md
**Comprehensive Debugging Procedures**

- **Purpose**: Complete debugging methodology for complex issues
- **Target**: Researchers and advanced developers
- **Contents**:
  - Environment setup procedures
  - Build configuration details
  - Advanced debugging techniques
  - Validation procedures

### HEX_DUMP_USAGE_GUIDE.md
**Raw Memory Analysis Guide**

- **Purpose**: Direct memory analysis using hex dumps
- **Target**: Users needing low-level memory inspection
- **Contents**:
  - QEMU monitor integration
  - Memory capture procedures
  - Analysis techniques

## 🎯 **Quick Decision Guide**

### **Want FreeRTOS to work immediately?**
→ Use `freertos-linux-qemu-setup-guide.md`

### **Want to research seL4 formal verification?**
→ Use `freertos-sel4-vm-complete-setup-guide.md` (be aware of current limitations)

### **Want to understand the technical differences?**
→ Read both guides and the comparison analysis files

### **Want to debug memory issues?**
→ Use `arm-exception-vector-analysis-guide.md` and `DATABASE_SNAPSHOT_GUIDE.md`

## 📊 **Feature Comparison**

| Feature | Linux QEMU | seL4 VM |
|---------|-------------|---------|
| **Task Scheduler** | ✅ Working | ❌ Fails (Page Fault at PC: 0x8) |
| **Context Switching** | ✅ Full Support | ❌ RFEIA instruction fails |
| **ARM Exception Vectors** | ✅ Present (0x0-0x1C) | ❌ Missing |
| **Multitasking** | ✅ Complete | ❌ Single task only |
| **Development Ready** | ✅ Yes | ❌ Research phase |
| **Formal Verification** | ❌ No | ✅ Yes |
| **Security Guarantees** | ❌ Standard | ✅ Mathematical proofs |

## Usage by Role

### 🎓 **Researchers**
1. Start with **freertos-linux-qemu-setup-guide.md** to see working system
2. Compare with **freertos-sel4-vm-complete-setup-guide.md** to understand issues
3. Use **arm-exception-vector-analysis-guide.md** for root cause analysis
4. Apply **DATABASE_SNAPSHOT_GUIDE.md** for advanced memory analysis

### 👩‍💻 **Developers**
1. Use **freertos-linux-qemu-setup-guide.md** for immediate development
2. Reference **freertos-sel4-vm-complete-setup-guide.md** for seL4 integration
3. Apply debugging guides for troubleshooting

### 🏫 **Students**
1. Begin with **freertos-linux-qemu-setup-guide.md** to understand basic concepts
2. Study **freertos-sel4-vm-complete-setup-guide.md** for complex integration
3. Practice with debugging guides for hands-on experience

### 🔬 **PhD Candidates**
1. Analyze both hypervisor approaches for research comparison
2. Use debugging guides for systematic investigation methodology
3. Apply database tools for comprehensive data collection

## Document Relationships

```
README-reproduction-steps.md (Quick Start)
    ↓
detailed-debugging-steps.md (Complete Process)
    ↓
DATABASE_SNAPSHOT_GUIDE.md (Advanced Analysis)
    ↓
HEX_DUMP_USAGE_GUIDE.md (Raw Memory Analysis)
```

## Prerequisites

Before using these guides, ensure you have:
- Ubuntu/Debian Linux system with development tools
- ARM cross-compilation toolchain
- Python 3.8+ with required packages
- QEMU ARM system emulation
- seL4 development environment

## Expected Outcomes

Following these guides will enable you to:
1. **Reproduce Research**: Complete reproduction of the research methodology
2. **Collect Data**: Systematic collection of memory and instruction trace data
3. **Analyze Results**: Comprehensive analysis using database queries and reports
4. **Validate Patterns**: Verification of memory pattern painting success
5. **Generate Reports**: HTML and CSV reports for research analysis

## Troubleshooting

Each guide includes comprehensive troubleshooting sections for:
- Build environment issues
- QEMU connection problems
- Database recording failures
- Analysis and reporting errors

## Support Materials

These guides are supported by:
- **Code**: Complete implementation in parent directory
- **Methodology**: Theoretical foundation in `/methodology/`
- **Analysis**: Comparative analysis in `/analysis/`
- **Implementation**: Technical details in `/implementation/`

## Validation

All procedures have been validated through:
- ✅ **Multiple Test Runs**: Verified on clean systems
- ✅ **Error Handling**: Comprehensive error scenarios tested
- ✅ **Output Validation**: Expected outputs documented and verified
- ✅ **Performance Testing**: Timing and resource usage measured