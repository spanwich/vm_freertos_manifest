# Implementation Plan: VM-Component UART Communication

## Objective
Implement UART communication between vm_minimal guest and a new CAmkES component using SerialServer mediation.

## Phase 1: Architecture Design

### Step 1.1: Component Architecture
Create new component structure:
```
vm_minimal_with_component/
├── vm_minimal_enhanced.camkes          # Main assembly
├── components/
│   └── UARTProcessor/
│       ├── UARTProcessor.camkes        # Component definition
│       ├── src/
│       │   └── uart_processor.c        # Implementation
│       └── CMakeLists.txt              # Build configuration
└── qemu-arm-virt/
    └── devices.camkes                  # Device configuration
```

### Step 1.2: Interface Design
Define communication interfaces:

```camkes
// UARTProcessor.camkes
component UARTProcessor {
    control;
    provides PutChar response_output;      // Send responses back
    uses PutChar debug_output;             // Debug messages to console
    consumes DataReady vm_data_event;      // Notification from VM
    emits ProcessingDone vm_response_event; // Notify VM of completion
    dataport Buf(4096) shared_buffer;      // Shared memory with VM
}
```

## Phase 2: SerialServer Integration

### Step 2.1: Modify vm_minimal Configuration
Transform direct UART access to SerialServer mediation:

```camkes
// vm_minimal_enhanced.camkes
assembly {
    composition {
        component VM vm0;
        component SerialServer serial;
        component UARTProcessor processor;
        component TimeServer time_server;

        // VM to SerialServer connections
        connection seL4SerialServer serial_vm(from vm0.batch, to serial.processed_batch);
        connection seL4SerialServer serial_input(from vm0.serial_getchar, to serial.getchar);
        
        // Processor to SerialServer connections  
        connection seL4PutChar processor_output(from processor.debug_output, to serial.processed_putchar);
        
        // VM to Processor cross-VM communication
        connection seL4SharedData vm_processor_data(from vm0.shared_buffer, to processor.shared_buffer);
        connection seL4Notification vm_to_processor(from vm0.data_ready, to processor.vm_data_event);
        connection seL4Notification processor_to_vm(from processor.vm_response_event, to vm0.processing_done);
        
        // Timer support
        connection seL4TimeServer serialserver_timer(from serial.timeout, to time_server.the_timer);
        connection seL4VMDTBPassthrough vm_dtb(from vm0.dtb_self, to vm0.dtb);
    }
    
    configuration {
        // VM configuration
        vm0.num_extra_frame_caps = 0;
        vm0.extra_frame_map_address = 0;
        vm0.serial_getchar_shmem_size = 0x1000;
        vm0.batch_shmem_size = 0x1000;
        vm0.shared_buffer_size = 0x1000;
        
        // SerialServer configuration
        time_server.timers_per_client = 1;
        time_server.priority = 255;
        time_server.simple = true;
        
        // Processor configuration
        processor.priority = 200;
        processor.heap_size = 16 * 1024;
    }
}
```

### Step 2.2: Update Device Configuration
Modify device tree and memory mappings:

```camkes
// qemu-arm-virt/devices.camkes
vm0.linux_image_config = {
    "linux_bootcmdline" : "",
    "linux_stdout" : "/virtio@serial",  // Changed from direct PL011
};

// Remove direct UART from device tree, add virtio serial
vm0.dtb = dtb([
    {"path": "/virtio@serial"},
]);
```

## Phase 3: Component Implementation

### Step 3.1: UARTProcessor Component
```c
// src/uart_processor.c
#include <camkes.h>
#include <stdio.h>
#include <string.h>

static char processing_buffer[4096];

void vm_data_event_callback(void) {
    // Data available from VM
    char *vm_data = (char*)shared_buffer;
    size_t data_len = strlen(vm_data);
    
    // Process the data (example: convert to uppercase)
    for (size_t i = 0; i < data_len; i++) {
        processing_buffer[i] = toupper(vm_data[i]);
    }
    processing_buffer[data_len] = '\0';
    
    // Log processing activity
    debug_output_puts("UARTProcessor: Processed data from VM\n");
    
    // Copy result back to shared buffer
    strcpy(vm_data, processing_buffer);
    
    // Notify VM that processing is complete
    vm_response_event_emit();
}

int run(void) {
    debug_output_puts("UARTProcessor: Component started\n");
    
    // Component main loop
    while (1) {
        // Wait for events (handled by generated code)
        seL4_Wait(vm_data_event_notification());
    }
    
    return 0;
}
```

### Step 3.2: VM Guest Integration
Create Linux kernel module or userspace program:

```c
// vm_guest_communicator.c (userspace example)
#include <sys/ioctl.h>
#include <fcntl.h>
#include <unistd.h>
#include <string.h>

#define DATAPORT_DEVICE "/dev/camkes_vm_dataport"
#define EVENT_DEVICE "/dev/camkes_vm_event"

int main() {
    int dataport_fd = open(DATAPORT_DEVICE, O_RDWR);
    int event_fd = open(EVENT_DEVICE, O_RDWR);
    
    char message[] = "Hello from VM!";
    char response[256];
    
    // Write data to shared buffer
    write(dataport_fd, message, strlen(message) + 1);
    
    // Emit event to notify processor
    ioctl(event_fd, EMIT_EVENT, DATA_READY_EVENT);
    
    // Wait for processing completion
    ioctl(event_fd, WAIT_EVENT, PROCESSING_DONE_EVENT);
    
    // Read processed result
    read(dataport_fd, response, sizeof(response));
    
    printf("VM received response: %s\n", response);
    
    close(dataport_fd);
    close(event_fd);
    return 0;
}
```

## Phase 4: Build System Integration

### Step 4.1: CMakeLists.txt Updates
```cmake
# UARTProcessor/CMakeLists.txt
cmake_minimum_required(VERSION 3.16.0)

project(UARTProcessor C)

add_definitions(-DCOMPONENT_NAME=UARTProcessor)

file(GLOB deps src/*.c)

list(APPEND deps
    uart_processor.c
)

DeclareCAmkESComponent(UARTProcessor
    SOURCES ${deps}
    LIBS sel4 sel4camkes
)
```

### Step 4.2: Application CMakeLists.txt
```cmake
# vm_minimal_with_component/CMakeLists.txt
include(${CAMKES_ARM_VM_HELPERS_PATH})

find_package(camkes-arm-vm REQUIRED)
find_package(camkes-vm-linux REQUIRED)
camkes_arm_vm_setup_arm_vm_environment()

# Include UARTProcessor component
add_subdirectory(components/UARTProcessor)

DeclareCAmkESComponent(VM
    SOURCES dummy.c
    LIBS sel4camkes sel4vmmplatsupport sel4arm-vmm UARTProcessor
)

DeclareCAmkESRootserver(vm_minimal_enhanced.camkes)

GenerateCAmkESRootserver()
```

## Phase 5: Testing and Validation

### Step 5.1: Build Verification
```bash
cd camkes-vm-examples
mkdir build_enhanced && cd build_enhanced

# Build with SerialServer integration
source ../../sel4-dev-env/bin/activate && \
export PYTHONPATH=/home/konton-otome/phd/camkes-vm-examples/projects/camkes-tool:/home/konton-otome/phd/camkes-vm-examples/projects/capdl/python-capdl-tool && \
../init-build.sh -DCAMKES_VM_APP=vm_minimal_enhanced -DPLATFORM=qemu-arm-virt -DSIMULATION=1 -DLibUSB=OFF

ninja
```

### Step 5.2: Functional Testing
```bash
# Run in QEMU
./simulate

# Expected output:
# 1. VM boots successfully
# 2. UARTProcessor component starts
# 3. Guest program communicates via shared memory
# 4. Processed data returned to guest
# 5. All communication logged via SerialServer
```

### Step 5.3: Communication Flow Verification
```
Guest Program → Dataport Write → Event Emit → UARTProcessor
      ↑                                            ↓
Response Read ← Event Wait ← Dataport Write ← Processing Complete
```

## Phase 6: Performance Optimization

### Step 6.1: Latency Optimization
- Optimize shared buffer sizes
- Minimize memory copying
- Use efficient event handling

### Step 6.2: Throughput Enhancement
- Implement batch processing
- Use larger dataports for bulk transfers
- Pipeline multiple requests

## Phase 7: Security Validation

### Step 7.1: Capability Verification
- Verify VM cannot access hardware directly
- Confirm all UART access mediated through SerialServer
- Validate component isolation

### Step 7.2: Information Flow Analysis
- Map all communication channels
- Verify no unintended data leakage
- Confirm capability-based access control

## Timeline Estimates

- **Phase 1-2 (Architecture)**: 1-2 weeks
- **Phase 3 (Implementation)**: 2-3 weeks  
- **Phase 4 (Build Integration)**: 1 week
- **Phase 5 (Testing)**: 1-2 weeks
- **Phase 6-7 (Optimization/Security)**: 1-2 weeks

**Total**: 6-10 weeks for complete implementation

## Risk Mitigation

### Technical Risks
- **CAmkES Build Complexity**: Use existing vm_serial_server as reference
- **Cross-VM Connector Issues**: Leverage proven seL4 connector implementations
- **Performance Bottlenecks**: Profile early and optimize incrementally

### Integration Risks  
- **VM Boot Failures**: Test with minimal configuration first
- **Component Communication Failures**: Implement comprehensive logging
- **Hardware Compatibility**: Validate on QEMU before hardware deployment

## Success Criteria

1. ✅ VM boots successfully with SerialServer integration
2. ✅ UARTProcessor component starts and registers interfaces
3. ✅ Guest program establishes cross-VM communication
4. ✅ Bidirectional data transfer works reliably
5. ✅ All UART access properly mediated through SerialServer
6. ✅ System maintains seL4 security properties
7. ✅ Performance acceptable for research applications

## Future Extensions

- **Multiple Components**: Scale to multiple processors
- **Protocol Layers**: Implement higher-level communication protocols  
- **Real-Time Support**: Add deterministic timing guarantees
- **Hardware Deployment**: Validate on ARM development boards