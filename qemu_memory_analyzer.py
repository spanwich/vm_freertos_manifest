#!/usr/bin/env python3
"""
QEMU Memory Pattern Analyzer for FreeRTOS-seL4 Integration Debugging

This script automates memory dumping and pattern analysis for the 
memory pattern debugging methodology described in the research document.

Usage:
    python3 qemu_memory_analyzer.py --monitor-port 55555 --output memory_dump.txt

Features:
- Connects to QEMU monitor interface
- Dumps memory regions with expected patterns
- Compares actual vs expected memory patterns
- Generates analysis reports for debugging
- Supports instruction tracing integration
"""

import argparse
import socket
import time
import struct
import sys
import os
from datetime import datetime
from typing import Dict, List, Tuple, Optional

class QEMUMonitor:
    """Interface for QEMU monitor commands"""
    
    def __init__(self, host='127.0.0.1', port=55555):
        self.host = host
        self.port = port
        self.sock = None
        self.connected = False
        
    def connect(self) -> bool:
        """Connect to QEMU monitor"""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))
            self.connected = True
            
            # Read initial prompt
            response = self.sock.recv(1024).decode('utf-8', errors='ignore')
            print(f"QEMU Monitor connected: {response.strip()}")
            return True
            
        except Exception as e:
            print(f"Failed to connect to QEMU monitor: {e}")
            return False
    
    def send_command(self, command: str) -> str:
        """Send command to QEMU monitor and return response"""
        if not self.connected:
            return "Error: Not connected to QEMU monitor"
            
        try:
            # Send command
            self.sock.send(f"{command}\n".encode('utf-8'))
            
            # Read response
            response = ""
            while True:
                data = self.sock.recv(4096).decode('utf-8', errors='ignore')
                response += data
                if "(qemu)" in data:
                    break
                time.sleep(0.1)
                
            return response
            
        except Exception as e:
            return f"Error sending command: {e}"
    
    def dump_memory(self, address: int, size: int, format: str = "wx") -> List[int]:
        """Dump memory from specified address and return as list of integers"""
        command = f"x/{size}{format} 0x{address:08x}"
        response = self.send_command(command)
        
        # Parse response to extract memory values
        values = []
        lines = response.split('\n')
        
        for line in lines:
            if ':' in line and not line.startswith('(qemu)'):
                parts = line.split(':')
                if len(parts) > 1:
                    hex_values = parts[1].strip().split()
                    for hex_val in hex_values:
                        if hex_val.startswith('0x'):
                            try:
                                values.append(int(hex_val, 16))
                            except ValueError:
                                pass
        
        return values
    
    def dump_memory_raw(self, address: int, size: int, format: str = "wx") -> str:
        """Dump memory and return raw QEMU output"""
        command = f"x/{size}{format} 0x{address:08x}"
        response = self.send_command(command)
        return response
    
    def save_hex_dump_to_file(self, address: int, size: int, filename: str, 
                             format: str = "wx", description: str = "") -> bool:
        """Save hex dump to file with timestamp and metadata"""
        try:
            raw_output = self.dump_memory_raw(address, size, format)
            
            with open(filename, 'w') as f:
                f.write(f"# QEMU Memory Hex Dump\n")
                f.write(f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"# Address: 0x{address:08x}\n")
                f.write(f"# Size: {size} words ({size * 4} bytes)\n")
                f.write(f"# Format: {format}\n")
                if description:
                    f.write(f"# Description: {description}\n")
                f.write(f"# Command: x/{size}{format} 0x{address:08x}\n")
                f.write("#" + "="*60 + "\n\n")
                f.write(raw_output)
                f.write("\n\n# End of dump\n")
            
            return True
        except Exception as e:
            print(f"Failed to save hex dump: {e}")
            return False
    
    def get_registers(self) -> Dict[str, int]:
        """Get CPU register values"""
        response = self.send_command("info registers")
        registers = {}
        
        lines = response.split('\n')
        for line in lines:
            if '=' in line and not line.startswith('(qemu)'):
                parts = line.split('=')
                if len(parts) >= 2:
                    reg_name = parts[0].strip()
                    reg_value_str = parts[1].strip().split()[0]
                    try:
                        if reg_value_str.startswith('0x'):
                            registers[reg_name] = int(reg_value_str, 16)
                        else:
                            registers[reg_name] = int(reg_value_str)
                    except ValueError:
                        pass
        
        return registers
    
    def close(self):
        """Close monitor connection"""
        if self.sock:
            self.sock.close()
            self.connected = False

class MemoryPatternAnalyzer:
    """Analyzes memory patterns for debugging"""
    
    # Expected patterns from FreeRTOS implementation
    PATTERNS = {
        'STACK': 0xDEADBEEF,
        'DATA': 0x12345678,
        'HEAP': 0xCAFEBABE,
        'TEST': 0x55AA55AA,
        'CYCLES': 0xAAAAAAAA
    }
    
    # Memory regions from FreeRTOS debug implementation
    REGIONS = {
        'GUEST_BASE': 0x40000000,
        'STACK_REGION': 0x41000000,
        'DATA_REGION': 0x41200000,
        'HEAP_REGION': 0x41400000,
        'PATTERN_REGION': 0x42000000
    }
    
    def __init__(self, monitor: QEMUMonitor):
        self.monitor = monitor
        self.analysis_results = []
        
    def analyze_region(self, region_name: str, address: int, size_words: int, expected_pattern: int, save_hex: bool = True) -> Dict:
        """Analyze a specific memory region for pattern matching"""
        print(f"\nAnalyzing {region_name} region at 0x{address:08x}...")
        
        # Save hex dump to file if requested
        if save_hex:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            hex_filename = f"hex_dump_{region_name.lower()}_{timestamp}.txt"
            description = f"{region_name} region - Expected pattern: 0x{expected_pattern:08x}"
            
            if self.monitor.save_hex_dump_to_file(address, size_words, hex_filename, "wx", description):
                print(f"💾 Hex dump saved to: {hex_filename}")
            else:
                print(f"⚠️  Failed to save hex dump for {region_name}")
        
        # Dump memory
        memory_values = self.monitor.dump_memory(address, size_words, "wx")
        
        if not memory_values:
            return {
                'region': region_name,
                'address': address,
                'error': 'Failed to read memory',
                'matches': 0,
                'total': 0,
                'match_percentage': 0.0,
                'hex_file': hex_filename if save_hex else None
            }
        
        # Count pattern matches
        matches = sum(1 for val in memory_values if val == expected_pattern)
        total = len(memory_values)
        match_percentage = (matches / total * 100) if total > 0 else 0
        
        # Find mismatches
        mismatches = []
        for i, val in enumerate(memory_values[:10]):  # Show first 10 mismatches
            if val != expected_pattern:
                mismatches.append({
                    'offset': i,
                    'address': address + (i * 4),
                    'expected': expected_pattern,
                    'actual': val
                })
        
        result = {
            'region': region_name,
            'address': address,
            'expected_pattern': expected_pattern,
            'matches': matches,
            'total': total,
            'match_percentage': match_percentage,
            'mismatches': mismatches[:5],  # Limit to first 5 for report
            'success': match_percentage > 90.0,  # Consider 90%+ a success
            'hex_file': hex_filename if save_hex else None
        }
        
        return result
    
    def comprehensive_analysis(self) -> List[Dict]:
        """Perform comprehensive memory pattern analysis"""
        print("Starting comprehensive memory pattern analysis...")
        
        # Define regions to analyze
        analysis_regions = [
            ('STACK', self.REGIONS['STACK_REGION'], 256, self.PATTERNS['STACK']),
            ('DATA', self.REGIONS['DATA_REGION'], 256, self.PATTERNS['DATA']),
            ('HEAP', self.REGIONS['HEAP_REGION'], 256, self.PATTERNS['HEAP']),
            ('PATTERN', self.REGIONS['PATTERN_REGION'], 1024, self.PATTERNS['TEST'])
        ]
        
        results = []
        for region_name, address, size, pattern in analysis_regions:
            result = self.analyze_region(region_name, address, size, pattern)
            results.append(result)
            
            # Print immediate feedback
            status = "✅ PASS" if result.get('success', False) else "❌ FAIL"
            print(f"{status} {region_name}: {result.get('match_percentage', 0):.1f}% pattern match")
        
        self.analysis_results = results
        return results
    
    def save_all_region_hex_dumps(self, cycle_number: int = None) -> Dict[str, str]:
        """Save hex dumps for all memory regions"""
        print(f"\n💾 Saving hex dumps for all regions...")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        cycle_suffix = f"_cycle{cycle_number:03d}" if cycle_number is not None else ""
        
        dump_files = {}
        
        # Define regions to dump
        regions_to_dump = [
            ('GUEST_BASE', self.REGIONS['GUEST_BASE'], 256, "Guest VM base region"),
            ('STACK', self.REGIONS['STACK_REGION'], 256, f"Stack region - Expected: 0x{self.PATTERNS['STACK']:08x}"),
            ('DATA', self.REGIONS['DATA_REGION'], 256, f"Data region - Expected: 0x{self.PATTERNS['DATA']:08x}"),
            ('HEAP', self.REGIONS['HEAP_REGION'], 256, f"Heap region - Expected: 0x{self.PATTERNS['HEAP']:08x}"),
            ('PATTERN', self.REGIONS['PATTERN_REGION'], 1024, f"Pattern region - Expected: 0x{self.PATTERNS['TEST']:08x}"),
        ]
        
        for region_name, address, size, description in regions_to_dump:
            filename = f"hex_dump_{region_name.lower()}_{timestamp}{cycle_suffix}.txt"
            
            if self.monitor.save_hex_dump_to_file(address, size, filename, "wx", description):
                dump_files[region_name] = filename
                print(f"  ✅ {region_name}: {filename}")
            else:
                print(f"  ❌ Failed to save {region_name}")
        
        # Also save CPU registers
        reg_filename = f"registers_{timestamp}{cycle_suffix}.txt"
        try:
            registers = self.monitor.get_registers()
            with open(reg_filename, 'w') as f:
                f.write(f"# CPU Registers Dump\n")
                f.write(f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                if cycle_number is not None:
                    f.write(f"# Cycle: {cycle_number}\n")
                f.write("#" + "="*60 + "\n\n")
                
                for reg_name, reg_value in sorted(registers.items()):
                    f.write(f"{reg_name:12}: 0x{reg_value:08x}\n")
            
            dump_files['REGISTERS'] = reg_filename
            print(f"  ✅ REGISTERS: {reg_filename}")
            
        except Exception as e:
            print(f"  ❌ Failed to save registers: {e}")
        
        return dump_files
    
    def analyze_dynamic_patterns(self) -> Dict:
        """Analyze dynamic patterns for instruction tracing"""
        print("\nAnalyzing dynamic patterns for instruction tracing...")
        
        pattern_base = self.REGIONS['PATTERN_REGION']
        
        # Sample dynamic pattern locations (every 4KB in pattern region)
        sample_locations = []
        for i in range(0, 16):  # Check first 64KB
            addr = pattern_base + (i * 1024 * 4)  # Every 4KB
            values = self.monitor.dump_memory(addr, 4, "wx")
            if values:
                sample_locations.append({
                    'offset': i * 4096,
                    'address': addr,
                    'values': values[:4]
                })
        
        return {
            'pattern_base': pattern_base,
            'samples': sample_locations,
            'total_samples': len(sample_locations)
        }
    
    def generate_report(self, output_file: str = None) -> str:
        """Generate comprehensive analysis report"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        report = f"""
========================================
FREERTOS-SEL4 MEMORY PATTERN ANALYSIS
Generated: {timestamp}
========================================

OVERVIEW:
This report analyzes memory patterns painted by the FreeRTOS memory
debugging implementation to verify correct virtual-to-physical 
memory mapping in the seL4 virtualization environment.

REGISTER STATE:
"""
        
        # Add register information
        registers = self.monitor.get_registers()
        for reg_name, reg_value in sorted(registers.items())[:8]:  # Show key registers
            report += f"  {reg_name:8}: 0x{reg_value:08x}\n"
        
        report += "\nMEMORY REGION ANALYSIS:\n"
        
        # Add region analysis
        for result in self.analysis_results:
            status = "PASS" if result.get('success', False) else "FAIL"
            report += f"\n[{status}] {result['region']} Region:\n"
            report += f"  Address: 0x{result['address']:08x}\n"
            report += f"  Expected Pattern: 0x{result['expected_pattern']:08x}\n"
            report += f"  Pattern Matches: {result['matches']}/{result['total']} ({result['match_percentage']:.1f}%)\n"
            
            if result.get('mismatches'):
                report += "  Sample Mismatches:\n"
                for mismatch in result['mismatches']:
                    report += f"    0x{mismatch['address']:08x}: expected 0x{mismatch['expected']:08x}, got 0x{mismatch['actual']:08x}\n"
        
        # Add dynamic pattern analysis
        dynamic_result = self.analyze_dynamic_patterns()
        report += f"\nDYNAMIC PATTERN ANALYSIS:\n"
        report += f"  Base Address: 0x{dynamic_result['pattern_base']:08x}\n"
        report += f"  Samples Collected: {dynamic_result['total_samples']}\n"
        
        if dynamic_result['samples']:
            report += "  Sample Pattern Values:\n"
            for sample in dynamic_result['samples'][:5]:  # Show first 5
                report += f"    +0x{sample['offset']:04x}: {' '.join(f'0x{v:08x}' for v in sample['values'])}\n"
        
        # Summary
        total_regions = len(self.analysis_results)
        passed_regions = sum(1 for r in self.analysis_results if r.get('success', False))
        
        report += f"\nSUMMARY:\n"
        report += f"  Regions Analyzed: {total_regions}\n"
        report += f"  Regions Passed: {passed_regions}\n"
        report += f"  Success Rate: {passed_regions/total_regions*100:.1f}%\n"
        
        if passed_regions == total_regions:
            report += "\n✅ ALL MEMORY PATTERNS VERIFIED - seL4 VM memory mapping working correctly\n"
        else:
            report += "\n❌ MEMORY PATTERN MISMATCHES DETECTED - investigate seL4 VM configuration\n"
        
        report += "\nQEMU MONITOR COMMANDS USED:\n"
        report += "  info registers\n"
        for region_name, address, _, _ in [
            ('STACK', self.REGIONS['STACK_REGION'], 256, self.PATTERNS['STACK']),
            ('DATA', self.REGIONS['DATA_REGION'], 256, self.PATTERNS['DATA']),
            ('HEAP', self.REGIONS['HEAP_REGION'], 256, self.PATTERNS['HEAP']),
            ('PATTERN', self.REGIONS['PATTERN_REGION'], 1024, self.PATTERNS['TEST'])
        ]:
            report += f"  x/256wx 0x{address:08x}  # {region_name} region\n"
        
        report += "\n========================================\n"
        
        if output_file:
            try:
                with open(output_file, 'w') as f:
                    f.write(report)
                print(f"Report saved to {output_file}")
            except Exception as e:
                print(f"Failed to save report: {e}")
        
        return report

def setup_qemu_monitor_access():
    """Instructions for setting up QEMU with monitor access"""
    instructions = """
To enable QEMU monitor access for memory debugging:

1. Start QEMU with monitor interface:
   qemu-system-arm -M virt -cpu cortex-a53 -m 2048M -nographic \\
   -kernel images/capdl-loader-image-arm-qemu-arm-virt \\
   -monitor tcp:127.0.0.1:55555,server,nowait

2. Alternative: Use UNIX socket:
   -monitor unix:/tmp/qemu-monitor,server,nowait

3. Test connection:
   telnet 127.0.0.1 55555
   (qemu) info registers
   (qemu) x/32wx 0x40000000

4. For instruction tracing, add:
   -d exec,cpu,guest_errors -D qemu_trace.log

Available monitor commands:
  info registers        - Show CPU registers
  x/NUMfmt ADDR        - Examine memory (NUM=count, fmt=format)
  info mtree           - Show memory tree
  info qtree           - Show device tree
  savevm TAG           - Save VM state
  loadvm TAG           - Load VM state
"""
    return instructions

def main():
    parser = argparse.ArgumentParser(description='QEMU Memory Pattern Analyzer for FreeRTOS-seL4')
    parser.add_argument('--monitor-host', default='127.0.0.1', help='QEMU monitor host')
    parser.add_argument('--monitor-port', type=int, default=55555, help='QEMU monitor port')
    parser.add_argument('--output', '-o', help='Output file for analysis report')
    parser.add_argument('--setup-help', action='store_true', help='Show QEMU monitor setup instructions')
    parser.add_argument('--continuous', '-c', action='store_true', help='Continuous monitoring mode')
    parser.add_argument('--interval', type=int, default=30, help='Monitoring interval in seconds')
    parser.add_argument('--save-hex', action='store_true', help='Save hex dumps to files')
    parser.add_argument('--hex-only', action='store_true', help='Only save hex dumps, skip analysis')
    
    args = parser.parse_args()
    
    if args.setup_help:
        print(setup_qemu_monitor_access())
        return
    
    # Connect to QEMU monitor
    print(f"Connecting to QEMU monitor at {args.monitor_host}:{args.monitor_port}...")
    monitor = QEMUMonitor(args.monitor_host, args.monitor_port)
    
    if not monitor.connect():
        print("Failed to connect to QEMU monitor. Make sure QEMU is running with monitor interface.")
        print("Use --setup-help for instructions.")
        return 1
    
    # Create analyzer
    analyzer = MemoryPatternAnalyzer(monitor)
    
    try:
        if args.hex_only:
            print("Hex dump only mode - saving memory dumps...")
            hex_files = analyzer.save_all_region_hex_dumps()
            print(f"\n✅ Saved {len(hex_files)} hex dump files:")
            for region, filename in hex_files.items():
                print(f"  {region}: {filename}")
        
        elif args.continuous:
            print(f"Starting continuous monitoring (interval: {args.interval}s)...")
            cycle = 0
            while True:
                print(f"\n=== Monitoring Cycle {cycle} ===")
                
                # Save hex dumps if requested
                if args.save_hex:
                    hex_files = analyzer.save_all_region_hex_dumps(cycle)
                
                # Perform analysis
                results = analyzer.comprehensive_analysis()
                
                # Generate report
                output_file = f"memory_analysis_cycle_{cycle:03d}.txt" if args.output else None
                report = analyzer.generate_report(output_file)
                
                cycle += 1
                
                if not args.output:  # Print to stdout if no output file
                    print(report)
                
                print(f"Waiting {args.interval} seconds for next cycle...")
                time.sleep(args.interval)
                
        else:
            # Single analysis
            print("Performing single memory pattern analysis...")
            
            # Save hex dumps if requested
            if args.save_hex:
                hex_files = analyzer.save_all_region_hex_dumps()
                print(f"\n💾 Saved {len(hex_files)} hex dump files")
            
            results = analyzer.comprehensive_analysis()
            
            # Generate and display report
            report = analyzer.generate_report(args.output)
            
            if not args.output:
                print(report)
    
    except KeyboardInterrupt:
        print("\nAnalysis interrupted by user.")
    
    except Exception as e:
        print(f"Error during analysis: {e}")
        return 1
    
    finally:
        monitor.close()
        print("QEMU monitor connection closed.")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())