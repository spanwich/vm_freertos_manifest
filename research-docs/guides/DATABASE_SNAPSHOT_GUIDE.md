# Database-Backed Memory Snapshot System Guide

## Overview

The enhanced memory debugging system now includes a comprehensive database-backed approach that captures:

- **Complete boot sequences** with instruction-level traces
- **Memory snapshots** at multiple boot stages  
- **ARM instruction execution** with disassembly
- **Register states** and stack traces
- **Pattern evolution** during memory painting
- **Performance metrics** and timing analysis

All data is stored in a SQLite database for powerful analysis and correlation.

## 🎯 Quick Start

### 1. Initialize Database
```bash
python3 memory_snapshot_db.py --init-db --db-path boot_snapshots.db
```

### 2. Start QEMU with GDB and Monitor
```bash
# Terminal 1: Start QEMU with full debug support
./run_qemu_full_debug.sh

# This provides:
# - GDB server on port 1234
# - Monitor interface on port 55555
# - Optional instruction tracing
```

### 3. Record Complete Boot Sequence
```bash
# Terminal 2: Record boot with memory snapshots
python3 memory_snapshot_db.py --record-boot --gdb-port 1234 --db-path boot_snapshots.db
```

### 4. Analyze Recorded Data
```bash
# Generate comprehensive HTML report
python3 analyze_snapshots.py --db boot_snapshots.db --session 1 --report boot_analysis.html

# Export to CSV for spreadsheet analysis
python3 analyze_snapshots.py --db boot_snapshots.db --session 1 --export-csv
```

## 🗄️ Database Schema

### Core Tables

#### boot_sessions
- Records each boot recording session
- Links to all snapshots and traces
- Stores metadata and timing

#### memory_snapshots
- Captures memory state at specific points
- Links to detailed region data
- Includes boot stage and PC context

#### memory_regions
- Detailed storage of memory contents
- Pattern analysis and checksums
- Binary data for exact reconstruction

#### instruction_traces
- Every executed instruction
- ARM disassembly and registers
- Function mapping and boot stages

#### boot_stages
- Tracks progression through boot phases
- Performance metrics per stage
- Memory snapshot associations

## 🔧 Advanced Usage

### Recording with Custom Breakpoints
```python
# Example: Record with specific breakpoints
recorder = BootRecorder(gdb_port=1234)
recorder.start_recording()

# Set breakpoints at key functions
recorder.gdb.set_breakpoint(0x40000e70)  # main()
recorder.gdb.set_breakpoint(0x400008e8)  # vMemoryPatternDebugTask()

recorder.record_boot_sequence(max_instructions=50000)
```

### Multi-Stage Analysis
```python
# Analyze memory evolution across boot stages
analyzer = SnapshotAnalyzer("boot_snapshots.db")
evolution = analyzer.analyze_memory_evolution(session_id=1)

for region_name, snapshots in evolution.items():
    print(f"Region {region_name}:")
    for snapshot in snapshots:
        print(f"  {snapshot['boot_stage']}: {snapshot['match_percentage']:.1f}% pattern match")
```

### Memory Region Comparison
```bash
# Compare specific memory region across boot stages
python3 analyze_snapshots.py --db boot_snapshots.db --session 1 --compare-region "stack_region_0x41000000"
```

## 📊 Data Analysis Capabilities

### 1. Boot Sequence Analysis
- **Stage Timing**: How long each boot phase takes
- **Instruction Counts**: Instructions executed per stage
- **Function Coverage**: Which functions are active when
- **Memory Changes**: How memory evolves during boot

### 2. Memory Pattern Verification
- **Pattern Painting Success**: Percentage of correct patterns
- **Pattern Evolution**: How patterns change over time
- **Memory Corruption Detection**: Unexpected pattern changes
- **Checksum Validation**: Binary-level change detection

### 3. Instruction Execution Analysis
- **Function Call Frequency**: Most executed functions
- **Execution Flow**: Branch and jump patterns
- **Register Usage**: How registers change
- **Performance Hotspots**: Most time-consuming code

### 4. ARM Instruction Tracing
- **Complete Disassembly**: Every instruction with context
- **Register State**: Full ARM register set per instruction
- **Memory Access Patterns**: Load/store operation tracking
- **Branch Analysis**: Control flow visualization

## 🎯 Expected Results

### Boot Stages Detected
1. **elfloader** (0x60000000-0x61000000)
2. **seL4_boot** (0xe0000000-0xe1000000)  
3. **rootserver_start** (0x10000-0x20000)
4. **camkes_init** (0x40000000-0x40001000)
5. **freertos_main** (0x40000e70-0x40001000)
6. **pattern_painting** (0x400008e8-0x40001000)
7. **scheduler_start** (0x40003000-0x40004000)

### Memory Snapshots Captured
- **Guest Base** (0x40000000): Boot code and data
- **Stack Region** (0x41000000): 0xDEADBEEF patterns
- **Data Region** (0x41200000): 0x12345678 patterns
- **Heap Region** (0x41400000): 0xCAFEBABE patterns  
- **Pattern Region** (0x42000000): 0x55AA55AA + dynamic
- **UART Region** (0x9000000): Device registers

### Instruction Traces Include
- **PC Address**: Program counter for each instruction
- **ARM Disassembly**: Human-readable instruction
- **Register State**: All ARM registers (R0-R15, CPSR)
- **Function Context**: Which function is executing
- **Boot Stage**: What phase of boot this is

## 🔍 Analysis Examples

### Find Memory Pattern Painting Activity
```sql
SELECT it.timestamp, it.pc_address, it.disassembly, it.function_name
FROM instruction_traces it
WHERE it.function_name LIKE '%Memory%Pattern%'
ORDER BY it.sequence_number;
```

### Memory Evolution Timeline
```sql
SELECT ms.timestamp, ms.boot_stage, mr.region_name, 
       mr.pattern_matches, mr.size, 
       (mr.pattern_matches * 100.0 / (mr.size / 4)) as match_percentage
FROM memory_snapshots ms
JOIN memory_regions mr ON ms.snapshot_id = mr.snapshot_id
WHERE mr.expected_pattern IS NOT NULL
ORDER BY ms.timestamp, mr.region_name;
```

### Function Execution Frequency
```sql
SELECT function_name, COUNT(*) as execution_count,
       COUNT(DISTINCT boot_stage) as active_stages
FROM instruction_traces
WHERE function_name != 'unknown'
GROUP BY function_name
ORDER BY execution_count DESC;
```

## 🚀 Advanced Workflows

### 1. Complete Boot Analysis
```bash
#!/bin/bash
# Complete analysis workflow

# Start QEMU with debug
./run_qemu_full_debug.sh &
QEMU_PID=$!

# Wait for QEMU to start
sleep 5

# Record boot sequence
python3 memory_snapshot_db.py --init-db --db-path complete_boot.db
python3 memory_snapshot_db.py --record-boot --db-path complete_boot.db --max-instructions 200000

# Generate analysis reports
python3 analyze_snapshots.py --db complete_boot.db --session 1 --report complete_analysis.html
python3 analyze_snapshots.py --db complete_boot.db --session 1 --export-csv
python3 analyze_snapshots.py --db complete_boot.db --session 1 --memory-evolution

# Stop QEMU
kill $QEMU_PID
```

### 2. Compare Multiple Boot Runs
```bash
# Record multiple sessions
for i in {1..3}; do
    ./run_qemu_full_debug.sh &
    QEMU_PID=$!
    sleep 5
    
    python3 memory_snapshot_db.py --record-boot --db-path multi_boot.db --max-instructions 100000
    
    kill $QEMU_PID
    sleep 2
done

# Analyze all sessions
python3 analyze_snapshots.py --db multi_boot.db --list-sessions
```

### 3. Memory Pattern Validation
```python
# Validate that memory patterns are working correctly
analyzer = SnapshotAnalyzer("boot_snapshots.db")
evolution = analyzer.analyze_memory_evolution(session_id=1)

success_threshold = 90.0
failed_regions = []

for region_name, snapshots in evolution.items():
    if snapshots:
        latest = snapshots[-1]
        if latest['expected_pattern'] and latest['match_percentage'] < success_threshold:
            failed_regions.append({
                'region': region_name,
                'percentage': latest['match_percentage'],
                'expected': latest['expected_pattern']
            })

if failed_regions:
    print("❌ Memory pattern validation failed:")
    for region in failed_regions:
        print(f"  {region['region']}: {region['percentage']:.1f}% (expected: 0x{region['expected']:08x})")
else:
    print("✅ All memory patterns validated successfully!")
```

## 📈 Performance and Scalability

### Database Size Estimates
- **100,000 instructions**: ~50MB database
- **Memory snapshots**: ~1MB per complete snapshot
- **Boot session**: ~100MB for full recording
- **Multiple sessions**: Linear growth

### Optimization Tips
```bash
# For large recordings, use periodic commits
python3 memory_snapshot_db.py --record-boot --max-instructions 1000000

# Analyze specific regions only
python3 analyze_snapshots.py --db large.db --session 1 --compare-region "pattern_region_0x42000000"

# Export specific data for external analysis
sqlite3 boot_snapshots.db "SELECT * FROM memory_regions WHERE expected_pattern IS NOT NULL" | csv
```

## 🔧 Integration with Existing Tools

### Combine with Hex Dump Capture
```bash
# Terminal 1: QEMU with full debug
./run_qemu_full_debug.sh

# Terminal 2: Database recording
python3 memory_snapshot_db.py --record-boot --db-path combined.db &

# Terminal 3: Parallel hex dump capture
python3 capture_hex_dumps.py --continuous --interval 30
```

### GDB Integration
```bash
# Connect to QEMU GDB server manually
gdb-multiarch
(gdb) target remote :1234
(gdb) info registers
(gdb) x/32wx 0x42000000
(gdb) disassemble main
```

This database-backed system provides unprecedented visibility into the FreeRTOS-seL4 boot process, enabling deep analysis of memory patterns, instruction execution, and system behavior for comprehensive debugging and research.