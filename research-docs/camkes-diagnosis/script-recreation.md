# Script Steps Manual Recreation

**Date**: September 3, 2025  
**Objective**: Execute claude-build.sh steps manually to understand how pre-built AST files worked  
**Focus**: Understand the EXACT sequence that made AST generation work before

## Step 0: Fresh Start

Starting completely fresh to eliminate any previous state.

**Commands:**
```bash
pwd  # /home/konton-otome/phd/camkes-vm-examples/build
rm -rf *
ls -la  # total 8, completely empty
```

## Step 1: Environment Setup

```bash
export PYTHONPATH=/home/konton-otome/phd/camkes-vm-examples/projects/camkes-tool:/home/konton-otome/phd/camkes-vm-examples/projects/capdl/python-capdl-tool
```

## Step 2: Initial CMake Run

```bash
cmake -G Ninja -DCAMKES_VM_APP=vm_minimal -DAARCH64=1 -DPLATFORM=qemu-arm-virt -DSIMULATION=1 -DLibUSB=OFF -DSEL4_CACHE_DIR=/home/konton-otome/phd/camkes-vm-examples/.sel4_cache -C /home/konton-otome/phd/camkes-vm-examples/projects/vm-examples/settings.cmake /home/konton-otome/phd/camkes-vm-examples/projects/vm-examples
```

**Result:**
- ❌ CMake fails with "ast.pickle is out of date. Regenerating..."
- ✅ Exit status: 0 (success)  
- ✅ kernel/kernel.dtb created (7,832 bytes)
- ❌ No ast.pickle.d file

## Step 3: Manual AST Generation (Following Script Logic)

Since ast.pickle.d is missing and kernel.dtb exists, run manual AST generation with comprehensive flags from script:

```bash
python3 -m camkes.parser [comprehensive flags from script]
```

**Result:**
- ✅ **Manual AST generation SUCCEEDED**
- ✅ ast.pickle: 177,234 bytes (valid)
- ✅ ast.pickle.d: 2,885 bytes (dependencies)

## Step 4: CMake Retry with Pre-built AST

Re-run CMake with valid pre-built AST files:

```bash
cmake -G Ninja [same flags as before]
```

**Result:**
- ❌ **STILL FAILS** with "ast.pickle is out of date. Regenerating..."  
- ❌ **CRITICAL**: CMake **DESTROYS** the valid ast.pickle file!
- ✅ ast.pickle.d remains (2,885 bytes)
- ❌ ast.pickle.cmd remains but **ast.pickle is DELETED**

## 🔍 KEY DISCOVERY: The Root Problem

**The fundamental issue**: CMake **always tries to regenerate AST files** even when valid ones exist, and when that regeneration fails, it **deletes the working AST files**.

This explains why:
1. ✅ Manual AST generation works perfectly
2. ❌ Pre-built AST approach fails - CMake destroys working files
3. ❌ Script approach fails - Same destructive behavior

## 🎯 The Missing Piece

For the pre-built AST approach to work, **CMake must NOT attempt regeneration**. This requires either:

1. **Timestamp manipulation** - Make AST files appear newer than dependencies
2. **CMake cache manipulation** - Prevent CMake from detecting "out of date"  
3. **Dependency bypass** - Somehow skip the dependency check
4. **Different CMake invocation** - Use flags that prevent regeneration

The evidence from previous successful builds suggests there was a condition where CMake **did not attempt AST regeneration**, allowing the pre-built files to be used directly.