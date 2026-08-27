"""Windows process freeze monitor with an Arduino serial alert channel."""

import argparse
import ctypes
from ctypes import wintypes
import heapq
import msvcrt
import time
from dataclasses import dataclass
import os
import sys

import psutil
import serial

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
    priority: int


def _unresponsive_pids():
    """Return PIDs whose top-level windows do not answer a bounded ping."""
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
    try:
        connection = serial.Serial(port, BAUD_RATE, timeout=0.2)
        time.sleep(2)
        print(f"{Colors.OKGREEN}[SUCCESS]{Colors.ENDC} Connected to Arduino on {port}")
        return connection
    except serial.SerialException as error:
        print(f"{Colors.FAIL}[ERROR]{Colors.ENDC} Serial port unavailable ({port}): {error}")
        return None


def scan_processes(exclude_processes=None, test_mode=False):
    """Collect process metrics and return only processes that appear frozen."""
    if exclude_processes is None:
        exclude_processes = []
        
    hung_pids = _unresponsive_pids() if hasattr(ctypes, "windll") else set()
    applications = []
    alerts = []
    
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
                
            # Test mode: mark calculator as frozen for testing
            if test_mode and name_normalized in ("calculator", "calculatorapp"):
                alerts.append(ProcessAlert(
                    process.pid, name, 0.0,
                    memory.rss / (1024 * 1024) if memory else 0.0,
                    "running", process.info["create_time"],
                    80,
                ))
                continue
                
            # Only alert if process is hung and has a visible window
            if process.pid in hung_pids:
                alerts.append(ProcessAlert(
                    process.pid, name, process.cpu_percent(None),
                    memory.rss / (1024 * 1024) if memory else 0.0,
                    process.info["status"], process.info["create_time"],
                    80,
                ))
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return applications, alerts


def terminate_process(alert):
    """Terminate only the process observed in the alert, guarding against PID reuse."""
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
    payload = f"ALERT|{alert.pid}|{alert.name[:16]}|{alert.cpu_percent:.1f}|{alert.memory_mb:.1f}|{alert.state}\n"
    connection.write(payload.encode("ascii", errors="replace"))


def report_processes(applications, alerts):
    """Display the process table collected during this scheduler cycle."""
    print("\n" + "="*70)
    print(f"{Colors.HEADER}{Colors.BOLD}Process Monitor Dashboard{Colors.ENDC}")
    print(f"{Colors.OKCYAN}Total Processes: {len(applications)}{Colors.ENDC} | {Colors.FAIL}Frozen: {len(alerts)}{Colors.ENDC}")
    print("="*70)
    
    if alerts:
        print(f"\n{Colors.FAIL}{Colors.BOLD}[FROZEN PROCESSES]{Colors.ENDC}")
        for alert in sorted(alerts, key=lambda a: a.priority, reverse=True):
            print(f"  {Colors.FAIL}*{Colors.ENDC} {Colors.BOLD}{alert.name}{Colors.ENDC} (PID {alert.pid})")
            print(f"     Priority: {alert.priority} | CPU: {alert.cpu_percent:.1f}% | Memory: {alert.memory_mb:.1f}MB")
    
    print(f"\n{Colors.OKGREEN}[ACTIVE PROCESSES]{Colors.ENDC} (top 20 by name):")
    for pid, name in sorted(applications, key=lambda item: item[1].lower())[:20]:
        print(f"  {Colors.OKGREEN}+{Colors.ENDC} {name} (PID {pid})")
    
    if len(applications) > 20:
        print(f"  ... and {len(applications) - 20} more processes")

def choose_alert(alerts, watch_target):
    """Schedule the most urgent frozen process using priority scheduling."""
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
    parser.add_argument("--test", action="store_true", help="Test mode: simulate frozen processes for testing")
    args = parser.parse_args()

    connection = connect_serial(args.port)

    scan_number = 0
    try:
        while True:
            if enter_was_pressed():
                print("Enter pressed; monitoring stopped.")
                break
            scan_number += 1
            applications, alerts = scan_processes(args.exclude, args.test)
            
            if args.compact:
                status = f"{Colors.FAIL}[FROZEN]{Colors.ENDC}" if alerts else f"{Colors.OKGREEN}[OK]{Colors.ENDC}"
                print(f"[{scan_number}] {status} - {Colors.OKCYAN}{len(applications)}{Colors.ENDC} processes, {Colors.FAIL}{len(alerts)}{Colors.ENDC} frozen")
                if alerts:
                    for alert in sorted(alerts, key=lambda a: a.priority, reverse=True):
                        print(f"  {Colors.FAIL}*{Colors.ENDC} {alert.name} (PID {alert.pid}) - CPU: {alert.cpu_percent:.1f}%")
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