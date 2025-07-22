#!/usr/bin/env python3
"""
MCP Proxy with NPX fix
"""

import sys
import subprocess
import threading
import json
from datetime import datetime
from pathlib import Path

# NPX full path
NPX_PATH = r"C:\Program Files\nodejs\npx.cmd"

# Create log file
log_file = Path(__file__).parent / "mcp_proxy_minimal.log"
data_dir = Path(__file__).parent / "mcp_captured_data"
data_dir.mkdir(exist_ok=True)

# Session directory
session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
session_name = f"session_{session_id}_{sys.argv[1] if len(sys.argv) > 1 else 'unknown'}"
session_dir = data_dir / session_name
session_dir.mkdir(exist_ok=True)

def log(message):
    """Log to file only"""
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(f"{datetime.now().isoformat()} - {message}\n")

def save_message(content, direction):
    """Save message to session file"""
    try:
        file_path = session_dir / f"{direction}s.jsonl"
        entry = {
            "timestamp": datetime.now().isoformat(),
            "direction": direction,
            "raw_message": content,
            "is_json": True
        }
        
        try:
            parsed = json.loads(content)
            entry["parsed"] = parsed
            entry["method"] = parsed.get("method")
            entry["id"] = parsed.get("id")
        except:
            entry["is_json"] = False
            
        with open(file_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry) + '\n')
    except Exception as e:
        log(f"Error saving message: {e}")

def forward_stdin(process):
    """Forward stdin to subprocess"""
    log("stdin forwarder started")
    try:
        while True:
            line = sys.stdin.readline()
            if not line:
                break
            
            line = line.rstrip('\n')
            log(f"STDIN: {line}")
            save_message(line, "request")
            
            process.stdin.write(line + '\n')
            process.stdin.flush()
    except Exception as e:
        log(f"stdin error: {e}")
    finally:
        log("stdin forwarder stopped")

def forward_stdout(process):
    """Forward subprocess stdout to stdout"""
    log("stdout forwarder started")
    try:
        while True:
            line = process.stdout.readline()
            if not line:
                break
                
            line = line.rstrip('\n')
            log(f"STDOUT: {line}")
            save_message(line, "response")
            
            print(line)
            sys.stdout.flush()
    except Exception as e:
        log(f"stdout error: {e}")
    finally:
        log("stdout forwarder stopped")

def forward_stderr(process):
    """Log stderr but don't forward"""
    log("stderr logger started")
    try:
        while True:
            line = process.stderr.readline()
            if not line:
                break
            log(f"STDERR: {line.rstrip()}")
    except Exception as e:
        log(f"stderr error: {e}")
    finally:
        log("stderr logger stopped")

def main():
    # Get command line arguments
    if len(sys.argv) < 3:
        log("Error: Not enough arguments")
        sys.exit(1)
        
    server_name = sys.argv[1]
    command = sys.argv[2]
    args = sys.argv[3:] if len(sys.argv) > 3 else []
    
    # Fix npx commands
    if command == "npx":
        command = NPX_PATH
        log(f"Replaced npx with: {command}")
    
    log(f"Starting proxy for {server_name}")
    log(f"Command: {command} {' '.join(args)}")
    log(f"Session: {session_name}")
    
    # Set environment variables for specific servers
    import os
    env = os.environ.copy()
    
    if server_name == "brave-search":
        env["BRAVE_API_KEY"] = "BSATj9TafDMVj2FfWqPK51OCyckivGR"
    elif server_name == "mcp-nvd":
        env["NVD_API_KEY"] = "0b2af499-c29b-4a5c-818e-e477836381b6"
    
    # Start subprocess
    try:
        process = subprocess.Popen(
            [command] + args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=0,
            env=env,
            shell=(command.endswith('.cmd') or command.endswith('.bat'))
        )
        
        log(f"Started subprocess PID: {process.pid}")
        
        # Start forwarding threads
        stdin_thread = threading.Thread(target=forward_stdin, args=(process,))
        stdout_thread = threading.Thread(target=forward_stdout, args=(process,))
        stderr_thread = threading.Thread(target=forward_stderr, args=(process,))
        
        stdin_thread.daemon = True
        stdout_thread.daemon = True
        stderr_thread.daemon = True
        
        stdin_thread.start()
        stdout_thread.start()
        stderr_thread.start()
        
        # Wait for process to complete
        process.wait()
        log(f"Process exited with code: {process.returncode}")
        
    except Exception as e:
        log(f"Error starting process: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
