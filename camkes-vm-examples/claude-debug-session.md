# Claude Code seL4 Build Debug Session

**Date**: August 14, 2025  
**Issue**: Claude Code bash tool failing to build seL4/CAmkES projects with "ast.pickle.d" error  
**Status**: ✅ **RESOLVED**

## Problem Summary

Claude Code's bash tool was consistently failing to build seL4 VM projects with the error:
```
CMake Error: file failed to open for reading (No such file or directory):
/home/konton-otome/phd/camkes-vm-examples/build/ast.pickle.d
```

The build worked perfectly in the user's terminal but failed in Claude's bash tool environment, despite identical system configurations.

## Root Cause Analysis

### Initial Hypotheses Tested:
1. ❌ **Python Virtual Environment**: Created `sel4-dev-env` and installed all CAmkES dependencies
2. ❌ **Python Version Differences**: Both environments used identical Python 3.12.3
3. ❌ **Bash Version Differences**: Both used GNU bash 5.2.21
4. ❌ **Python Wrapper Scripts**: Created wrapper scripts with correct environment
5. ❌ **Manual Step-by-Step Execution**: Broke down init-build.sh into individual commands

### Breakthrough Discovery

The actual issue was discovered by running the CAmkES parser command manually outside of CMake:

```bash
# This command revealed the real error (hidden by CMake):
export PYTHONPATH=/path/to/camkes-tool:/path/to/python-capdl-tool
python3 -m camkes.parser [full command with all flags...]

# Error revealed:
ERROR:CAmkES:import 'devices.camkes' not found
```

**Root Cause**: CMake's `execute_process` with `-E env` was not properly passing environment variables to subprocesses in the Claude Code bash tool context, causing the CAmkES parser to fail silently during AST generation.

## Solution

### The Fix:
Export PYTHONPATH explicitly in the shell session before running any build commands:

```bash
export PYTHONPATH=/home/konton-otome/phd/camkes-vm-examples/projects/camkes-tool:/home/konton-otome/phd/camkes-vm-examples/projects/capdl/python-capdl-tool
```

### Complete Working Build Process:
```bash
cd /home/konton-otome/phd/camkes-vm-examples/build
rm -rf *

# Export PYTHONPATH (critical for Claude Code bash tool)
export PYTHONPATH=/home/konton-otome/phd/camkes-vm-examples/projects/camkes-tool:/home/konton-otome/phd/camkes-vm-examples/projects/capdl/python-capdl-tool

# Run standard build commands
../init-build.sh -DCAMKES_VM_APP=vm_freertos -DPLATFORM=qemu-arm-virt -DSIMULATION=1 -DLibUSB=OFF
ninja
```

### Verification of Success:
```
-- Configuring done (2.7s)
-- Generating done (0.2s)
-- Build files have been written to: /home/konton-otome/phd/camkes-vm-examples/build
[391/391] Generating images/capdl-loader-image-arm-qemu-arm-virt
```

## Key Learning Points

1. **Environment Variable Inheritance**: Different execution contexts (interactive terminal vs programmatic bash tool) can have subtle differences in how environment variables are passed to subprocesses.

2. **Error Masking**: CMake's `execute_process` can hide detailed error messages, making debugging difficult. Running commands manually revealed the actual issue.

3. **Debugging Methodology**: 
   - Test individual components in isolation
   - Compare successful vs failed environments systematically
   - Break down complex build processes into individual steps
   - Run failing commands manually to see detailed errors

4. **Process Execution Context Matters**: Even with identical system configurations, different execution contexts can behave differently with subprocess environment inheritance.

## Files Modified

### CLAUDE.md Updates:
- Added "Claude Code Bash Tool Compatibility Fix" section
- Updated all build command examples to include PYTHONPATH export
- Documented root cause and solution for future reference

## Impact

This fix enables Claude Code's bash tool to successfully build seL4/CAmkES projects, matching the functionality available in standard terminal environments. The solution is now documented in CLAUDE.md for future use.

---

**Final Status**: ✅ **FULLY RESOLVED** - Claude Code bash tool can now build seL4 VM projects successfully.