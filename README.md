# 🖥️ Hardware-Assisted Deadlock and Process Freeze Detection & Recovery System

This project aims to develop a hardware-assisted operating system monitoring system capable of detecting frozen applications, unresponsive processes, and potential deadlock situations in real time. A Python-based monitoring service continuously runs in the background of a Windows operating system. The service periodically scans all active processes using operating system APIs and system performance metrics. It identifies applications that become unresponsive ("Not Responding"), remain blocked for an extended period, or exhibit abnormal execution behavior.

When such a process is detected, the monitoring service collects its Process ID (PID), process name, CPU usage, memory consumption, and current execution state. This information is transmitted through serial communication to an Arduino Uno. The Arduino functions as an external monitoring dashboard. It displays the process information on a 128x64 OLED, activates LEDs for visual indication, and sounds a buzzer to notify the user. A physical push-button on the Arduino allows the user to acknowledge the alert and request termination of the frozen process.

When the button is pressed, the Arduino sends a command back to the host computer via serial communication. The Python application receives the command and safely terminates the selected process using operating system process management functions. The project demonstrates the integration of operating system concepts with embedded hardware, providing a practical solution for monitoring and managing system processes.

## ✨ Features

- **Real-time Process Monitoring**: Continuously scans Windows processes for frozen/unresponsive applications
- **Deadlock Detection**: Identifies processes blocked for extended periods (potential deadlock situations)
- **Hardware Alert System**: Arduino-based alert system with OLED display, LED indicators, and buzzer
- **Visual Dashboard**: Color-coded console output with detailed process information
- **Automatic Process Termination**: Safely terminates frozen processes with PID reuse protection
- **Multiple Display Modes**: Compact, detailed, and silent monitoring modes
- **Process Exclusions**: Exclude specific processes from monitoring
- **Test Mode**: Simulate frozen processes for testing without actual crashes
- **Professional OLED Display**: Custom-designed UI with frames, headers, and status indicators
- **Button-Based Control**: Physical button to terminate frozen processes
- **Priority-Based Alerting**: Prioritizes processes by severity and resource usage
- **Differentiated Alerts**: Visual and audio distinction between freeze and deadlock alerts

## 🛠️ Hardware Requirements

### Arduino Components
- **Arduino Board** (Uno, Nano, or compatible)
- **OLED Display** (128x64, SSD1306, I2C) - *Professional UI with frames and headers*
- **4-Pin Push Button** - *Hardware interrupt-based control*
- **Red LED** (for alerts) - *Visual freeze indicator*
- **Green LED** (for normal status) - *System health indicator*
- **Buzzer** (for audio alerts) - *Audible notification system*
- **Resistors** (220Ω for LEDs, 10kΩ for button pull-up if needed)
- **Jumper wires and breadboard**

### Wiring Diagram
```
Arduino      OLED Display        Button         LEDs          Buzzer
------       ------------       ------         -----         ------
5V          VCC               One pin pair   Anode        +
GND         GND               Other pair     Cathode       -
A4 (SDA)    SDA                                (Red)        
A5 (SCL)    SCL               Pin 2          (Green)      
D2          ---               ---            ---          ---
D7          ---               ---            ---          ---
D8          ---               ---            ---          ---
D9          ---               ---            ---          ---
```

## 💻 Software Requirements

### Python Environment
- **Python 3.8+**
- **Windows 10/11** (uses Windows API for process detection)

### Python Dependencies
```bash
pip install -r requirements.txt
```

Required packages:
- `psutil>=5.9.0` - Process monitoring
- `pyserial>=3.5` - Serial communication
- `colorama>=0.4.6` - Console colors

### Arduino Libraries
- **Adafruit SSD1306** - OLED display driver
- **Adafruit GFX Library** - Graphics library
- **Wire** - I2C communication

Install via Arduino IDE Library Manager.

## 📦 Installation

### 1. Clone the Repository
```bash
git clone https://github.com/s-m-sharafat-hossain/Hardware-Deadlock-Recovery-System.git
cd process-freeze-monitor
```

### 2. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Arduino
1. Open `arduino_monitor.ino` in Arduino IDE
2. Install required libraries via Library Manager
3. Select your Arduino board and port
4. Upload the code to your Arduino

### 4. Configure Serial Port
- Default: `COM6`
- Change in `main.py` or use `--port` argument:
```bash
python main.py --port COM3
```

## 🚀 Usage

### Basic Usage
```bash
python main.py --port COM6
```

### Display Modes

**Standard Mode** (detailed output):
```bash
python main.py --port COM6
```

**Compact Mode** (minimal output):
```bash
python main.py --port COM6 --compact
```

**Silent Mode** (only frozen processes):
```bash
python main.py --port COM6 --no-display
```

### Advanced Options

**Test Mode** (simulate frozen Calculator):
```bash
python main.py --port COM6 --test
```

**Exclude Specific Processes**:
```bash
python main.py --port COM6 --exclude calculator notepad
```

**Custom Scan Interval**:
```bash
python main.py --port COM6 --interval 5.0
```

**Monitor Specific Process Groups**:
```bash
python main.py --port COM6 --watch calculator
python main.py --port COM6 --watch terminal
```

**Combined Options**:
```bash
python main.py --port COM6 --compact --interval 2.0 --exclude calculator
```

## 🎯 How It Works

### System Architecture
```
Windows System → Python Monitor → Serial Port → Arduino → Hardware Alerts
     ↓                ↓                ↓            ↓            ↓
Process List    Frozen Detection   Alert Data   OLED Display   LED/Buzzer
     ↓                ↓                ↓            ↓            ↓
Unresponsive    Windows API       ASCII Text   Visual UI     Button
Windows         SendMessage()      Protocol     Status       Control
```

### Detection Process
1. **Process Scanning**: Python scans all running processes every 3 seconds (System Call)
2. **Process State Determination**: Classifies processes into states (Running, Blocked, Suspended, etc.)
3. **Deadlock Detection**: Monitors blocked process duration (>30 seconds indicates potential deadlock)
4. **Window Responsiveness**: Uses Windows API to test if application windows respond (System Call)
5. **Freeze Detection**: Identifies processes with unresponsive windows as "Not Responding"
6. **Priority Assignment**: Assigns priority based on state and resource usage (Priority Scheduling)
7. **Alert Generation**: Creates alert with process details (PID, name, CPU, memory, state)
8. **Serial Transmission**: Sends alert to Arduino via serial port (IPC)
9. **Hardware Alert**: Arduino displays alert type (DEADLOCK/FROZEN) on OLED, activates red LED and buzzer
10. **User Action**: Press button triggers interrupt (Interrupt Handling)
11. **Command Transmission**: Arduino sends KILL command via serial (IPC)
12. **Process Termination**: Python safely terminates the problematic process (System Call)
13. **Confirmation**: Arduino shows termination confirmation and returns to normal state

### Operating System Concepts Implemented

#### 1. **Process Management**
- **Process Creation & Termination**: Uses system calls to create and terminate processes
- **Process Identification (PID)**: Tracks processes using unique Process IDs
- **Process Monitoring**: Continuous scanning of running processes using `psutil`
- **Process Lifecycle Management**: Manages process states from creation to termination

#### 2. **Process States**
- **Running**: Processes actively using CPU (`psutil.STATUS_RUNNING`)
- **Ready**: Processes waiting for CPU time
- **Blocked/Waiting**: Processes waiting for I/O or events (`psutil.STATUS_SLEEPING`)
- **Suspended**: Processes that are stopped (`psutil.STATUS_STOPPED`)
- **Terminated**: Processes that have finished execution
- **Not Responding**: Custom state for frozen/unresponsive applications
- **Deadlocked**: Processes blocked for extended periods (potential deadlock detection)

#### 3. **Deadlock Detection**
- **Blocked Duration Tracking**: Monitors how long processes remain in blocked state
- **Threshold-Based Detection**: Processes blocked >30 seconds flagged as potential deadlock
- **State Transition Analysis**: Tracks process state changes over time
- **Resource Wait Monitoring**: Identifies processes waiting for resources unusually long
- **Heuristic-Based Approach**: Uses time-based heuristics for deadlock detection
- **Higher Priority Assignment**: Deadlocked processes get priority 100 (highest priority)

#### 4. **Priority Scheduling**
- **Priority-Based Queue**: Uses Python's `heapq` for priority scheduling
- **Ready Queue Management**: Implements a ready queue for frozen process handling
- **Priority Assignment**: 
  - Priority 80: Processes with unresponsive windows
  - Priority 100: Processes in stopped state or deadlocked
- **Resource-Based Scheduling**: Considers CPU and memory usage for priority

#### 5. **Inter-Process Communication (IPC)**
- **Serial Communication**: UART-based communication between Python and Arduino
- **Message Protocol**: Custom ASCII protocol (`ALERT|PID|NAME|CPU|MEMORY|STATE`)
- **Bidirectional Communication**: Python sends alerts, Arduino sends KILL commands
- **Non-blocking I/O**: Serial communication with timeout for asynchronous operation

#### 6. **Interrupt Handling**
- **Hardware Interrupts**: Arduino uses `attachInterrupt()` for button press detection
- **Interrupt Service Routine**: `onButtonPressed()` function handles button interrupts
- **Debouncing**: Software debouncing to handle contact bounce (50ms delay)
- **Volatile Variables**: Uses `volatile` keyword for interrupt-modified variables
- **Atomic Operations**: `noInterrupts()`/`interrupts()` for atomic operations

#### 7. **System Calls**
- **Process Information Reading**: Uses `psutil` to read process tables and information
- **Termination Signals**: Sends `SIGKILL` equivalent via `process.kill()`
- **Windows API Integration**: Uses `SendMessageTimeoutW` for window responsiveness testing
- **Window Enumeration**: Uses `EnumWindows` to iterate through visible windows
- **Process ID Mapping**: Maps window handles to process IDs using `GetWindowThreadProcessId`

#### 8. **Asynchronous I/O**
- **Non-blocking Serial**: Serial communication with timeout (0.2s)
- **Background Monitoring**: Continuous process scanning without blocking
- **Event-Driven Architecture**: Button interrupts trigger immediate responses
- **Concurrent Operations**: Process monitoring and Arduino communication run concurrently

#### 9. **Memory Management**
- **Memory Usage Tracking**: Monitors RSS (Resident Set Size) memory usage
- **Memory Conversion**: Converts bytes to MB for human-readable display
- **Process Memory Info**: Uses `process.info["memory_info"]` for memory statistics
- **Memory-Based Priority**: Uses memory usage in priority calculations

#### 10. **CPU Utilization**
- **CPU Percentage Monitoring**: Tracks CPU usage per process
- **CPU Sampling**: Uses `process.cpu_percent()` with interval sampling
- **Resource-Based Priority**: Incorporates CPU usage into priority calculations
- **Load Monitoring**: Continuously monitors system load through process scanning

## ⚙️ Configuration

### Python Configuration
Edit constants in `main.py`:
```python
COM_PORT = "COM6"           # Arduino serial port
BAUD_RATE = 9600           # Serial communication speed
SCAN_INTERVAL = 3.0         # Seconds between scans
WINDOW_TIMEOUT_MS = 250     # Window response timeout
```

### Arduino Configuration
Edit constants in `arduino_monitor.ino`:
```cpp
const byte BUTTON_PIN = 2;      // Button pin
const byte GREEN_LED_PIN = 7;   // Green LED pin
const byte RED_LED_PIN = 8;     // Red LED pin
const byte BUZZER_PIN = 9;      // Buzzer pin
const byte OLED_ADDRESS = 0x3C; // OLED I2C address
```

### Process Exclusions
Add processes to the exclusion list in `main.py`:
```python
system_processes = {
    "system", "system idle process", "registry",
    # Add your custom exclusions here
}
```

## 🔧 Troubleshooting

### Serial Port Issues
- **Problem**: "Serial port unavailable"
- **Solution**: Check COM port number, ensure Arduino is connected, close other serial applications

### Arduino Not Responding
- **Problem**: No alerts on Arduino
- **Solution**: Check wiring, verify baud rate matches (9600), ensure OLED is properly connected

### False Positives
- **Problem**: System processes showing as frozen
- **Solution**: Add process names to exclusion list or use `--exclude` flag

### Button Not Working
- **Problem**: Button press not detected
- **Solution**: Check button wiring, ensure proper pull-up configuration, check interrupt pin

### Colorama Issues
- **Problem**: Colors not displaying in console
- **Solution**: Ensure colorama is installed, try running in different terminal

### Windows API Errors
- **Problem**: Crashes on Windows API calls
- **Solution**: Run as administrator, ensure Windows API libraries are available

## 📊 Visual Indicators

### Console Colors
- **Green**: Success, normal operation, active processes
- **Red**: Errors, frozen processes, alerts
- **Yellow**: Warnings, waiting states
- **Cyan**: Information, process counts
- **Purple**: Headers, important messages

### Arduino LED States
- **Green LED**: System normal, monitoring active
- **Red LED**: Frozen process detected, alert active
- **Both Off**: System inactive or connection lost

### OLED Display Screens
- **Normal**: "MONITOR" header, "System OK" status, checkmark
- **Alert**: "!!! ALERT !!!" header, process details, X mark
- **Kill**: "KILL CMD" header, termination status, arrow

## 🛡️ Security Features

- **PID Reuse Protection**: Checks process creation time before termination
- **System Process Exclusion**: Prevents termination of critical system processes
- **Permission Handling**: Gracefully handles access denied errors
- **Atomic Operations**: Prevents race conditions in interrupt handling
- **User Confirmation**: Requires button press for process termination

## 📈 Performance

- **Process Scanning**: ~0.5-2 seconds per scan (depends on system load)
- **Memory Usage**: ~20-50MB (Python) + ~2KB (Arduino)
- **CPU Usage**: <1% during normal operation
- **Response Time**: <1 second from freeze detection to alert display

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **psutil** - Python process monitoring library
- **pyserial** - Python serial communication library
- **Adafruit** - Arduino display and graphics libraries
- **Windows API** - Process and window management functions

## 📞 Support

For issues, questions, or suggestions:
- Open an issue on GitHub
- Check the troubleshooting section
- Review the code comments for detailed explanations

## 🎮 Demo Commands

### Quick Start
```bash
# Basic monitoring
python main.py --port COM6

# Test with simulated freeze
python main.py --port COM6 --test

# Compact monitoring mode
python main.py --port COM6 --compact
```

### Advanced Usage
```bash
# Monitor specific apps, exclude others
python main.py --port COM6 --watch terminal --exclude calculator

# Custom scan interval with test mode
python main.py --port COM6 --interval 1.0 --test

# Silent monitoring (only alerts when frozen)
python main.py --port COM6 --no-display --exclude systemsettings
```

---

**Built with ❤️ for Windows process monitoring and automation**
