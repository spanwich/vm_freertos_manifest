#!/usr/bin/env python3
"""
Hypervisor Exception Vector Comparison
Compares ARM exception vectors between Linux KVM and seL4 VM
"""

import json
import sys
from pathlib import Path

def load_snapshot(filename):
    """Load snapshot data from JSON file"""
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Failed to load {filename}: {e}")
        return None

def analyze_exception_vectors(data, hypervisor_name):
    """Analyze exception vector data"""
    print(f"\n📊 {hypervisor_name} Exception Vector Analysis:")
    print("=" * 50)
    
    exception_table = data.get('exception_table', '')
    
    # Check if vectors are accessible
    if 'Cannot access memory' in exception_table:
        print("❌ Exception vectors NOT accessible")
        print("🔍 Memory at 0x0-0x1C returns: 'Cannot access memory'")
        return False
    else:
        print("✅ Exception vectors ARE accessible")
        print("🔍 Memory at 0x0-0x1C contains valid data:")
        print(exception_table[:200] + "..." if len(exception_table) > 200 else exception_table)
        
        # Analyze instruction patterns
        instructions = data.get('exception_instructions', '')
        if instructions:
            print("\n📋 Exception Vector Instructions:")
            print(instructions[:300] + "..." if len(instructions) > 300 else instructions)
        
        return True

def compare_snapshots(linux_file, sel4_file):
    """Compare Linux and seL4 snapshots"""
    print("🔍 Loading snapshots for comparison...")
    
    linux_data = load_snapshot(linux_file)
    sel4_data = load_snapshot(sel4_file)
    
    if not linux_data or not sel4_data:
        print("❌ Failed to load snapshot data")
        return
    
    print(f"\n📅 Linux snapshot: {linux_data.get('timestamp', 'Unknown')}")
    print(f"📅 seL4 snapshot: {sel4_data.get('timestamp', 'Unknown')}")
    
    # Analyze each hypervisor
    linux_has_vectors = analyze_exception_vectors(linux_data['data'], "Linux KVM")
    sel4_has_vectors = analyze_exception_vectors(sel4_data['data'], "seL4 VM")
    
    # Comparison summary
    print("\n" + "="*60)
    print("🏁 HYPERVISOR COMPARISON SUMMARY")
    print("="*60)
    
    print(f"Linux KVM Exception Vectors:  {'✅ PRESENT' if linux_has_vectors else '❌ MISSING'}")
    print(f"seL4 VM Exception Vectors:    {'✅ PRESENT' if sel4_has_vectors else '❌ MISSING'}")
    
    if linux_has_vectors and not sel4_has_vectors:
        print("\n🎯 HYPOTHESIS CONFIRMED:")
        print("   • Linux KVM provides ARM exception vectors at 0x0-0x1C")
        print("   • seL4 VM does NOT provide ARM exception vectors")
        print("   • This explains why FreeRTOS fails with 'Page Fault at PC: 0x8' in seL4")
        print("   • FreeRTOS works in Linux KVM because SWI vector at 0x8 is accessible")
        
        return True
    elif not linux_has_vectors and not sel4_has_vectors:
        print("\n🤔 UNEXPECTED RESULT:")
        print("   • Both hypervisors lack exception vectors")
        print("   • Need to investigate why FreeRTOS works in Linux")
        
        return False
    elif linux_has_vectors and sel4_has_vectors:
        print("\n🤔 UNEXPECTED RESULT:")
        print("   • Both hypervisors have exception vectors")
        print("   • Need to investigate other causes of seL4 VM failure")
        
        return False
    else:
        print("\n🔍 INVESTIGATION NEEDED:")
        print("   • seL4 has vectors but Linux doesn't - unusual scenario")
        
        return False

def main():
    if len(sys.argv) != 3:
        print("Usage: python3 compare_hypervisor_vectors.py <linux_snapshot.json> <sel4_snapshot.json>")
        print("\nExample:")
        print("  python3 compare_hypervisor_vectors.py \\")
        print("    linux_kvm_exception_vectors_20250118_143022.json \\")
        print("    /home/konton-otome/phd/research-docs/analysis/sel4_vm_exception_vectors.json")
        return
    
    linux_file = sys.argv[1]
    sel4_file = sys.argv[2]
    
    # Verify files exist
    if not Path(linux_file).exists():
        print(f"❌ Linux snapshot file not found: {linux_file}")
        return
    
    if not Path(sel4_file).exists():
        print(f"❌ seL4 snapshot file not found: {sel4_file}")
        return
    
    # Perform comparison
    result = compare_snapshots(linux_file, sel4_file)
    
    if result:
        print("\n✅ Comparison analysis complete - hypothesis confirmed!")
    else:
        print("\n⚠️ Comparison complete - further investigation needed")

if __name__ == "__main__":
    main()