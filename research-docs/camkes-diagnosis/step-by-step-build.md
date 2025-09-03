# CAmkES Build Step-by-Step Diagnosis

**Date**: September 3, 2025  
**Objective**: Recreate the working build process that reaches ninja successfully  
**Platform**: qemu-arm-virt, AArch64, vm_minimal

## Step 1: Clean Environment Setup

Starting with completely clean build directory.

```bash
rm -rf *
ls -la
```

**Result**: ✅ Build directory completely empty (only . and .. entries)

## Step 2: Initial CMake Run

Running initial cmake to generate build infrastructure.

```bash
export PYTHONPATH=/home/konton-otome/phd/camkes-vm-examples/projects/camkes-tool:/home/konton-otome/phd/camkes-vm-examples/projects/capdl/python-capdl-tool && cmake -G Ninja -DCAMKES_VM_APP=vm_minimal -DAARCH64=1 -DPLATFORM=qemu-arm-virt -DSIMULATION=1 -DLibUSB=OFF -DSEL4_CACHE_DIR=/home/konton-otome/phd/camkes-vm-examples/.sel4_cache -C /home/konton-otome/phd/camkes-vm-examples/projects/vm-examples/settings.cmake /home/konton-otome/phd/camkes-vm-examples/projects/vm-examples
```

**Result**: ✅ **CMAKE SUCCEEDED!**
- "Configuring done (4.0s)"
- "Generating done (0.1s)" 
- "Build files have been written to..."
- ast.pickle: 177,234 bytes (valid)
- ast.pickle.d: 2,885 bytes (dependencies)  
- build.ninja: 2,027,086 bytes (ninja build file)

## Step 3: Ninja Build

Running ninja to compile the complete system.

```bash
ninja
```

**Result**: ✅ **NINJA BUILD SUCCEEDED!**
- Built 392/392 targets successfully
- Final image: images/capdl-loader-image-arm-qemu-arm-virt (19.8MB)
- Simulate script: ./simulate (executable)

## BREAKTHROUGH DISCOVERY

**The build actually WORKS when run properly!** The issue was not with the CAmkES build system itself.

### Key Success Factors

1. **Clean Environment**: Starting with completely empty build directory
2. **Proper PYTHONPATH**: Must be set before cmake:
   ```bash
   export PYTHONPATH=/home/konton-otome/phd/camkes-vm-examples/projects/camkes-tool:/home/konton-otome/phd/camkes-vm-examples/projects/capdl/python-capdl-tool
   ```
3. **Single Command**: Environment and cmake in same shell session
4. **Allow Natural Timing**: CMake needs ~4 seconds to complete AST generation
5. **All Required Flags**: Complete cmake command with all necessary parameters

### What Was Wrong Before

- **Interrupted Processes**: Previous attempts may have been interrupted during AST generation
- **Environment Issues**: PYTHONPATH not properly inherited by subprocesses
- **Impatience**: Not allowing CMake the full 4+ seconds it needs for complex builds
- **Partial Builds**: Incremental attempts on corrupted build state

### Final Working Command

```bash
cd /home/konton-otome/phd/camkes-vm-examples/build
rm -rf *
export PYTHONPATH=/home/konton-otome/phd/camkes-vm-examples/projects/camkes-tool:/home/konton-otome/phd/camkes-vm-examples/projects/capdl/python-capdl-tool
cmake -G Ninja -DCAMKES_VM_APP=vm_minimal -DAARCH64=1 -DPLATFORM=qemu-arm-virt -DSIMULATION=1 -DLibUSB=OFF -DSEL4_CACHE_DIR=/home/konton-otome/phd/camkes-vm-examples/.sel4_cache -C /home/konton-otome/phd/camkes-vm-examples/projects/vm-examples/settings.cmake /home/konton-otome/phd/camkes-vm-examples/projects/vm-examples
ninja
```

**Result**: Complete successful build with working artifacts ready for QEMU simulation.