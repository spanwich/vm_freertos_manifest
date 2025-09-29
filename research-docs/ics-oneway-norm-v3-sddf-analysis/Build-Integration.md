# sDDF + ICS Build System Integration

## Current Echo Server Build Process

### 1. Component Building (echo.mk lines 29-30)
```makefile
IMAGES := eth_driver.elf lwip.elf benchmark.elf idle.elf network_virt_rx.elf\
	  network_virt_tx.elf copy.elf timer_driver.elf uart_driver.elf serial_virt_tx.elf
```

### 2. System Assembly (echo.mk lines 89-90)
```makefile
$(MICROKIT_TOOL) $(SYSTEM_FILE) --search-path $(BUILD_DIR) --board $(MICROKIT_BOARD) \
  --config $(MICROKIT_CONFIG) -o $(IMAGE_FILE) -r $(REPORT_FILE)
```

**Key Insight**: Each component is built as a separate `.elf` file, then Microkit assembles them into one system image.

## ICS Integration Plan

### Replace Single `lwip.elf` with Multiple ICS Components

#### Current (echo_server.system):
```xml
<protection_domain name="client0" priority="97" budget="20000" id="6">
    <program_image path="lwip.elf" />
    <!-- ... -->
</protection_domain>
<protection_domain name="client1" priority="95" budget="20000" id="7">
    <program_image path="lwip.elf" />
    <!-- ... -->
</protection_domain>
```

#### New (ics_gateway.system):
```xml
<protection_domain name="network_nic_drv" priority="98" budget="20000" id="4">
    <program_image path="network_nic_drv.elf" />
    <!-- ... -->
</protection_domain>
<protection_domain name="ext_frontend" priority="97" budget="20000" id="6">
    <program_image path="ext_frontend.elf" />
    <!-- ... -->
</protection_domain>
<protection_domain name="parser_norm" priority="96" budget="20000" id="7">
    <program_image path="parser_norm.elf" />
    <!-- ... -->
</protection_domain>
<protection_domain name="policy_emit" priority="95" budget="20000" id="8">
    <program_image path="policy_emit.elf" />
    <!-- ... -->
</protection_domain>
<protection_domain name="int_nic_drv" priority="94" budget="20000" id="9">
    <program_image path="int_nic_drv.elf" />
    <!-- ... -->
</protection_domain>
```

## Step-by-Step Build Integration

### Step 1: Copy and Modify Echo Server Structure
```bash
# Copy echo server as base
cp -r /home/iamfo470/phd/sDDF/examples/echo_server ./ics_gateway_sddf
cd ics_gateway_sddf

# Copy our existing ICS components
cp -r /home/iamfo470/phd/camkes-vm-examples/projects/vm-examples/apps/Arm/ics_oneway_norm/components/* ./components/
```

### Step 2: Create ICS Makefile (ics.mk)
```makefile
#
# ICS Gateway Makefile - Based on echo.mk
#

QEMU := qemu-system-aarch64

# sDDF infrastructure (unchanged from echo.mk)
MICROKIT_TOOL ?= $(MICROKIT_SDK)/bin/microkit
ICS_SERVER:=${SDDF}/examples/ics_gateway_sddf
BENCHMARK:=$(SDDF)/benchmark
UTIL:=$(SDDF)/util
ETHERNET_DRIVER:=$(SDDF)/drivers/network/$(DRIV_DIR)
ETHERNET_CONFIG_INCLUDE:=${ICS_SERVER}/include/ethernet_config
SERIAL_COMPONENTS := $(SDDF)/serial/components
UART_DRIVER := $(SDDF)/drivers/serial/$(UART_DRIV_DIR)
SERIAL_CONFIG_INCLUDE:=${ICS_SERVER}/include/serial_config
TIMER_DRIVER:=$(SDDF)/drivers/timer/$(TIMER_DRV_DIR)
NETWORK_COMPONENTS:=$(SDDF)/network/components

BOARD_DIR := $(MICROKIT_SDK)/board/$(MICROKIT_BOARD)/$(MICROKIT_CONFIG)
SYSTEM_FILE := ${ICS_SERVER}/board/$(MICROKIT_BOARD)/ics_gateway.system
IMAGE_FILE := loader.img
REPORT_FILE := report.txt

vpath %.c ${SDDF} ${ICS_SERVER}

# REPLACE lwip.elf with ICS pipeline components
IMAGES := eth_driver.elf network_nic_drv.elf ext_frontend.elf parser_norm.elf \
          policy_emit.elf int_nic_drv.elf benchmark.elf idle.elf \
          network_virt_rx.elf network_virt_tx.elf copy.elf \
          timer_driver.elf uart_driver.elf serial_virt_tx.elf

CFLAGS := -mcpu=$(CPU) \
	  -mstrict-align \
	  -ffreestanding \
	  -g3 -O3 -Wall \
	  -Wno-unused-function \
	  -DMICROKIT_CONFIG_$(MICROKIT_CONFIG) \
	  -I$(BOARD_DIR)/include \
	  -I$(SDDF)/include \
	  -I${ICS_SERVER}/include \
	  -I${ICS_SERVER}/components/shared \
	  -I${ETHERNET_CONFIG_INCLUDE} \
	  -I$(SERIAL_CONFIG_INCLUDE) \
	  -MD \
	  -MP

LDFLAGS := -L$(BOARD_DIR)/lib -L${LIBC}
LIBS := --start-group -lmicrokit -Tmicrokit.ld -lc libsddf_util_debug.a --end-group

CHECK_FLAGS_BOARD_MD5:=.board_cflags-$(shell echo -- ${CFLAGS} ${BOARD} ${MICROKIT_CONFIG} | shasum | sed 's/ *-//')

${CHECK_FLAGS_BOARD_MD5}:
	-rm -f .board_cflags-*
	touch $@

%.elf: %.o
	$(LD) $(LDFLAGS) $< $(LIBS) -o $@

# ICS Component Build Rules
network_nic_drv.o: components/NetworkNicDrv/NetworkNicDrv.c
	$(CC) $(CFLAGS) -c $< -o $@

ext_frontend.o: components/ExtFrontend/ExtFrontend.c
	$(CC) $(CFLAGS) -c $< -o $@

parser_norm.o: components/ParserNorm/ParserNorm.c
	$(CC) $(CFLAGS) -c $< -o $@

policy_emit.o: components/PolicyEmit/PolicyEmit.c
	$(CC) $(CFLAGS) -c $< -o $@

int_nic_drv.o: components/IntNicDrv/IntNicDrv.c
	$(CC) $(CFLAGS) -c $< -o $@

# Link ICS components
network_nic_drv.elf: network_nic_drv.o libsddf_util_debug.a
	$(LD) $(LDFLAGS) $^ $(LIBS) -o $@

ext_frontend.elf: ext_frontend.o libsddf_util_debug.a
	$(LD) $(LDFLAGS) $^ $(LIBS) -o $@

parser_norm.elf: parser_norm.o libsddf_util_debug.a
	$(LD) $(LDFLAGS) $^ $(LIBS) -o $@

policy_emit.elf: policy_emit.o libsddf_util_debug.a
	$(LD) $(LDFLAGS) $^ $(LIBS) -o $@

int_nic_drv.elf: int_nic_drv.o libsddf_util_debug.a
	$(LD) $(LDFLAGS) $^ $(LIBS) -o $@

all: loader.img

# Need to build libsddf_util_debug.a because it's included in LIBS
${IMAGES}: libsddf_util_debug.a

${IMAGE_FILE} $(REPORT_FILE): $(IMAGES) $(SYSTEM_FILE)
	$(MICROKIT_TOOL) $(SYSTEM_FILE) --search-path $(BUILD_DIR) --board $(MICROKIT_BOARD) --config $(MICROKIT_CONFIG) -o $(IMAGE_FILE) -r $(REPORT_FILE)

# Include sDDF build rules (unchanged)
include ${SDDF}/util/util.mk
include ${SDDF}/network/components/network_components.mk
include ${ETHERNET_DRIVER}/eth_driver.mk
include ${BENCHMARK}/benchmark.mk
include ${TIMER_DRIVER}/timer_driver.mk
include ${UART_DRIVER}/uart_driver.mk
include ${SERIAL_COMPONENTS}/serial_components.mk

qemu: $(IMAGE_FILE)
	$(QEMU) -machine virt,virtualization=on \
			-cpu cortex-a53 \
			-serial mon:stdio \
			-device loader,file=$(IMAGE_FILE),addr=0x70000000,cpu-num=0 \
			-m size=2G \
			-nographic \
			-device virtio-net-device,netdev=netdev0 \
			-device virtio-net-device,netdev=netdev1 \
			-netdev tap,id=netdev0,ifname=tap0,script=no \
			-netdev tap,id=netdev1,ifname=tap1,script=no \
			-global virtio-mmio.force-legacy=false \
			-d guest_errors

clean::
	${RM} -f *.elf .depend* $
	find . -name \*.[do] |xargs --no-run-if-empty rm

clobber:: clean
	rm -f *.a
	rm -f ${IMAGE_FILE} ${REPORT_FILE}
```

### Step 3: Adapt ICS Components for Microkit

#### NetworkNicDrv.c - Microkit Integration
```c
// Based on existing NetworkNicDrv.c but adapted for Microkit instead of CAmkES

#include <microkit.h>
#include <sddf/network/queue.h>
#include "ring_buffer.h"
#include "message_format.h"

// sDDF input interface (from network stack)
extern void *sddf_rx_free;
extern void *sddf_rx_active;
extern void *buffer_data_region;

// ICS pipeline output interface
static RingBuffer *ics_output_buffer;

void init(void) {
    // Initialize sDDF network interface
    sddf_network_init();

    // Initialize ICS output buffer
    ics_output_buffer = (RingBuffer*)microkit_lookup("ics_pipeline_buffer_0");
    rb_init(ics_output_buffer, 4096);

    microkit_dbg_puts("NetworkNicDrv: Initialized\n");
}

void notified(microkit_channel ch) {
    switch (ch) {
    case 0: // sDDF network frame available
        handle_network_frames();
        break;
    default:
        microkit_dbg_puts("NetworkNicDrv: Unexpected notification\n");
    }
}

static void handle_network_frames(void) {
    struct net_buff *frame;

    while ((frame = sddf_net_queue_dequeue(sddf_rx_active)) != NULL) {
        // Parse ethernet frame (existing logic)
        if (parse_ethernet_to_ics(frame)) {
            MsgHeader header = {
                .protocol_tag = detected_protocol,
                .len = payload_len,
                .timestamp = microkit_timer_now()
            };

            // Forward to ICS pipeline
            if (rb_write(ics_output_buffer, &header, payload_data)) {
                microkit_notify(EXT_FRONTEND_CHANNEL);
            }
        }

        // Return buffer to sDDF
        sddf_net_buffer_free(frame);
    }
}
```

#### ExtFrontend.c - Microkit Integration
```c
// Minimal changes from CAmkES version

#include <microkit.h>
#include "ring_buffer.h"
#include "message_format.h"

static RingBuffer *input_buffer;
static RingBuffer *output_buffer;

void init(void) {
    input_buffer = (RingBuffer*)microkit_lookup("ics_pipeline_buffer_0");
    output_buffer = (RingBuffer*)microkit_lookup("ics_pipeline_buffer_1");

    microkit_dbg_puts("ExtFrontend: Initialized\n");
}

void notified(microkit_channel ch) {
    switch (ch) {
    case 0: // Input from NetworkNicDrv
        handle_input_messages();
        break;
    default:
        microkit_dbg_puts("ExtFrontend: Unexpected notification\n");
    }
}

static void handle_input_messages(void) {
    MsgHeader header;
    uint8_t payload[MAX_PAYLOAD_SIZE];

    while (rb_peek_header(input_buffer, &header) > 0) {
        size_t payload_len = rb_peek_payload(input_buffer, payload, sizeof(payload));

        // Same validation logic as CAmkES version
        if (validate_message(&header, payload, payload_len)) {
            if (rb_write(output_buffer, &header, payload)) {
                microkit_notify(PARSER_NORM_CHANNEL);
            }
        }

        rb_consume(input_buffer);
    }
}
```

### Step 4: Build Process

#### 1. Build individual components
```bash
# Each component builds to separate .elf file
make network_nic_drv.elf
make ext_frontend.elf
make parser_norm.elf
make policy_emit.elf
make int_nic_drv.elf

# Plus sDDF infrastructure
make eth_driver.elf
make network_virt_rx.elf
make network_virt_tx.elf
# etc.
```

#### 2. Microkit assembles final system
```bash
# All .elf files combined into single bootable image
$(MICROKIT_TOOL) ics_gateway.system --search-path $(BUILD_DIR) \
  --board qemu_virt_aarch64 --config debug -o loader.img -r report.txt
```

#### 3. QEMU boots the complete system
```bash
qemu-system-aarch64 -machine virt,virtualization=on \
  -device loader,file=loader.img,addr=0x70000000,cpu-num=0 \
  -device virtio-net-device,netdev=netdev0 \
  -device virtio-net-device,netdev=netdev1 \
  -netdev tap,id=netdev0,ifname=tap0,script=no \
  -netdev tap,id=netdev1,ifname=tap1,script=no
```

## Directory Structure After Integration

```
ics_gateway_sddf/
├── Makefile                           # Calls ics.mk
├── ics.mk                             # Build rules for ICS components
├── board/
│   └── qemu_virt_aarch64/
│       └── ics_gateway.system         # Modified from echo_server.system
├── components/
│   ├── NetworkNicDrv/
│   │   └── NetworkNicDrv.c           # Microkit version (not CAmkES)
│   ├── ExtFrontend/
│   │   └── ExtFrontend.c             # Microkit version
│   ├── ParserNorm/
│   │   └── ParserNorm.c              # Microkit version
│   ├── PolicyEmit/
│   │   └── PolicyEmit.c              # Microkit version
│   ├── IntNicDrv/
│   │   └── IntNicDrv.c               # Microkit version
│   └── shared/
│       ├── ring_buffer.h             # Shared between components
│       ├── message_format.h          # ICS message format
│       └── ics_protocols.h           # Protocol definitions
├── include/
│   ├── ethernet_config/              # From echo_server
│   └── serial_config/                # From echo_server
└── build/                            # Build output
    ├── network_nic_drv.elf
    ├── ext_frontend.elf
    ├── parser_norm.elf
    ├── policy_emit.elf
    ├── int_nic_drv.elf
    ├── eth_driver.elf               # sDDF components
    ├── network_virt_rx.elf
    ├── network_virt_tx.elf
    └── loader.img                   # Final bootable image
```

## Key Conversion Tasks

### 1. CAmkES → Microkit API
```c
// CAmkES                           // Microkit
#include <camkes.h>           →     #include <microkit.h>
void component_init(void)     →     void init(void)
void interrupt_handle(void)   →     void notified(microkit_channel ch)
dataport Buf dp              →     void *microkit_lookup("region_name")
emit signal()                →     microkit_notify(channel)
```

### 2. Memory Region Access
```c
// CAmkES shared dataports
extern Buf *shared_buffer;

// Microkit memory regions
void *shared_buffer = microkit_lookup("pipeline_buffer_region");
```

### 3. Component Communication
```c
// CAmkES notifications
component_signal_emit();

// Microkit notifications
microkit_notify(NEXT_COMPONENT_CHANNEL);
```

## Build Command Sequence

```bash
# 1. Setup build environment
export MICROKIT_SDK=/path/to/microkit/sdk
export MICROKIT_BOARD=qemu_virt_aarch64
export MICROKIT_CONFIG=debug

# 2. Build all components
make BUILD_DIR=build

# 3. Result: loader.img contains complete system
# - sDDF networking infrastructure
# - ICS security pipeline
# - All properly interconnected

# 4. Boot in QEMU with dual NICs
make qemu
```

## Answer to Your Question

**Q: Can we build them together, or do we need to build ICS pipeline as image first, then put it in sDDF?**

**A: We build them together in one unified build process.**

The process is:
1. **Individual component builds**: Each ICS component (NetworkNicDrv, ExtFrontend, etc.) builds to separate `.elf` files
2. **sDDF infrastructure**: Builds to separate `.elf` files (eth_driver, network_virt_rx, etc.)
3. **Microkit assembly**: All `.elf` files combined into single `loader.img` system image
4. **QEMU boot**: Single image contains complete integrated system

**No separate image building required** - it's all one cohesive build process, just like echo_server but with our ICS components instead of lwip.