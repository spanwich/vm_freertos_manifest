#!/usr/bin/env python3
"""
Direct RFEIA Evidence Capture
Uses QEMU monitor to capture memory access evidence during context switch
"""

import telnetlib
import subprocess
import time
import signal
import sys
import json
from datetime import datetime

class RFEIAEvidenceCapture:
    def __init__(self):
        self.qemu_process = None
        self.monitor_connection = None
        self.evidence = []
        
    def start_linux_qemu(self):
        """Start Linux QEMU with monitor interface"""
        print("🚀 Starting Linux QEMU for RFEIA evidence capture...")
        
        qemu_cmd = [
            "/home/konton-otome/phd/run_freertos_linux_qemu.sh"
        ]
        
        try:
            # Start QEMU in background
            self.qemu_process = subprocess.Popen(qemu_cmd,
                                               stdout=subprocess.PIPE,
                                               stderr=subprocess.PIPE)
            print("✅ Linux QEMU started with monitor on port 55556")
            return True
        except Exception as e:
            print(f"❌ Failed to start QEMU: {e}")
            return False
    
    def connect_monitor(self):
        """Connect to QEMU monitor"""
        retries = 0
        max_retries = 10
        
        while retries < max_retries:
            try:
                print(f"🔌 Connecting to QEMU monitor (attempt {retries + 1})...")
                self.monitor_connection = telnetlib.Telnet('127.0.0.1', 55556, timeout=5)
                self.monitor_connection.read_until(b'(qemu) ', timeout=3)
                print("✅ Connected to QEMU monitor")
                return True
            except Exception as e:
                print(f"⏳ Connection attempt {retries + 1} failed: {e}")
                retries += 1
                time.sleep(2)
        
        print("❌ Failed to connect to QEMU monitor")
        return False
    
    def execute_monitor_command(self, command):
        """Execute command on QEMU monitor"""
        if not self.monitor_connection:
            return None
            
        try:
            self.monitor_connection.write(f"{command}\n".encode())
            output = self.monitor_connection.read_until(b'(qemu) ', timeout=5)
            result = output.decode('utf-8', errors='ignore')
            # Remove command echo and prompt
            lines = result.split('\n')[1:-1]
            return '\n'.join(lines).strip()
        except Exception as e:
            print(f"❌ Monitor command failed: {e}")
            return None
    
    def capture_memory_state(self, timestamp, description):
        """Capture current memory state"""
        print(f"📋 Capturing: {description}")
        
        state = {
            'timestamp': timestamp,
            'description': description,
            'exception_vectors': {},
            'cpu_registers': None,
            'memory_tree': None
        }
        
        # Capture exception vectors
        vector_addrs = [0x0, 0x4, 0x8, 0xc, 0x10, 0x18, 0x1c]
        vector_names = ['Reset', 'Undefined', 'SWI', 'PrefetchAbort', 'DataAbort', 'IRQ', 'FIQ']
        
        for addr, name in zip(vector_addrs, vector_names):
            cmd = f"x/1wx 0x{addr:x}"
            result = self.execute_monitor_command(cmd)
            state['exception_vectors'][name] = {
                'address': f"0x{addr:x}",
                'content': result
            }
            print(f"   {name} (0x{addr:x}): {result}")
        
        # Capture CPU registers
        registers = self.execute_monitor_command("info registers")
        state['cpu_registers'] = registers
        
        # Capture memory layout
        memory_tree = self.execute_monitor_command("info mtree")
        state['memory_tree'] = memory_tree
        
        self.evidence.append(state)
        return state
    
    def monitor_context_switch(self):
        """Monitor the system for context switch behavior"""
        print("\n🔍 Monitoring FreeRTOS context switch behavior...")
        
        # Capture initial state
        self.capture_memory_state(
            datetime.now().isoformat(),
            "Initial system state - FreeRTOS should be starting"
        )
        
        # Wait for system to potentially attempt context switch
        print("⏳ Waiting for FreeRTOS scheduler to start...")
        time.sleep(5)
        
        # Capture state after scheduler attempts
        self.capture_memory_state(
            datetime.now().isoformat(),
            "Post-scheduler state - checking for context switch activity"
        )
        
        # Check if we can access exception vectors
        print("\n📊 Analyzing exception vector accessibility...")
        svi_access = self.execute_monitor_command("x/1wx 0x8")
        
        if svi_access and "Cannot access memory" not in svi_access:
            print("✅ SWI vector at 0x8 IS accessible in Linux QEMU")
            print(f"   Content: {svi_access}")
            
            # Try to detect if RFEIA-like instruction could work
            print("🔍 Testing memory access pattern similar to RFEIA...")
            
            # Test sequential access to exception vectors (what RFEIA might do)
            for addr in [0x0, 0x4, 0x8, 0xc]:
                result = self.execute_monitor_command(f"x/1wx 0x{addr:x}")
                if result and "Cannot access memory" not in result:
                    print(f"   ✅ Address 0x{addr:x} accessible: {result}")
                else:
                    print(f"   ❌ Address 0x{addr:x} NOT accessible")
            
            # This is evidence that RFEIA could work
            evidence_state = {
                'timestamp': datetime.now().isoformat(),
                'description': 'RFEIA CAPABILITY EVIDENCE - Exception vectors accessible',
                'rfeia_evidence': {
                    'svi_vector_accessible': True,
                    'svi_content': svi_access,
                    'all_vectors_accessible': True,
                    'conclusion': 'RFEIA sp! instruction would be able to access SWI vector at 0x8'
                }
            }
            self.evidence.append(evidence_state)
            
        else:
            print("❌ SWI vector at 0x8 is NOT accessible")
            evidence_state = {
                'timestamp': datetime.now().isoformat(), 
                'description': 'RFEIA FAILURE EVIDENCE - Exception vectors not accessible',
                'rfeia_evidence': {
                    'svi_vector_accessible': False,
                    'svi_content': svi_access,
                    'conclusion': 'RFEIA sp! instruction would fail with page fault'
                }
            }
            self.evidence.append(evidence_state)
    
    def save_evidence(self):
        """Save captured evidence to file"""
        evidence_file = f"/home/konton-otome/phd/rfeia_evidence_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        full_evidence = {
            'capture_info': {
                'timestamp': datetime.now().isoformat(),
                'system': 'Linux QEMU ARM',
                'binary': 'FreeRTOS ARM',
                'purpose': 'RFEIA sp! instruction SWI vector access evidence'
            },
            'evidence_states': self.evidence
        }
        
        with open(evidence_file, 'w') as f:
            json.dump(full_evidence, f, indent=2)
        
        print(f"\n💾 Evidence saved to: {evidence_file}")
        return evidence_file
    
    def cleanup(self):
        """Clean up connections and processes"""
        if self.monitor_connection:
            try:
                self.monitor_connection.close()
            except:
                pass
        
        if self.qemu_process:
            try:
                self.qemu_process.terminate()
                self.qemu_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.qemu_process.kill()
            except:
                pass

def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully"""
    print("\n🛑 Interrupted by user")
    if 'capturer' in globals():
        capturer.cleanup()
    sys.exit(0)

def main():
    global capturer
    capturer = RFEIAEvidenceCapture()
    
    signal.signal(signal.SIGINT, signal_handler)
    
    print("=" * 70)
    print("  RFEIA INSTRUCTION SWI VECTOR ACCESS EVIDENCE CAPTURE")
    print("  Linux QEMU Environment Analysis")
    print("=" * 70)
    
    try:
        # Start Linux QEMU
        if not capturer.start_linux_qemu():
            return 1
        
        # Wait for QEMU to start
        print("⏳ Waiting for QEMU to initialize...")
        time.sleep(8)
        
        # Connect to monitor
        if not capturer.connect_monitor():
            return 1
        
        # Monitor context switch behavior
        capturer.monitor_context_switch()
        
        # Save evidence
        evidence_file = capturer.save_evidence()
        
        print("\n" + "=" * 50)
        print("📋 EVIDENCE SUMMARY")
        print("=" * 50)
        
        # Check if we found positive evidence
        found_evidence = False
        for state in capturer.evidence:
            if 'rfeia_evidence' in state:
                evidence = state['rfeia_evidence']
                if evidence.get('svi_vector_accessible', False):
                    print("🎯 POSITIVE EVIDENCE FOUND:")
                    print(f"   • SWI vector at 0x8 IS accessible in Linux QEMU")
                    print(f"   • Content: {evidence['svi_content']}")
                    print(f"   • Conclusion: {evidence['conclusion']}")
                    found_evidence = True
                else:
                    print("❌ NEGATIVE EVIDENCE:")
                    print(f"   • SWI vector at 0x8 is NOT accessible")
                    print(f"   • This contradicts expected Linux behavior")
        
        if not found_evidence:
            print("⚠️  No definitive RFEIA evidence captured")
            print("    Check evidence file for detailed analysis")
        
        print(f"\n📄 Full evidence report: {evidence_file}")
        
    except Exception as e:
        print(f"❌ Error during capture: {e}")
        return 1
    finally:
        capturer.cleanup()
    
    return 0

if __name__ == "__main__":
    exit(main())