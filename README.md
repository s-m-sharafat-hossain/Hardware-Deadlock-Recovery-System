# 🖥️ Windows Process Freeze Monitor with Arduino Alert System
A sophisticated process monitoring system that detects frozen Windows applications and provides hardware-based alerts through an Arduino with OLED display, LEDs, and buzzer. The system automatically identifies unresponsive applications and allows for remote termination via a physical button.

<video autoplay muted loop playsinline width="100%">
  <source src="https://github.com/user-attachments/assets/1b8474a5-d632-4210-93c4-f74908b80f13" type="video/mp4">
  Your browser does not support the video tag.
</video>


## ✨ Features

- **Real-time Process Monitoring**: Continuously scans Windows processes for frozen/unresponsive applications
- **Hardware Alert System**: Arduino-based alert system with OLED display, LED indicators, and buzzer
- **Visual Dashboard**: Color-coded console output with detailed process information
- **Automatic Process Termination**: Safely terminates frozen processes with PID reuse protection
- **Multiple Display Modes**: Compact, detailed, and silent monitoring modes
- **Process Exclusions**: Exclude specific processes from monitoring
- **Test Mode**: Simulate frozen processes for testing without actual crashes
- **Professional OLED Display**: Custom-designed UI with frames, headers, and status indicators
- **Button-Based Control**: Physical button to terminate frozen processes
- **Priority-Based Alerting**: Prioritizes processes by severity and resource usage

## 🛠️ Hardware Requirements

### Arduino Components
- **Arduino Board** (Uno, Nano, or compatible)
- **OLED Display** (128x64, SSD1306, I2C)
- **4-Pin Push Button**
- **Red LED** (for alerts)
- **Green LED** (for normal status)
- **Buzzer** (for audio alerts)
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
git clone https://github.com/yourusername/process-freeze-monitor.git
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
1. **Process Scanning**: Python scans all running processes every 3 seconds
2. **Window Responsiveness**: Uses Windows API to test if application windows respond
3. **Freeze Detection**: Identifies processes with unresponsive windows
4. **Alert Generation**: Creates alert with process details (PID, name, CPU, memory)
5. **Serial Transmission**: Sends alert to Arduino via serial port
6. **Hardware Alert**: Arduino displays alert on OLED, activates red LED and buzzer
7. **User Action**: Press button to send KILL command back to Python
8. **Process Termination**: Python safely terminates the frozen process
9. **Confirmation**: Arduino shows termination confirmation and returns to normal state

### OS Concepts Implemented
- **Process Management**: Monitoring, state tracking, termination
- **Inter-Process Communication**: Serial protocol between Python and Arduino
- **Windows API Integration**: Window message handling and enumeration
- **Interrupt Handling**: Hardware interrupts for button press detection
- **Memory Management**: Memory usage tracking and reporting
- **CPU Utilization**: CPU percentage monitoring and priority assignment
- **Process Scheduling**: Priority-based queue for frozen process handling
- **Concurrency Control**: Atomic operations and thread safety

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
