#!/usr/bin/env python3
"""
Memory Snapshot Database Analysis Tool

Analyzes the recorded boot sequences, memory snapshots, and instruction traces
to provide insights into FreeRTOS-seL4 boot behavior and memory patterns.

Usage:
    python3 analyze_snapshots.py --db memory_snapshots.db --report boot_analysis.html
    python3 analyze_snapshots.py --db memory_snapshots.db --export-csv
    python3 analyze_snapshots.py --db memory_snapshots.db --memory-evolution
"""

import sqlite3
import argparse
import json
import sys
import struct
from datetime import datetime
from typing import Dict, List, Tuple, Any
import matplotlib.pyplot as plt
import pandas as pd
from collections import defaultdict

class SnapshotAnalyzer:
    """Analyzes memory snapshot database"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row  # Enable column access by name
    
    def get_boot_sessions(self) -> List[Dict]:
        """Get all boot sessions"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT session_id, start_time, end_time, description,
                   COUNT(DISTINCT ms.snapshot_id) as snapshot_count,
                   COUNT(DISTINCT it.trace_id) as instruction_count
            FROM boot_sessions bs
            LEFT JOIN memory_snapshots ms ON bs.session_id = ms.session_id
            LEFT JOIN instruction_traces it ON bs.session_id = it.session_id
            GROUP BY bs.session_id
            ORDER BY bs.start_time DESC
        ''')
        
        sessions = []
        for row in cursor.fetchall():
            sessions.append({
                'session_id': row['session_id'],
                'start_time': row['start_time'],
                'end_time': row['end_time'],
                'description': row['description'],
                'snapshot_count': row['snapshot_count'],
                'instruction_count': row['instruction_count']
            })
        
        return sessions
    
    def analyze_boot_sequence(self, session_id: int) -> Dict:
        """Analyze complete boot sequence for a session"""
        print(f"🔍 Analyzing boot sequence for session {session_id}")
        
        # Get memory snapshots
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT snapshot_id, timestamp, boot_stage, pc_address, memory_regions, total_size
            FROM memory_snapshots 
            WHERE session_id = ?
            ORDER BY timestamp
        ''', (session_id,))
        
        snapshots = []
        for row in cursor.fetchall():
            snapshots.append({
                'snapshot_id': row['snapshot_id'],
                'timestamp': row['timestamp'],
                'boot_stage': row['boot_stage'],
                'pc_address': row['pc_address'],
                'memory_regions': json.loads(row['memory_regions']),
                'total_size': row['total_size']
            })
        
        # Get instruction trace summary
        cursor.execute('''
            SELECT boot_stage, COUNT(*) as instruction_count,
                   MIN(pc_address) as min_pc, MAX(pc_address) as max_pc,
                   COUNT(DISTINCT function_name) as function_count
            FROM instruction_traces
            WHERE session_id = ?
            GROUP BY boot_stage
            ORDER BY MIN(sequence_number)
        ''', (session_id,))
        
        instruction_summary = []
        for row in cursor.fetchall():
            instruction_summary.append({
                'boot_stage': row['boot_stage'],
                'instruction_count': row['instruction_count'],
                'min_pc': row['min_pc'],
                'max_pc': row['max_pc'],
                'function_count': row['function_count']
            })
        
        return {
            'session_id': session_id,
            'snapshots': snapshots,
            'instruction_summary': instruction_summary,
            'total_snapshots': len(snapshots),
            'total_stages': len(instruction_summary)
        }
    
    def analyze_memory_evolution(self, session_id: int) -> Dict:
        """Analyze how memory patterns evolve during boot"""
        print(f"📊 Analyzing memory pattern evolution for session {session_id}")
        
        cursor = self.conn.cursor()
        
        # Get all memory regions for the session
        cursor.execute('''
            SELECT ms.timestamp, ms.boot_stage, mr.region_name, mr.start_address,
                   mr.size, mr.expected_pattern, mr.pattern_matches, mr.checksum
            FROM memory_snapshots ms
            JOIN memory_regions mr ON ms.snapshot_id = mr.snapshot_id
            WHERE ms.session_id = ?
            ORDER BY ms.timestamp, mr.region_name
        ''', (session_id,))
        
        regions = defaultdict(list)
        for row in cursor.fetchall():
            region_data = {
                'timestamp': row['timestamp'],
                'boot_stage': row['boot_stage'],
                'start_address': row['start_address'],
                'size': row['size'],
                'expected_pattern': row['expected_pattern'],
                'pattern_matches': row['pattern_matches'],
                'checksum': row['checksum'],
                'match_percentage': (row['pattern_matches'] / (row['size'] // 4) * 100) if row['expected_pattern'] else 0
            }
            regions[row['region_name']].append(region_data)
        
        return dict(regions)
    
    def analyze_instruction_patterns(self, session_id: int) -> Dict:
        """Analyze instruction execution patterns"""
        print(f"🔍 Analyzing instruction patterns for session {session_id}")
        
        cursor = self.conn.cursor()
        
        # Function call frequency
        cursor.execute('''
            SELECT function_name, COUNT(*) as call_count,
                   COUNT(DISTINCT boot_stage) as stages_active
            FROM instruction_traces
            WHERE session_id = ? AND function_name != 'unknown'
            GROUP BY function_name
            ORDER BY call_count DESC
        ''', (session_id,))
        
        function_stats = []
        for row in cursor.fetchall():
            function_stats.append({
                'function_name': row['function_name'],
                'call_count': row['call_count'],
                'stages_active': row['stages_active']
            })
        
        # Boot stage timing
        cursor.execute('''
            SELECT boot_stage, 
                   MIN(timestamp) as start_time,
                   MAX(timestamp) as end_time,
                   COUNT(*) as instruction_count,
                   MAX(sequence_number) - MIN(sequence_number) as sequence_span
            FROM instruction_traces
            WHERE session_id = ?
            GROUP BY boot_stage
            ORDER BY MIN(sequence_number)
        ''', (session_id,))
        
        stage_timing = []
        for row in cursor.fetchall():
            stage_timing.append({
                'boot_stage': row['boot_stage'],
                'start_time': row['start_time'],
                'end_time': row['end_time'],
                'instruction_count': row['instruction_count'],
                'sequence_span': row['sequence_span']
            })
        
        return {
            'function_stats': function_stats,
            'stage_timing': stage_timing
        }
    
    def compare_memory_snapshots(self, session_id: int, region_name: str) -> Dict:
        """Compare memory snapshots for a specific region across boot stages"""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            SELECT ms.boot_stage, mr.data, mr.pattern_matches, mr.checksum, ms.timestamp
            FROM memory_snapshots ms
            JOIN memory_regions mr ON ms.snapshot_id = mr.snapshot_id
            WHERE ms.session_id = ? AND mr.region_name = ?
            ORDER BY ms.timestamp
        ''', (session_id, region_name))
        
        snapshots = []
        for row in cursor.fetchall():
            snapshots.append({
                'boot_stage': row['boot_stage'],
                'timestamp': row['timestamp'],
                'data_checksum': row['checksum'],
                'pattern_matches': row['pattern_matches'],
                'data_size': len(row['data'])
            })
        
        # Calculate differences between consecutive snapshots
        differences = []
        for i in range(1, len(snapshots)):
            prev = snapshots[i-1]
            curr = snapshots[i]
            
            differences.append({
                'from_stage': prev['boot_stage'],
                'to_stage': curr['boot_stage'],
                'checksum_changed': prev['data_checksum'] != curr['data_checksum'],
                'pattern_change': curr['pattern_matches'] - prev['pattern_matches']
            })
        
        return {
            'region_name': region_name,
            'snapshots': snapshots,
            'differences': differences
        }
    
    def export_to_csv(self, session_id: int, output_prefix: str = "snapshot_export") -> List[str]:
        """Export session data to CSV files"""
        print(f"📤 Exporting session {session_id} to CSV files...")
        
        files_created = []
        
        # Export memory snapshots
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT ms.timestamp, ms.boot_stage, ms.pc_address, mr.region_name,
                   mr.start_address, mr.size, mr.expected_pattern, mr.pattern_matches,
                   mr.checksum, (mr.pattern_matches * 100.0 / (mr.size / 4)) as match_percentage
            FROM memory_snapshots ms
            JOIN memory_regions mr ON ms.snapshot_id = mr.snapshot_id
            WHERE ms.session_id = ?
            ORDER BY ms.timestamp, mr.region_name
        ''', (session_id,))
        
        df_memory = pd.DataFrame(cursor.fetchall(), columns=[
            'timestamp', 'boot_stage', 'pc_address', 'region_name',
            'start_address', 'size', 'expected_pattern', 'pattern_matches',
            'checksum', 'match_percentage'
        ])
        
        memory_file = f"{output_prefix}_memory_{session_id}.csv"
        df_memory.to_csv(memory_file, index=False)
        files_created.append(memory_file)
        
        # Export instruction traces (sample)
        cursor.execute('''
            SELECT timestamp, pc_address, disassembly, function_name, boot_stage
            FROM instruction_traces
            WHERE session_id = ?
            ORDER BY sequence_number
            LIMIT 10000
        ''', (session_id,))
        
        df_instructions = pd.DataFrame(cursor.fetchall(), columns=[
            'timestamp', 'pc_address', 'disassembly', 'function_name', 'boot_stage'
        ])
        
        instructions_file = f"{output_prefix}_instructions_{session_id}.csv"
        df_instructions.to_csv(instructions_file, index=False)
        files_created.append(instructions_file)
        
        print(f"✅ Exported {len(files_created)} CSV files")
        return files_created
    
    def generate_html_report(self, session_id: int, output_file: str = "boot_analysis.html") -> bool:
        """Generate comprehensive HTML analysis report"""
        print(f"📄 Generating HTML report for session {session_id}")
        
        try:
            # Analyze all aspects
            boot_analysis = self.analyze_boot_sequence(session_id)
            memory_evolution = self.analyze_memory_evolution(session_id)
            instruction_patterns = self.analyze_instruction_patterns(session_id)
            
            # Generate HTML
            html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Boot Analysis Report - Session {session_id}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background: #f0f0f0; padding: 20px; border-radius: 5px; }}
        .section {{ margin: 20px 0; border: 1px solid #ddd; padding: 15px; }}
        .success {{ color: green; font-weight: bold; }}
        .warning {{ color: orange; font-weight: bold; }}
        .error {{ color: red; font-weight: bold; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>FreeRTOS-seL4 Boot Analysis Report</h1>
        <p><strong>Session ID:</strong> {session_id}</p>
        <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p><strong>Total Snapshots:</strong> {boot_analysis['total_snapshots']}</p>
        <p><strong>Boot Stages:</strong> {boot_analysis['total_stages']}</p>
    </div>
    
    <div class="section">
        <h2>Boot Sequence Overview</h2>
        <table>
            <tr><th>Boot Stage</th><th>Instructions</th><th>PC Range</th><th>Functions</th></tr>
"""
            
            for stage in instruction_patterns['stage_timing']:
                html_content += f"""
            <tr>
                <td>{stage['boot_stage']}</td>
                <td>{stage['instruction_count']:,}</td>
                <td>0x{instruction_patterns['function_stats'][0].get('min_pc', 0):08x} - 0x{instruction_patterns['function_stats'][0].get('max_pc', 0):08x}</td>
                <td>{len([f for f in instruction_patterns['function_stats'] if stage['boot_stage'] in f.get('stages_active', [])])}</td>
            </tr>
"""
            
            html_content += """
        </table>
    </div>
    
    <div class="section">
        <h2>Memory Pattern Analysis</h2>
        <table>
            <tr><th>Region</th><th>Snapshots</th><th>Pattern Success</th><th>Changes</th></tr>
"""
            
            for region_name, snapshots in memory_evolution.items():
                if snapshots:
                    latest = snapshots[-1]
                    success_class = "success" if latest['match_percentage'] > 90 else "warning" if latest['match_percentage'] > 50 else "error"
                    html_content += f"""
            <tr>
                <td>{region_name}</td>
                <td>{len(snapshots)}</td>
                <td class="{success_class}">{latest['match_percentage']:.1f}%</td>
                <td>{len(set(s['checksum'] for s in snapshots))}</td>
            </tr>
"""
            
            html_content += """
        </table>
    </div>
    
    <div class="section">
        <h2>Function Execution Statistics</h2>
        <table>
            <tr><th>Function</th><th>Instructions</th><th>Active Stages</th></tr>
"""
            
            for func in instruction_patterns['function_stats'][:10]:  # Top 10
                html_content += f"""
            <tr>
                <td>{func['function_name']}</td>
                <td>{func['call_count']:,}</td>
                <td>{func['stages_active']}</td>
            </tr>
"""
            
            html_content += """
        </table>
    </div>
    
    <div class="section">
        <h2>Memory Snapshots</h2>
        <table>
            <tr><th>Timestamp</th><th>Boot Stage</th><th>PC Address</th><th>Regions</th><th>Total Size</th></tr>
"""
            
            for snapshot in boot_analysis['snapshots']:
                html_content += f"""
            <tr>
                <td>{snapshot['timestamp']}</td>
                <td>{snapshot['boot_stage']}</td>
                <td>0x{snapshot['pc_address']:08x}</td>
                <td>{len(snapshot['memory_regions'])}</td>
                <td>{snapshot['total_size']:,} bytes</td>
            </tr>
"""
            
            html_content += """
        </table>
    </div>
    
    <div class="section">
        <h2>Analysis Summary</h2>
        <p>This report shows the complete boot sequence analysis with memory pattern verification.</p>
        <ul>
            <li><strong>Boot Stages:</strong> Successfully tracked through multiple stages</li>
            <li><strong>Memory Patterns:</strong> Pattern painting and verification captured</li>
            <li><strong>Instruction Traces:</strong> Complete execution flow recorded</li>
            <li><strong>Database Storage:</strong> All data available for further analysis</li>
        </ul>
    </div>
    
</body>
</html>
"""
            
            with open(output_file, 'w') as f:
                f.write(html_content)
            
            print(f"✅ HTML report generated: {output_file}")
            return True
            
        except Exception as e:
            print(f"❌ Report generation failed: {e}")
            return False
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()

def main():
    parser = argparse.ArgumentParser(description='Analyze Memory Snapshot Database')
    parser.add_argument('--db', required=True, help='Database file path')
    parser.add_argument('--list-sessions', action='store_true', help='List all boot sessions')
    parser.add_argument('--session', type=int, help='Session ID to analyze')
    parser.add_argument('--report', help='Generate HTML report file')
    parser.add_argument('--export-csv', action='store_true', help='Export to CSV files')
    parser.add_argument('--memory-evolution', action='store_true', help='Analyze memory evolution')
    parser.add_argument('--compare-region', help='Compare specific memory region')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.db):
        print(f"❌ Database not found: {args.db}")
        sys.exit(1)
    
    analyzer = SnapshotAnalyzer(args.db)
    
    try:
        if args.list_sessions:
            sessions = analyzer.get_boot_sessions()
            print(f"📋 Found {len(sessions)} boot sessions:")
            for session in sessions:
                print(f"  Session {session['session_id']}: {session['start_time']}")
                print(f"    Description: {session['description']}")
                print(f"    Snapshots: {session['snapshot_count']}, Instructions: {session['instruction_count']:,}")
                print()
        
        elif args.session:
            session_id = args.session
            
            if args.report:
                analyzer.generate_html_report(session_id, args.report)
            
            if args.export_csv:
                files = analyzer.export_to_csv(session_id)
                print(f"✅ Exported files: {', '.join(files)}")
            
            if args.memory_evolution:
                evolution = analyzer.analyze_memory_evolution(session_id)
                print(f"📊 Memory evolution analysis for session {session_id}:")
                for region, snapshots in evolution.items():
                    print(f"  {region}: {len(snapshots)} snapshots")
                    if snapshots:
                        latest = snapshots[-1]
                        print(f"    Latest: {latest['match_percentage']:.1f}% pattern match")
            
            if args.compare_region:
                comparison = analyzer.compare_memory_snapshots(session_id, args.compare_region)
                print(f"🔍 Memory region comparison: {args.compare_region}")
                for diff in comparison['differences']:
                    print(f"  {diff['from_stage']} → {diff['to_stage']}: {'Changed' if diff['checksum_changed'] else 'No change'}")
            
            if not any([args.report, args.export_csv, args.memory_evolution, args.compare_region]):
                # Default analysis
                boot_analysis = analyzer.analyze_boot_sequence(session_id)
                print(f"🔍 Boot analysis for session {session_id}:")
                print(f"  Snapshots: {boot_analysis['total_snapshots']}")
                print(f"  Stages: {boot_analysis['total_stages']}")
        
        else:
            parser.print_help()
    
    finally:
        analyzer.close()

if __name__ == "__main__":
    import os
    main()