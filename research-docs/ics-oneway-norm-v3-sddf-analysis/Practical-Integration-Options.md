# Practical sDDF + CAmkES Integration Options

## Your Requirement
**"I need sDDF, integrate with our existing ics_oneway_norm. What can I do now? Can I reduce them to single framework?"**

## The Reality Check

**Short Answer**: You **cannot** reduce them to a single framework - they are architecturally incompatible. However, there are **3 practical integration strategies** that can work.

## Option 1: Extract sDDF Network Code (RECOMMENDED)

### Concept: Use sDDF algorithms in CAmkES components

**Approach**: Study sDDF's efficient network handling and implement similar patterns within CAmkES framework.

**Why This Works**:
- sDDF network drivers are **just C code** with good algorithms
- CAmkES can **incorporate external C libraries** (like lwip)
- We keep your existing ICS pipeline **unchanged**
- We get sDDF's network efficiency **without** framework change

### Implementation Strategy:

#### Step 1: Extract Key sDDF Components
```bash
# Copy sDDF network code for study
mkdir /home/iamfo470/phd/camkes-vm-examples/projects/vm-examples/apps/Arm/ics_oneway_norm_v2_sddf_inspired/
cd /home/iamfo470/phd/camkes-vm-examples/projects/vm-examples/apps/Arm/ics_oneway_norm_v2_sddf_inspired/

# Copy sDDF networking components
cp /home/iamfo470/phd/sDDF/drivers/network/virtio/ethernet.c ./sddf_study/
cp /home/iamfo470/phd/sDDF/network/components/virt_rx.c ./sddf_study/
cp /home/iamfo470/phd/sDDF/network/components/virt_tx.c ./sddf_study/
cp /home/iamfo470/phd/sDDF/include/sddf/network/queue.h ./sddf_study/
```

#### Step 2: Create CAmkES Network Driver Based on sDDF
```c
// NetworkDriverDrv.c - CAmkES component using sDDF algorithms
#include <camkes.h>
#include "sddf_queue_algorithms.h"  // Extracted from sDDF
#include "ring_buffer.h"            // Our existing format

// Hardware access (like sDDF ethernet.c)
void virtio_net_rx_handler(void) {
    // Use sDDF's efficient virtio handling
    struct virtio_net_hdr *hdr;
    uint8_t *frame_data;

    while (virtio_net_get_frame(&hdr, &frame_data)) {
        // Convert to our ICS pipeline format
        MsgHeader ics_msg = sddf_frame_to_ics(frame_data);

        // Forward to existing pipeline
        rb_write(output_buffer, &ics_msg, frame_data);
        ext_frontend_emit();
    }
}

// Component definition
component NetworkDriverDrv {
    hardware;                    // Direct hardware access like sDDF
    provides EthInterface eth;   // Interface to ICS pipeline
    dataport Buf output_buffer;  // To existing ExtFrontend
    emits Signal ext_frontend;   // Existing pipeline integration
    consumes HardwareInterrupt eth_irq;
}
```

#### Step 3: Integrate with Existing Pipeline
```c
// Your existing components unchanged:
// ExtFrontend.c, ParserNorm.c, PolicyEmit.c, IntNicDrv.c

// Only replace:
// OLD: VM → VirtQueue → NetworkNicDrv → ExtFrontend
// NEW: Hardware → sDDF-inspired NetworkDriverDrv → ExtFrontend
```

#### Step 4: CAmkES Assembly
```c
// icf_sddf_inspired.camkes
assembly {
    composition {
        // New sDDF-inspired network driver
        component NetworkDriverDrv net_drv;

        // Existing ICS pipeline (unchanged)
        component ExtFrontend ext_fe;
        component ParserNorm parser;
        component PolicyEmit policy;
        component IntNicDrv int_drv;

        // Connections (mostly unchanged)
        connection seL4SharedData net_to_ext(from net_drv.output_buffer, to ext_fe.input_buffer);
        connection seL4Notification net_signal(from net_drv.ext_frontend, to ext_fe.input_signal);
        // ... rest of existing pipeline connections
    }
    configuration {
        // Hardware access for network driver
        net_drv.eth_irq_irq_type = "pci";
        net_drv.eth_irq_irq_number = 79;  // virtio-net interrupt
        net_drv.simple_untyped23_pool = 8;  // Reasonable memory allocation
    }
}
```

### Advantages:
- ✅ **Keep all existing ICS code**
- ✅ **Solve VirtIO memory issues** with sDDF algorithms
- ✅ **Single framework** (CAmkES only)
- ✅ **Direct hardware access** (no VM needed)
- ✅ **Manageable implementation** (2-3 weeks)

### Implementation Timeline:
- **Week 1**: Study sDDF network code, extract algorithms
- **Week 2**: Implement CAmkES network driver component
- **Week 3**: Integration testing with existing pipeline

## Option 2: Hybrid System Architecture

### Concept: Two separate systems communicating externally

**Approach**: Run sDDF (Microkit) and your ICS pipeline (CAmkES) as separate systems that communicate via network/files.

```
┌─────────────────────┐    ┌─────────────────────┐
│   sDDF System       │    │   CAmkES System     │
│   (Microkit)        │    │   (Your ICS)        │
├─────────────────────┤    ├─────────────────────┤
│ • External Network  │    │ • ExtFrontend       │
│ • eth_driver        │    │ • ParserNorm        │
│ • Frame processing  │◄──►│ • PolicyEmit        │
│ • Internal Network  │    │ • IntNicDrv         │
└─────────────────────┘    └─────────────────────┘
       sDDF Image              CAmkES Image
```

#### Implementation:
```bash
# Terminal 1: Run sDDF network processor
cd /home/iamfo470/phd/sDDF/examples/echo_server
make BUILD_DIR=build MICROKIT_SDK=<path> MICROKIT_CONFIG=debug
qemu-system-aarch64 -machine virt -device virtio-net-device -netdev tap,id=net0,ifname=tap0 \
  -device loader,file=build/loader.img,addr=0x70000000 -m 2G -nographic

# Terminal 2: Run CAmkES ICS pipeline
cd /home/iamfo470/phd/camkes-vm-examples/build
qemu-system-aarch64 -machine virt -device virtio-net-device -netdev tap,id=net1,ifname=tap1 \
  -kernel images/capdl-loader-image-arm-qemu-arm-virt -m 2G -nographic

# Bridge between systems via host networking
sudo ip link add name br0 type bridge
sudo ip link set tap0 master br0
sudo ip link set tap1 master br0
```

### Advantages:
- ✅ **Use sDDF as designed** (full Microkit system)
- ✅ **Keep existing CAmkES work** completely unchanged
- ✅ **Independent development** of both parts
- ✅ **Best of both frameworks**

### Disadvantages:
- ❌ **Complex QEMU setup** (dual systems)
- ❌ **External communication overhead**
- ❌ **More complex testing**

## Option 3: Sequential Migration Strategy

### Concept: Migrate incrementally from CAmkES to Microkit

**Phase 1**: Keep CAmkES, fix immediate VirtIO issues
**Phase 2**: Port one component at a time to Microkit
**Phase 3**: Complete Microkit+sDDF system

#### Phase 1 (Immediate - 1-2 weeks):
```c
// Fix VirtIO issues in existing CAmkES system
// Replace VM approach with direct network access
component DirectNetworkDrv {
    hardware;
    // Use simpler memory allocation (not 256MB VirtQueues)
}
```

#### Phase 2 (Medium term - 1-2 months):
```bash
# Port components incrementally
1. Create Microkit version of PolicyEmit (simplest component)
2. Create Microkit version of ParserNorm
3. Create Microkit version of ExtFrontend
4. Create Microkit NetworkNicDrv with sDDF integration
5. Test each component individually
```

#### Phase 3 (Long term - 2-3 months):
```xml
<!-- Complete Microkit+sDDF system -->
<system>
    <!-- sDDF network infrastructure -->
    <protection_domain name="eth_driver">
        <program_image path="eth_driver.elf" />
    </protection_domain>

    <!-- Your ICS pipeline in Microkit -->
    <protection_domain name="network_nic_drv">
        <program_image path="network_nic_drv.elf" />
    </protection_domain>
    <protection_domain name="ext_frontend">
        <program_image path="ext_frontend.elf" />
    </protection_domain>
    <!-- etc. -->
</system>
```

## Recommendation: Option 1 (sDDF-Inspired CAmkES)

### Why Option 1 is Best for Your Situation:

1. **Immediate Results**: Working system in 2-3 weeks
2. **Preserve Investment**: Keep all existing ICS pipeline code
3. **Solve Core Problem**: Eliminate VirtIO memory limitations
4. **Single Framework**: No complex multi-system setup
5. **Incremental**: Can always migrate to full Microkit later

### Concrete Next Steps:

#### Day 1-2: Study sDDF Network Code
```bash
# Extract and analyze sDDF algorithms
cd /home/iamfo470/phd/camkes-vm-examples/projects/vm-examples/apps/Arm/
mkdir ics_oneway_norm_v2_sddf_inspired
cd ics_oneway_norm_v2_sddf_inspired

# Copy for analysis
cp -r /home/iamfo470/phd/sDDF/drivers/network/virtio/* ./sddf_study/
cp -r /home/iamfo470/phd/sDDF/network/components/* ./sddf_study/
cp -r /home/iamfo470/phd/sDDF/include/sddf/network/* ./sddf_study/

# Study how sDDF handles:
# 1. Virtio-net hardware access
# 2. Efficient buffer management
# 3. Queue algorithms
# 4. Memory allocation patterns
```

#### Day 3-5: Implement CAmkES Network Driver
```c
// Create NetworkDriverDrv.c based on sDDF patterns
// Integrate with your existing ring buffer and message format
// Test basic frame reception
```

#### Day 6-8: Integration with Existing Pipeline
```c
// Connect new driver to existing ExtFrontend
// Test complete pipeline with real network traffic
// Performance optimization
```

#### Day 9-10: Testing and Validation
```bash
# End-to-end testing
echo "READ_COILS_0001_16" | nc <external_ip> 502
# Verify output on internal network

# Multi-protocol testing
# Security validation
# Performance benchmarking
```

## Implementation Code Templates

### CAmkES Component (NetworkDriverDrv.c):
```c
#include <camkes.h>
#include <virtqueue.h>
#include <platsupport/io.h>

// Hardware access (based on sDDF)
static ps_io_ops_t io_ops;
static virtio_net_t virtio_net;

void pre_init(void) {
    // Initialize hardware access
    camkes_io_ops(&io_ops);
    virtio_net_init(&virtio_net, &io_ops, VIRTIO_NET_BASE_ADDR);
}

void eth_irq_handle(void) {
    // Handle network interrupts (sDDF algorithm)
    while (virtio_net_has_frame(&virtio_net)) {
        uint8_t frame_data[1500];
        size_t frame_len = virtio_net_get_frame(&virtio_net, frame_data);

        // Convert to ICS format (your existing logic)
        MsgHeader header = parse_ethernet_to_ics(frame_data, frame_len);

        // Forward to existing pipeline (your existing interface)
        rb_write(output_buffer, &header, frame_data);
        ext_frontend_emit();
    }
}
```

### Build Integration (CMakeLists.txt):
```cmake
# Add sDDF-inspired network driver to your build
DeclareCAmkESComponent(
    NetworkDriverDrv
    SOURCES
    components/NetworkDriverDrv/NetworkDriverDrv.c
    sddf_study/virtio_algorithms.c  # Extracted sDDF code
    INCLUDES
    sddf_study/
    LIBS
    virtqueue
    platsupport
)
```

This approach gives you **sDDF network efficiency within your existing CAmkES framework** - the best of both worlds without the complexity of dual frameworks.