# OpenPLC v3 Complete File Inventory and Removal Analysis

## Overview

This document provides a comprehensive inventory of all source files in OpenPLC v3 with their purposes and recommendations for creating a minimal control logic + Modbus version.

**Legend:**
- 🟢 **KEEP** - Essential for minimal version
- 🟡 **OPTIONAL** - Useful but not essential
- 🔴 **REMOVE** - Can be safely removed
- 📋 **MODIFY** - Keep but modify/simplify

## WebServer Core Directory (`webserver/core/`)

### Core Runtime Files

| File | Size | Purpose | Recommendation |
|------|------|---------|----------------|
| `main.cpp` | 9,978 | Main control loop, initialization, threading | 📋 **MODIFY** - Remove protocol threads, simplify |
| `ladder.h` | 4,762 | Core data structures, prototypes, constants | 📋 **MODIFY** - Remove unused protocol definitions |
| `server.cpp` | 10,440 | Generic network server infrastructure | 🟢 **KEEP** - Needed for Modbus TCP |
| `utils.cpp` | 8,319 | Utility functions (timing, logging, special functions) | 📋 **MODIFY** - Keep timing/logging, remove web interface functions |

### Protocol Implementations

| File | Size | Purpose | Recommendation |
|------|------|---------|----------------|
| `modbus.cpp` | 39,609 | Modbus TCP server, function code handlers | 🟢 **KEEP** - Core Modbus functionality |
| `modbus_master.cpp` | 29,312 | Modbus master/client functionality | 🟡 **OPTIONAL** - Keep if Modbus master needed |
| `dnp3.cpp` | 16,557 | DNP3 protocol server implementation | 🔴 **REMOVE** - Not needed for minimal version |
| `enip.cpp` | 24,389 | EtherNet/IP protocol implementation | 🔴 **REMOVE** - Not needed for minimal version |
| `pccc.cpp` | 24,678 | Allen-Bradley PCCC protocol | 🔴 **REMOVE** - Not needed for minimal version |

### Infrastructure Components

| File | Size | Purpose | Recommendation |
|------|------|---------|----------------|
| `interactive_server.cpp` | 19,420 | Web interface server, protocol management | 🔴 **REMOVE** - Web interface not needed |
| `persistent_storage.cpp` | 9,613 | Database storage functionality | 🔴 **REMOVE** - Database not needed |
| `client.cpp` | 3,903 | Client-side network utilities | 🔴 **REMOVE** - Client functionality not needed |
| `debug.cpp` | 1,711 | Debug interface and MD5 validation | 🟡 **OPTIONAL** - Keep if debugging needed |
| `debug.h` | 433 | Debug function prototypes | 🟡 **OPTIONAL** - Associated with debug.cpp |

### Protocol Headers

| File | Size | Purpose | Recommendation |
|------|------|---------|----------------|
| `enipStruct.h` | - | EtherNet/IP data structures | 🔴 **REMOVE** - Not needed without EtherNet/IP |

## Hardware Abstraction Layer (`webserver/core/hardware_layers/`)

### Hardware Platform Support

| File | Size | Purpose | Recommendation |
|------|------|---------|----------------|
| `blank.cpp` | 3,652 | Generic/blank hardware abstraction | 🟢 **KEEP** - Minimal hardware layer |
| `raspberrypi.cpp` | 5,235 | Raspberry Pi GPIO support | 🔴 **REMOVE** - Platform-specific |
| `raspberrypi_old.cpp` | 5,182 | Legacy Raspberry Pi support | 🔴 **REMOVE** - Platform-specific |
| `PiPLC.cpp` | 5,756 | PiPLC hardware support | 🔴 **REMOVE** - Platform-specific |
| `opi_zero2.cpp` | 5,048 | Orange Pi Zero2 support | 🔴 **REMOVE** - Platform-specific |
| `sl_rp4.cpp` | 5,183 | SL-RP4 hardware support | 🔴 **REMOVE** - Platform-specific |
| `unipi.cpp` | 7,900 | UniPi hardware support | 🔴 **REMOVE** - Platform-specific |
| `simulink.cpp` | 7,398 | MATLAB Simulink integration | 🔴 **REMOVE** - Platform-specific |
| `fischertechnik.cpp` | 8,481 | Fischertechnik hardware support | 🔴 **REMOVE** - Platform-specific |
| `neuron.cpp` | 11,907 | Neuron hardware platform | 🔴 **REMOVE** - Platform-specific |
| `psm.cpp` | 15,315 | PSM hardware support | 🔴 **REMOVE** - Platform-specific |
| `pixtend.cpp` | 23,689 | PiXtend hardware support | 🔴 **REMOVE** - Platform-specific |
| `pixtend2s.cpp` | 24,580 | PiXtend v2S hardware support | 🔴 **REMOVE** - Platform-specific |
| `pixtend2l.cpp` | 28,167 | PiXtend v2L hardware support | 🔴 **REMOVE** - Platform-specific |
| `sequent.cpp` | 38,354 | Sequent Microsystems hardware | 🔴 **REMOVE** - Platform-specific |

## IEC 61131-3 Runtime Library (`webserver/core/lib/`)

### Essential Runtime Components

| File | Size | Purpose | Recommendation |
|------|------|---------|----------------|
| `iec_types.h` | - | IEC 61131-3 data type definitions | 🟢 **KEEP** - Core data types |
| `iec_types_all.h` | - | Complete IEC type system | 🟢 **KEEP** - Type system |
| `iec_std_lib.h` | - | Standard library functions | 🟢 **KEEP** - Core runtime functions |
| `iec_std_functions.h` | - | IEC standard function implementations | 🟢 **KEEP** - Standard functions |
| `iec_std_FB.h` | - | IEC function block implementations | 🟢 **KEEP** - Function blocks |
| `accessor.h` | - | Variable access macros | 🟢 **KEEP** - Variable access |

### Hardware-Specific Libraries

| File | Size | Purpose | Recommendation |
|------|------|---------|----------------|
| `communication.h` | - | Communication function blocks | 🟡 **OPTIONAL** - For communication FBs |
| `openplc_networking.h` | - | Networking utilities | 🟡 **OPTIONAL** - For network FBs |
| `SL-RP4.h` | - | SL-RP4 specific functions | 🔴 **REMOVE** - Hardware-specific |
| `sm_cards.h` | - | SM card support functions | 🔴 **REMOVE** - Hardware-specific |

## Utilities Directory (`utils/`)

### Build and Compilation Tools

| Directory | Files | Purpose | Recommendation |
|-----------|-------|---------|----------------|
| `matiec_src/` | 55 C++ | IEC 61131-3 compiler (MatIEC) | 🟢 **KEEP** - Essential for compilation |
| `glue_generator_src/` | 1 C++ | Variable binding code generator | 🟢 **KEEP** - Essential for variable mapping |
| `st_optimizer_src/` | Several | Structured Text optimizer | 🟡 **OPTIONAL** - Performance optimization |

### Protocol Libraries

| Directory | Files | Purpose | Recommendation |
|-----------|-------|---------|----------------|
| `libmodbus_src/` | ~30 C | Modbus library (libmodbus) | 🟢 **KEEP** - Needed for Modbus master |
| `dnp3_src/` | 641 C++ | DNP3 library (OpenDNP3) | 🔴 **REMOVE** - Not needed without DNP3 |
| `snap7_src/` | ~50 C++ | Siemens S7 protocol library | 🔴 **REMOVE** - Not needed |
| `ethercat_src/` | Several | EtherCAT support | 🔴 **REMOVE** - Not needed |

### Platform Support

| Directory | Files | Purpose | Recommendation |
|-----------|-------|---------|----------------|
| `apt-cyg/` | Shell | Cygwin package manager | 🔴 **REMOVE** - Windows-specific |
| `python2/` | Python | Python 2 compatibility | 🔴 **REMOVE** - Legacy support |

## WebServer Directory (`webserver/`)

### Additional Files

| File | Purpose | Recommendation |
|------|---------|----------------|
| `lib/test_iec_std_lib.c` | IEC library test program | 🟡 **OPTIONAL** - Testing only |

## Root Directory Files

### Configuration and Build

| File | Purpose | Recommendation |
|------|---------|----------------|
| `install.sh` | Installation script | 📋 **MODIFY** - Simplify for minimal version |
| `background_installer.sh` | Background installation | 📋 **MODIFY** - Remove unused dependencies |
| `requirements.txt` | Python dependencies | 📋 **MODIFY** - Remove unused packages |
| `Dockerfile` | Docker container build | 📋 **MODIFY** - Simplify for minimal version |

### Documentation

| File | Purpose | Recommendation |
|------|---------|----------------|
| `README.md` | Project documentation | 📋 **MODIFY** - Update for minimal version |
| `LICENSE` | GPL license | 🟢 **KEEP** - Legal requirement |
| `documentation/` | Complete documentation | 🟡 **OPTIONAL** - Reference only |

## File Removal Summary

### Core Runtime (webserver/core/)
- **Keep:** 4 files (~60KB) - main.cpp, ladder.h, server.cpp, utils.cpp
- **Keep (Modbus):** 2 files (~70KB) - modbus.cpp, modbus_master.cpp (optional)
- **Remove:** 6 files (~120KB) - All other protocols and infrastructure

### Hardware Layers (webserver/core/hardware_layers/)
- **Keep:** 1 file (3.6KB) - blank.cpp
- **Remove:** 15 files (~200KB) - All platform-specific implementations

### Libraries (webserver/core/lib/)
- **Keep:** 6 files (~15KB) - All IEC 61131-3 core libraries
- **Remove:** 2 files - Hardware-specific libraries

### Utilities (utils/)
- **Keep:** 2 directories - matiec_src/, glue_generator_src/
- **Keep (Modbus):** 1 directory - libmodbus_src/  
- **Remove:** 5 directories - dnp3_src/, snap7_src/, ethercat_src/, apt-cyg/, python2/

## Minimal Version Characteristics

### Final File Count
- **Original:** 702 source files
- **Minimal:** ~65 source files (90% reduction)

### Final Code Size
- **Original:** ~350KB core + ~5MB utilities
- **Minimal:** ~80KB core + ~500KB utilities (95% reduction)

### Preserved Functionality
✅ IEC 61131-3 program execution  
✅ Core control loop with timing  
✅ Modbus TCP server  
✅ Modbus master/client (optional)  
✅ Generic hardware abstraction  
✅ Basic logging and utilities  

### Removed Functionality
❌ DNP3, EtherNet/IP, PCCC protocols  
❌ Web interface and configuration  
❌ Platform-specific hardware support  
❌ Interactive debugging  
❌ Persistent storage  
❌ Advanced monitoring features  

## Implementation Priority

### Phase 1: Remove Protocol Files (Save 95KB)
```bash
rm webserver/core/dnp3.cpp
rm webserver/core/enip.cpp  
rm webserver/core/pccc.cpp
rm webserver/core/enipStruct.h
rm -rf utils/dnp3_src/
rm -rf utils/snap7_src/
```

### Phase 2: Remove Infrastructure (Save 33KB)
```bash
rm webserver/core/interactive_server.cpp
rm webserver/core/persistent_storage.cpp
rm webserver/core/client.cpp
rm webserver/core/debug.cpp
rm webserver/core/debug.h
```

### Phase 3: Remove Hardware Layers (Save 200KB)  
```bash
cd webserver/core/hardware_layers/
ls | grep -v blank.cpp | xargs rm
```

### Phase 4: Remove Utility Libraries
```bash
rm -rf utils/ethercat_src/
rm -rf utils/apt-cyg/
rm -rf utils/python2/
```

### Phase 5: Modify Core Files
- Simplify `main.cpp` - remove protocol threads
- Clean `ladder.h` - remove unused protocol definitions  
- Trim `utils.cpp` - keep only essential functions
- Update build scripts for minimal dependencies

This inventory provides the complete roadmap for creating a minimal OpenPLC version focused solely on control logic execution with optional Modbus support.