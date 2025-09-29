# sDDF + ICS Pipeline Integration Strategy

## Problem Statement

**Question**: How do we merge existing `ics_oneway_norm` components with sDDF `echo_server`?

**Answer**: Replace the LWIP network stack in echo_server with our ICS security pipeline components.

## Echo Server Architecture Analysis

### Current Echo Server Flow:
```
External Network → eth_driver → net_virt_rx → copy → lwip.elf → net_virt_tx → eth_driver → External Network
```

### Our Target ICS Flow:
```
External Network → eth_driver → net_virt_rx → [ICS Pipeline] → net_virt_tx → eth_driver → Internal Network
```

## Component Mapping

### Echo Server Components → ICS Components

| Echo Server | ICS Equivalent | Function |
|-------------|----------------|----------|
| `eth` (lines 71-85) | `eth_ext_driver` | External network interface |
| `net_virt_rx` (lines 111-123) | `net_ext_virt_rx` | Frame reception |
| `copy0` (lines 125-135) | `NetworkNicDrv` | Frame → ICS message conversion |
| `client0` (lwip.elf) | `ExtFrontend` | First pipeline component |
| `client1` (lwip.elf) | `ParserNorm` | Protocol analysis |
| _New_ | `PolicyEmit` | Security policy |
| _New_ | `IntNicDrv` | Output handler |
| `net_virt_tx` (lines 149-163) | `net_int_virt_tx` | Frame transmission |
| _New_ | `eth_int_driver` | Internal network interface |

## Concrete Integration Steps

### Step 1: Copy Echo Server as Base
```bash
cp -r /home/iamfo470/phd/sDDF/examples/echo_server /home/iamfo470/phd/camkes-vm-examples/projects/vm-examples/apps/Arm/ics_oneway_norm_v3_sddf/
```

### Step 2: Replace LWIP with ICS Components

#### Current echo_server.system (lines 165-180):
```xml
<protection_domain name="client0" priority="97" budget="20000" id="6">
    <program_image path="lwip.elf" />
    <map mr="net_rx_free_cli0" vaddr="0x2_000_000" perms="rw" cached="true" setvar_vaddr="rx_free" />
    <map mr="net_rx_active_cli0" vaddr="0x2_200_000" perms="rw" cached="true" setvar_vaddr="rx_active" />
    <map mr="net_tx_free_cli0" vaddr="0x2_400_000" perms="rw" cached="true" setvar_vaddr="tx_free" />
    <map mr="net_tx_active_cli0" vaddr="0x2_600_000" perms="rw" cached="true" setvar_vaddr="tx_active" />
    <!-- ... -->
</protection_domain>
```

#### New ICS system (replace client0/client1):
```xml
<!-- Replace client0 with ExtFrontend -->
<protection_domain name="ext_frontend" priority="97" budget="20000" id="6">
    <program_image path="ext_frontend.elf" />
    <map mr="net_rx_free_cli0" vaddr="0x2_000_000" perms="rw" cached="true" setvar_vaddr="rx_free" />
    <map mr="net_rx_active_cli0" vaddr="0x2_200_000" perms="rw" cached="true" setvar_vaddr="rx_active" />
    <!-- Add ring buffer for ExtFrontend → ParserNorm -->
    <map mr="pipeline_buffer_1" vaddr="0x3_000_000" perms="rw" cached="true" setvar_vaddr="output_buffer" />
</protection_domain>

<!-- Replace client1 with ParserNorm -->
<protection_domain name="parser_norm" priority="96" budget="20000" id="7">
    <program_image path="parser_norm.elf" />
    <map mr="pipeline_buffer_1" vaddr="0x3_000_000" perms="rw" cached="true" setvar_vaddr="input_buffer" />
    <map mr="pipeline_buffer_2" vaddr="0x3_200_000" perms="rw" cached="true" setvar_vaddr="output_buffer" />
</protection_domain>

<!-- Add PolicyEmit -->
<protection_domain name="policy_emit" priority="95" budget="20000" id="8">
    <program_image path="policy_emit.elf" />
    <map mr="pipeline_buffer_2" vaddr="0x3_200_000" perms="rw" cached="true" setvar_vaddr="input_buffer" />
    <map mr="pipeline_buffer_3" vaddr="0x3_400_000" perms="rw" cached="true" setvar_vaddr="output_buffer" />
</protection_domain>

<!-- Add IntNicDrv -->
<protection_domain name="int_nic_drv" priority="94" budget="20000" id="9">
    <program_image path="int_nic_drv.elf" />
    <map mr="pipeline_buffer_3" vaddr="0x3_400_000" perms="rw" cached="true" setvar_vaddr="input_buffer" />
    <map mr="net_tx_free_cli0" vaddr="0x2_400_000" perms="rw" cached="true" setvar_vaddr="tx_free" />
    <map mr="net_tx_active_cli0" vaddr="0x2_600_000" perms="rw" cached="true" setvar_vaddr="tx_active" />
</protection_domain>
```

### Step 3: Adapt Existing ICS Components

#### NetworkNicDrv → Copy Component Replacement

**Current copy0 component** (lines 125-135):
```xml
<protection_domain name="copy0" priority="98" budget="20000" id="4">
    <program_image path="copy.elf" />
    <map mr="net_rx_free_copy0" vaddr="0x2_000_000" perms="rw" cached="true" setvar_vaddr="rx_free_virt" />
    <map mr="net_rx_active_copy0" vaddr="0x2_200_000" perms="rw" cached="true" setvar_vaddr="rx_active_virt" />
    <map mr="net_rx_free_cli0" vaddr="0x2_400_000" perms="rw" cached="true" setvar_vaddr="rx_free_cli" />
    <map mr="net_rx_active_cli0" vaddr="0x2_600_000" perms="rw" cached="true" setvar_vaddr="rx_active_cli" />
    <!-- ... -->
</protection_domain>
```

**Replace with NetworkNicDrv**:
```xml
<protection_domain name="network_nic_drv" priority="98" budget="20000" id="4">
    <program_image path="network_nic_drv.elf" />
    <!-- Input from sDDF -->
    <map mr="net_rx_free_copy0" vaddr="0x2_000_000" perms="rw" cached="true" setvar_vaddr="sddf_rx_free" />
    <map mr="net_rx_active_copy0" vaddr="0x2_200_000" perms="rw" cached="true" setvar_vaddr="sddf_rx_active" />
    <!-- Output to ICS pipeline -->
    <map mr="net_rx_free_cli0" vaddr="0x2_400_000" perms="rw" cached="true" setvar_vaddr="ics_rx_free" />
    <map mr="net_rx_active_cli0" vaddr="0x2_600_000" perms="rw" cached="true" setvar_vaddr="ics_rx_active" />
    <!-- Ring buffer for pipeline -->
    <map mr="pipeline_buffer_0" vaddr="0x3_000_000" perms="rw" cached="true" setvar_vaddr="pipeline_output" />
</protection_domain>
```

## Code Adaptation Strategy

### NetworkNicDrv.c Integration
```c
// Based on sDDF copy.c but with ICS parsing
#include <sddf/network/queue.h>
#include "ring_buffer.h"     // Our existing ring buffer
#include "message_format.h"  // Our existing MsgHeader

// sDDF input interface (from copy.c)
extern void *sddf_rx_free;
extern void *sddf_rx_active;
extern void *virt_buffer_data_region;

// ICS pipeline output interface (our existing format)
extern RingBuffer *pipeline_output;

void network_frame_notification(void) {
    struct net_buff *frame;

    // Get frame from sDDF (like copy.c)
    while ((frame = sddf_net_queue_dequeue(sddf_rx_active)) != NULL) {
        // Parse ethernet frame to ICS protocol (our logic)
        if (parse_ethernet_to_ics(frame)) {
            MsgHeader header = {
                .protocol_tag = detected_protocol,
                .len = payload_len,
                .timestamp = get_timestamp()
            };

            // Output to ICS pipeline (our existing interface)
            rb_write(pipeline_output, &header, payload_data);
            ext_frontend_notify();
        }

        // Return buffer to sDDF (like copy.c)
        sddf_net_buffer_free(frame);
    }
}
```

### ExtFrontend.c Integration
```c
// Keep existing ExtFrontend logic, just change input source
// Instead of: input from NetworkNicDrv via dataport
// Now: input from NetworkNicDrv via sDDF queue

#include <sddf/network/queue.h>
#include "ring_buffer.h"     // Keep existing

// sDDF input interface
extern void *ics_rx_free;
extern void *ics_rx_active;

// Existing ICS pipeline output
extern RingBuffer *output_buffer;

void ics_message_notification(void) {
    MsgHeader header;

    // Get ICS message from sDDF queue instead of dataport
    while (sddf_queue_peek_header(ics_rx_active, &header) > 0) {
        // Same validation logic as before
        if (validate_message(&header)) {
            rb_write(output_buffer, &header, payload);
            parser_norm_notify();
        }

        sddf_queue_consume(ics_rx_active);
    }
}
```

## File Structure Integration

### Copy sDDF Base
```bash
# Copy echo_server as foundation
cp -r /home/iamfo470/phd/sDDF/examples/echo_server ./ics_sddf_base

# Copy our existing ICS components
cp -r /home/iamfo470/phd/camkes-vm-examples/projects/vm-examples/apps/Arm/ics_oneway_norm/components/* ./ics_sddf_base/
```

### Modified Directory Structure
```
ics_sddf_base/
├── board/qemu_virt_aarch64/
│   └── ics_gateway.system              # Modified from echo_server.system
├── components/                         # Our existing ICS components
│   ├── NetworkNicDrv/
│   │   └── NetworkNicDrv.c            # Modified to use sDDF input
│   ├── ExtFrontend/                   # Minimal changes
│   ├── ParserNorm/                    # No changes
│   ├── PolicyEmit/                    # No changes
│   └── IntNicDrv/
│       └── IntNicDrv.c                # Modified to use sDDF output
├── sddf_integration/                   # New bridge components
│   ├── sddf_to_ics_bridge.c          # NetworkNicDrv sDDF integration
│   └── ics_to_sddf_bridge.c          # IntNicDrv sDDF integration
├── lwip.c                             # Remove (replaced by ICS pipeline)
├── Makefile                           # Modified to build ICS components
└── README.md                          # Integration documentation
```

## Build System Integration

### Modified Makefile
```makefile
# Based on echo_server Makefile but building ICS components
COMPONENTS := network_nic_drv ext_frontend parser_norm policy_emit int_nic_drv

# sDDF dependencies (from echo_server)
include $(SDDF_PATH)/network/components/network_components.mk

# ICS component dependencies (our existing)
network_nic_drv_SOURCES := components/NetworkNicDrv/NetworkNicDrv.c sddf_integration/sddf_to_ics_bridge.c
ext_frontend_SOURCES := components/ExtFrontend/ExtFrontend.c
parser_norm_SOURCES := components/ParserNorm/ParserNorm.c
policy_emit_SOURCES := components/PolicyEmit/PolicyEmit.c
int_nic_drv_SOURCES := components/IntNicDrv/IntNicDrv.c sddf_integration/ics_to_sddf_bridge.c

# Build rules (from echo_server)
include $(MICROKIT_SDK)/mk/microkit.mk
```

## Testing Integration

### Validate sDDF Base Works
```bash
# First, verify echo_server builds and runs
cd /home/iamfo470/phd/sDDF/examples/echo_server
make BUILD_DIR=build MICROKIT_SDK=<path> MICROKIT_CONFIG=debug

# Test basic echo functionality
echo "test" | nc 192.168.100.10 1234
```

### Integrate ICS Components Incrementally
```bash
# Step 1: Replace copy0 with NetworkNicDrv only
# Step 2: Replace client0 with ExtFrontend only
# Step 3: Add ParserNorm, PolicyEmit, IntNicDrv
# Step 4: Test complete ICS pipeline
```

## Key Integration Points

### 1. Data Format Conversion
```c
// sDDF → ICS conversion in NetworkNicDrv
struct net_buff *sddf_frame;  // sDDF format
MsgHeader ics_msg;            // Our ICS format

// ICS → sDDF conversion in IntNicDrv
MsgHeader ics_msg;            // Our ICS format
struct net_buff *sddf_frame;  // sDDF format
```

### 2. Memory Management
```c
// sDDF buffers (2MB regions)
extern void *net_rx_buffer_data_region;

// ICS ring buffers (existing)
extern RingBuffer *pipeline_buffers;
```

### 3. Notification Interface
```c
// sDDF notifications
microkit_notify(NEXT_COMPONENT_ID);

// ICS notifications (existing)
ext_frontend_notify();
parser_norm_notify();
// etc.
```

## Summary

**The integration is absolutely feasible!**

**Key insight**: Echo server's `lwip.elf` components are **exactly equivalent** to our ICS pipeline components. We just replace the network stack with security processing.

**Steps**:
1. **Copy echo_server** as the sDDF foundation
2. **Replace lwip components** with our ExtFrontend, ParserNorm, PolicyEmit, IntNicDrv
3. **Adapt NetworkNicDrv** to receive sDDF frames instead of VM messages
4. **Adapt IntNicDrv** to output sDDF frames instead of console logging
5. **Keep all sDDF networking infrastructure** (eth drivers, virt_rx/tx, memory regions)

This gives us the **exact dual network isolation** you wanted, using **proven sDDF infrastructure**, with **our existing ICS security pipeline**!