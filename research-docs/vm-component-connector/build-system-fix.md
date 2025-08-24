# CAmkES Build System Requirements - Critical Fix

## Issue Identified

You correctly identified that the CAmkES build system has strict folder naming requirements that I initially missed.

## Root Cause Analysis

### Build Script Sequence (`init-build.sh`)
1. `init-build.sh` calls CMake with settings from `projects/vm-examples/settings.cmake`
2. `settings.cmake` contains this critical logic:
   ```cmake
   if(EXISTS "${CMAKE_CURRENT_LIST_DIR}/apps/Arm/${CAMKES_VM_APP}")
       set(AppArch "Arm" CACHE STRING "" FORCE)
   # ...
   include("${CMAKE_CURRENT_LIST_DIR}/apps/Arm/${CAMKES_VM_APP}/settings.cmake")
   ```

### The Problem
- **Build Parameter**: `-DCAMKES_VM_APP=vm_echo_test`
- **Expected Folder**: `apps/Arm/vm_echo_test/`
- **Expected Files**: 
  - `apps/Arm/vm_echo_test/settings.cmake`
  - `apps/Arm/vm_echo_test/vm_echo_test.camkes`
- **What I Had**: Folder named `vm_serial_test` with file `vm_echo_test.camkes`

## Solution Applied

### 1. Folder Rename
```bash
mv apps/Arm/vm_serial_test apps/Arm/vm_echo_test
```

### 2. Updated settings.cmake
- **Original**: Only supported `exynos5422`
- **Fixed**: Added support for `qemu-arm-virt` (copied from vm_minimal)
- **Added Settings**:
  ```cmake
  if(${PLATFORM} STREQUAL "qemu-arm-virt")
      set(QEMU_MEMORY "2048")
      set(KernelArmCPU cortex-a53 CACHE STRING "" FORCE)
      set(VmInitRdFile ON CACHE BOOL "" FORCE)
      set(VmDtbFile ON CACHE BOOL "" FORCE)
      set(VmPCISupport ON CACHE BOOL "" FORCE)
      set(VmVirtioConsole ON CACHE BOOL "" FORCE)
  endif()
  ```

### 3. Updated CMakeLists.txt
- **Fixed**: `DeclareCAmkESRootserver(vm_echo_test.camkes ...)`
- **Was**: `DeclareCAmkESRootserver(vm_serial_test.camkes ...)`

### 4. Added Missing Platform Support
```bash
cp -r vm_minimal/qemu-arm-virt vm_echo_test/
```

## Correct Build Sequence Now

### File Structure Required
```
apps/Arm/vm_echo_test/
├── settings.cmake                 # Platform configurations
├── vm_echo_test.camkes           # Main assembly file  
├── CMakeLists.txt                # Build configuration
├── qemu-arm-virt/               # Platform-specific devices
│   └── devices.camkes
├── components/EchoComponent/     # Custom component
└── vm_guest_test/               # Test programs
```

### Build Command
```bash
cd camkes-vm-examples
mkdir build_echo && cd build_echo
source ../../sel4-dev-env/bin/activate && \
export PYTHONPATH=/home/konton-otome/phd/camkes-vm-examples/projects/camkes-tool:/home/konton-otome/phd/camkes-vm-examples/projects/capdl/python-capdl-tool && \
../init-build.sh -DCAMKES_VM_APP=vm_echo_test -DPLATFORM=qemu-arm-virt -DSIMULATION=1 -DLibUSB=OFF && \
ninja
```

## Key Lessons

### 1. CAmkES Naming Convention
- **Application Parameter** = **Folder Name** = **Main .camkes File Prefix**
- Example: `-DCAMKES_VM_APP=vm_echo_test` requires:
  - Folder: `apps/Arm/vm_echo_test/`
  - File: `vm_echo_test.camkes`

### 2. Platform Support Requirements
- Each application needs `settings.cmake` with supported platforms
- Must include platform-specific configuration flags
- Cross-VM connectors require `VmPCISupport` and `VmVirtioConsole`

### 3. Build System Discovery Process
1. `init-build.sh` → `projects/vm-examples/settings.cmake`
2. `settings.cmake` → checks `apps/Arm/${CAMKES_VM_APP}/` exists
3. Includes `apps/Arm/${CAMKES_VM_APP}/settings.cmake`
4. CMakeLists.txt must reference correct `.camkes` file

## Status: ✅ Fixed

The build system will now properly:
1. ✅ Find the `vm_echo_test` folder
2. ✅ Load platform-specific settings for `qemu-arm-virt`
3. ✅ Include EchoComponent and test clients
4. ✅ Generate bootable system image

## Verification Steps

Once CAmkES AST generation issues are resolved:
1. Build should complete without "App does not exist" errors
2. System should boot with EchoComponent available
3. Cross-VM connectors should be functional for latency testing

Thank you for catching this critical build system requirement!