# Detailed Debugging Steps for FreeRTOS-seL4 Memory Pattern Analysis

## Overview

This document provides step-by-step instructions for debugging FreeRTOS-seL4 integration using the database-backed memory snapshot methodology. Follow these procedures to reproduce the research and analyze memory pattern painting behavior.

## Prerequisites

### System Requirements
- Ubuntu/Debian Linux system with seL4 development environment
- Python 3.8+ with required packages
- ARM cross-compilation toolchain (`arm-none-eabi-gcc`)
- QEMU ARM system emulation
- SQLite3 database support

### Environment Setup
```bash
# Activate seL4 development environment
cd /home/konton-otome/phd
source sel4-dev-env/bin/activate

# Export required Python path for CAmkES tools
export PYTHONPATH=/home/konton-otome/phd/camkes-vm-examples/projects/camkes-tool:/home/konton-otome/phd/camkes-vm-examples/projects/capdl/python-capdl-tool
```

## Step 1: Build FreeRTOS Debug Binary

### 1.1 Navigate to FreeRTOS Source
```bash
cd /home/konton-otome/phd/freertos_vexpress_a9
```

### 1.2 Build Debug Version
```bash
# Make the build script executable
chmod +x build_debug.sh

# Build FreeRTOS with memory pattern debugging
./build_debug.sh
```

**Expected Output:**
```
🔨 Building FreeRTOS with Memory Pattern Debugging
Using toolchain: arm-none-eabi-gcc
✅ Build completed successfully
📦 Debug binary: /home/konton-otome/phd/freertos_vexpress_a9/freertos_debug.bin
```

### 1.3 Deploy to seL4 VM Directory
```bash
# Copy debug binary to seL4 VM guest directory
cp freertos_debug.bin /home/konton-otome/phd/camkes-vm-examples/projects/vm-examples/apps/Arm/vm_freertos/qemu-arm-virt/
```

## Step 2: Build seL4 System

### 2.1 Configure seL4 Build
```bash
cd /home/konton-otome/phd/camkes-vm-examples
mkdir -p build && cd build

# Activate Python environment and export PYTHONPATH
source ../../sel4-dev-env/bin/activate
export PYTHONPATH=/home/konton-otome/phd/camkes-vm-examples/projects/camkes-tool:/home/konton-otome/phd/camkes-vm-examples/projects/capdl/python-capdl-tool

# Initialize build system for FreeRTOS VM
../init-build.sh -DCAMKES_VM_APP=vm_freertos -DPLATFORM=qemu-arm-virt -DSIMULATION=1 -DLibUSB=OFF
```

### 2.2 Build System
```bash
# Build the complete seL4 system
ninja
```

**Expected Output:**
```
[1/XXX] Building seL4 kernel
[XXX/XXX] Linking capdl-loader-image-arm-qemu-arm-virt
✅ Build completed successfully
```

### 2.3 Verify Build Artifacts
```bash
# Check that the seL4 image was created
ls -la images/capdl-loader-image-arm-qemu-arm-virt
```

## Step 3: Initialize Database System

### 3.1 Create Database
```bash
cd /home/konton-otome/phd

# Initialize SQLite database with schema
python3 memory_snapshot_db.py --init-db --db-path freertos_debug_session.db
```

**Expected Output:**
```
🗄️  Initializing database schema
✅ Database initialized: freertos_debug_session.db
📊 Tables created: boot_sessions, memory_snapshots, memory_regions, instruction_traces, boot_stages
```

### 3.2 Verify Database Structure
```bash
# Check database tables
sqlite3 freertos_debug_session.db ".schema"
```

## Step 4: Start QEMU with Full Debug Support

### 4.1 Launch QEMU in Debug Mode
```bash
# Terminal 1: Start QEMU with GDB server and monitor
./run_qemu_full_debug.sh
```

**Expected Output:**
```
==========================================
  QEMU Full Debug Mode
  GDB + Monitor + Memory Snapshots
==========================================

Configuration:
  QEMU Image: /home/konton-otome/phd/camkes-vm-examples/build/images/capdl-loader-image-arm-qemu-arm-virt
  GDB Server: tcp::1234
  Monitor: tcp:127.0.0.1:55555

🚀 Starting QEMU with full debugging support...

Debugging interfaces available:
1. GDB Server: Connect with gdb-multiarch, target remote :1234
2. Monitor Interface: telnet 127.0.0.1 55555
3. Memory Snapshot Database: python3 memory_snapshot_db.py --record-boot
```

### 4.2 Verify QEMU Startup
Wait for seL4 boot messages to appear, then verify GDB server is accessible:
```bash
# Test GDB connection (in another terminal)
echo "info registers" | nc localhost 1234
```

## Step 5: Record Boot Sequence with Database Snapshots

### 5.1 Start Database Recording
```bash
# Terminal 2: Record complete boot sequence
python3 memory_snapshot_db.py --record-boot --gdb-port 1234 --db-path freertos_debug_session.db --max-instructions 200000
```

**Expected Output:**
```
🔍 Starting boot sequence recording
📡 Connecting to QEMU GDB server on port 1234
✅ GDB connection established
🗄️  Database session started
📊 Recording boot sequence...

Boot Stage Detection:
  elfloader (0x60000000-0x61000000)
  seL4_boot (0xe0000000-0xe1000000)
  rootserver_start (0x10000-0x20000)
  camkes_init (0x40000000-0x40001000)
  freertos_main (0x40000e70-0x40001000)
  pattern_painting (0x400008e8-0x40001000)
  scheduler_start (0x40003000-0x40004000)

Memory Snapshots Captured:
  📸 Snapshot 1: elfloader stage
  📸 Snapshot 2: seL4_boot stage
  📸 Snapshot 3: freertos_main stage
  📸 Snapshot 4: pattern_painting stage
```

### 5.2 Monitor Recording Progress
```bash
# Monitor database growth during recording
watch -n 5 "sqlite3 freertos_debug_session.db 'SELECT COUNT(*) as instructions FROM instruction_traces; SELECT COUNT(*) as snapshots FROM memory_snapshots;'"
```

## Step 6: Parallel Hex Dump Capture (Optional)

### 6.1 Start Hex Dump Collection
```bash
# Terminal 3: Parallel hex dump capture
python3 qemu_memory_analyzer.py --continuous-dump --interval 30 --save-files
```

**Expected Output:**
```
🔍 QEMU Memory Analyzer - Continuous Mode
📡 Connecting to QEMU monitor on port 55555
✅ Monitor connection established

📸 Capturing memory dumps every 30 seconds
💾 Saving hex dumps to files: memory_dump_YYYYMMDD_HHMMSS.hex

Memory Region Captures:
  0x40000000: Guest base memory (boot code and data)
  0x41000000: Stack region (0xDEADBEEF patterns)
  0x41200000: Data region (0x12345678 patterns)
  0x41400000: Heap region (0xCAFEBABE patterns)
  0x42000000: Pattern region (0x55AA55AA + dynamic)
  0x9000000:  UART device registers
```

## Step 7: Analyze Recorded Data

### 7.1 List Available Sessions
```bash
# Check recorded sessions
python3 analyze_snapshots.py --db freertos_debug_session.db --list-sessions
```

**Expected Output:**
```
📋 Found 1 boot sessions:
  Session 1: 2025-08-15 14:30:22
    Description: FreeRTOS-seL4 boot sequence with memory pattern painting
    Snapshots: 8, Instructions: 187,432
```

### 7.2 Generate Comprehensive Analysis Report
```bash
# Generate HTML report
python3 analyze_snapshots.py --db freertos_debug_session.db --session 1 --report freertos_boot_analysis.html
```

**Expected Output:**
```
📄 Generating HTML report for session 1
🔍 Analyzing boot sequence for session 1
📊 Analyzing memory pattern evolution for session 1
🔍 Analyzing instruction patterns for session 1
✅ HTML report generated: freertos_boot_analysis.html
```

### 7.3 Export Data for External Analysis
```bash
# Export to CSV files
python3 analyze_snapshots.py --db freertos_debug_session.db --session 1 --export-csv
```

**Expected Output:**
```
📤 Exporting session 1 to CSV files...
✅ Exported files: snapshot_export_memory_1.csv, snapshot_export_instructions_1.csv
```

## Step 8: Manual GDB Debugging (Advanced)

### 8.1 Connect GDB Manually
```bash
# Terminal 4: Manual GDB debugging
gdb-multiarch
```

**GDB Commands:**
```gdb
# Connect to QEMU
(gdb) target remote :1234

# Examine memory regions
(gdb) info registers
(gdb) x/32wx 0x40000000   # Guest base
(gdb) x/32wx 0x42000000   # Pattern region

# Set breakpoints for pattern painting
(gdb) break *0x400008e8   # vMemoryPatternDebugTask

# Continue execution
(gdb) continue

# When breakpoint hits, examine pattern painting
(gdb) x/32wx 0x42000000   # Before pattern painting
(gdb) stepi 100           # Step through painting
(gdb) x/32wx 0x42000000   # After pattern painting
```

### 8.2 Verify Pattern Painting
```gdb
# Check for expected patterns
(gdb) x/8wx 0x41000000    # Should show 0xDEADBEEF
(gdb) x/8wx 0x41200000    # Should show 0x12345678
(gdb) x/8wx 0x41400000    # Should show 0xCAFEBABE
(gdb) x/8wx 0x42000000    # Should show 0x55AA55AA
```

## Step 9: Advanced Analysis Queries

### 9.1 SQL Analysis Examples
```bash
# Open database for manual queries
sqlite3 freertos_debug_session.db
```

**Key Analysis Queries:**
```sql
-- Boot stage timing analysis
SELECT boot_stage, 
       COUNT(*) as instruction_count,
       MIN(timestamp) as start_time,
       MAX(timestamp) as end_time
FROM instruction_traces 
WHERE session_id = 1
GROUP BY boot_stage 
ORDER BY MIN(sequence_number);

-- Memory pattern evolution
SELECT ms.timestamp, ms.boot_stage, mr.region_name,
       mr.pattern_matches, mr.size,
       (mr.pattern_matches * 100.0 / (mr.size / 4)) as match_percentage
FROM memory_snapshots ms
JOIN memory_regions mr ON ms.snapshot_id = mr.snapshot_id
WHERE mr.expected_pattern IS NOT NULL
ORDER BY ms.timestamp, mr.region_name;

-- Function execution frequency
SELECT function_name, COUNT(*) as execution_count,
       COUNT(DISTINCT boot_stage) as active_stages
FROM instruction_traces
WHERE function_name != 'unknown'
GROUP BY function_name
ORDER BY execution_count DESC
LIMIT 10;

-- Pattern painting instruction correlation
SELECT it.timestamp, it.pc_address, it.disassembly,
       mr.region_name, mr.pattern_matches
FROM instruction_traces it
JOIN memory_snapshots ms ON it.timestamp = ms.timestamp
JOIN memory_regions mr ON ms.snapshot_id = mr.snapshot_id
WHERE it.function_name LIKE '%Memory%Pattern%'
ORDER BY it.sequence_number;
```

## Step 10: Troubleshooting Common Issues

### 10.1 Build Issues
**Problem:** ARM toolchain not found
```bash
# Install ARM toolchain
sudo apt-get update
sudo apt-get install gcc-arm-none-eabi binutils-arm-none-eabi
```

**Problem:** PYTHONPATH issues with CAmkES
```bash
# Ensure correct PYTHONPATH export
export PYTHONPATH=/home/konton-otome/phd/camkes-vm-examples/projects/camkes-tool:/home/konton-otome/phd/camkes-vm-examples/projects/capdl/python-capdl-tool

# Verify CAmkES tools are accessible
python3 -c "import camkes; print('✅ CAmkES tools accessible')"
```

### 10.2 QEMU Connection Issues
**Problem:** GDB server not accessible
```bash
# Check if QEMU is running with GDB server
netstat -an | grep 1234

# Check QEMU process
ps aux | grep qemu
```

**Problem:** Monitor interface not responding
```bash
# Test monitor connection
echo "info registers" | nc 127.0.0.1 55555
```

### 10.3 Database Recording Issues
**Problem:** No instruction traces recorded
```bash
# Verify GDB connection manually
echo "info registers" | nc localhost 1234

# Check database permissions
ls -la freertos_debug_session.db

# Enable debug logging
python3 memory_snapshot_db.py --record-boot --db-path freertos_debug_session.db --debug
```

### 10.4 Memory Pattern Validation
**Problem:** Low pattern match percentages
```bash
# Examine raw memory dumps
sqlite3 freertos_debug_session.db "SELECT hex(data) FROM memory_regions WHERE region_name LIKE '%pattern%' LIMIT 1;"

# Check pattern painting timing
sqlite3 freertos_debug_session.db "SELECT * FROM instruction_traces WHERE function_name LIKE '%pattern%' ORDER BY sequence_number;"
```

## Step 11: Expected Results Validation

### 11.1 Boot Stage Detection
Verify all expected boot stages are detected:
- ✅ elfloader (0x60000000-0x61000000)
- ✅ seL4_boot (0xe0000000-0xe1000000)
- ✅ rootserver_start (0x10000-0x20000)
- ✅ camkes_init (0x40000000-0x40001000)
- ✅ freertos_main (0x40000e70-0x40001000)
- ✅ pattern_painting (0x400008e8-0x40001000)
- ✅ scheduler_start (0x40003000-0x40004000)

### 11.2 Memory Pattern Validation
Expected pattern match rates:
- Stack region (0xDEADBEEF): >90% match
- Data region (0x12345678): >90% match
- Heap region (0xCAFEBABE): >90% match
- Pattern region (0x55AA55AA): >90% match

### 11.3 Database Completeness
Expected database contents:
- Instructions recorded: 100,000-500,000 (depending on max-instructions setting)
- Memory snapshots: 5-15 (depending on boot stages encountered)
- Memory regions per snapshot: 6-8 regions
- Function mappings: 10+ unique functions identified

## Step 12: Research Analysis Workflow

### 12.1 Pattern Evolution Analysis
```bash
# Analyze how patterns evolve during boot
python3 analyze_snapshots.py --db freertos_debug_session.db --session 1 --memory-evolution
```

### 12.2 Cross-Session Comparison
```bash
# Record multiple sessions for comparison
for i in {1..3}; do
    echo "Recording session $i..."
    ./run_qemu_full_debug.sh &
    QEMU_PID=$!
    sleep 5
    
    python3 memory_snapshot_db.py --record-boot --db-path multi_session.db --max-instructions 100000
    
    kill $QEMU_PID
    sleep 2
done

# Compare sessions
python3 analyze_snapshots.py --db multi_session.db --list-sessions
```

### 12.3 Performance Analysis
```bash
# Analyze database performance
sqlite3 freertos_debug_session.db "PRAGMA table_info(instruction_traces);"
sqlite3 freertos_debug_session.db "SELECT COUNT(*) FROM instruction_traces;"
sqlite3 freertos_debug_session.db "EXPLAIN QUERY PLAN SELECT * FROM instruction_traces WHERE boot_stage = 'pattern_painting';"
```

## Conclusion

This debugging methodology provides comprehensive visibility into FreeRTOS-seL4 integration behavior through:

1. **Complete Boot Sequence Recording**: Every instruction traced with context
2. **Memory Pattern Verification**: Systematic validation of pattern painting
3. **Database-Backed Analysis**: SQL-queryable data for research analysis
4. **Multi-Interface Debugging**: GDB, monitor, and database integration
5. **Reproducible Results**: Standardized methodology for consistent analysis

The recorded data enables deep analysis of virtualization behavior, memory management patterns, and boot sequence dependencies that are crucial for embedded systems research and formal verification studies.