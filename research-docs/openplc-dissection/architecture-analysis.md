# OpenPLC v3 Architecture Analysis for Protocol Decoupling

## Executive Summary

This analysis examines the OpenPLC v3 codebase to identify opportunities for decoupling ICS protocol message parsers (Modbus, DNP3, EtherNet/IP, PCCC) from the core control logic. The goal is to create a cleaner separation between communication protocols and the PLC runtime engine.

## Current Architecture Overview

### Core Components Structure

```
OpenPLC_v3/
├── webserver/core/           # Main runtime engine
│   ├── main.cpp              # Control loop and initialization
│   ├── ladder.h              # Core data structures and function prototypes
│   ├── server.cpp            # Generic network server implementation
│   ├── hardware_layers/      # Hardware abstraction layer
│   └── protocol modules:
│       ├── modbus.cpp        # Modbus TCP server
│       ├── modbus_master.cpp # Modbus master/client functionality
│       ├── dnp3.cpp          # DNP3 protocol implementation
│       ├── enip.cpp          # EtherNet/IP protocol implementation
│       └── pccc.cpp          # PCCC protocol implementation
├── utils/                    # External dependencies and utilities
│   ├── libmodbus_src/        # libmodbus library source
│   ├── dnp3_src/             # DNP3 library source (opendnp3)
│   ├── snap7_src/            # Snap7 library for Siemens protocols
│   └── glue_generator_src/   # Code generator for variable binding
└── documentation/            # Project documentation
```

### Control Loop Architecture

The main control loop in `main.cpp:182-237` follows this sequence:

```cpp
while (run_openplc) {
    // 1. Hardware Input Phase
    updateBuffersIn();           // Read physical I/O
    
    // 2. Protocol Input Phase  
    updateBuffersIn_MB();        // Update from Modbus slave devices
    
    // 3. Control Logic Execution
    config_run__(__tick++);      // Execute PLC program logic
    
    // 4. Protocol Output Phase
    updateBuffersOut_MB();       // Update Modbus slave devices
    
    // 5. Hardware Output Phase
    updateBuffersOut();          // Write physical I/O
    
    // 6. Timing Management
    sleep_until(&timer_start, common_ticktime__);
}
```

## Current Protocol Integration Points

### 1. Modbus Integration

**Files:** `modbus.cpp`, `modbus_master.cpp`

**Integration Points:**
- **Data Access:** Direct access to global I/O buffers (`mb_discrete_input[]`, `mb_coils[]`, `mb_input_regs[]`, `mb_holding_regs[]`)
- **Control Loop Integration:** `updateBuffersIn_MB()` and `updateBuffersOut_MB()` called from main loop
- **Network Server:** Dedicated server thread processes Modbus TCP requests
- **Hardware Coupling:** RTS pin control for RS485 (`rpi_modbus_rts_pin`)

**Current Coupling Issues:**
```cpp
// modbus.cpp:78-81 - Global buffer declarations tightly coupled to core
IEC_BOOL mb_discrete_input[MAX_DISCRETE_INPUT];
IEC_BOOL mb_coils[MAX_COILS]; 
IEC_UINT mb_input_regs[MAX_INP_REGS];
IEC_UINT mb_holding_regs[MAX_HOLD_REGS];

// Direct buffer manipulation in protocol handler
// modbus.cpp:450+ - Protocol functions directly modify core buffers
```

### 2. DNP3 Integration

**Files:** `dnp3.cpp`

**Integration Points:**
- **Server Thread:** `dnp3StartServer()` creates separate thread
- **Data Mapping:** Direct access to OpenPLC I/O buffers through custom mapping
- **Library Dependency:** Uses opendnp3 library from `utils/dnp3_src/`

### 3. EtherNet/IP Integration

**Files:** `enip.cpp`

**Integration Points:**
- **Message Processing:** `processEnipMessage()` called from server dispatcher
- **Data Access:** Direct manipulation of I/O buffers
- **Session Management:** Built-in session and connection handling

### 4. PCCC Integration

**Files:** `pccc.cpp`

**Integration Points:**
- **Protocol Handler:** `processPCCCMessage()` for Allen-Bradley PCCC protocol
- **Data Access:** Direct buffer access for tag-based addressing

## Current Data Flow Architecture

### Global I/O Buffer System

Defined in `ladder.h:61-86`:

```cpp
// Core I/O buffers shared across all components
extern IEC_BOOL *bool_input[BUFFER_SIZE][8];     // Digital inputs
extern IEC_BOOL *bool_output[BUFFER_SIZE][8];    // Digital outputs  
extern IEC_BYTE *byte_input[BUFFER_SIZE];        // Byte inputs
extern IEC_BYTE *byte_output[BUFFER_SIZE];       // Byte outputs
extern IEC_UINT *int_input[BUFFER_SIZE];         // Analog inputs
extern IEC_UINT *int_output[BUFFER_SIZE];        // Analog outputs
extern IEC_UDINT *dint_input[BUFFER_SIZE];       // 32-bit I/O
extern IEC_UDINT *dint_output[BUFFER_SIZE];
extern IEC_ULINT *lint_input[BUFFER_SIZE];       // 64-bit I/O
extern IEC_ULINT *lint_output[BUFFER_SIZE];
```

### Variable Binding System

The `glue_generator` creates `glueVars.cpp` which maps IEC 61131-3 program variables to buffer positions:

```cpp
// Generated code example
void glueVars() {
    // Map program variables to I/O buffers
    bool_input[0][0] = &__QX0_0;  // Map output coil
    int_input[0] = &__IW0;        // Map input word
    // ... additional mappings
}
```

## Coupling Analysis

### High Coupling Areas

1. **Direct Buffer Access**: Protocol handlers directly manipulate global I/O buffers
2. **Hardcoded Memory Layout**: Fixed buffer sizes and addressing schemes
3. **Control Loop Integration**: Protocol update functions called directly from main loop
4. **Shared Global State**: Multiple protocols share same buffer space
5. **Hardware Dependencies**: Some protocols have hardware-specific code (RTS pins, etc.)

### Medium Coupling Areas

1. **Network Server Management**: Generic server infrastructure shared
2. **Threading Model**: Each protocol manages its own threads
3. **Configuration**: Protocol-specific configuration mixed with core settings

### Low Coupling Areas

1. **Library Dependencies**: External protocol libraries (libmodbus, opendnp3) are well-encapsulated
2. **Hardware Abstraction**: Hardware layers provide some abstraction

## Decoupling Strategy Recommendations

### 1. Protocol Abstraction Layer

Create a unified protocol interface:

```cpp
// Proposed protocol_interface.h
class ProtocolHandler {
public:
    virtual ~ProtocolHandler() = default;
    virtual void initialize(const ProtocolConfig& config) = 0;
    virtual void start() = 0;
    virtual void stop() = 0;
    virtual void updateInputs() = 0;   // Pull data from protocol into core
    virtual void updateOutputs() = 0;  // Push data from core to protocol
    virtual ProtocolStatus getStatus() = 0;
};
```

### 2. Data Access Layer

Replace direct buffer access with controlled interface:

```cpp
// Proposed data_access.h  
class DataAccessLayer {
public:
    // Read operations
    virtual bool readBool(uint16_t address, uint8_t bit) = 0;
    virtual uint16_t readWord(uint16_t address) = 0;
    virtual uint32_t readDWord(uint16_t address) = 0;
    
    // Write operations  
    virtual void writeBool(uint16_t address, uint8_t bit, bool value) = 0;
    virtual void writeWord(uint16_t address, uint16_t value) = 0;
    virtual void writeDWord(uint16_t address, uint32_t value) = 0;
    
    // Bulk operations
    virtual void readRange(uint16_t start, uint16_t count, void* buffer) = 0;
    virtual void writeRange(uint16_t start, uint16_t count, const void* buffer) = 0;
};
```

### 3. Control Loop Refactoring

Modify main control loop to use protocol abstraction:

```cpp
// Proposed main loop modification
std::vector<std::unique_ptr<ProtocolHandler>> protocol_handlers;

while (run_openplc) {
    // 1. Hardware Input Phase
    updateBuffersIn();
    
    // 2. Protocol Input Phase (decoupled)
    for (auto& handler : protocol_handlers) {
        handler->updateInputs();
    }
    
    // 3. Control Logic Execution  
    config_run__(__tick++);
    
    // 4. Protocol Output Phase (decoupled)
    for (auto& handler : protocol_handlers) {
        handler->updateOutputs();
    }
    
    // 5. Hardware Output Phase
    updateBuffersOut();
    
    // 6. Timing Management
    sleep_until(&timer_start, common_ticktime__);
}
```

### 4. Configuration Management

Separate protocol configuration from core configuration:

```
config/
├── core_config.json          # Core PLC runtime settings
├── protocols/
│   ├── modbus_config.json     # Modbus-specific settings
│   ├── dnp3_config.json       # DNP3-specific settings  
│   ├── enip_config.json       # EtherNet/IP settings
│   └── pccc_config.json       # PCCC settings
└── mappings/
    ├── modbus_mappings.json   # Protocol-specific data mappings
    └── dnp3_mappings.json
```

## Implementation Phases

### Phase 1: Create Abstraction Interfaces
- Define `ProtocolHandler` base class
- Define `DataAccessLayer` interface
- Create protocol registry/factory system

### Phase 2: Refactor Modbus Implementation
- Convert `modbus.cpp` to implement `ProtocolHandler`
- Replace direct buffer access with `DataAccessLayer` calls
- Maintain backward compatibility

### Phase 3: Refactor Remaining Protocols
- Convert DNP3, EtherNet/IP, PCCC to use new interfaces
- Remove direct buffer access from all protocol handlers

### Phase 4: Control Loop Integration
- Modify main control loop to use protocol abstraction
- Remove hardcoded protocol function calls
- Add dynamic protocol loading/unloading

### Phase 5: Configuration Decoupling
- Separate protocol configurations from core configuration
- Implement configuration validation and hot-reloading
- Add protocol-specific diagnostic interfaces

## Benefits of Decoupling

1. **Maintainability**: Protocol implementations become self-contained modules
2. **Extensibility**: New protocols can be added without modifying core runtime
3. **Testing**: Protocol handlers can be unit tested independently
4. **Security**: Controlled data access reduces risk of buffer overruns
5. **Performance**: Protocol-specific optimizations become possible
6. **Deployment**: Protocols can be enabled/disabled without recompilation

## Migration Considerations

1. **Backward Compatibility**: Existing configurations must continue to work
2. **Performance Impact**: Additional abstraction layer may introduce overhead
3. **Memory Usage**: Protocol instances may increase memory footprint
4. **Thread Safety**: Data access layer must handle concurrent protocol access
5. **Error Handling**: Unified error handling across protocol boundaries

## Conclusion

The OpenPLC v3 codebase shows significant coupling between protocol parsers and core control logic. The proposed decoupling strategy using protocol abstraction and data access layers would create a more modular, maintainable, and extensible architecture while preserving existing functionality.

The implementation should proceed incrementally, starting with interface definitions and gradually refactoring existing protocols to use the new architecture. This approach minimizes risk while providing clear benefits in code organization and future extensibility.