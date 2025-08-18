#!/bin/bash
# QEMU Debug Script for FreeRTOS-seL4 Memory Pattern Analysis
# This script launches QEMU with monitoring and tracing capabilities

set -e

echo "=========================================="
echo "  QEMU Debug Runner for Memory Analysis"
echo "  PhD Research - Secure Virtualization"
echo "=========================================="

# Configuration
QEMU_IMAGE="/home/konton-otome/phd/camkes-vm-examples/build/images/capdl-loader-image-arm-qemu-arm-virt"
MONITOR_PORT=55555
TRACE_FILE="/home/konton-otome/phd/qemu_trace.log"
MEMORY_DUMP_DIR="/home/konton-otome/phd/memory_dumps"

# Create memory dump directory
mkdir -p "$MEMORY_DUMP_DIR"

echo "Configuration:"
echo "  QEMU Image: $QEMU_IMAGE"
echo "  Monitor Port: $MONITOR_PORT"
echo "  Trace File: $TRACE_FILE"
echo "  Memory Dumps: $MEMORY_DUMP_DIR"
echo ""

# Check if image exists
if [ ! -f "$QEMU_IMAGE" ]; then
    echo "ERROR: QEMU image not found: $QEMU_IMAGE"
    echo "Please build the seL4 system first:"
    echo "  cd /home/konton-otome/phd/camkes-vm-examples/build"
    echo "  source ../../sel4-dev-env/bin/activate"
    echo "  export PYTHONPATH=..."
    echo "  ninja"
    exit 1
fi

echo "Starting QEMU with debug capabilities..."
echo ""
echo "Available debugging features:"
echo "1. Monitor interface on tcp:127.0.0.1:$MONITOR_PORT"
echo "2. Instruction tracing to $TRACE_FILE"
echo "3. Memory pattern analysis support"
echo ""
echo "Connect to monitor with:"
echo "  telnet 127.0.0.1 $MONITOR_PORT"
echo "  nc 127.0.0.1 $MONITOR_PORT"
echo "  python3 qemu_memory_analyzer.py --monitor-port $MONITOR_PORT"
echo ""
echo "Monitor commands to try:"
echo "  info registers"
echo "  x/32wx 0x40000000  # Guest base"
echo "  x/32wx 0x41000000  # Stack region"
echo "  x/32wx 0x41200000  # Data region"
echo "  x/32wx 0x41400000  # Heap region"
echo "  x/32wx 0x42000000  # Pattern region"
echo "  info mtree         # Memory tree"
echo "  info qtree         # Device tree"
echo ""

# Instruction tracing options
TRACE_OPTIONS=""
if [ "${1:-}" = "--trace" ]; then
    echo "Enabling instruction tracing..."
    TRACE_OPTIONS="-d exec,cpu,guest_errors -D $TRACE_FILE"
    echo "Trace will be written to: $TRACE_FILE"
    echo ""
fi

# Run QEMU with debug options
exec qemu-system-arm \
    -M virt \
    -cpu cortex-a53 \
    -m 2048M \
    -nographic \
    -kernel "$QEMU_IMAGE" \
    -monitor tcp:127.0.0.1:$MONITOR_PORT,server,nowait \
    $TRACE_OPTIONS \
    "$@"