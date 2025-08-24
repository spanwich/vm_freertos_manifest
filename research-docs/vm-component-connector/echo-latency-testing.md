# VM-Component Echo Latency Testing

## Overview

A simple echo component has been created to test VM-to-component communication latency and verify connection reliability. This provides a minimal overhead test to measure the baseline performance of CAmkES cross-VM connectors.

## EchoComponent Architecture

### Component Design
```
Linux VM Guest → Cross-VM Connectors → EchoComponent → SerialServer → Console
     ↑                                       ↓
  Test Client ←──────── Echo Response ────────┘
```

### Key Features
- **Minimal Processing**: Simply echoes data back with small prefix
- **Latency Measurement**: Built-in timing using CAmkES Timer interface
- **Serial Logging**: All activity logged via SerialServer
- **Performance Monitoring**: Tracks average processing time

## Implementation Details

### EchoComponent Interfaces
```camkes
component EchoComponent {
    uses PutChar serial_output;        // Output to SerialServer
    dataport Buf(4096) data;           // Shared memory with VM
    consumes DoPrint do_print;         // Event from VM
    emits DonePrinting done_printing;  // Event to VM
    uses Timer timer;                  // For latency measurement
}
```

### Communication Protocol
1. **VM writes message** to shared dataport
2. **VM emits DoPrint event** to EchoComponent
3. **EchoComponent receives event**, records timestamp
4. **EchoComponent processes data** (adds "ECHO[n]: " prefix)
5. **EchoComponent logs timing info** via SerialServer
6. **EchoComponent emits DonePrinting event** back to VM
7. **VM receives completion event** and reads echoed result

### Latency Measurement Features
- **Nanosecond precision** using Timer interface
- **Per-message timing** for individual latency measurement
- **Running average** calculation for ongoing performance monitoring
- **Message counter** for tracking throughput

## Test Clients

### 1. Basic Test Client (`test_client`)
- **Purpose**: Verify basic connectivity and communication
- **Test**: Sends 5 test messages and verifies echo responses
- **Usage**: `/usr/bin/test_client`

### 2. Latency Benchmark (`echo_latency_test`)
- **Purpose**: Comprehensive latency and performance measurement
- **Features**:
  - **Multiple message sizes**: 16, 64, 256, 1024, 4000 bytes
  - **Warmup phase**: 10 warmup messages per size
  - **Measurement phase**: 100 latency measurements per size
  - **Statistics**: Min/Max/Average latency, throughput calculation
  - **Stability test**: 30-second continuous communication test

### Test Results Expected

#### Latency Metrics
```
=== 16 byte messages Results ===
Samples: 100
Min latency: X ns (X.X μs)
Max latency: Y ns (Y.Y μs) 
Avg latency: Z ns (Z.Z μs)
Throughput: N.N messages/sec
```

#### Performance Characteristics
- **Small messages (16-64 bytes)**: Lowest latency, highest relative overhead
- **Medium messages (256 bytes)**: Good balance of latency vs throughput
- **Large messages (1-4KB)**: Higher latency but better data efficiency
- **Stability**: Consistent performance over extended periods

## Build Configuration

### Files Added
```
vm_serial_test/
├── components/EchoComponent/
│   ├── EchoComponent.camkes           # Component definition
│   ├── src/echo_component.c           # Implementation
│   └── CMakeLists.txt                 # Build config
├── vm_echo_test.camkes                # Assembly with EchoComponent
├── vm_guest_test/
│   ├── echo_latency_test.c            # Latency benchmark
│   └── run_benchmarks.sh              # Test automation
└── CMakeLists.txt                     # Updated build system
```

### Build Commands

#### Build vm_echo_test
```bash
cd camkes-vm-examples
mkdir build_echo && cd build_echo
source ../../sel4-dev-env/bin/activate && \
export PYTHONPATH=/home/konton-otome/phd/camkes-vm-examples/projects/camkes-tool:/home/konton-otome/phd/camkes-vm-examples/projects/capdl/python-capdl-tool && \
../init-build.sh -DCAMKES_VM_APP=vm_echo_test -DPLATFORM=qemu-arm-virt -DSIMULATION=1 -DLibUSB=OFF && \
ninja
```

**Note**: The folder structure is critical:
- Build system looks for `apps/Arm/${CAMKES_VM_APP}/` folder
- Must contain `settings.cmake` and `vm_echo_test.camkes` files
- Folder was renamed from `vm_serial_test` to `vm_echo_test` to match the application name

#### Run Tests
```bash
./simulate

# Inside VM:
/usr/bin/run_benchmarks.sh
```

## Expected Console Output

### EchoComponent Startup
```
EchoComponent: Started - ready for latency testing
EchoComponent: Will echo all received messages with timing info
```

### Per-Message Processing
```
EchoComponent[1]: Received 23 bytes from VM
EchoComponent[1]: Processing time: 1234 ns, Avg: 1234 ns
EchoComponent[2]: Received 25 bytes from VM  
EchoComponent[2]: Processing time: 1156 ns, Avg: 1195 ns
```

### VM Test Output
```
Echo Latency Test: Starting VM-to-Component communication benchmark
Testing round-trip latency with various message sizes

--- Testing 16 byte messages ---
Running 10 warmup tests...
Running 100 latency measurements...
Completed 20/100 tests
...
=== 16 byte messages Results ===
Samples: 100
Min latency: 1234 ns (1.234 μs)
Max latency: 5678 ns (5.678 μs)
Avg latency: 2345 ns (2.345 μs)
Throughput: 426.44 messages/sec
```

## Performance Analysis

### Latency Components
1. **VM syscall overhead**: ioctl() for event emission/waiting
2. **Cross-VM connector latency**: CAmkES-generated communication code
3. **Component processing time**: EchoComponent callback execution
4. **SerialServer logging**: Optional logging overhead
5. **Memory copy operations**: Dataport read/write operations

### Optimization Opportunities
1. **Remove serial logging** for pure latency measurement
2. **Batch operations** for higher throughput testing
3. **Different message patterns** (sequential vs random data)
4. **CPU affinity** configuration for deterministic timing

## Research Applications

### Baseline Measurements
- **Cross-VM Communication Overhead**: Quantify CAmkES connector performance
- **Scalability Analysis**: How latency changes with message size
- **System Load Impact**: Performance under different conditions

### Comparison Studies
- **Direct Hardware Access** vs **Mediated Access** (SerialServer)
- **CAmkES Connectors** vs **Other IPC Mechanisms**
- **seL4 Performance** vs **Other Hypervisors**

### Security Research
- **Information Flow Timing**: Verify no timing side-channels
- **Capability Overhead**: Cost of capability-based security
- **Isolation Verification**: Confirm VM cannot bypass component

## Future Enhancements

### Additional Test Scenarios
1. **Multi-threaded clients** for concurrency testing
2. **Stress testing** with high message rates
3. **Error injection** for reliability testing
4. **Real-time analysis** with deadline monitoring

### Advanced Metrics
1. **Jitter measurement** for real-time systems
2. **Throughput vs latency** trade-off analysis
3. **Memory usage** profiling
4. **CPU utilization** monitoring

This echo component provides a solid foundation for understanding VM-to-component communication performance in the seL4/CAmkES environment and serves as a baseline for more complex communication patterns in your research.