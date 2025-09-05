#!/bin/bash
# seL4 Manual AST Build Script - Ground Truth Method
# Usage: APP_NAME=vm_echo_connector ./build_manual_ast.sh

set -e

if [ -z "$APP_NAME" ]; then
    echo "Error: APP_NAME environment variable not set"
    echo "Usage: APP_NAME=vm_echo_connector ./build_manual_ast.sh"
    exit 1
fi

echo "=== seL4 Manual AST Build for $APP_NAME ==="

cd /home/konton-otome/phd/camkes-vm-examples
rm -rf build && mkdir -p build && cd build

# Step 1: Create necessary directory structure
echo "Creating directory structure..."
mkdir -p kernel plat_interfaces/qemu-arm-virt plat_components/qemu-arm-virt
mkdir -p camkes-arm-vm/components camkes-arm-vm/interfaces

# Step 2: Generate or copy DTB file
echo "Setting up device tree blob..."
if [ -f ../test-debug/qemu-arm-virt.dtb ]; then
    echo "Reusing existing DTB file..."
    cp ../test-debug/qemu-arm-virt.dtb kernel/kernel.dtb
else
    echo "Generating new DTB file..."
    qemu-system-arm -M virt -cpu cortex-a53 -m 2048M -nographic -dumpdtb kernel/kernel.dtb -kernel /dev/null 2>/dev/null || true
fi

# Verify DTB file exists and has reasonable size
if [ ! -f kernel/kernel.dtb ] || [ $(stat -f%z kernel/kernel.dtb 2>/dev/null || stat -c%s kernel/kernel.dtb 2>/dev/null) -lt 1000 ]; then
    echo "Error: DTB file missing or too small"
    exit 1
fi

echo "DTB file ready: $(ls -lh kernel/kernel.dtb)"

# Step 3: Set environment
export PYTHONPATH="../projects/camkes-tool:../projects/capdl/python-capdl-tool"

# Step 4: Verify application exists
APP_PATH="../projects/vm-examples/apps/Arm/${APP_NAME}"
if [ ! -d "$APP_PATH" ]; then
    echo "Error: Application $APP_NAME not found at $APP_PATH"
    exit 1
fi

CAMKES_FILE="${APP_PATH}/${APP_NAME}.camkes"
if [ ! -f "$CAMKES_FILE" ]; then
    echo "Error: CAmkES file not found: $CAMKES_FILE"
    exit 1
fi

echo "Building application: $APP_NAME"
echo "CAmkES file: $CAMKES_FILE"

# Step 5: Generate AST with ALL required include paths from successful command analysis
echo "Generating AST file with COMPLETE path configuration from working command..."
echo "Using all C/C++ includes, import paths, and compile flags from successful AST generation"

/usr/bin/cmake -E env PYTHONPATH=/home/konton-otome/phd/camkes-vm-examples/projects/camkes-tool:/home/konton-otome/phd/camkes-vm-examples/projects/capdl/python-capdl-tool python3 -m camkes.parser \
  --import-path=/home/konton-otome/phd/camkes-vm-examples/projects/camkes-tool/include/builtin \
  --dtb=/home/konton-otome/phd/camkes-vm-examples/build/kernel/kernel.dtb \
  --cpp --cpp-bin /usr/bin/cpp \
  --cpp-flag=-I/home/konton-otome/phd/camkes-vm-examples/projects/global-components/remote-drivers/picotcp-ethernet-async/camkes-include \
  --cpp-flag=-I/home/konton-otome/phd/camkes-vm-examples/projects/global-components/remote-drivers/picotcp-socket-sync/camkes-include \
  --cpp-flag=-I/home/konton-otome/phd/camkes-vm-examples/projects/global-components/components/modules/fdt-bind-driver/camkes-include \
  --cpp-flag=-I/home/konton-otome/phd/camkes-vm-examples/projects/global-components/components/modules/dynamic-untyped-allocators/camkes-include \
  --cpp-flag=-I/home/konton-otome/phd/camkes-vm-examples/projects/global-components/components/modules/single-threaded/camkes-include \
  --cpp-flag=-I/home/konton-otome/phd/camkes-vm-examples/projects/global-components/components/modules/x86-iospace-dma/camkes-include \
  --cpp-flag=-I/home/konton-otome/phd/camkes-vm-examples/projects/global-components/components/modules/picotcp-base/camkes-include \
  --cpp-flag=-I/home/konton-otome/phd/camkes-vm-examples/projects/global-components/components/ClockServer/camkes-include \
  --cpp-flag=-I/home/konton-otome/phd/camkes-vm-examples/projects/global-components/components/ClockServer/include/plat/qemu-arm-virt \
  --cpp-flag=-I/home/konton-otome/phd/camkes-vm-examples/projects/global-components/components/GPIOMUXServer/camkes-include \
  --cpp-flag=-I/home/konton-otome/phd/camkes-vm-examples/projects/global-components/components/GPIOMUXServer/include/plat/qemu-arm-virt \
  --cpp-flag=-I/home/konton-otome/phd/camkes-vm-examples/projects/global-components/components/ResetServer/camkes-include \
  --cpp-flag=-I/home/konton-otome/phd/camkes-vm-examples/projects/global-components/components/ResetServer/include/plat/qemu-arm-virt \
  --cpp-flag=-I/home/konton-otome/phd/camkes-vm-examples/projects/global-components/plat_components/tx2/BPMPServer/camkes-include \
  --cpp-flag=-I/home/konton-otome/phd/camkes-vm-examples/projects/global-components/components/SerialServer/include/plat/arm_common \
  --cpp-flag=-I/home/konton-otome/phd/camkes-vm-examples/projects/global-components/components/SerialServer/camkes-putchar-client/camkes-include \
  --cpp-flag=-I/home/konton-otome/phd/camkes-vm-examples/projects/global-components/components/TimeServer/include/plat/qemu-arm-virt \
  --cpp-flag=-I/home/konton-otome/phd/camkes-vm-examples/projects/global-components/components/BenchUtiliz/camkes-include \
  --cpp-flag=-I/home/konton-otome/phd/camkes-vm-examples/projects/global-components/components/Ethdriver/include/plat/qemu-arm-virt \
  --cpp-flag=-DKERNELARMPLATFORM_QEMU-ARM-VIRT \
  --cpp-flag=-DVMEMMC2NODMA=0 \
  --cpp-flag=-DVMVUSB=0 \
  --cpp-flag=-DVMVCHAN=0 \
  --cpp-flag=-DTK1DEVICEFWD=0 \
  --cpp-flag=-DTK1INSECURE=0 \
  --cpp-flag=-DVMVIRTIONETVIRTQUEUE=0 \
  --cpp-flag=-I/home/konton-otome/phd/camkes-vm-examples/projects/vm/components/VM_Arm \
  --cpp-flag=-DCAMKES_TOOL_PROCESSING \
  --import-path=/home/konton-otome/phd/camkes-vm-examples/projects/camkes-tool/components \
  --import-path=/home/konton-otome/phd/camkes-vm-examples/projects/camkes-tool/components/arch/arm \
  --import-path=/home/konton-otome/phd/camkes-vm-examples/projects/global-components/interfaces \
  --import-path=/home/konton-otome/phd/camkes-vm-examples/build/plat_interfaces/qemu-arm-virt \
  --import-path=/home/konton-otome/phd/camkes-vm-examples/projects/global-components/components \
  --import-path=/home/konton-otome/phd/camkes-vm-examples/build/plat_components/qemu-arm-virt \
  --import-path=/home/konton-otome/phd/camkes-vm-examples/projects/global-components/remote-drivers/picotcp-ethernet-async/camkes-include \
  --import-path=/home/konton-otome/phd/camkes-vm-examples/projects/global-components/remote-drivers/picotcp-socket-sync/camkes-include \
  --import-path=/home/konton-otome/phd/camkes-vm-examples/projects/global-components/components/modules/fdt-bind-driver/camkes-include \
  --import-path=/home/konton-otome/phd/camkes-vm-examples/projects/global-components/components/modules/dynamic-untyped-allocators/camkes-include \
  --import-path=/home/konton-otome/phd/camkes-vm-examples/projects/global-components/components/modules/single-threaded/camkes-include \
  --import-path=/home/konton-otome/phd/camkes-vm-examples/projects/global-components/components/modules/x86-iospace-dma/camkes-include \
  --import-path=/home/konton-otome/phd/camkes-vm-examples/projects/global-components/components/modules/picotcp-base/camkes-include \
  --import-path=/home/konton-otome/phd/camkes-vm-examples/projects/global-components/components/ClockServer/camkes-include \
  --import-path=/home/konton-otome/phd/camkes-vm-examples/projects/global-components/components/GPIOMUXServer/camkes-include \
  --import-path=/home/konton-otome/phd/camkes-vm-examples/projects/global-components/components/ResetServer/camkes-include \
  --import-path=/home/konton-otome/phd/camkes-vm-examples/projects/global-components/plat_components/tx2/BPMPServer/camkes-include \
  --import-path=/home/konton-otome/phd/camkes-vm-examples/projects/global-components/components/SerialServer/camkes-putchar-client/camkes-include \
  --import-path=/home/konton-otome/phd/camkes-vm-examples/projects/global-components/components/BenchUtiliz/camkes-include \
  --import-path=/home/konton-otome/phd/camkes-vm-examples/projects/vm/components \
  --import-path=/home/konton-otome/phd/camkes-vm-examples/build/camkes-arm-vm/components \
  --import-path=/home/konton-otome/phd/camkes-vm-examples/projects/vm/interfaces \
  --import-path=/home/konton-otome/phd/camkes-vm-examples/build/camkes-arm-vm/interfaces \
  --import-path=/home/konton-otome/phd/camkes-vm-examples/projects/vm-examples/apps/Arm/${APP_NAME}/qemu-arm-virt \
  --makefile-dependencies /home/konton-otome/phd/camkes-vm-examples/build/ast.pickle.d \
  --file /home/konton-otome/phd/camkes-vm-examples/projects/vm-examples/apps/Arm/${APP_NAME}/${APP_NAME}.camkes \
  --save-ast /home/konton-otome/phd/camkes-vm-examples/build/ast.pickle

# Step 6: Verify AST generation success
echo "Verifying AST generation..."
if [ ! -f ast.pickle ]; then
    echo "❌ AST generation FAILED - ast.pickle not created"
    exit 1
fi

if [ ! -f ast.pickle.d ]; then
    echo "❌ AST generation FAILED - ast.pickle.d not created"  
    exit 1
fi

AST_SIZE=$(stat -f%z ast.pickle 2>/dev/null || stat -c%s ast.pickle 2>/dev/null)
if [ $AST_SIZE -lt 50000 ]; then
    echo "❌ AST file suspiciously small: $AST_SIZE bytes"
    exit 1
fi

echo "✅ AST generation SUCCESS!"
echo "   ast.pickle: $(ls -lh ast.pickle)"
echo "   ast.pickle.d: $(ls -lh ast.pickle.d)"

# Step 7: Success summary
echo ""
echo "=== BUILD SUMMARY ==="
echo "✅ Application: $APP_NAME"  
echo "✅ AST generated: $(($AST_SIZE / 1024))KB"
echo "✅ Dependencies tracked: $(wc -l < ast.pickle.d) files"
echo ""
echo "⚠️  IMPORTANT: Do NOT run cmake - it will destroy the AST file"
echo "    Use manual build process or specialized tools from here forward"
echo ""
echo "Next steps:"
echo "1. Generate capDL specification from AST"
echo "2. Build seL4 kernel and user components"  
echo "3. Create final system image"
echo ""
echo "Ground Truth AST Generation Complete! 🎉"