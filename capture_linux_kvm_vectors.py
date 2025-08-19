#!/usr/bin/env python3
"""
Linux KVM ARM Exception Vector Analysis
Captures memory snapshots from Linux KVM for comparison with seL4 VM
"""

import telnetlib
import time
import json
from datetime import datetime

class LinuxKVMAnalyzer:
    def __init__(self, monitor_host='127.0.0.1', monitor_port=55556):
        self.monitor_host = monitor_host
        self.monitor_port = monitor_port
        self.tn = None

    def connect(self):
        """Connect to QEMU monitor interface"""
        try:
            self.tn = telnetlib.Telnet(self.monitor_host, self.monitor_port, timeout=10)
            # Wait for QEMU prompt
            self.tn.read_until(b'(qemu) ', timeout=5)
            print(f"✅ Connected to Linux KVM QEMU monitor at {self.monitor_host}:{self.monitor_port}")
            return True
        except Exception as e:
            print(f"❌ Failed to connect to monitor: {e}")
            return False

    def execute_command(self, command):
        """Execute QEMU monitor command and return output"""
        if not self.tn:
            return None
        
        try:
            self.tn.write(f"{command}\n".encode())
            output = self.tn.read_until(b'(qemu) ', timeout=5)
            # Remove the command echo and prompt
            result = output.decode('utf-8', errors='ignore')
            lines = result.split('\n')[1:-1]  # Remove first (command) and last (prompt) lines
            return '\n'.join(lines)
        except Exception as e:
            print(f"❌ Command execution failed: {e}")
            return None

    def capture_exception_vectors(self):
        """Capture ARM exception vectors at 0x0-0x1C"""
        print("\n🔍 Analyzing ARM Exception Vectors in Linux KVM...")
        
        vectors = {}
        
        # Read exception vector table
        print("📋 Reading exception vector table at 0x0-0x1C:")
        vector_data = self.execute_command("x/8wx 0x0")
        print(vector_data)
        vectors['exception_table'] = vector_data
        
        # Read as instructions
        print("\n📋 Reading exception vectors as ARM instructions:")
        vector_instructions = self.execute_command("x/8i 0x0")
        print(vector_instructions)
        vectors['exception_instructions'] = vector_instructions
        
        # CPU registers
        print("\n📋 CPU Register State:")
        registers = self.execute_command("info registers")
        print(registers[:500] + "..." if len(registers) > 500 else registers)
        vectors['cpu_registers'] = registers
        
        # Memory tree
        print("\n📋 Memory Layout:")
        memory_tree = self.execute_command("info mtree")
        print(memory_tree[:800] + "..." if len(memory_tree) > 800 else memory_tree)
        vectors['memory_layout'] = memory_tree
        
        return vectors

    def save_snapshot(self, data, filename):
        """Save snapshot data to file"""
        snapshot = {
            'timestamp': datetime.now().isoformat(),
            'hypervisor': 'Linux KVM',
            'system': 'FreeRTOS ARM',
            'data': data
        }
        
        with open(filename, 'w') as f:
            json.dump(snapshot, f, indent=2)
        
        print(f"💾 Snapshot saved to: {filename}")

    def disconnect(self):
        """Disconnect from monitor"""
        if self.tn:
            self.tn.close()

def main():
    analyzer = LinuxKVMAnalyzer()
    
    if not analyzer.connect():
        print("❌ Cannot connect to Linux KVM monitor. Make sure QEMU is running with monitor enabled.")
        return
    
    try:
        # Capture exception vector data
        vector_data = analyzer.capture_exception_vectors()
        
        # Save snapshot
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"/home/konton-otome/phd/linux_kvm_exception_vectors_{timestamp}.json"
        analyzer.save_snapshot(vector_data, filename)
        
        print(f"\n✅ Linux KVM exception vector analysis complete!")
        print(f"📄 Data saved to: {filename}")
        
    except KeyboardInterrupt:
        print("\n🛑 Analysis interrupted by user")
    finally:
        analyzer.disconnect()

if __name__ == "__main__":
    main()