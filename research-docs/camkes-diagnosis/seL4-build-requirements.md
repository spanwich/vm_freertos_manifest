# seL4/CAmkES Build Requirements - Complete Path Documentation

## Overview

This document provides the complete and authoritative list of ALL required paths, environment variables, and configuration flags needed for successful seL4/CAmkES VM application builds. This is derived from systematic analysis of successful AST generation commands.

## Critical Environment Variables

### Python Path Configuration
```bash
export PYTHONPATH="/home/konton-otome/phd/camkes-vm-examples/projects/camkes-tool:/home/konton-otome/phd/camkes-vm-examples/projects/capdl/python-capdl-tool"
```

**Purpose**: Enables Python to find CAmkES parser modules and capDL tools
**Critical**: Without this exact path, `python3 -m camkes.parser` will fail to import required modules

## Complete C/C++ Include Paths (--cpp-flag)

### Remote Network Drivers
Required for network-capable VM applications:
```
-I/home/konton-otome/phd/camkes-vm-examples/projects/global-components/remote-drivers/picotcp-ethernet-async/camkes-include
-I/home/konton-otome/phd/camkes-vm-examples/projects/global-components/remote-drivers/picotcp-socket-sync/camkes-include
```

### Component Modules  
Core CAmkES component functionality:
```
-I/home/konton-otome/phd/camkes-vm-examples/projects/global-components/components/modules/fdt-bind-driver/camkes-include
-I/home/konton-otome/phd/camkes-vm-examples/projects/global-components/components/modules/dynamic-untyped-allocators/camkes-include
-I/home/konton-otome/phd/camkes-vm-examples/projects/global-components/components/modules/single-threaded/camkes-include
-I/home/konton-otome/phd/camkes-vm-examples/projects/global-components/components/modules/x86-iospace-dma/camkes-include
-I/home/konton-otome/phd/camkes-vm-examples/projects/global-components/components/modules/picotcp-base/camkes-include
```

### Platform-Specific Components (QEMU ARM virt)
Platform hardware abstraction:
```
-I/home/konton-otome/phd/camkes-vm-examples/projects/global-components/components/ClockServer/camkes-include
-I/home/konton-otome/phd/camkes-vm-examples/projects/global-components/components/ClockServer/include/plat/qemu-arm-virt
-I/home/konton-otome/phd/camkes-vm-examples/projects/global-components/components/GPIOMUXServer/camkes-include
-I/home/konton-otome/phd/camkes-vm-examples/projects/global-components/components/GPIOMUXServer/include/plat/qemu-arm-virt
-I/home/konton-otome/phd/camkes-vm-examples/projects/global-components/components/ResetServer/camkes-include
-I/home/konton-otome/phd/camkes-vm-examples/projects/global-components/components/ResetServer/include/plat/qemu-arm-virt
-I/home/konton-otome/phd/camkes-vm-examples/projects/global-components/plat_components/tx2/BPMPServer/camkes-include
```

### Serial Communication (CRITICAL)
**These were the primary missing paths that caused CMAKE failures:**
```
-I/home/konton-otome/phd/camkes-vm-examples/projects/global-components/components/SerialServer/include/plat/arm_common
-I/home/konton-otome/phd/camkes-vm-examples/projects/global-components/components/SerialServer/camkes-putchar-client/camkes-include
```
**Headers provided**: `plat/serial.h`, serial client interfaces
**Failure symptom**: "plat/serial.h: No such file or directory"

### Time Management (CRITICAL)
```
-I/home/konton-otome/phd/camkes-vm-examples/projects/global-components/components/TimeServer/include/plat/qemu-arm-virt
```
**Headers provided**: `plat/timers.h`
**Failure symptom**: "plat/timers.h: No such file or directory"

### Utility Components
```
-I/home/konton-otome/phd/camkes-vm-examples/projects/global-components/components/BenchUtiliz/camkes-include
-I/home/konton-otome/phd/camkes-vm-examples/projects/global-components/components/Ethdriver/include/plat/qemu-arm-virt
```

### VM Core Components
```
-I/home/konton-otome/phd/camkes-vm-examples/projects/vm/components/VM_Arm
```

## Required Platform Definitions (--cpp-flag)

### Platform Identification
```
-DKERNELARMPLATFORM_QEMU-ARM-VIRT
```
**Purpose**: Enables platform-specific code compilation

### VM Configuration Flags
```
-DVMEMMC2NODMA=0
-DVMVUSB=0
-DVMVCHAN=0
-DTK1DEVICEFWD=0
-DTK1INSECURE=0
-DVMVIRTIONETVIRTQUEUE=0
```
**Purpose**: Configures VM capabilities and hardware support

### Build System Flag
```
-DCAMKES_TOOL_PROCESSING
```
**Purpose**: Enables CAmkES preprocessing mode

## Complete CAmkES Import Paths (--import-path)

### Core CAmkES Framework
```
--import-path=/home/konton-otome/phd/camkes-vm-examples/projects/camkes-tool/include/builtin
--import-path=/home/konton-otome/phd/camkes-vm-examples/projects/camkes-tool/components
--import-path=/home/konton-otome/phd/camkes-vm-examples/projects/camkes-tool/components/arch/arm
```

### Global Component Interfaces
```
--import-path=/home/konton-otome/phd/camkes-vm-examples/projects/global-components/interfaces
--import-path=/home/konton-otome/phd/camkes-vm-examples/projects/global-components/components
```

### Remote Drivers
```
--import-path=/home/konton-otome/phd/camkes-vm-examples/projects/global-components/remote-drivers/picotcp-ethernet-async/camkes-include
--import-path=/home/konton-otome/phd/camkes-vm-examples/projects/global-components/remote-drivers/picotcp-socket-sync/camkes-include
```

### Component Modules
```
--import-path=/home/konton-otome/phd/camkes-vm-examples/projects/global-components/components/modules/fdt-bind-driver/camkes-include
--import-path=/home/konton-otome/phd/camkes-vm-examples/projects/global-components/components/modules/dynamic-untyped-allocators/camkes-include
--import-path=/home/konton-otome/phd/camkes-vm-examples/projects/global-components/components/modules/single-threaded/camkes-include
--import-path=/home/konton-otome/phd/camkes-vm-examples/projects/global-components/components/modules/x86-iospace-dma/camkes-include
--import-path=/home/konton-otome/phd/camkes-vm-examples/projects/global-components/components/modules/picotcp-base/camkes-include
```

### Platform-Specific Component Imports
```
--import-path=/home/konton-otome/phd/camkes-vm-examples/projects/global-components/components/ClockServer/camkes-include
--import-path=/home/konton-otome/phd/camkes-vm-examples/projects/global-components/components/GPIOMUXServer/camkes-include
--import-path=/home/konton-otome/phd/camkes-vm-examples/projects/global-components/components/ResetServer/camkes-include
--import-path=/home/konton-otome/phd/camkes-vm-examples/projects/global-components/plat_components/tx2/BPMPServer/camkes-include
--import-path=/home/konton-otome/phd/camkes-vm-examples/projects/global-components/components/SerialServer/camkes-putchar-client/camkes-include
--import-path=/home/konton-otome/phd/camkes-vm-examples/projects/global-components/components/BenchUtiliz/camkes-include
```

### VM Components
```
--import-path=/home/konton-otome/phd/camkes-vm-examples/projects/vm/components
--import-path=/home/konton-otome/phd/camkes-vm-examples/projects/vm/interfaces
```

### Build-Generated Paths (Must Be Created Manually)
```
--import-path=/home/konton-otome/phd/camkes-vm-examples/build/plat_interfaces/qemu-arm-virt
--import-path=/home/konton-otome/phd/camkes-vm-examples/build/plat_components/qemu-arm-virt
--import-path=/home/konton-otome/phd/camkes-vm-examples/build/camkes-arm-vm/components
--import-path=/home/konton-otome/phd/camkes-vm-examples/build/camkes-arm-vm/interfaces
```

### Application-Specific Path
```
--import-path=/home/konton-otome/phd/camkes-vm-examples/projects/vm-examples/apps/Arm/${APP_NAME}/qemu-arm-virt
```

## Required Directory Structure

Must be created manually before AST generation:
```bash
mkdir -p kernel
mkdir -p plat_interfaces/qemu-arm-virt
mkdir -p plat_components/qemu-arm-virt
mkdir -p camkes-arm-vm/components
mkdir -p camkes-arm-vm/interfaces
```

## Device Tree Blob Requirement

```bash
# DTB file must exist at:
/home/konton-otome/phd/camkes-vm-examples/build/kernel/kernel.dtb

# Generate with:
qemu-system-arm -M virt -cpu cortex-a53 -m 2048M -nographic -dumpdtb kernel/kernel.dtb -kernel /dev/null
```

## Critical Dependencies

### Files That Must Exist
- `kernel/kernel.dtb` - Device tree blob for platform
- `ast.pickle.d` - Dependency tracking (generated)
- `ast.pickle` - AST file (generated, ~187KB for VM apps)

### Applications That Work
- `vm_minimal` - Basic VM with minimal components
- `vm_freertos` - FreeRTOS guest VM
- `vm_echo_connector` - Cross-VM communication demo
- `vm_cross_connector` - Cross-VM dataport demo

## Failure Analysis

### Why CMAKE Failed
CMAKE was missing **ALL** of the following critical path categories:
1. **20+ C/C++ include paths** - caused "header not found" errors
2. **8 platform definition flags** - caused undefined symbol errors  
3. **25+ import paths** - caused CAmkES component discovery failures
4. **Manual directory creation** - caused path resolution failures

### Common Error Patterns
```
# Missing SerialServer paths:
error: plat/serial.h: No such file or directory

# Missing TimeServer paths:  
error: plat/timers.h: No such file or directory

# Missing platform definitions:
error: KERNELARMPLATFORM_QEMU_ARM_VIRT not defined

# Missing import paths:
error: Cannot find component definition for SerialServer
```

## Validation

### Success Indicators
- AST file created: ~187KB `ast.pickle`
- Dependency file created: `ast.pickle.d` with ~100+ dependencies
- No header file errors during parsing
- All CAmkES components discovered and parsed

### Command Verification
The complete working command (single line):
```bash
/usr/bin/cmake -E env PYTHONPATH=/home/konton-otome/phd/camkes-vm-examples/projects/camkes-tool:/home/konton-otome/phd/camkes-vm-examples/projects/capdl/python-capdl-tool python3 -m camkes.parser --import-path=/home/konton-otome/phd/camkes-vm-examples/projects/camkes-tool/include/builtin --dtb=/home/konton-otome/phd/camkes-vm-examples/build/kernel/kernel.dtb --cpp --cpp-bin /usr/bin/cpp [ALL 45+ FLAGS AND PATHS FROM ABOVE] --makefile-dependencies /home/konton-otome/phd/camkes-vm-examples/build/ast.pickle.d --file /home/konton-otome/phd/camkes-vm-examples/projects/vm-examples/apps/Arm/${APP_NAME}/${APP_NAME}.camkes --save-ast /home/konton-otome/phd/camkes-vm-examples/build/ast.pickle
```

## Usage

### Automated Script
```bash
cd /home/konton-otome/phd/research-docs/camkes-diagnosis
APP_NAME=vm_echo_connector ./build_manual_ast.sh
```

### Manual Implementation
Follow the exact paths and flags documented above - **ALL are required** for successful builds.

---

**Document Status**: Complete and validated against successful AST generation commands
**Last Updated**: Based on analysis of `/home/konton-otome/phd/camkes-vm-examples/test-echo/ast.pickle.cmd`
**Validation**: Confirmed working for vm_echo_connector, vm_freertos, vm_minimal applications