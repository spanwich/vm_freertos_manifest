#!/usr/bin/env python3
"""
Complete Memory Pattern Debugging Workflow for FreeRTOS-seL4 Integration

This script demonstrates the full methodology for debugging memory mappings
between FreeRTOS guest VM and seL4 host system using memory pattern painting.

Usage:
    python3 memory_debug_workflow.py [--build] [--run] [--analyze]

Commands:
    --build     Build the memory debugging FreeRTOS binary
    --run       Run QEMU with debug capabilities (interactive)
    --analyze   Connect to running QEMU and perform memory analysis
    --all       Perform complete workflow (build + run + analyze)
"""

import argparse
import subprocess
import time
import sys
import os
from pathlib import Path

# Import our memory analyzer
sys.path.append('/home/konton-otome/phd')
from qemu_memory_analyzer import QEMUMonitor, MemoryPatternAnalyzer

class MemoryDebugWorkflow:
    """Complete workflow for memory pattern debugging"""
    
    def __init__(self):
        self.base_dir = Path("/home/konton-otome/phd")
        self.freertos_dir = self.base_dir / "freertos_vexpress_a9"
        self.camkes_dir = self.base_dir / "camkes-vm-examples"
        self.build_dir = self.camkes_dir / "build"
        
    def build_debug_binary(self) -> bool:
        """Build the FreeRTOS debug binary with memory pattern painting"""
        print("=== Building FreeRTOS Debug Binary ===")
        
        build_script = self.freertos_dir / "build_debug.sh"
        if not build_script.exists():
            print(f"ERROR: Build script not found: {build_script}")
            return False
        
        try:
            # Build debug version
            result = subprocess.run([
                str(build_script), "debug"
            ], cwd=str(self.freertos_dir), capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"Build failed: {result.stderr}")
                return False
            
            print("✅ FreeRTOS debug binary built successfully")
            print(f"📁 Binary location: {self.freertos_dir}/Build/freertos_debug_image.bin")
            
            # Update seL4 CMakeLists.txt to use debug binary
            self.update_camkes_config()
            
            return True
            
        except Exception as e:
            print(f"Build error: {e}")
            return False
    
    def update_camkes_config(self):
        """Update CAmkES configuration to use debug binary"""
        print("=== Updating seL4 Configuration ===")
        
        cmake_file = self.camkes_dir / "projects/vm-examples/apps/Arm/vm_freertos/CMakeLists.txt"
        
        try:
            content = cmake_file.read_text()
            
            # Replace binary path
            old_path = 'set(FREERTOS_BINARY_PATH "/home/konton-otome/phd/freertos_vexpress_a9/Build/freertos_image.bin")'
            new_path = 'set(FREERTOS_BINARY_PATH "/home/konton-otome/phd/freertos_vexpress_a9/Build/freertos_debug_image.bin")'
            
            if old_path in content:
                content = content.replace(old_path, new_path)
                cmake_file.write_text(content)
                print("✅ Updated CMakeLists.txt to use debug binary")
            else:
                print("⚠️  CMakeLists.txt already configured for debug binary")
                
        except Exception as e:
            print(f"Configuration update error: {e}")
    
    def build_sel4_system(self) -> bool:
        """Build the seL4 system with debug FreeRTOS"""
        print("=== Building seL4 System ===")
        
        if not self.build_dir.exists():
            self.build_dir.mkdir(parents=True)
        
        try:
            # Set up environment
            env = os.environ.copy()
            env['PYTHONPATH'] = str(self.camkes_dir / "projects/camkes-tool") + ":" + \
                               str(self.camkes_dir / "projects/capdl/python-capdl-tool")
            
            # Initialize build if needed
            if not (self.build_dir / "build.ninja").exists():
                print("Initializing seL4 build...")
                init_cmd = [
                    str(self.camkes_dir / "init-build.sh"),
                    "-DCAMKES_VM_APP=vm_freertos",
                    "-DPLATFORM=qemu-arm-virt",
                    "-DSIMULATION=1",
                    "-DLibUSB=OFF"
                ]
                
                result = subprocess.run(init_cmd, cwd=str(self.build_dir), 
                                      capture_output=True, text=True, env=env)
                
                if result.returncode != 0:
                    print(f"Build initialization failed: {result.stderr}")
                    return False
            
            # Build with ninja
            print("Building seL4 system...")
            result = subprocess.run(["ninja"], cwd=str(self.build_dir), 
                                  capture_output=True, text=True, env=env)
            
            if result.returncode != 0:
                print(f"Ninja build failed: {result.stderr}")
                return False
            
            print("✅ seL4 system built successfully")
            return True
            
        except Exception as e:
            print(f"seL4 build error: {e}")
            return False
    
    def run_qemu_debug(self, background=False) -> subprocess.Popen:
        """Run QEMU with debug capabilities"""
        print("=== Starting QEMU with Debug Support ===")
        
        image_path = self.build_dir / "images/capdl-loader-image-arm-qemu-arm-virt"
        
        if not image_path.exists():
            print(f"ERROR: QEMU image not found: {image_path}")
            print("Please build the seL4 system first")
            return None
        
        qemu_cmd = [
            "qemu-system-arm",
            "-M", "virt",
            "-cpu", "cortex-a53", 
            "-m", "2048M",
            "-nographic",
            "-kernel", str(image_path),
            "-monitor", "tcp:127.0.0.1:55555,server,nowait"
        ]
        
        try:
            if background:
                print("🚀 Starting QEMU in background...")
                print("Monitor available at: tcp://127.0.0.1:55555")
                proc = subprocess.Popen(qemu_cmd, stdout=subprocess.PIPE, 
                                      stderr=subprocess.PIPE)
                time.sleep(3)  # Give QEMU time to start
                return proc
            else:
                print("🚀 Starting QEMU (interactive mode)")
                print("Press Ctrl+C to exit")
                subprocess.run(qemu_cmd)
                return None
                
        except KeyboardInterrupt:
            print("\n⏹️  QEMU stopped by user")
            return None
        except Exception as e:
            print(f"QEMU start error: {e}")
            return None
    
    def analyze_memory_patterns(self) -> bool:
        """Perform comprehensive memory pattern analysis"""
        print("=== Memory Pattern Analysis ===")
        
        # Connect to QEMU monitor
        monitor = QEMUMonitor("127.0.0.1", 55555)
        
        if not monitor.connect():
            print("❌ Failed to connect to QEMU monitor")
            print("Make sure QEMU is running with monitor interface")
            return False
        
        try:
            # Create analyzer
            analyzer = MemoryPatternAnalyzer(monitor)
            
            print("🔍 Performing memory pattern analysis...")
            
            # Perform comprehensive analysis
            results = analyzer.comprehensive_analysis()
            
            # Generate report
            timestamp = int(time.time())
            report_file = f"/home/konton-otome/phd/memory_analysis_{timestamp}.txt"
            report = analyzer.generate_report(report_file)
            
            print(f"📄 Analysis report saved to: {report_file}")
            
            # Print summary
            total_regions = len(results)
            passed_regions = sum(1 for r in results if r.get('success', False))
            
            print(f"\n📊 Analysis Summary:")
            print(f"   Regions analyzed: {total_regions}")
            print(f"   Regions passed: {passed_regions}")
            print(f"   Success rate: {passed_regions/total_regions*100:.1f}%")
            
            if passed_regions == total_regions:
                print("✅ All memory patterns verified successfully!")
                print("   seL4 VM memory mapping is working correctly")
            else:
                print("⚠️  Some memory patterns failed verification")
                print("   Check the detailed report for debugging information")
            
            return True
            
        except Exception as e:
            print(f"Analysis error: {e}")
            return False
        finally:
            monitor.close()
    
    def run_complete_workflow(self):
        """Run the complete memory debugging workflow"""
        print("🔬 Starting Complete Memory Pattern Debugging Workflow")
        print("=" * 60)
        
        # Step 1: Build debug binary
        if not self.build_debug_binary():
            print("❌ Failed to build debug binary")
            return False
        
        # Step 2: Build seL4 system
        if not self.build_sel4_system():
            print("❌ Failed to build seL4 system")
            return False
        
        # Step 3: Start QEMU in background
        qemu_proc = self.run_qemu_debug(background=True)
        if not qemu_proc:
            print("❌ Failed to start QEMU")
            return False
        
        try:
            # Step 4: Wait for FreeRTOS to boot and start pattern painting
            print("⏳ Waiting for FreeRTOS to boot and start memory pattern painting...")
            time.sleep(10)  # Give time for FreeRTOS to initialize
            
            # Step 5: Perform analysis
            if not self.analyze_memory_patterns():
                print("❌ Memory analysis failed")
                return False
            
            print("\n🎉 Complete workflow finished successfully!")
            print("📁 Check the generated report for detailed results")
            
            return True
            
        finally:
            if qemu_proc:
                print("🛑 Stopping QEMU...")
                qemu_proc.terminate()
                try:
                    qemu_proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    qemu_proc.kill()

def main():
    parser = argparse.ArgumentParser(description='Memory Pattern Debugging Workflow')
    parser.add_argument('--build', action='store_true', help='Build debug binary and seL4 system')
    parser.add_argument('--run', action='store_true', help='Run QEMU with debug support')
    parser.add_argument('--analyze', action='store_true', help='Analyze memory patterns')
    parser.add_argument('--all', action='store_true', help='Run complete workflow')
    parser.add_argument('--trace', action='store_true', help='Enable instruction tracing')
    
    args = parser.parse_args()
    
    workflow = MemoryDebugWorkflow()
    
    if args.all:
        success = workflow.run_complete_workflow()
        sys.exit(0 if success else 1)
    
    if args.build:
        if not workflow.build_debug_binary():
            sys.exit(1)
        if not workflow.build_sel4_system():
            sys.exit(1)
    
    if args.run:
        workflow.run_qemu_debug(background=False)
    
    if args.analyze:
        if not workflow.analyze_memory_patterns():
            sys.exit(1)
    
    if not any([args.build, args.run, args.analyze, args.all]):
        parser.print_help()

if __name__ == "__main__":
    main()