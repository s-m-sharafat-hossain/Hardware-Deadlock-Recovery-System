"""Windows process freeze monitor with an Arduino serial alert channel.
   Implements Operating System concepts: Process Management, IPC, Priority Scheduling,
   Interrupt Handling, System Calls, and Asynchronous I/O.
"""

import argparse
import ctypes
from ctypes import wintypes
import heapq
import msvcrt
import time
from dataclasses import dataclass
import os
import sys
from enum import Enum

import psutil
import serial

# Process State Enumeration (OS Concept: Process States)
class ProcessState(Enum):
    RUNNING = "running"
    READY = "ready"
    BLOCKED = "blocked"
    SUSPENDED = "suspended"
    TERMINATED = "terminated"
    NOT_RESPONDING = "not_responding"
    DEADLOCKED = "deadlocked"  # OS Concept: Deadlock Detection

# Windows console color support
try:
    import colorama
    colorama.init()
    COLORS_AVAILABLE = True
except ImportError:
    COLORS_AVAILABLE = False

# ANSI color codes
class Colors:
    HEADER = '\033[95m' if COLORS_AVAILABLE else ''
    OKBLUE = '\033[94m' if COLORS_AVAILABLE else ''
    OKCYAN = '\033[96m' if COLORS_AVAILABLE else ''
    OKGREEN = '\033[92m' if COLORS_AVAILABLE else ''
    WARNING = '\033[93m' if COLORS_AVAILABLE else ''
    FAIL = '\033[91m' if COLORS_AVAILABLE else ''
    ENDC = '\033[0m' if COLORS_AVAILABLE else ''
    BOLD = '\033[1m' if COLORS_AVAILABLE else ''
    UNDERLINE = '\033[4m' if COLORS_AVAILABLE else ''

COM_PORT = "COM6"
BAUD_RATE = 9600
SCAN_INTERVAL = 3.0
WINDOW_TIMEOUT_MS = 250
DEADLOCK_THRESHOLD_SECONDS = 40  # OS Concept: Deadlock detection threshold (40s - very conservative)
DEADLOCK_DETECTION_ENABLED = False  # Disable deadlock detection by default to prevent false positives

# OS Concept: Deadlock Detection - Track blocked process durations
blocked_process_tracker = {}  # {pid: block_start_time}

WM_NULL = 0x0000
SMTO_ABORTIFHUNG = 0x0002

WATCH_PROCESS_NAMES = {
    "calculator": {"calculatorapp.exe", "calculator.exe"},
    "terminal": {"windowsterminal.exe", "conhost.exe", "cmd.exe", "powershell.exe", "pwsh.exe"},
}


@dataclass(frozen=True)
class ProcessAlert:
    pid: int
    name: str
    cpu_percent: float
    memory_mb: float
    state: str
    create_time: float
    priority: int  # OS Concept: Priority Scheduling
    process_state: ProcessState  # OS Concept: Process State Tracking


def _unresponsive_pids():
    """Return PIDs whose top-level windows do not answer a bounded ping.
       OS Concept: System Call - Windows API window message handling
    """
    hung = set()
    user32 = ctypes.windll.user32

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def inspect_window(hwnd, _lparam):
        process_id = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(process_id))
        if user32.IsWindowVisible(hwnd) and process_id.value:
            result = wintypes.DWORD()
            response = user32.SendMessageTimeoutW(
                hwnd, WM_NULL, 0, 0, SMTO_ABORTIFHUNG,
                WINDOW_TIMEOUT_MS, ctypes.byref(result)
            )
            if not response:
                hung.add(process_id.value)
        return True

    user32.EnumWindows(inspect_window, 0)
    return hung


def connect_serial(port):
    """Establish serial connection with Arduino.
       OS Concept: Inter-Process Communication (IPC) via Serial/UART
    """
    try:
        connection = serial.Serial(port, BAUD_RATE, timeout=0.2)
        time.sleep(2)
        print(f"{Colors.OKGREEN}[SUCCESS]{Colors.ENDC} Connected to Arduino on {port}")
        return connection
    except serial.SerialException as error:
        print(f"{Colors.FAIL}[ERROR]{Colors.ENDC} Serial port unavailable ({port}): {error}")
        return None


def scan_processes(exclude_processes=None, test_mode=False, enable_deadlock=False):
    """Collect process metrics and return only processes that appear frozen.
       OS Concepts: Process Monitoring, Process State Detection, System Calls, Deadlock Detection
    """
    global blocked_process_tracker
    global DEADLOCK_DETECTION_ENABLED
    
    DEADLOCK_DETECTION_ENABLED = enable_deadlock
    
    if exclude_processes is None:
        exclude_processes = []
        
    hung_pids = _unresponsive_pids() if hasattr(ctypes, "windll") else set()
    applications = []
    alerts = []
    current_time = time.time()
    
    # Windows system processes to exclude from monitoring
    system_processes = {
        "system", "system idle process", "registry", "memcompression",
        "systemsettings", "applicationframehost", "shellhost", "sihost",
        "runtimebroker", "searchhost", "searchindexer", "searchprotocolhost",
        "backgroundtaskhost", "startmenuexperiencehost", "widgetservice",
        "widgets", "textinputhost", "lockapp", "useroobebroker",
        "securityhealthservice", "securityhealthsystray", "wmiregistrationservice",
        "fontdrvhost", "dwm", "lsaiso", "ngciso", "smss", "csrss", "wininit",
        "winlogon", "services", "lsass", "svchost", "taskhostw", "spoolsv",
        "presentationfontcache", "rastls", "unsecapp", "wmiprvse", "wudfhost",
        "sdxhelper", "networkcap", "sysinfocap", "diagscap", "touchpointanalyticsclientservice",
        "crossdeviceresume", "crossdeviceservice", "lanwlanwwanswitchingserviceuwp",
        "officeclicktorun", "rstmwservice", "xtuservice", "syntpenh", "syntpenhservice"
    }
    
    # Add user-specified exclusions
    user_exclusions = {name.lower().replace(".exe", "") for name in exclude_processes}
    
    # Add Calculator to exclusions in normal mode, but allow it in test mode
    # In test mode, we want to detect real Calculator for testing the Arduino button
    if not test_mode:
        system_processes.add("calculator")
        system_processes.add("calculatorapp")
    
    # Test mode: don't create simulated processes - use real detection
    calculator_found = False

    for process in psutil.process_iter(["pid", "name", "status", "create_time", "memory_info"]):
        try:
            name = process.info["name"] or "Unknown"
            memory = process.info["memory_info"]
            process.cpu_percent(None)
            applications.append((process.pid, name))
            
            # Skip system processes and processes without proper names
            if process.pid < 100 or name == "Unknown":
                continue
                
            # Skip Windows system processes (normalize by removing .exe)
            name_normalized = name.lower().replace(".exe", "")
            if name_normalized in system_processes or name_normalized in user_exclusions:
                continue
            
            # OS Concept: Process State Determination
            process_status = process.info["status"]
            if process_status == psutil.STATUS_RUNNING:
                current_state = ProcessState.RUNNING
            elif process_status == psutil.STATUS_SLEEPING:
                current_state = ProcessState.BLOCKED
                # OS Concept: Deadlock Detection - Track blocked process duration
                if DEADLOCK_DETECTION_ENABLED:
                    if process.pid not in blocked_process_tracker:
                        blocked_process_tracker[process.pid] = current_time
                    elif current_time - blocked_process_tracker[process.pid] > DEADLOCK_THRESHOLD_SECONDS:
                        # Process has been blocked too long - potential deadlock
                        current_state = ProcessState.DEADLOCKED
                        alerts.append(ProcessAlert(
                            process.pid, name, process.cpu_percent(None),
                            memory.rss / (1024 * 1024) if memory else 0.0,
                            process.info["status"], process.info["create_time"],
                            100, ProcessState.DEADLOCKED  # Higher priority for deadlocks
                        ))
                        continue
            elif process_status == psutil.STATUS_RUNNING:
                current_state = ProcessState.RUNNING
                # Remove from blocked tracker if now running
                if process.pid in blocked_process_tracker:
                    del blocked_process_tracker[process.pid]
            elif process_status == psutil.STATUS_STOPPED:
                current_state = ProcessState.SUSPENDED
            else:
                current_state = ProcessState.READY
                
            # Test mode: treat real Calculator as frozen for Arduino button testing
            if test_mode and name_normalized in ("calculator", "calculatorapp"):
                # This allows testing the Arduino button with the real Calculator
                # The button will kill the real Calculator when pressed
                alerts.append(ProcessAlert(
                    process.pid, name, process.cpu_percent(None),
                    memory.rss / (1024 * 1024) if memory else 0.0,
                    process.info["status"], process.info["create_time"],
                    80, ProcessState.NOT_RESPONDING
                ))
                continue
                
            # OS Concept: Blocked/Not Responding Detection
            if process.pid in hung_pids:
                # Skip Calculator in normal mode, but allow in test mode
                if not test_mode or name_normalized not in ("calculator", "calculatorapp"):
                    alerts.append(ProcessAlert(
                        process.pid, name, process.cpu_percent(None),
                        memory.rss / (1024 * 1024) if memory else 0.0,
                        process.info["status"], process.info["create_time"],
                        80, ProcessState.NOT_RESPONDING
                    ))
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    
    # Clean up blocked tracker for processes that no longer exist
    blocked_process_tracker = {pid: start_time for pid, start_time in blocked_process_tracker.items() 
                              if any(app[0] == pid for app in applications)}
    

    # In test mode, we'll detect real Calculator when it's frozen
    if test_mode:
        
        pass
    
    return applications, alerts


def terminate_process(alert):
    """Terminate only the process observed in the alert, guarding against PID reuse.
       OS Concept: Process Termination System Call
    """
    try:
        process = psutil.Process(alert.pid)
        if process.create_time() != alert.create_time:
            return f"{Colors.WARNING}[SKIPPED]{Colors.ENDC} PID was reused; refusing to terminate the new process"
        for child in process.children(recursive=True):
            child.kill()
        process.kill()
        return f"{Colors.OKGREEN}[TERMINATED]{Colors.ENDC} {alert.name} (PID {alert.pid})"
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as error:
        return f"{Colors.FAIL}[FAILED]{Colors.ENDC} Could not terminate PID {alert.pid}: {error}"


def send_alert(connection, alert):
    """Send alert to Arduino via serial.
       OS Concept: Inter-Process Communication (IPC)
    """
    # Include process state for Arduino to differentiate deadlock vs freeze
    state_for_arduino = "deadlock" if alert.process_state == ProcessState.DEADLOCKED else "freeze"
    payload = f"ALERT|{alert.pid}|{alert.name[:16]}|{alert.cpu_percent:.1f}|{alert.memory_mb:.1f}|{state_for_arduino}\n"
    connection.write(payload.encode("ascii", errors="replace"))


def report_processes(applications, alerts):
    """Display the process table collected during this scheduler cycle."""
    print("\n" + "="*70)
    print(f"{Colors.HEADER}{Colors.BOLD}Process Monitor Dashboard{Colors.ENDC}")
    print(f"{Colors.OKCYAN}Total Processes: {len(applications)}{Colors.ENDC} | {Colors.FAIL}Issues: {len(alerts)}{Colors.ENDC}")
    print("="*70)
    
    if alerts:
        print(f"\n{Colors.FAIL}{Colors.BOLD}[DETECTED ISSUES]{Colors.ENDC}")
        for alert in sorted(alerts, key=lambda a: a.priority, reverse=True):
            state_indicator = "DEADLOCK" if alert.process_state == ProcessState.DEADLOCKED else "FROZEN"
            state_color = Colors.WARNING if alert.process_state == ProcessState.DEADLOCKED else Colors.FAIL
            print(f"  {state_color}[{state_indicator}]{Colors.ENDC} {Colors.BOLD}{alert.name}{Colors.ENDC} (PID {alert.pid})")
            print(f"     Priority: {alert.priority} | CPU: {alert.cpu_percent:.1f}% | Memory: {alert.memory_mb:.1f}MB")
    
    print(f"\n{Colors.OKGREEN}[ACTIVE PROCESSES]{Colors.ENDC} (top 20 by name):")
    for pid, name in sorted(applications, key=lambda item: item[1].lower())[:20]:
        print(f"  {Colors.OKGREEN}+{Colors.ENDC} {name} (PID {pid})")
    
    if len(applications) > 20:
        print(f"  ... and {len(applications) - 20} more processes")

def choose_alert(alerts, watch_target):
    """Schedule the most urgent frozen process using priority scheduling.
       OS Concept: Priority Scheduling (uses heap queue for ready queue management)
    """
    if watch_target != "all":
        allowed_names = WATCH_PROCESS_NAMES[watch_target]
        alerts = [alert for alert in alerts if alert.name.lower() in allowed_names]
    if not alerts:
        return None

    # The heap is the ready queue: higher priority and memory use are handled first.
    ready_queue = [(-alert.priority, -alert.memory_mb, alert.pid, alert) for alert in alerts]
    heapq.heapify(ready_queue)
    return heapq.heappop(ready_queue)[-1]


def enter_was_pressed():
    """Return True when Enter is pressed in the monitor console."""
    if msvcrt.kbhit():
        return msvcrt.getwch() in ("\r", "\n")
    return False


def wait_for_command(connection, alert):
    print(f"{Colors.WARNING}[WAITING]{Colors.ENDC} Alert sent for {alert.name} (PID {alert.pid}); waiting for KILL.")
    while True:
        if enter_was_pressed():
            print(f"{Colors.WARNING}[STOPPED]{Colors.ENDC} Enter pressed; monitoring stopped.")
            return False
        command = connection.readline().decode("ascii", errors="ignore").strip()
        if command in ("KILL", f"KILL|{alert.pid}"):
            result = terminate_process(alert)
            connection.write(f"ACK|{alert.pid}\n".encode("ascii"))
            print(f"{Colors.OKGREEN}[RESULT]{Colors.ENDC} {result}")
            return True


def main():
    parser = argparse.ArgumentParser(description="Detect and recover Windows frozen processes")
    parser.add_argument("--port", default=COM_PORT, help="Arduino COM port")
    parser.add_argument("--interval", type=float, default=SCAN_INTERVAL, help="Seconds between scans")
    parser.add_argument(
        "--watch", choices=["all", *sorted(WATCH_PROCESS_NAMES)], default="all",
        help="Frozen process group to monitor (default: all)",
    )
    parser.add_argument("--no-display", action="store_true", help="Hide process list, show only frozen processes")
    parser.add_argument("--compact", action="store_true", help="Compact mode: minimal output with status indicators")
    parser.add_argument("--exclude", nargs="*", default=[], help="Process names to exclude from monitoring (e.g., --exclude calculator notepad)")
    parser.add_argument("--test", action="store_true", help="Test mode: treats real Calculator as frozen for Arduino button testing")
    parser.add_argument("--enable-deadlock", action="store_true", help="Enable deadlock detection (disabled by default to prevent false positives)")
    args = parser.parse_args()

    connection = connect_serial(args.port)

    scan_number = 0
    try:
        while True:
            if enter_was_pressed():
                print("Enter pressed; monitoring stopped.")
                break
            scan_number += 1
            applications, alerts = scan_processes(args.exclude, args.test, args.enable_deadlock)
            
            if args.compact:
                if alerts:
                    # Check if any deadlock alerts
                    has_deadlock = any(alert.process_state == ProcessState.DEADLOCKED for alert in alerts)
                    status = f"{Colors.WARNING}[DEADLOCK]{Colors.ENDC}" if has_deadlock else f"{Colors.FAIL}[FROZEN]{Colors.ENDC}"
                else:
                    status = f"{Colors.OKGREEN}[OK]{Colors.ENDC}"
                
                print(f"[{scan_number}] {status} - {Colors.OKCYAN}{len(applications)}{Colors.ENDC} processes, {Colors.FAIL}{len(alerts)}{Colors.ENDC} issues")
                if alerts:
                    for alert in sorted(alerts, key=lambda a: a.priority, reverse=True):
                        state_symbol = "D" if alert.process_state == ProcessState.DEADLOCKED else "*"
                        state_color = Colors.WARNING if alert.process_state == ProcessState.DEADLOCKED else Colors.FAIL
                        print(f"  {state_color}{state_symbol}{Colors.ENDC} {alert.name} (PID {alert.pid}) - CPU: {alert.cpu_percent:.1f}%")
            elif args.no_display:
                if alerts:
                    print(f"\n{Colors.FAIL}{Colors.BOLD}[FROZEN PROCESSES DETECTED]{Colors.ENDC} (Scan {scan_number}):")
                    for alert in sorted(alerts, key=lambda a: a.priority, reverse=True):
                        print(f"  {Colors.FAIL}*{Colors.ENDC} {alert.name} (PID {alert.pid}) - Priority: {alert.priority}, CPU: {alert.cpu_percent:.1f}%")
                else:
                    print(f"[{scan_number}] {Colors.OKGREEN}[OK]{Colors.ENDC} No frozen processes detected")
            else:
                print(f"\nScan {scan_number}: {len(applications)} processes, {len(alerts)} alerts")
                report_processes(applications, alerts)
            alert = choose_alert(alerts, args.watch)
            if alert:
                if not args.compact:
                    print(
                        f"{Colors.FAIL}{Colors.BOLD}[FREEZE ALERT]{Colors.ENDC} {alert.name} (PID {alert.pid}) "
                        f"priority={alert.priority} state={alert.state}"
                    )
                if connection is not None:
                    send_alert(connection, alert)
                    if not wait_for_command(connection, alert):
                        break
                else:
                    print(f"{Colors.WARNING}[WARNING]{Colors.ENDC} {alert.name} is not responding (PID {alert.pid})")
            for _ in range(max(1, int(args.interval * 10))):
                if enter_was_pressed():
                    print("Enter pressed; monitoring stopped.")
                    return
                time.sleep(0.1)
    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}[STOPPED]{Colors.ENDC} Monitoring stopped by user.")
    finally:
        if connection is not None:
            connection.close()
            print(f"{Colors.OKGREEN}[CLEANUP]{Colors.ENDC} Arduino connection closed.")


if __name__ == "__main__":
    main()