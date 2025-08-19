#!/bin/bash
# Enhanced QEMU launcher with GDB server and monitor for comprehensive debugging
# This enables both memory snapshots via GDB and monitor-based hex dumps

set -e

echo "=========================================="
echo "  QEMU Full Debug Mode"
echo "  GDB + Monitor + Memory Snapshots"
echo "=========================================="

# Configuration
QEMU_IMAGE="/home/konton-otome/phd/camkes-vm-examples/build/images/capdl-loader-image-arm-qemu-arm-virt"
GDB_PORT=1234
MONITOR_PORT=55555
TRACE_FILE="/home/konton-otome/phd/qemu_full_trace.log"

echo "Configuration:"
echo "  QEMU Image: $QEMU_IMAGE"
echo "  GDB Server: tcp::$GDB_PORT"
echo "  Monitor: tcp:127.0.0.1:$MONITOR_PORT"
echo "  Trace File: $TRACE_FILE"
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

echo "🚀 Starting QEMU with full debugging support..."
echo ""
echo "Debugging interfaces available:"
echo "1. GDB Server:"
echo "   Connect with: gdb-multiarch"
echo "   (gdb) target remote :$GDB_PORT"
echo "   (gdb) info registers"
echo "   (gdb) x/32wx 0x40000000"
echo ""
echo "2. Monitor Interface:"
echo "   Connect with: telnet 127.0.0.1 $MONITOR_PORT"
echo "   Or use: python3 qemu_memory_analyzer.py"
echo ""
echo "3. Memory Snapshot Database:"
echo "   python3 memory_snapshot_db.py --record-boot --gdb-port $GDB_PORT"
echo ""
echo "4. Combined Analysis:"
echo "   python3 capture_hex_dumps.py --continuous &"
echo "   python3 memory_snapshot_db.py --record-boot"
echo ""

# Trace options
TRACE_OPTIONS=""
if [ "${1:-}" = "--trace" ]; then
    echo "Enabling instruction tracing..."
    TRACE_OPTIONS="-d exec,cpu,guest_errors,int -D $TRACE_FILE"
    echo "Trace will be written to: $TRACE_FILE"
    echo ""
fi

# Additional debug options
DEBUG_OPTIONS=""
if [ "${1:-}" = "--debug" ] || [ "${2:-}" = "--debug" ]; then
    echo "Enabling additional debug options..."
    DEBUG_OPTIONS="-d exec,cpu,guest_errors,int,mmu -D $TRACE_FILE"
    echo ""
fi

echo "QEMU Command Line:"
echo "qemu-system-arm -M virt -cpu cortex-a53 -m 2048M -nographic \\"
echo "  -kernel $QEMU_IMAGE \\"
echo "  -gdb tcp::$GDB_PORT \\"
echo "  -monitor tcp:127.0.0.1:$MONITOR_PORT,server,nowait \\"
echo "  $TRACE_OPTIONS $DEBUG_OPTIONS"
echo ""

echo "Press Ctrl+C to stop QEMU"
echo "Starting in 3 seconds..."
sleep 3

# Run QEMU with full debugging
exec qemu-system-arm \
    -M virt \
    -cpu cortex-a53 \
    -m 2048M \
    -nographic \
    -kernel "$QEMU_IMAGE" \
    -gdb tcp::$GDB_PORT \
    -monitor tcp:127.0.0.1:$MONITOR_PORT,server,nowait \
    $TRACE_OPTIONS \
    $DEBUG_OPTIONS \
    "$@"