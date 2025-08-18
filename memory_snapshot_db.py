#!/usr/bin/env python3
"""
Database-Backed Memory Snapshot System for FreeRTOS-seL4 Debug Analysis

This system integrates with QEMU GDB server to capture:
- Memory snapshots at multiple boot stages
- ARM instruction execution traces
- Register states and stack traces
- All data stored in SQLite database for analysis

Usage:
    python3 memory_snapshot_db.py --init-db
    python3 memory_snapshot_db.py --record-boot --gdb-port 1234
    python3 memory_snapshot_db.py --analyze --db snapshots.db
"""

import sqlite3
import argparse
import time
import json
import struct
import sys
import os
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
import socket
import threading
import queue

class GDBInterface:
    """Interface to QEMU GDB server for instruction and memory capture"""
    
    def __init__(self, host='127.0.0.1', port=1234):
        self.host = host
        self.port = port
        self.sock = None
        self.connected = False
        
    def connect(self) -> bool:
        """Connect to QEMU GDB server"""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))
            self.connected = True
            
            # Send initial GDB handshake
            self._send_command("qSupported")
            response = self._receive_response()
            print(f"GDB connected: {response[:100]}...")
            return True
            
        except Exception as e:
            print(f"Failed to connect to GDB server: {e}")
            return False
    
    def _send_command(self, command: str) -> None:
        """Send GDB command with proper packet format"""
        if not self.connected:
            raise RuntimeError("Not connected to GDB")
        
        # GDB remote protocol: $<command>#<checksum>
        checksum = sum(ord(c) for c in command) % 256
        packet = f"${command}#{checksum:02x}"
        self.sock.send(packet.encode('ascii'))
    
    def _receive_response(self) -> str:
        """Receive GDB response"""
        response = ""
        while True:
            data = self.sock.recv(1024).decode('ascii', errors='ignore')
            response += data
            if '#' in response or '+' in response or '-' in response:
                break
        return response
    
    def read_memory(self, address: int, size: int) -> bytes:
        """Read memory from target"""
        try:
            command = f"m{address:x},{size:x}"
            self._send_command(command)
            response = self._receive_response()
            
            # Parse hex response
            if response.startswith('$') and '#' in response:
                hex_data = response[1:response.index('#')]
                return bytes.fromhex(hex_data)
            return b''
            
        except Exception as e:
            print(f"Memory read error: {e}")
            return b''
    
    def read_registers(self) -> Dict[str, int]:
        """Read all CPU registers"""
        try:
            self._send_command("g")
            response = self._receive_response()
            
            if response.startswith('$') and '#' in response:
                hex_data = response[1:response.index('#')]
                # Parse ARM register format (assuming 32-bit ARM)
                registers = {}
                for i in range(16):  # R0-R15
                    if len(hex_data) >= (i + 1) * 8:
                        reg_hex = hex_data[i*8:(i+1)*8]
                        # Convert little-endian hex to int
                        reg_val = struct.unpack('<I', bytes.fromhex(reg_hex))[0]
                        registers[f'r{i}'] = reg_val
                
                return registers
            
        except Exception as e:
            print(f"Register read error: {e}")
        
        return {}
    
    def single_step(self) -> bool:
        """Execute single instruction step"""
        try:
            self._send_command("s")
            response = self._receive_response()
            return 'S05' in response  # SIGTRAP
        except Exception as e:
            print(f"Single step error: {e}")
            return False
    
    def set_breakpoint(self, address: int) -> bool:
        """Set breakpoint at address"""
        try:
            command = f"Z0,{address:x},4"  # Software breakpoint
            self._send_command(command)
            response = self._receive_response()
            return 'OK' in response
        except Exception as e:
            print(f"Breakpoint error: {e}")
            return False
    
    def continue_execution(self) -> str:
        """Continue execution until breakpoint"""
        try:
            self._send_command("c")
            response = self._receive_response()
            return response
        except Exception as e:
            print(f"Continue error: {e}")
            return ""
    
    def get_current_pc(self) -> int:
        """Get current program counter"""
        registers = self.read_registers()
        return registers.get('r15', 0)  # PC is R15 in ARM
    
    def close(self):
        """Close GDB connection"""
        if self.sock:
            self.sock.close()
            self.connected = False

class MemorySnapshotDB:
    """Database for storing memory snapshots and execution traces"""
    
    def __init__(self, db_path: str = "memory_snapshots.db"):
        self.db_path = db_path
        self.conn = None
    
    def init_database(self) -> bool:
        """Initialize database schema"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            cursor = self.conn.cursor()
            
            # Boot sessions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS boot_sessions (
                    session_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    description TEXT,
                    qemu_version TEXT,
                    freertos_version TEXT
                )
            ''')
            
            # Memory snapshots table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS memory_snapshots (
                    snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER REFERENCES boot_sessions(session_id),
                    timestamp TEXT NOT NULL,
                    boot_stage TEXT NOT NULL,
                    pc_address INTEGER NOT NULL,
                    memory_regions TEXT NOT NULL,  -- JSON of region data
                    total_size INTEGER NOT NULL
                )
            ''')
            
            # Memory regions table (detailed storage)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS memory_regions (
                    region_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    snapshot_id INTEGER REFERENCES memory_snapshots(snapshot_id),
                    region_name TEXT NOT NULL,
                    start_address INTEGER NOT NULL,
                    end_address INTEGER NOT NULL,
                    size INTEGER NOT NULL,
                    data BLOB NOT NULL,
                    expected_pattern INTEGER,
                    pattern_matches INTEGER,
                    checksum TEXT
                )
            ''')
            
            # Instruction traces table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS instruction_traces (
                    trace_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER REFERENCES boot_sessions(session_id),
                    sequence_number INTEGER NOT NULL,
                    timestamp TEXT NOT NULL,
                    pc_address INTEGER NOT NULL,
                    instruction_bytes BLOB,
                    disassembly TEXT,
                    registers TEXT,  -- JSON of register state
                    stack_pointer INTEGER,
                    function_name TEXT,
                    boot_stage TEXT
                )
            ''')
            
            # Boot stages table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS boot_stages (
                    stage_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER REFERENCES boot_sessions(session_id),
                    stage_name TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    start_pc INTEGER,
                    end_pc INTEGER,
                    instruction_count INTEGER DEFAULT 0,
                    memory_snapshot_id INTEGER REFERENCES memory_snapshots(snapshot_id)
                )
            ''')
            
            # Performance metrics table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    metric_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER REFERENCES boot_sessions(session_id),
                    timestamp TEXT NOT NULL,
                    metric_name TEXT NOT NULL,
                    metric_value REAL NOT NULL,
                    unit TEXT
                )
            ''')
            
            # Create indexes for performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_snapshots_session ON memory_snapshots(session_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_traces_session ON instruction_traces(session_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_traces_pc ON instruction_traces(pc_address)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_regions_snapshot ON memory_regions(snapshot_id)')
            
            self.conn.commit()
            print(f"✅ Database initialized: {self.db_path}")
            return True
            
        except Exception as e:
            print(f"Database initialization error: {e}")
            return False
    
    def start_boot_session(self, description: str = "") -> int:
        """Start new boot recording session"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO boot_sessions (start_time, description, qemu_version, freertos_version)
            VALUES (?, ?, ?, ?)
        ''', (
            datetime.now().isoformat(),
            description,
            "QEMU ARM virt",
            "FreeRTOS Debug with Memory Patterns"
        ))
        self.conn.commit()
        session_id = cursor.lastrowid
        print(f"📝 Started boot session {session_id}")
        return session_id
    
    def save_memory_snapshot(self, session_id: int, boot_stage: str, pc: int, memory_data: Dict[str, bytes]) -> int:
        """Save complete memory snapshot"""
        cursor = self.conn.cursor()
        
        # Calculate total size
        total_size = sum(len(data) for data in memory_data.values())
        
        # Save snapshot metadata
        cursor.execute('''
            INSERT INTO memory_snapshots (session_id, timestamp, boot_stage, pc_address, memory_regions, total_size)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            session_id,
            datetime.now().isoformat(),
            boot_stage,
            pc,
            json.dumps(list(memory_data.keys())),
            total_size
        ))
        
        snapshot_id = cursor.lastrowid
        
        # Save individual memory regions
        for region_name, data in memory_data.items():
            # Parse region name to get address (assuming format like "stack_0x41000000")
            if '_0x' in region_name:
                addr_str = region_name.split('_0x')[1]
                start_address = int(addr_str, 16)
            else:
                start_address = 0
            
            end_address = start_address + len(data)
            
            # Calculate pattern analysis if applicable
            expected_pattern = None
            pattern_matches = 0
            
            if 'stack' in region_name.lower():
                expected_pattern = 0xDEADBEEF
            elif 'data' in region_name.lower():
                expected_pattern = 0x12345678
            elif 'heap' in region_name.lower():
                expected_pattern = 0xCAFEBABE
            elif 'pattern' in region_name.lower():
                expected_pattern = 0x55AA55AA
            
            if expected_pattern:
                pattern_bytes = struct.pack('<I', expected_pattern)
                pattern_matches = data.count(pattern_bytes)
            
            # Calculate checksum
            import hashlib
            checksum = hashlib.md5(data).hexdigest()
            
            cursor.execute('''
                INSERT INTO memory_regions (snapshot_id, region_name, start_address, end_address, 
                                          size, data, expected_pattern, pattern_matches, checksum)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                snapshot_id,
                region_name,
                start_address,
                end_address,
                len(data),
                data,
                expected_pattern,
                pattern_matches,
                checksum
            ))
        
        self.conn.commit()
        print(f"💾 Saved memory snapshot {snapshot_id} for stage '{boot_stage}' (PC: 0x{pc:08x})")
        return snapshot_id
    
    def save_instruction_trace(self, session_id: int, sequence: int, pc: int, 
                              instruction_bytes: bytes, disassembly: str, 
                              registers: Dict[str, int], boot_stage: str) -> None:
        """Save single instruction trace entry"""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            INSERT INTO instruction_traces (session_id, sequence_number, timestamp, pc_address,
                                          instruction_bytes, disassembly, registers, stack_pointer,
                                          function_name, boot_stage)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            session_id,
            sequence,
            datetime.now().isoformat(),
            pc,
            instruction_bytes,
            disassembly,
            json.dumps(registers),
            registers.get('r13', 0),  # SP is R13
            self._get_function_name(pc),
            boot_stage
        ))
        
        if sequence % 1000 == 0:  # Commit every 1000 instructions
            self.conn.commit()
    
    def _get_function_name(self, pc: int) -> str:
        """Get function name for PC address"""
        # Known function addresses from FreeRTOS build
        functions = {
            0x40000000: "_start",
            0x40000e70: "main",
            0x400008e8: "vMemoryPatternDebugTask",
            0x40001014: "vMonitorTask",
        }
        
        for addr, name in functions.items():
            if pc >= addr and pc < addr + 0x1000:  # Assume 4KB max function size
                return name
        
        return f"unknown_0x{pc:08x}"
    
    def end_boot_session(self, session_id: int) -> None:
        """End boot recording session"""
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE boot_sessions SET end_time = ? WHERE session_id = ?
        ''', (datetime.now().isoformat(), session_id))
        self.conn.commit()
        print(f"✅ Ended boot session {session_id}")
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()

class BootRecorder:
    """Records complete boot sequence with memory snapshots and instruction traces"""
    
    def __init__(self, gdb_port: int = 1234, db_path: str = "memory_snapshots.db"):
        self.gdb = GDBInterface(port=gdb_port)
        self.db = MemorySnapshotDB(db_path)
        self.session_id = None
        self.instruction_count = 0
        
        # Define boot stages and their trigger conditions
        self.boot_stages = [
            {"name": "elfloader", "pc_range": (0x60000000, 0x61000000), "snapshot": True},
            {"name": "seL4_boot", "pc_range": (0xe0000000, 0xe1000000), "snapshot": True},
            {"name": "rootserver_start", "pc_range": (0x10000, 0x20000), "snapshot": True},
            {"name": "camkes_init", "pc_range": (0x40000000, 0x40001000), "snapshot": True},
            {"name": "freertos_main", "pc_range": (0x40000e70, 0x40001000), "snapshot": True},
            {"name": "pattern_painting", "pc_range": (0x400008e8, 0x40001000), "snapshot": True},
            {"name": "scheduler_start", "pc_range": (0x40003000, 0x40004000), "snapshot": True},
        ]
        
        self.current_stage = "unknown"
        self.stage_snapshots = {}
        
        # Memory regions to capture
        self.memory_regions = {
            'guest_base': (0x40000000, 0x1000),      # 4KB
            'stack_region': (0x41000000, 0x1000),    # 4KB  
            'data_region': (0x41200000, 0x1000),     # 4KB
            'heap_region': (0x41400000, 0x1000),     # 4KB
            'pattern_region': (0x42000000, 0x4000),  # 16KB
            'uart_region': (0x9000000, 0x100),       # 256B
        }
    
    def start_recording(self) -> bool:
        """Start boot recording session"""
        print("🚀 Starting boot recording with memory snapshots and instruction traces")
        
        # Initialize database
        if not self.db.init_database():
            return False
        
        # Connect to GDB
        if not self.gdb.connect():
            print("❌ Failed to connect to GDB server")
            print("Make sure QEMU is running with: -gdb tcp::1234")
            return False
        
        # Start session
        self.session_id = self.db.start_boot_session("Complete boot recording with memory snapshots")
        
        print("✅ Recording started - capturing instruction traces and memory snapshots")
        return True
    
    def record_boot_sequence(self, max_instructions: int = 100000) -> bool:
        """Record complete boot sequence"""
        try:
            for i in range(max_instructions):
                # Get current state
                pc = self.gdb.get_current_pc()
                registers = self.gdb.read_registers()
                
                # Read instruction bytes
                instr_bytes = self.gdb.read_memory(pc, 4)
                
                # Simple ARM disassembly (basic)
                disassembly = self._disassemble_arm(instr_bytes, pc)
                
                # Determine boot stage
                new_stage = self._determine_boot_stage(pc)
                if new_stage != self.current_stage:
                    print(f"🔄 Boot stage: {self.current_stage} → {new_stage} (PC: 0x{pc:08x})")
                    
                    # Take memory snapshot at stage transitions
                    if new_stage != "unknown":
                        memory_data = self._capture_memory_regions()
                        snapshot_id = self.db.save_memory_snapshot(
                            self.session_id, new_stage, pc, memory_data
                        )
                        self.stage_snapshots[new_stage] = snapshot_id
                    
                    self.current_stage = new_stage
                
                # Save instruction trace
                self.db.save_instruction_trace(
                    self.session_id, i, pc, instr_bytes, disassembly, registers, self.current_stage
                )
                
                # Single step
                if not self.gdb.single_step():
                    print("❌ Single step failed")
                    break
                
                # Progress indicator
                if i % 1000 == 0:
                    print(f"📊 Recorded {i} instructions, current PC: 0x{pc:08x}, stage: {self.current_stage}")
                
                # Special handling for pattern painting stage
                if self.current_stage == "pattern_painting" and i % 5000 == 0:
                    memory_data = self._capture_memory_regions()
                    self.db.save_memory_snapshot(
                        self.session_id, f"pattern_painting_step_{i//5000}", pc, memory_data
                    )
            
            print(f"✅ Recorded {max_instructions} instructions")
            return True
            
        except KeyboardInterrupt:
            print(f"\n⏹️  Recording stopped by user after {i} instructions")
            return True
        except Exception as e:
            print(f"❌ Recording error: {e}")
            return False
    
    def _determine_boot_stage(self, pc: int) -> str:
        """Determine current boot stage based on PC"""
        for stage in self.boot_stages:
            start, end = stage["pc_range"]
            if start <= pc < end:
                return stage["name"]
        return "unknown"
    
    def _capture_memory_regions(self) -> Dict[str, bytes]:
        """Capture all defined memory regions"""
        memory_data = {}
        
        for region_name, (start_addr, size) in self.memory_regions.items():
            try:
                data = self.gdb.read_memory(start_addr, size)
                if data:
                    memory_data[f"{region_name}_0x{start_addr:08x}"] = data
            except Exception as e:
                print(f"⚠️  Failed to read {region_name}: {e}")
        
        return memory_data
    
    def _disassemble_arm(self, instr_bytes: bytes, pc: int) -> str:
        """Basic ARM instruction disassembly"""
        if len(instr_bytes) < 4:
            return "invalid"
        
        instr = struct.unpack('<I', instr_bytes)[0]
        
        # Very basic ARM decoding
        if (instr & 0x0F000000) == 0x0A000000:
            return f"b 0x{pc + ((instr & 0x00FFFFFF) << 2):08x}"
        elif (instr & 0x0F000000) == 0x0B000000:
            return f"bl 0x{pc + ((instr & 0x00FFFFFF) << 2):08x}"
        elif (instr & 0x0FE00000) == 0x01A00000:
            return "mov r?, r?"
        elif (instr & 0x0C000000) == 0x04000000:
            return "ldr/str"
        else:
            return f"instr_0x{instr:08x}"
    
    def finish_recording(self) -> None:
        """Finish recording session"""
        if self.session_id:
            self.db.end_boot_session(self.session_id)
        
        self.gdb.close()
        self.db.close()
        
        print(f"🎉 Recording complete - {self.instruction_count} instructions captured")
        print(f"📊 Memory snapshots: {len(self.stage_snapshots)}")
        print(f"💾 Database: {self.db.db_path}")

def main():
    parser = argparse.ArgumentParser(description='Memory Snapshot Database System')
    parser.add_argument('--init-db', action='store_true', help='Initialize database')
    parser.add_argument('--record-boot', action='store_true', help='Record boot sequence')
    parser.add_argument('--gdb-port', type=int, default=1234, help='GDB server port')
    parser.add_argument('--db-path', default='memory_snapshots.db', help='Database file path')
    parser.add_argument('--max-instructions', type=int, default=100000, help='Max instructions to record')
    parser.add_argument('--analyze', action='store_true', help='Analyze recorded data')
    
    args = parser.parse_args()
    
    if args.init_db:
        db = MemorySnapshotDB(args.db_path)
        if db.init_database():
            print(f"✅ Database initialized: {args.db_path}")
        db.close()
    
    elif args.record_boot:
        recorder = BootRecorder(args.gdb_port, args.db_path)
        
        if recorder.start_recording():
            try:
                recorder.record_boot_sequence(args.max_instructions)
            finally:
                recorder.finish_recording()
    
    elif args.analyze:
        # TODO: Implement analysis functionality
        print("📊 Analysis functionality coming soon!")
        print(f"Database: {args.db_path}")
    
    else:
        parser.print_help()

if __name__ == "__main__":
    main()