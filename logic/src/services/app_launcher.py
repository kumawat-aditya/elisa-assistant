# utils/app_launcher.py
import subprocess
import os
import platform
import glob
from difflib import get_close_matches
import shutil # For finding executables on Windows

def get_linux_gui_apps():
    """Fetch GUI applications from .desktop entries on Linux."""
    app_names = set()
    desktop_paths = [
        "/usr/share/applications/*.desktop",
        "/usr/local/share/applications/*.desktop",
        os.path.expanduser("~/.local/share/applications/*.desktop")
    ]
    for path_pattern in desktop_paths:
        for desktop_file in glob.glob(path_pattern):
            try:
                app_name = None
                exec_command = None
                with open(desktop_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.startswith("Name="):
                            app_name = line.strip().split("=", 1)[1]
                        if line.startswith("Exec="):
                            # Get the first part of the exec command, before %U, %F, etc.
                            exec_command = line.strip().split("=", 1)[1].split(" ")[0]
                            # Sometimes exec_command is a full path, sometimes just a name
                            # If it's just a name, we'll rely on it being in PATH
                        if app_name and exec_command: # Found both, good enough
                            break
                if app_name:
                    # Prefer the simple name, but store exec_command if needed
                    app_names.add(app_name.lower()) 
                    # You could store a dict: app_name.lower() -> exec_command
            except Exception:
                continue # Ignore malformed .desktop files
    return list(app_names)

def get_windows_installed_apps():
    """
    Attempts to list applications from common locations on Windows.
    This is more heuristic than Linux's .desktop files.
    """
    app_names = set()
    # Common Program Files locations
    program_files_paths = [
        os.environ.get("ProgramFiles", "C:\\Program Files"),
        os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs") # For some user-installed apps
    ]
    # Start Menu locations
    start_menu_paths = [
        os.path.join(os.environ.get("APPDATA", ""), "Microsoft\\Windows\\Start Menu\\Programs"),
        os.path.join(os.environ.get("ALLUSERSPROFILE", "C:\\ProgramData"), "Microsoft\\Windows\\Start Menu\\Programs")
    ]

    # Scan for .exe files in program files (can be slow and generate many results)
    # for pf_path in program_files_paths:
    #     if os.path.exists(pf_path):
    #         for root, dirs, files in os.walk(pf_path, topdown=True, max_depth=3): # Limit depth
    #             for file in files:
    #                 if file.lower().endswith(".exe"):
    #                     app_names.add(os.path.splitext(file)[0].lower())

    # More reliably, scan Start Menu shortcuts (.lnk files)
    for sm_path in start_menu_paths:
        if os.path.exists(sm_path):
            for root, dirs, files in os.walk(sm_path):
                for file in files:
                    if file.lower().endswith(".lnk"):
                        app_names.add(os.path.splitext(file)[0].lower())
    return list(app_names)


def find_best_match(app_name_query: str, available_app_names: list):
    """Find the closest matching app name using fuzzy matching."""
    app_name_query = app_name_query.lower()
    matches = get_close_matches(app_name_query, [name.lower() for name in available_app_names], n=1, cutoff=0.6) # Adjusted cutoff
    if matches:
        # Find the original casing
        for original_name in available_app_names:
            if original_name.lower() == matches[0]:
                return original_name
    return None

def open_application(app_name_query: str):
    """Open an application by finding the closest matching name, cross-platform."""
    os_platform = platform.system().lower()
    app_name_query = app_name_query.lower() # Normalize query

    if os_platform == "linux":
        # For Linux, we can try to find the executable name and run it directly,
        # or use xdg-open for .desktop names if we refine get_linux_gui_apps
        # For simplicity now, let's try common commands or rely on PATH
        
        # Common Linux commands mapping (add more as needed)
        linux_common_apps = {
            "firefox": ["firefox", "firefox-esr"],
            "chrome": ["google-chrome-stable", "google-chrome", "chromium-browser", "chromium"],
            "terminal": ["gnome-terminal", "konsole", "xfce4-terminal", "xterm"],
            "text editor": ["gedit", "kate", "mousepad", "code", "subl"], # 'code' for VS Code, 'subl' for Sublime
            "visual studio code": ["code"],
            "files": ["nautilus", "dolphin", "thunar"],
            "calculator": ["gnome-calculator", "kcalc"],
        }
        
        possible_commands = linux_common_apps.get(app_name_query)
        if not possible_commands and app_name_query: # If not a common mapped name, try query directly
            possible_commands = [app_name_query]

        if possible_commands:
            for cmd_name in possible_commands:
                # Check if command exists in PATH
                if shutil.which(cmd_name):
                    try:
                        # Detach the process so it doesn't block the action server
                        subprocess.Popen([cmd_name]) 
                        return f"Attempting to open {cmd_name}..."
                    except Exception as e:
                        print(f"Error running {cmd_name}: {e}")
                        continue # Try next command in list
            return f"Could not find or run '{app_name_query}'. Make sure it's installed and in your PATH."
        else:
            return f"I don't know how to open '{app_name_query}' on Linux yet."

    elif os_platform == "windows":
        # On Windows, 'start' command is quite versatile for launching apps
        # It can launch executables in PATH, registered apps, and even some document types.
        # For specific apps, you might need their .exe name.
        
        # Common Windows apps mapping (add more)
        # Keys are lowercase queries, values are commands/exe names
        windows_common_apps = {
            "notepad": "notepad.exe",
            "calculator": "calc.exe",
            "paint": "mspaint.exe",
            "explorer": "explorer.exe", # Opens File Explorer
            "file explorer": "explorer.exe",
            "cmd": "cmd.exe",
            "command prompt": "cmd.exe",
            "powershell": "powershell.exe",
            "firefox": "firefox.exe", # Assumes firefox is in PATH or registered
            "chrome": "chrome.exe",   # Assumes chrome is in PATH or registered
            "edge": "msedge.exe",
            "visual studio code": "code.exe" # if 'code' added to PATH during install
        }

        command_to_run = windows_common_apps.get(app_name_query)
        
        if not command_to_run:
            # If not in common map, try the query directly if it ends with .exe
            # Or try with 'start' which might find it if it's a registered app name
            if app_name_query.endswith(".exe"):
                command_to_run = app_name_query
            else:
                # Try 'start' with the app name, it might be a registered app or alias
                 try:
                    # Using shell=True with 'start' is common on Windows for this.
                    # Be cautious with shell=True if app_name_query could be malicious.
                    # Here, app_name_query is from a slot, so hopefully sanitized by Rasa/user.
                    subprocess.Popen(f'start "" "{app_name_query}"', shell=True)
                    return f"Attempting to open '{app_name_query}' on Windows..."
                 except Exception as e:
                    print(f"Error trying 'start {app_name_query}': {e}")
                    return f"Could not open '{app_name_query}' on Windows. Error: {e}"

        if command_to_run:
            try:
                # For specific .exe, try 'start' as well for better behavior (detaching)
                subprocess.Popen(['start', '', command_to_run], shell=True)
                return f"Attempting to open {command_to_run} on Windows..."
            except Exception as e:
                print(f"Error running 'start {command_to_run}': {e}")
                # Fallback: try finding it in PATH directly (less common for GUI apps without 'start')
                if shutil.which(command_to_run):
                    try:
                        subprocess.Popen([command_to_run])
                        return f"Attempting to open {command_to_run} (direct) on Windows..."
                    except Exception as e2:
                        return f"Could not open '{app_name_query}'. Error: {e2}"
                return f"Could not open '{app_name_query}'. Command '{command_to_run}' not found or failed."
        else:
             return f"I don't have a specific command for '{app_name_query}' on Windows."


    elif os_platform == "darwin": # macOS
        # On macOS, 'open -a ApplicationName' is used.
        # You might need to map app_name_query to the actual Application.app name.
        # Example: "text editor" -> "TextEdit"
        macos_common_apps = {
            "firefox": "Firefox",
            "chrome": "Google Chrome",
            "safari": "Safari",
            "terminal": "Terminal",
            "textedit": "TextEdit",
            "visual studio code": "Visual Studio Code",
            "calculator": "Calculator",
            "files": "Finder" # 'open -a Finder' opens a new Finder window
        }
        
        app_to_open = macos_common_apps.get(app_name_query, app_name_query.capitalize()) # Default to capitalized
        
        try:
            subprocess.Popen(["open", "-a", app_to_open])
            return f"Attempting to open {app_to_open} on macOS..."
        except Exception as e:
            return f"Could not open '{app_to_open}' on macOS. Error: {e}"
    else:
        return f"Opening applications is not specifically supported for OS '{os_platform}' yet."