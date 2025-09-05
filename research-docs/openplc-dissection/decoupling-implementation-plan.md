# OpenPLC v3 Protocol Decoupling Implementation Plan

## Overview

This document provides a detailed implementation plan for decoupling ICS protocol message parsers from the OpenPLC v3 core control logic. The plan is structured in phases to minimize risk and maintain system stability throughout the transition.

## Design Principles

1. **Backward Compatibility:** Existing configurations and behavior must be preserved
2. **Minimal Performance Impact:** Real-time control loop performance cannot be degraded
3. **Thread Safety:** All data access must be properly synchronized
4. **Incremental Migration:** Changes should be implementable and testable incrementally
5. **Plugin Architecture:** Future protocols should be addable without core modifications

## Proposed Architecture

### Core Interfaces

#### 1. Protocol Handler Interface

```cpp
// protocol_handler.h
#ifndef PROTOCOL_HANDLER_H
#define PROTOCOL_HANDLER_H

#include <stdint.h>
#include <memory>
#include <string>

enum class ProtocolStatus {
    STOPPED,
    STARTING,
    RUNNING,
    STOPPING,
    ERROR
};

struct ProtocolConfig {
    std::string name;
    uint16_t port;
    bool enabled;
    std::string config_file;
    // Protocol-specific configuration map
    std::map<std::string, std::string> parameters;
};

struct ProtocolStats {
    uint64_t messages_received;
    uint64_t messages_sent;
    uint64_t errors;
    uint64_t bytes_in;
    uint64_t bytes_out;
    double last_response_time_ms;
};

class ProtocolHandler {
public:
    virtual ~ProtocolHandler() = default;
    
    // Lifecycle management
    virtual bool initialize(const ProtocolConfig& config) = 0;
    virtual bool start() = 0;
    virtual bool stop() = 0;
    virtual void shutdown() = 0;
    
    // Core integration points
    virtual void updateInputs() = 0;   // Protocol -> Core data transfer
    virtual void updateOutputs() = 0;  // Core -> Protocol data transfer
    
    // Status and diagnostics
    virtual ProtocolStatus getStatus() const = 0;
    virtual ProtocolStats getStatistics() const = 0;
    virtual std::string getLastError() const = 0;
    
    // Configuration
    virtual const ProtocolConfig& getConfig() const = 0;
    virtual bool updateConfig(const ProtocolConfig& config) = 0;
    
    // Protocol identification
    virtual std::string getProtocolName() const = 0;
    virtual std::string getVersion() const = 0;
};
```

#### 2. Data Access Layer Interface

```cpp
// data_access_layer.h
#ifndef DATA_ACCESS_LAYER_H
#define DATA_ACCESS_LAYER_H

#include <stdint.h>
#include <vector>
#include <mutex>

enum class DataType {
    BOOL,
    BYTE,
    WORD,
    DWORD,
    LWORD,
    REAL,
    LREAL
};

enum class DataDirection {
    INPUT,
    OUTPUT,
    MEMORY
};

class DataAccessLayer {
public:
    virtual ~DataAccessLayer() = default;
    
    // Boolean operations
    virtual bool readBool(DataDirection dir, uint16_t address, uint8_t bit) = 0;
    virtual bool writeBool(DataDirection dir, uint16_t address, uint8_t bit, bool value) = 0;
    
    // Word operations
    virtual uint16_t readWord(DataDirection dir, uint16_t address) = 0;
    virtual bool writeWord(DataDirection dir, uint16_t address, uint16_t value) = 0;
    
    // Double word operations
    virtual uint32_t readDWord(DataDirection dir, uint16_t address) = 0;
    virtual bool writeDWord(DataDirection dir, uint16_t address, uint32_t value) = 0;
    
    // 64-bit operations
    virtual uint64_t readLWord(DataDirection dir, uint16_t address) = 0;
    virtual bool writeLWord(DataDirection dir, uint16_t address, uint64_t value) = 0;
    
    // Bulk operations for efficiency
    virtual bool readRange(DataDirection dir, uint16_t start_addr, uint16_t count, 
                          DataType type, void* buffer) = 0;
    virtual bool writeRange(DataDirection dir, uint16_t start_addr, uint16_t count,
                           DataType type, const void* buffer) = 0;
    
    // Address validation
    virtual bool isValidAddress(DataDirection dir, uint16_t address, DataType type) = 0;
    virtual uint16_t getMaxAddress(DataDirection dir, DataType type) = 0;
    
    // Thread-safe batch operations
    virtual void beginTransaction() = 0;
    virtual void commitTransaction() = 0;
    virtual void rollbackTransaction() = 0;
};
```

#### 3. Protocol Registry

```cpp
// protocol_registry.h
#ifndef PROTOCOL_REGISTRY_H
#define PROTOCOL_REGISTRY_H

#include "protocol_handler.h"
#include <memory>
#include <map>
#include <functional>

using ProtocolFactory = std::function<std::unique_ptr<ProtocolHandler>()>;

class ProtocolRegistry {
public:
    static ProtocolRegistry& instance();
    
    // Protocol factory registration
    void registerProtocol(const std::string& name, ProtocolFactory factory);
    void unregisterProtocol(const std::string& name);
    
    // Protocol instance management
    std::unique_ptr<ProtocolHandler> createProtocol(const std::string& name);
    std::vector<std::string> getAvailableProtocols() const;
    bool isProtocolAvailable(const std::string& name) const;
    
private:
    std::map<std::string, ProtocolFactory> protocols_;
    mutable std::mutex mutex_;
};
```

### Core Implementation Classes

#### 1. OpenPLC Data Access Layer

```cpp
// openplc_data_access.h
#ifndef OPENPLC_DATA_ACCESS_H
#define OPENPLC_DATA_ACCESS_H

#include "data_access_layer.h"
#include "ladder.h"
#include <mutex>

class OpenPLCDataAccess : public DataAccessLayer {
public:
    OpenPLCDataAccess();
    virtual ~OpenPLCDataAccess();
    
    // Implement DataAccessLayer interface
    bool readBool(DataDirection dir, uint16_t address, uint8_t bit) override;
    bool writeBool(DataDirection dir, uint16_t address, uint8_t bit, bool value) override;
    
    uint16_t readWord(DataDirection dir, uint16_t address) override;
    bool writeWord(DataDirection dir, uint16_t address, uint16_t value) override;
    
    // ... implement remaining virtual methods
    
    // OpenPLC-specific methods
    void setBufferLock(pthread_mutex_t* lock) { buffer_lock_ = lock; }
    
private:
    pthread_mutex_t* buffer_lock_;
    
    // Helper methods
    bool validateBoolAccess(DataDirection dir, uint16_t address, uint8_t bit);
    bool validateWordAccess(DataDirection dir, uint16_t address);
    IEC_BOOL** getBoolBuffer(DataDirection dir, uint16_t address, uint8_t bit);
    IEC_UINT** getWordBuffer(DataDirection dir, uint16_t address);
};
```

#### 2. Protocol Manager

```cpp
// protocol_manager.h
#ifndef PROTOCOL_MANAGER_H
#define PROTOCOL_MANAGER_H

#include "protocol_handler.h"
#include "data_access_layer.h"
#include <vector>
#include <memory>
#include <thread>
#include <mutex>
#include <atomic>

class ProtocolManager {
public:
    ProtocolManager(std::shared_ptr<DataAccessLayer> data_access);
    ~ProtocolManager();
    
    // Protocol lifecycle
    bool addProtocol(const ProtocolConfig& config);
    bool removeProtocol(const std::string& name);
    bool startProtocol(const std::string& name);
    bool stopProtocol(const std::string& name);
    
    // Control loop integration
    void updateInputs();
    void updateOutputs();
    
    // Management
    std::vector<ProtocolHandler*> getActiveProtocols();
    ProtocolHandler* getProtocol(const std::string& name);
    
    // Configuration
    bool loadConfiguration(const std::string& config_file);
    bool saveConfiguration(const std::string& config_file);
    
    // Shutdown
    void shutdown();
    
private:
    struct ProtocolInstance {
        std::unique_ptr<ProtocolHandler> handler;
        ProtocolConfig config;
        std::atomic<bool> active;
        
        ProtocolInstance(std::unique_ptr<ProtocolHandler> h, const ProtocolConfig& c)
            : handler(std::move(h)), config(c), active(false) {}
    };
    
    std::vector<std::unique_ptr<ProtocolInstance>> protocols_;
    std::shared_ptr<DataAccessLayer> data_access_;
    mutable std::mutex protocols_mutex_;
    std::atomic<bool> shutdown_requested_;
};
```

## Implementation Phases

### Phase 1: Foundation Infrastructure (Weeks 1-2)

**Objectives:**
- Create core interfaces and base implementations
- Implement data access layer
- Set up protocol registry system

**Tasks:**
1. **Create Interface Headers** (1 day)
   - `protocol_handler.h`
   - `data_access_layer.h` 
   - `protocol_registry.h`

2. **Implement OpenPLC Data Access Layer** (3 days)
   ```cpp
   // File: openplc_data_access.cpp
   bool OpenPLCDataAccess::readBool(DataDirection dir, uint16_t address, uint8_t bit) {
       if (!validateBoolAccess(dir, address, bit)) return false;
       
       pthread_mutex_lock(buffer_lock_);
       IEC_BOOL** buffer = getBoolBuffer(dir, address, bit);
       bool value = (buffer && *buffer) ? **buffer : false;
       pthread_mutex_unlock(buffer_lock_);
       
       return value;
   }
   ```

3. **Implement Protocol Registry** (2 days)
   - Singleton pattern implementation
   - Thread-safe protocol factory registration
   - Dynamic protocol loading support

4. **Create Protocol Manager** (3 days)
   - Protocol instance lifecycle management
   - Configuration loading/saving
   - Integration with control loop

5. **Unit Tests** (1 day)
   - Data access layer tests
   - Protocol registry tests
   - Mock protocol handler for testing

### Phase 2: Modbus Protocol Refactoring (Weeks 3-4)

**Objectives:**
- Convert existing Modbus implementation to use new architecture
- Maintain full backward compatibility
- Validate performance impact

**Tasks:**
1. **Create Modbus Protocol Handler** (4 days)
   ```cpp
   // File: modbus_protocol_handler.cpp
   class ModbusProtocolHandler : public ProtocolHandler {
   private:
       std::shared_ptr<DataAccessLayer> data_access_;
       uint16_t port_;
       std::thread server_thread_;
       std::atomic<bool> running_;
       
       // Modbus-specific data structures
       struct ModbusMapping {
           uint16_t coil_start, coil_count;
           uint16_t discrete_start, discrete_count;
           uint16_t holding_start, holding_count;
           uint16_t input_start, input_count;
       } mapping_;
       
   public:
       bool initialize(const ProtocolConfig& config) override {
           port_ = std::stoi(config.parameters.at("port"));
           // Load Modbus-specific mapping configuration
           loadMapping(config.config_file);
           return true;
       }
       
       void updateInputs() override {
           // Transfer data FROM Modbus buffers TO core via data_access_
           // Replace current updateBuffersIn_MB() logic
       }
       
       void updateOutputs() override {
           // Transfer data FROM core TO Modbus buffers via data_access_
           // Replace current updateBuffersOut_MB() logic
       }
   };
   ```

2. **Migrate Message Processing Logic** (3 days)
   - Extract message parsing from modbus.cpp
   - Remove direct buffer access
   - Use DataAccessLayer for all I/O operations

3. **Configuration Migration** (2 days)
   - Create modbus_config.json schema
   - Migration utility for existing configurations
   - Validation and error handling

4. **Integration Testing** (1 day)
   - Test with existing Modbus clients
   - Performance benchmarking
   - Regression testing

### Phase 3: DNP3 and EtherNet/IP Refactoring (Weeks 5-7)

**Objectives:**
- Convert DNP3 and EtherNet/IP implementations
- Standardize configuration approach
- Implement protocol-specific optimizations

**Tasks:**
1. **DNP3 Protocol Handler** (4 days)
   ```cpp
   // File: dnp3_protocol_handler.cpp  
   class DNP3ProtocolHandler : public ProtocolHandler {
   private:
       std::unique_ptr<opendnp3::DNP3Manager> manager_;
       std::shared_ptr<DataAccessLayer> data_access_;
       
       // DNP3-specific callback handlers
       class DNP3CommandHandler : public opendnp3::ICommandHandler {
           std::shared_ptr<DataAccessLayer> data_access_;
       public:
           DNP3CommandHandler(std::shared_ptr<DataAccessLayer> da) 
               : data_access_(da) {}
               
           opendnp3::CommandStatus Select(const opendnp3::ControlRelayOutputBlock& command, 
                                         uint16_t index, opendnp3::IUpdateHandler& handler,
                                         opendnp3::OperateType opType) override {
               // Use data_access_ instead of direct buffer access
               bool success = data_access_->writeBool(DataDirection::OUTPUT, 
                                                     index / 8, index % 8, 
                                                     command.functionCode == opendnp3::ControlCode::LATCH_ON);
               return success ? opendnp3::CommandStatus::SUCCESS : opendnp3::CommandStatus::HARDWARE_ERROR;
           }
       };
   };
   ```

2. **EtherNet/IP Protocol Handler** (4 days)
   - Extract CIP message processing
   - Implement tag-based addressing through DataAccessLayer
   - Session management refactoring

3. **Configuration Standardization** (2 days)
   - JSON configuration schemas
   - Common configuration loading infrastructure
   - Validation and error reporting

4. **Testing and Validation** (1 day)
   - Protocol interoperability testing
   - Performance measurement
   - Memory usage analysis

### Phase 4: PCCC and Control Loop Integration (Weeks 8-9)

**Objectives:**
- Complete protocol migration
- Integrate with main control loop
- Performance optimization

**Tasks:**
1. **PCCC Protocol Handler** (3 days)
   - Convert pccc.cpp to protocol handler
   - Implement Allen-Bradley addressing scheme
   - File-based address mapping

2. **Control Loop Integration** (3 days)
   ```cpp
   // File: main.cpp modifications
   // Replace hardcoded protocol calls with ProtocolManager
   
   // Old approach:
   // updateBuffersIn_MB();
   // updateBuffersOut_MB();
   
   // New approach:
   protocol_manager->updateInputs();
   protocol_manager->updateOutputs();
   ```

3. **Configuration Migration Tool** (2 days)
   - Utility to convert existing configurations
   - Backward compatibility validation
   - Migration documentation

4. **Performance Optimization** (2 days)
   - Profile critical paths
   - Optimize data access patterns
   - Reduce memory allocations

### Phase 5: Advanced Features and Cleanup (Weeks 10-11)

**Objectives:**
- Implement advanced features
- Clean up deprecated code
- Documentation and testing

**Tasks:**
1. **Dynamic Protocol Loading** (3 days)
   - Plugin architecture for protocols
   - Runtime protocol addition/removal
   - Configuration hot-reloading

2. **Enhanced Diagnostics** (2 days)
   - Protocol statistics collection
   - Performance monitoring
   - Debug interfaces

3. **Code Cleanup** (2 days)
   - Remove deprecated functions
   - Clean up global variables
   - Code review and refactoring

4. **Documentation** (2 days)
   - API documentation
   - Migration guide
   - Architecture documentation

5. **Comprehensive Testing** (1 day)
   - End-to-end testing
   - Load testing
   - Edge case validation

## File Structure Changes

### New Files to Create

```
webserver/core/
├── protocols/
│   ├── protocol_handler.h
│   ├── data_access_layer.h
│   ├── protocol_registry.h
│   ├── protocol_manager.h
│   ├── openplc_data_access.h
│   ├── openplc_data_access.cpp
│   ├── protocol_manager.cpp
│   ├── protocol_registry.cpp
│   └── handlers/
│       ├── modbus_protocol_handler.h
│       ├── modbus_protocol_handler.cpp
│       ├── dnp3_protocol_handler.h
│       ├── dnp3_protocol_handler.cpp
│       ├── enip_protocol_handler.h
│       ├── enip_protocol_handler.cpp
│       ├── pccc_protocol_handler.h
│       └── pccc_protocol_handler.cpp
├── config/
│   ├── protocol_config.h
│   ├── protocol_config.cpp
│   └── schemas/
│       ├── modbus_config.schema.json
│       ├── dnp3_config.schema.json
│       ├── enip_config.schema.json
│       └── pccc_config.schema.json
```

### Modified Files

```
webserver/core/
├── main.cpp              # Modified control loop
├── ladder.h              # Updated with new interfaces
├── server.cpp            # Simplified with protocol abstraction
└── interactive_server.cpp # Modified to use ProtocolManager
```

### Deprecated Files (Phase 5)

```
webserver/core/
├── modbus.cpp            # Logic moved to modbus_protocol_handler.cpp
├── modbus_master.cpp     # Integrated into modbus_protocol_handler.cpp
├── dnp3.cpp              # Logic moved to dnp3_protocol_handler.cpp
├── enip.cpp              # Logic moved to enip_protocol_handler.cpp
└── pccc.cpp              # Logic moved to pccc_protocol_handler.cpp
```

## Risk Mitigation Strategies

### Performance Risks

1. **Baseline Measurement:** Establish performance benchmarks before changes
2. **Incremental Profiling:** Profile each phase for performance regression
3. **Optimization Points:** Identify and optimize critical data paths
4. **Fallback Plan:** Keep old implementation available during transition

### Compatibility Risks

1. **Configuration Migration:** Automated tools for configuration conversion
2. **API Compatibility:** Maintain existing function signatures during transition
3. **Testing Matrix:** Comprehensive testing with different client configurations
4. **Rollback Capability:** Ability to revert to previous implementation

### Integration Risks

1. **Thread Safety:** Extensive testing of concurrent access patterns
2. **Memory Management:** Careful tracking of memory allocation changes
3. **Error Handling:** Robust error handling and recovery mechanisms
4. **Monitoring:** Enhanced logging and diagnostics during transition

## Success Criteria

### Functional Requirements

1. **Zero Downtime Migration:** System continues operating during upgrade
2. **Protocol Compatibility:** All existing protocol clients continue working
3. **Configuration Compatibility:** Existing configurations work without modification
4. **Feature Parity:** All current protocol features remain available

### Performance Requirements

1. **Control Loop Timing:** No degradation in control loop execution time
2. **Protocol Response Time:** Protocol response times within 5% of baseline
3. **Memory Usage:** Memory usage increase limited to <10%
4. **CPU Utilization:** CPU usage increase limited to <5%

### Quality Requirements

1. **Code Coverage:** Unit test coverage >90% for new protocol handlers
2. **Documentation:** Complete API documentation and migration guide
3. **Code Quality:** All code passes static analysis without warnings
4. **Maintainability:** Clear separation of concerns and modular design

## Timeline Summary

| Phase | Duration | Key Deliverables |
|-------|----------|------------------|
| 1     | 2 weeks  | Foundation interfaces and data access layer |
| 2     | 2 weeks  | Modbus protocol handler and testing |
| 3     | 3 weeks  | DNP3 and EtherNet/IP protocol handlers |
| 4     | 2 weeks  | PCCC handler and control loop integration |
| 5     | 2 weeks  | Advanced features and cleanup |
| **Total** | **11 weeks** | **Complete protocol decoupling** |

This implementation plan provides a structured approach to decoupling OpenPLC v3 protocol parsers while maintaining system stability and performance. The phased approach allows for incremental validation and reduces risk throughout the migration process.