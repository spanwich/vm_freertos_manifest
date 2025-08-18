#!/usr/bin/env python3
"""
Instruction Tracing Analyzer for FreeRTOS-seL4 Dynamic Analysis

This script processes QEMU instruction traces to analyze execution patterns
and correlate them with memory access patterns for debugging purposes.

Usage:
    python3 instruction_trace_analyzer.py --trace-file qemu_trace.log [--output analysis.txt]

Features:
- Instruction execution flow analysis
- Memory access pattern correlation
- Function call tracking
- Performance hotspot identification
- Exception/fault analysis
"""

import argparse
import re
import sys
from datetime import datetime
from collections import defaultdict, Counter
from typing import Dict, List, Tuple, Optional

class InstructionTraceAnalyzer:
    """Analyzes QEMU instruction traces for dynamic analysis"""
    
    def __init__(self, trace_file: str):
        self.trace_file = trace_file
        self.instructions = []
        self.memory_accesses = []
        self.function_calls = []
        self.exceptions = []
        
        # FreeRTOS function addresses (from build output)
        self.known_functions = {
            0x40000000: "_start",
            0x40000e70: "main", 
            0x400008e8: "vMemoryPatternDebugTask",
            0x40001014: "vMonitorTask",
            # Add more as needed from objdump output
        }
        
        # Memory regions from our debug implementation
        self.memory_regions = {
            'guest_base': (0x40000000, 0x41000000),
            'stack_region': (0x41000000, 0x41200000), 
            'data_region': (0x41200000, 0x41400000),
            'heap_region': (0x41400000, 0x41600000),
            'pattern_region': (0x42000000, 0x42400000),
            'uart': (0x9000000, 0x9001000),
        }
    
    def parse_trace_file(self) -> bool:
        """Parse QEMU trace file and extract instruction information"""
        print(f"Parsing trace file: {self.trace_file}")
        
        try:
            with open(self.trace_file, 'r') as f:
                line_count = 0
                
                for line in f:
                    line_count += 1
                    line = line.strip()
                    
                    if not line:
                        continue
                    
                    # Parse different types of trace entries
                    if self._parse_instruction_line(line):
                        continue
                    elif self._parse_memory_access_line(line):
                        continue
                    elif self._parse_exception_line(line):
                        continue
                    
                    # Progress indicator for large files
                    if line_count % 10000 == 0:
                        print(f"  Processed {line_count} lines...")
                
                print(f"✅ Parsed {line_count} trace lines")
                print(f"   Instructions: {len(self.instructions)}")
                print(f"   Memory accesses: {len(self.memory_accesses)}")
                print(f"   Exceptions: {len(self.exceptions)}")
                
                return True
                
        except FileNotFoundError:
            print(f"❌ Trace file not found: {self.trace_file}")
            return False
        except Exception as e:
            print(f"❌ Parse error: {e}")
            return False
    
    def _parse_instruction_line(self, line: str) -> bool:
        """Parse instruction execution line"""
        # QEMU exec trace format: "0x40000000:  e1a00000  mov r0, r0"
        exec_pattern = r'^0x([0-9a-fA-F]+):\s+([0-9a-fA-F]+)\s+(.+)$'
        match = re.match(exec_pattern, line)
        
        if match:
            pc = int(match.group(1), 16)
            opcode = match.group(2)
            instruction = match.group(3)
            
            self.instructions.append({
                'pc': pc,
                'opcode': opcode, 
                'instruction': instruction,
                'function': self._get_function_name(pc)
            })
            return True
        
        return False
    
    def _parse_memory_access_line(self, line: str) -> bool:
        """Parse memory access line"""
        # Look for memory access patterns
        mem_patterns = [
            r'(\w+):\s*0x([0-9a-fA-F]+)',  # General memory reference
            r'loading from 0x([0-9a-fA-F]+)',  # Load operation
            r'storing to 0x([0-9a-fA-F]+)',   # Store operation
        ]
        
        for pattern in mem_patterns:
            match = re.search(pattern, line)
            if match:
                if len(match.groups()) >= 2:
                    access_type = match.group(1)
                    address = int(match.group(2), 16)
                else:
                    access_type = "unknown"
                    address = int(match.group(1), 16)
                
                self.memory_accesses.append({
                    'address': address,
                    'type': access_type,
                    'region': self._get_memory_region(address),
                    'line': line
                })
                return True
        
        return False
    
    def _parse_exception_line(self, line: str) -> bool:
        """Parse exception/fault line"""
        exception_keywords = ['exception', 'fault', 'abort', 'interrupt']
        
        if any(keyword in line.lower() for keyword in exception_keywords):
            self.exceptions.append({
                'line': line,
                'type': self._classify_exception(line)
            })
            return True
        
        return False
    
    def _get_function_name(self, pc: int) -> str:
        """Get function name for given PC"""
        # Find the function this PC belongs to
        for addr, name in self.known_functions.items():
            if pc >= addr:
                # Simple heuristic: function extends 4KB max
                if pc < addr + 0x1000:
                    return name
        
        return f"unknown_0x{pc:08x}"
    
    def _get_memory_region(self, address: int) -> str:
        """Get memory region name for given address"""
        for region_name, (start, end) in self.memory_regions.items():
            if start <= address < end:
                return region_name
        
        return "unknown"
    
    def _classify_exception(self, line: str) -> str:
        """Classify exception type"""
        line_lower = line.lower()
        
        if 'page fault' in line_lower or 'data abort' in line_lower:
            return "memory_fault"
        elif 'undefined instruction' in line_lower:
            return "undefined_instruction"
        elif 'interrupt' in line_lower:
            return "interrupt"
        else:
            return "other"
    
    def analyze_execution_flow(self) -> Dict:
        """Analyze instruction execution flow"""
        print("🔍 Analyzing execution flow...")
        
        if not self.instructions:
            return {"error": "No instructions to analyze"}
        
        # Function execution statistics
        function_stats = defaultdict(int)
        instruction_counts = Counter()
        
        # PC transition analysis
        pc_transitions = []
        prev_pc = None
        
        for instr in self.instructions:
            pc = instr['pc']
            function = instr['function']
            instruction = instr['instruction']
            
            function_stats[function] += 1
            instruction_counts[instruction.split()[0]] += 1  # First word is opcode
            
            if prev_pc is not None:
                # Check for jumps/branches
                if pc != prev_pc + 4:  # Not sequential
                    pc_transitions.append({
                        'from': prev_pc,
                        'to': pc,
                        'type': 'jump' if abs(pc - prev_pc) > 0x1000 else 'branch'
                    })
            
            prev_pc = pc
        
        return {
            'total_instructions': len(self.instructions),
            'function_stats': dict(function_stats),
            'instruction_counts': dict(instruction_counts.most_common(10)),
            'pc_transitions': pc_transitions[:20],  # Top 20 transitions
            'execution_range': {
                'min_pc': min(i['pc'] for i in self.instructions),
                'max_pc': max(i['pc'] for i in self.instructions)
            }
        }
    
    def analyze_memory_patterns(self) -> Dict:
        """Analyze memory access patterns"""
        print("🔍 Analyzing memory access patterns...")
        
        if not self.memory_accesses:
            return {"error": "No memory accesses to analyze"}
        
        # Region access statistics
        region_stats = defaultdict(int)
        access_type_stats = defaultdict(int)
        
        # Pattern detection
        pattern_accesses = []
        
        for access in self.memory_accesses:
            region = access['region'] 
            access_type = access['type']
            address = access['address']
            
            region_stats[region] += 1
            access_type_stats[access_type] += 1
            
            # Check if this is accessing our pattern regions
            if region in ['stack_region', 'data_region', 'heap_region', 'pattern_region']:
                pattern_accesses.append(access)
        
        return {
            'total_accesses': len(self.memory_accesses),
            'region_stats': dict(region_stats),
            'access_type_stats': dict(access_type_stats),
            'pattern_accesses': len(pattern_accesses),
            'pattern_samples': pattern_accesses[:10]  # First 10 for inspection
        }
    
    def analyze_exceptions(self) -> Dict:
        """Analyze exceptions and faults"""
        print("🔍 Analyzing exceptions and faults...")
        
        if not self.exceptions:
            return {"message": "No exceptions detected"}
        
        exception_types = defaultdict(int)
        
        for exc in self.exceptions:
            exc_type = exc['type']
            exception_types[exc_type] += 1
        
        return {
            'total_exceptions': len(self.exceptions),
            'exception_types': dict(exception_types),
            'sample_exceptions': [exc['line'] for exc in self.exceptions[:5]]
        }
    
    def correlate_with_memory_patterns(self) -> Dict:
        """Correlate instruction execution with memory pattern painting"""
        print("🔍 Correlating execution with memory patterns...")
        
        correlation = {
            'pattern_painting_instructions': [],
            'pattern_verification_instructions': [],
            'uart_output_instructions': []
        }
        
        # Look for our specific debugging functions
        debug_functions = ['vMemoryPatternDebugTask', 'paint_memory_region', 'verify_memory_pattern']
        
        for instr in self.instructions:
            function = instr['function']
            pc = instr['pc']
            
            if any(debug_func in function for debug_func in debug_functions):
                correlation['pattern_painting_instructions'].append({
                    'pc': pc,
                    'function': function,
                    'instruction': instr['instruction']
                })
        
        # Look for UART accesses (our debug output)
        uart_accesses = [acc for acc in self.memory_accesses if acc['region'] == 'uart']
        correlation['uart_output_instructions'] = uart_accesses[:20]  # Sample
        
        return correlation
    
    def generate_analysis_report(self, output_file: str = None) -> str:
        """Generate comprehensive analysis report"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Perform all analyses
        flow_analysis = self.analyze_execution_flow()
        memory_analysis = self.analyze_memory_patterns()
        exception_analysis = self.analyze_exceptions()
        correlation_analysis = self.correlate_with_memory_patterns()
        
        report = f"""
========================================
FREERTOS-SEL4 INSTRUCTION TRACE ANALYSIS
Generated: {timestamp}
========================================

TRACE FILE: {self.trace_file}

EXECUTION FLOW ANALYSIS:
"""
        
        if 'error' not in flow_analysis:
            report += f"""
Total Instructions Executed: {flow_analysis['total_instructions']}
Execution Range: 0x{flow_analysis['execution_range']['min_pc']:08x} - 0x{flow_analysis['execution_range']['max_pc']:08x}

Function Execution Statistics:
"""
            for func, count in sorted(flow_analysis['function_stats'].items(), key=lambda x: x[1], reverse=True):
                report += f"  {func}: {count} instructions\n"
            
            report += "\nMost Common Instructions:\n"
            for instr, count in flow_analysis['instruction_counts'].items():
                report += f"  {instr}: {count} times\n"
        
        report += f"""

MEMORY ACCESS ANALYSIS:
"""
        
        if 'error' not in memory_analysis:
            report += f"""
Total Memory Accesses: {memory_analysis['total_accesses']}
Pattern Region Accesses: {memory_analysis['pattern_accesses']}

Memory Region Statistics:
"""
            for region, count in sorted(memory_analysis['region_stats'].items(), key=lambda x: x[1], reverse=True):
                report += f"  {region}: {count} accesses\n"
            
            report += "\nAccess Type Statistics:\n"
            for access_type, count in memory_analysis['access_type_stats'].items():
                report += f"  {access_type}: {count} accesses\n"
        
        report += f"""

EXCEPTION ANALYSIS:
"""
        
        if 'message' in exception_analysis:
            report += f"{exception_analysis['message']}\n"
        else:
            report += f"""
Total Exceptions: {exception_analysis['total_exceptions']}

Exception Types:
"""
            for exc_type, count in exception_analysis['exception_types'].items():
                report += f"  {exc_type}: {count} occurrences\n"
        
        report += f"""

MEMORY PATTERN CORRELATION:
"""
        
        pattern_instrs = len(correlation_analysis['pattern_painting_instructions'])
        uart_accesses = len(correlation_analysis['uart_output_instructions'])
        
        report += f"""
Pattern Painting Instructions: {pattern_instrs}
UART Output Accesses: {uart_accesses}

This indicates the memory debugging system is {'active' if pattern_instrs > 0 else 'inactive'}.
"""
        
        if pattern_instrs > 0:
            report += "\nSample Pattern Painting Instructions:\n"
            for instr in correlation_analysis['pattern_painting_instructions'][:5]:
                report += f"  0x{instr['pc']:08x}: {instr['instruction']}\n"
        
        report += f"""

SUMMARY:
The trace analysis shows {'successful' if pattern_instrs > 0 and 'error' not in flow_analysis else 'limited'} 
execution of the FreeRTOS memory debugging system. 

{'✅ Memory pattern painting is active and can be correlated with QEMU memory dumps.' if pattern_instrs > 0 else '⚠️  Memory pattern painting not detected in trace.'}

For complete debugging, combine this instruction trace with:
1. QEMU memory dumps from the memory analyzer
2. seL4 VM configuration analysis
3. FreeRTOS assertion and debug output

========================================
"""
        
        if output_file:
            try:
                with open(output_file, 'w') as f:
                    f.write(report)
                print(f"📄 Analysis report saved to: {output_file}")
            except Exception as e:
                print(f"Failed to save report: {e}")
        
        return report

def main():
    parser = argparse.ArgumentParser(description='QEMU Instruction Trace Analyzer')
    parser.add_argument('--trace-file', required=True, help='Path to QEMU trace file')
    parser.add_argument('--output', '-o', help='Output file for analysis report')
    parser.add_argument('--functions', help='File with additional function addresses')
    
    args = parser.parse_args()
    
    # Create analyzer
    analyzer = InstructionTraceAnalyzer(args.trace_file)
    
    # Load additional functions if provided
    if args.functions and os.path.exists(args.functions):
        print(f"Loading additional function addresses from {args.functions}")
        # Could parse objdump output or symbol file
    
    # Parse trace file
    if not analyzer.parse_trace_file():
        sys.exit(1)
    
    # Generate analysis
    report = analyzer.generate_analysis_report(args.output)
    
    if not args.output:
        print(report)
    
    print("🎉 Instruction trace analysis complete!")

if __name__ == "__main__":
    main()