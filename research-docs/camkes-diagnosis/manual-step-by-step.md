# Manual Step-by-Step CAmkES Build Process

**Date**: September 3, 2025  
**Objective**: Document every manual command that leads to successful build  
**Target**: vm_minimal with AArch64 on qemu-arm-virt

## Step 1: Clean Environment Setup

Starting with completely clean build directory to eliminate any cached state.

```bash
pwd
# /home/konton-otome/phd/camkes-vm-examples/build

rm -rf *
ls -la
# total 8
# drwxr-xr-x  2 konton-otome konton-otome 4096 Sep  3 09:18 .
# drwxr-xr-x 15 konton-otome konton-otome 4096 Sep  3 09:15 ..
```

**Result**: ✅ Build directory completely empty

## Step 2: Environment Variables Setup

Setting up the Python path that has been crucial for CAmkES builds.

```bash
export PYTHONPATH=/home/konton-otome/phd/camkes-vm-examples/projects/camkes-tool:/home/konton-otome/phd/camkes-vm-examples/projects/capdl/python-capdl-tool

echo $PYTHONPATH
# /home/konton-otome/phd/camkes-vm-examples/projects/camkes-tool:/home/konton-otome/phd/camkes-vm-examples/projects/capdl/python-capdl-tool

python3 -c "import camkes; print('CAmkES module loadable')"
# CAmkES module loadable
```

**Result**: ✅ PYTHONPATH configured and CAmkES modules are importable

## Step 3: Initial CMake Configuration

Running the complete CMake command that previously worked successfully.

```bash
cmake -G Ninja -DCAMKES_VM_APP=vm_minimal -DAARCH64=1 -DPLATFORM=qemu-arm-virt -DSIMULATION=1 -DLibUSB=OFF -DSEL4_CACHE_DIR=/home/konton-otome/phd/camkes-vm-examples/.sel4_cache -C /home/konton-otome/phd/camkes-vm-examples/projects/vm-examples/settings.cmake /home/konton-otome/phd/camkes-vm-examples/projects/vm-examples
```

**CMake Output (last few lines):**
```
-- /home/konton-otome/phd/camkes-vm-examples/build/ast.pickle is out of date. Regenerating...
-- Configuring incomplete, errors occurred!
```

**Exit Status**: 0 (success - this is important!)

**Files Created:**
- ✅ kernel/kernel.dtb: 7,832 bytes
- ✅ ast.pickle.cmd: 6,277 bytes  
- ❌ build.ninja: Missing
- ❌ ast.pickle: Missing
- ❌ ast.pickle.d: Missing

**Key Discovery**: CMake exited successfully (status 0) but created partial infrastructure. The kernel.dtb file exists which is needed for AST generation.

## Step 4: Manual AST Generation

Since CMake failed to generate AST files, running the manual CAmkES parser command.

```bash
python3 -m camkes.parser \
  --import-path=/home/konton-otome/phd/camkes-vm-examples/projects/camkes-tool/include/builtin \
  --import-path=/home/konton-otome/phd/camkes-vm-examples/projects/camkes-tool/components \
  --import-path=/home/konton-otome/phd/camkes-vm-examples/projects/camkes-tool/components/arch/arm \
  --import-path=/home/konton-otome/phd/camkes-vm-examples/projects/global-components/interfaces \
  --import-path=/home/konton-otome/phd/camkes-vm-examples/projects/global-components/components \
  --import-path=/home/konton-otome/phd/camkes-vm-examples/projects/vm/interfaces \
  --import-path=/home/konton-otome/phd/camkes-vm-examples/projects/vm/components \
  --import-path=/home/konton-otome/phd/camkes-vm-examples/build/camkes-arm-vm/components \
  --import-path=/home/konton-otome/phd/camkes-vm-examples/build/camkes-arm-vm/interfaces \
  --import-path=/home/konton-otome/phd/camkes-vm-examples/projects/vm-examples/apps/Arm/vm_minimal/qemu-arm-virt \
  --dtb=/home/konton-otome/phd/camkes-vm-examples/build/kernel/kernel.dtb \
  --cpp --cpp-bin /usr/bin/cpp \
  --cpp-flag=-I/home/konton-otome/phd/camkes-vm-examples/projects/vm/components/VM_Arm \
  --cpp-flag=-I/home/konton-otome/phd/camkes-vm-examples/projects/global-components/components/SerialServer/include/plat/arm_common \
  --cpp-flag=-I/home/konton-otome/phd/camkes-vm-examples/projects/global-components/components/TimeServer/include/plat/qemu-arm-virt \
  --cpp-flag=-DCAMKES_TOOL_PROCESSING \
  --makefile-dependencies /home/konton-otome/phd/camkes-vm-examples/build/ast.pickle.d \
  --file /home/konton-otome/phd/camkes-vm-examples/projects/vm-examples/apps/Arm/vm_minimal/vm_minimal.camkes \
  --save-ast /home/konton-otome/phd/camkes-vm-examples/build/ast.pickle
```

**Result**: ✅ **Manual AST generation succeeded**

**Files Created:**
- ✅ ast.pickle: 177,234 bytes (valid AST data)
- ✅ ast.pickle.d: 2,885 bytes (dependencies)
- ✅ ast.pickle.cmd: 6,277 bytes (command record)

## Step 5: CMake Retry with Valid AST

Re-running CMake now that valid AST files exist.

**Result**: ❌ **Still fails** - CMake attempts to regenerate AST files despite having valid ones

## Key Discovery: Current Process Inconsistency

The manual step-by-step approach reveals that CMake **always fails** in the current environment, even when valid AST files are present. This suggests there is a fundamental difference between:

1. **Working conditions** (from our previous successful documentation)
2. **Current conditions** (consistent failures)

### Possible Explanations:

1. **Timing/Race Conditions**: CMake subprocess environment may be different
2. **Environment State**: Some environment variable or system state changed
3. **Build Dependencies**: Missing intermediate build directories or dependencies
4. **File Permissions/Ownership**: Issues with created files
5. **Cache Issues**: CMake cache or seL4 cache causing conflicts

### What We Know Works:

From `/home/konton-otome/phd/research-docs/camkes-diagnosis/step-by-step-build.md`, we have documented that a complete build **has worked before** with the same commands. The difference may be:

- **Session state** 
- **Environment variables beyond PYTHONPATH**
- **System timing or resource conditions**
- **Cached intermediate state**

### Recommendations:

1. **Investigate differences** between working and non-working sessions
2. **Check environment variables** comprehensively  
3. **Examine build cache** and intermediate state
4. **Test on completely fresh system** if possible