"""Power management utilities for executing shutdown, sleep, and hibernate actions"""
import subprocess
import platform
import time


def execute_power_action(action: str, delay_seconds: int = 5):
    """
    Execute a power management action after a delay
    
    Args:
        action: One of 'shutdown', 'sleep', 'hibernate', or 'none'
        delay_seconds: Delay before executing the action (default 5 seconds)
    """
    if action == "none":
        return
    
    # Give user time to see the completion message
    time.sleep(delay_seconds)
    
    system = platform.system()
    
    try:
        if action == "shutdown":
            if system == "Windows":
                subprocess.run(["shutdown", "/s", "/t", "0"], check=False)
            elif system == "Darwin":  # macOS
                subprocess.run(["sudo", "shutdown", "-h", "now"], check=False)
            else:  # Linux
                subprocess.run(["shutdown", "-h", "now"], check=False)
        
        elif action == "sleep":
            if system == "Windows":
                # Use rundll32 to sleep
                subprocess.run(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"], check=False)
            elif system == "Darwin":  # macOS
                subprocess.run(["pmset", "sleepnow"], check=False)
            else:  # Linux
                subprocess.run(["systemctl", "suspend"], check=False)
        
        elif action == "hibernate":
            if system == "Windows":
                subprocess.run(["shutdown", "/h"], check=False)
            elif system == "Darwin":  # macOS
                subprocess.run(["pmset", "hibernatemode", "25"], check=False)
                subprocess.run(["pmset", "sleepnow"], check=False)
            else:  # Linux
                subprocess.run(["systemctl", "hibernate"], check=False)
    
    except Exception as e:
        print(f"Error executing power action '{action}': {e}")
