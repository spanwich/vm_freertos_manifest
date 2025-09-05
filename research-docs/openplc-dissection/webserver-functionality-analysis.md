# OpenPLC v3 Webserver Functionality Analysis

## Overview

This document analyzes the webserver components of OpenPLC v3 to determine what functionality is provided by the web interface and whether any of it is essential for core PLC operation.

## Webserver Architecture

### Directory Structure
```
webserver/
├── webserver.py          # Main Flask web application
├── openplc.py           # Runtime control and communication
├── pages.py             # HTML templates and UI components
├── monitoring.py        # Real-time monitoring and debugging
├── check_openplc_db.py  # Database utilities
├── openplc.db          # SQLite configuration database
├── scripts/            # Build and compilation scripts
├── static/             # Web assets (CSS, JS, images)
├── st_files/           # Structured Text program storage
├── lib/                # Additional libraries
└── core/               # C++ runtime (analyzed separately)
```

## Core Webserver Functions

### 1. Program Management (`webserver.py` + `openplc.py`)

#### Program Compilation
**Purpose:** Convert IEC 61131-3 programs to executable code
**Implementation:**
```python
def compile_program(self, st_file):
    # Calls ./scripts/compile_program.sh
    # Invokes MatIEC compiler: ./iec2c -f -l -p -r -R -a ./st_files/{file}
    # Generates C code: POUS.c, LOCATED_VARIABLES.h, Config0.c
    # Compiles to binary: core/openplc executable
```

**Critical Functions:**
- IEC 61131-3 to C code translation
- Variable binding generation (`glueVars.cpp`)
- Hardware layer linking
- Binary compilation and linking

#### Program Upload/Storage
**Purpose:** Store and manage PLC programs
**Database:** `Programs` table stores program metadata
```sql
Programs (Prog_ID, Name, Description, File, Date_upload)
```

#### Runtime Control
**Purpose:** Start/stop PLC runtime execution
```python
def start_runtime(self):
    self.theprocess = subprocess.Popen(['./core/openplc'])
    
def stop_runtime(self):
    self._rpc('stop_runtime')  # Socket command to runtime
```

### 2. Protocol Configuration (`webserver.py`)

#### Protocol Management
**Purpose:** Enable/disable communication protocols dynamically
**Database:** `Settings` table stores protocol configuration
```sql
Settings: Key-Value pairs
- Modbus_port: 502 | disabled
- Dnp3_port: 20000 | disabled  
- Enip_port: 44818 | disabled
- snap7: true | false
```

**Runtime Protocol Control:**
```python
def configure_runtime():
    # Read settings from database
    # Send RPC commands to runtime:
    openplc_runtime.start_modbus(port)
    openplc_runtime.start_dnp3(port)
    openplc_runtime.start_enip(port)
```

#### Communication via Interactive Server
**Mechanism:** Socket communication on port 43628
```python
def _rpc(self, msg):
    s.connect(('localhost', 43628))
    s.send(f'{msg}\n'.encode('utf-8'))
    # Commands: start_modbus(502), start_dnp3(20000), etc.
```

### 3. Hardware Configuration (`webserver.py`)

#### Hardware Layer Selection
**Purpose:** Choose hardware abstraction layer at runtime
**Script:** `scripts/change_hardware_layer.sh`
**Implementation:**
- Recompiles runtime with selected hardware layer
- Updates `openplc_platform` file
- Links appropriate hardware-specific code

#### Hardware Options Available:
- Blank/Generic (default)
- Raspberry Pi variants
- Industrial platforms (PiXtend, UniPi, Sequent, etc.)
- Simulation platforms (Simulink integration)

### 4. Modbus Slave Device Management

#### Slave Device Configuration
**Purpose:** Configure Modbus master functionality
**Database:** `Slave_dev` table with comprehensive device parameters
```sql
Slave_dev: 
- Device identification (dev_id, dev_name, slave_id)
- Communication (com_port, ip_address, baud_rate, parity)
- Memory mapping (di_start, coil_start, hr_read_start, etc.)
- Timing (pause, polling intervals)
```

**Memory Layout Configuration:**
- Discrete Inputs (DI): start address + size
- Coils: start address + size  
- Input Registers (IR): start address + size
- Holding Registers (HR): read/write start + size

### 5. User Authentication and Security

#### User Management
**Database:** `Users` table
```sql
Users (user_id, name, username, email, password, pict_file)
```

**Authentication:** Flask-Login session management
**Security Features:**
- Password-protected access
- Session management
- File upload validation (image magic number checking)

### 6. Real-time Monitoring (`monitoring.py`)

#### Variable Monitoring
**Purpose:** Real-time debugging and variable inspection
**Implementation:**
```python
def parse_st(st_file):
    # Parse Structured Text for variables with AT declarations
    # Extract: name, location (%IX0.0, %QW1), type (BOOL, INT)
    # Build debug_vars[] array for monitoring
```

**Monitoring Capabilities:**
- Real-time variable values via Modbus
- Variable forcing/setting
- Program execution tracing
- Performance metrics (cycle time, latency)

#### Debug Interface Integration
**Connection:** Uses Modbus client to read runtime variables
```python
mb_client = ModbusTcpClient('localhost', port=502)
# Read variables via Modbus function codes
```

### 7. Build System Integration (`scripts/`)

#### Program Compilation (`compile_program.sh`)
**Process:**
1. **MatIEC Compilation:** `./iec2c` converts ST to C
2. **File Processing:** Move generated files to `core/`
3. **Optional Features:** EtherCAT, Snap7 integration
4. **Binary Compilation:** Compile with hardware layer
5. **Library Linking:** Link protocol libraries

**Generated Files:**
- `POUS.c/.h` - Program Organization Units
- `LOCATED_VARIABLES.h` - Variable declarations
- `Config0.c/.h` - Configuration
- `Res0.c` - Resource definitions
- `glueVars.cpp` - Variable binding (auto-generated)

#### Hardware Layer Management (`change_hardware_layer.sh`)
**Purpose:** Recompile runtime with different hardware support

## Essential vs. Optional Functionality Analysis

### Essential Functions (Required for PLC Operation)

#### 1. Program Compilation ⭐ CRITICAL
**Why Essential:**
- Only way to convert IEC 61131-3 programs to executable code
- Generates essential variable binding (`glueVars.cpp`)
- Links hardware abstraction layer
- No alternative mechanism exists in runtime

**Alternative:** Manual compilation via command line possible but complex

#### 2. Runtime Process Management ⭐ CRITICAL  
**Why Essential:**
- Webserver starts/stops the `./core/openplc` process
- No built-in mechanism for standalone startup
- Process lifecycle management

**Alternative:** Manual process startup possible but loses control

#### 3. Hardware Layer Configuration ⭐ CRITICAL
**Why Essential:**
- Runtime must be compiled with correct hardware layer
- No runtime hardware switching mechanism
- Hardware abstraction layer selection

**Alternative:** Pre-compile with fixed hardware layer

### Semi-Essential Functions (Important but Workarounds Exist)

#### 1. Protocol Configuration 🟡 IMPORTANT
**Current Implementation:** Dynamic protocol enable/disable via RPC
**Web Function:** Database storage + runtime RPC commands
**Alternative:** 
- Static configuration files
- Command-line parameters
- Environment variables

#### 2. Variable Monitoring and Debugging 🟡 IMPORTANT  
**Web Function:** Real-time variable inspection via Modbus
**Alternative:**
- Direct Modbus client tools
- Custom monitoring applications
- Debug prints in code

#### 3. Program Storage and Management 🟡 IMPORTANT
**Web Function:** Database storage of multiple programs
**Alternative:**
- File system storage
- Manual file management
- Version control systems

### Optional Functions (Convenience Features)

#### 1. User Authentication 🟢 OPTIONAL
**Purpose:** Web access security
**Alternative:** Network-level security, VPN access

#### 2. Web UI and Visualizations 🟢 OPTIONAL
**Purpose:** User-friendly interface
**Alternative:** Command-line tools, external HMI

#### 3. Modbus Slave Device Management 🟢 OPTIONAL
**Purpose:** GUI configuration of Modbus master
**Alternative:** Configuration files, static setup

## Critical Dependencies on Webserver

### 1. Program Compilation Pipeline
**Dependency Chain:**
```
ST Program → webserver.py → compile_program.sh → MatIEC → C Code → GCC → Binary
```
**Removal Impact:** ❌ No program compilation capability

### 2. Runtime Communication Channel  
**Current:** Socket RPC on port 43628 via `interactive_server.cpp`
```
webserver.py ↔ Socket(43628) ↔ interactive_server.cpp ↔ Runtime
```
**Purpose:** Protocol start/stop, configuration changes
**Removal Impact:** ❌ No dynamic protocol management

### 3. Variable Binding Generation
**Process:** `glue_generator` creates `glueVars.cpp` during compilation
**Trigger:** Webserver compilation process
**Removal Impact:** ❌ Variables not bound to I/O buffers

## Minimal Operation Scenarios

### Scenario 1: Pre-compiled Runtime (Webserver-free)
**Requirements:**
- Pre-compile program with webserver
- Generate all required files (`glueVars.cpp`, etc.)
- Fixed protocol configuration
- Static hardware layer

**Limitations:**
- No program changes without recompilation
- No dynamic protocol management
- No monitoring/debugging interface
- Fixed configuration

### Scenario 2: Compilation-only Webserver
**Keep:** 
- Program compilation functionality
- Hardware layer selection
- Build scripts

**Remove:**
- User authentication
- Real-time monitoring  
- Web UI components
- Runtime management

### Scenario 3: Configuration-only Interface
**Purpose:** Minimal interface for essential functions
**Functions:**
- Program upload and compilation
- Hardware layer selection  
- Basic protocol configuration
- Runtime start/stop

## Recommendations for Minimal Version

### Option 1: Remove Webserver Entirely
**Requirements:**
1. **Pre-compilation:** Use webserver once to compile programs
2. **Static Configuration:** Hard-code protocol settings in runtime
3. **Manual Process Management:** Direct `./core/openplc` execution
4. **Fixed Hardware Layer:** Compile with target hardware layer

**Benefits:** Minimal attack surface, reduced complexity
**Drawbacks:** No flexibility, difficult program updates

### Option 2: Minimal Command-Line Interface
**Replace webserver with:**
```bash
# Compilation
./compile_st_program.sh program.st hardware_layer

# Runtime management  
./start_openplc [modbus_port] [dnp3_port] [enip_port]
./stop_openplc

# Configuration
./configure_protocols.sh config.json
```

### Option 3: Essential Webserver Functions Only
**Keep:**
- `compile_program.sh` and compilation infrastructure
- Basic runtime start/stop via RPC
- Minimal configuration interface
- Hardware layer selection

**Remove:**
- User authentication and session management
- Real-time monitoring and debugging
- Advanced UI components
- Database complexity

## Conclusion

The webserver provides **three critical functions** that are difficult to replace:

1. **Program Compilation:** Complex toolchain integration (MatIEC, GCC, variable binding)
2. **Runtime Communication:** RPC channel for protocol management
3. **Hardware Layer Integration:** Dynamic hardware abstraction selection

**For a minimal version, the safest approach is Option 3:** Keep essential webserver functions but remove UI complexity, authentication, and monitoring features. This preserves critical functionality while significantly reducing codebase complexity.

The webserver is **not just a UI** - it's an integral part of the build system and runtime management infrastructure. Complete removal requires significant re-engineering of the compilation and configuration systems.