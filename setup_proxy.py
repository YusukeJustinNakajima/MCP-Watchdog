#!/usr/bin/env python3
"""
MCPSentinel Proxy Setup
Configure Claude Desktop to use MCPSentinel proxy for monitoring
"""

import json
from pathlib import Path
import sys
import os
import ctypes


class ProxyConfigurator:
    """Configure MCP proxy for Claude Desktop"""
    
    def __init__(self):
        self.claude_config_path = Path.home() / "AppData" / "Roaming" / "Claude" / "claude_desktop_config.json"
        self.proxy_script_path = Path(__file__).parent / "mcp_proxy.py"
        self.backup_suffix = ".backup"
        
        # Use simple "python" command instead of full path
        self.python_command = "python"
        print(f"Using Python command: {self.python_command}")
        
    def validate_environment(self):
        """Validate that all required files exist"""
        if not self.proxy_script_path.exists():
            print(f"Error: Proxy script not found at {self.proxy_script_path}")
            print("Please ensure mcp_proxy.py is in the same directory")
            return False
            
        if not self.claude_config_path.exists():
            print(f"Error: Claude Desktop config not found at {self.claude_config_path}")
            print("Please ensure Claude Desktop is installed")
            return False
        
        # Check if config file is writable
        try:
            import stat
            file_stats = os.stat(self.claude_config_path)
            if not os.access(self.claude_config_path, os.W_OK):
                print(f"⚠️ Warning: Config file may not be writable")
                print("Try running with: python setup_proxy.py --admin")
        except Exception as e:
            print(f"⚠️ Warning: Could not check file permissions: {e}")
            
        return True
    
    def backup_config(self):
        """Create backup of current configuration"""
        backup_path = self.claude_config_path.with_suffix(self.backup_suffix)
        
        # Read current config
        with open(self.claude_config_path, 'r', encoding='utf-8') as f:
            config_data = f.read()
            
        # Write backup
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(config_data)
            
        print(f"✓ Configuration backed up to: {backup_path}")
        
    def update_server_config(self, server_name, server_config):
        """Update individual server configuration to use proxy"""
        print(f"\n  Processing {server_name}:")
        print(f"    Current config: {json.dumps(server_config, indent=6)}")
        
        original_command = server_config.get("command", "")
        original_args = server_config.get("args", [])
        
        # Check if already using proxy
        # Also check for Microsoft Store Python paths
        is_python_command = (
            original_command == "python" or 
            original_command == self.python_command or
            "python.exe" in original_command.lower()
        )
        
        if is_python_command and any("mcp_proxy" in str(arg) for arg in original_args):
            # Already using proxy - skip
            print("    Status: Already using proxy, skipping...")
            return False
        else:
            # Insert proxy wrapper
            print("    Status: Adding proxy wrapper...")
            print(f"    Original command: {original_command}")
            print(f"    Original args: {original_args}")
            
            # Change command to python and wrap original command
            server_config["command"] = self.python_command
            server_config["args"] = [
                str(self.proxy_script_path),
                server_name,
                original_command  # Original command (e.g., "npx")
            ] + original_args  # Original arguments
            
            print(f"    New command: {server_config['command']}")
            print(f"    New args: {server_config['args']}")
            
            return True
                
        return False
    
    def reset_server_config(self, server_name, server_config):
        """Reset server configuration to remove proxy"""
        args = server_config.get("args", [])
        
        # Check if using proxy
        if len(args) >= 3 and "mcp_proxy" in str(args[0]):
            # Extract original command and args
            original_command = args[2]  # The original command is at index 2
            original_args = args[3:]    # Original args start from index 3
            
            # Reset to original configuration
            server_config["command"] = original_command
            server_config["args"] = original_args
            
            print(f"  ✓ Reset {server_name} to original configuration")
            return True
            
        return False
    
    def reset_all_configs(self):
        """Reset all server configurations to remove proxy"""
        print("Resetting all configurations to remove proxy...")
        
        # Read configuration
        with open(self.claude_config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # Reset all servers
        mcp_servers = config.get("mcpServers", {})
        reset_count = 0
        
        for server_name, server_config in mcp_servers.items():
            if self.reset_server_config(server_name, server_config):
                reset_count += 1
        
        # Save configuration
        with open(self.claude_config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
        
        print(f"✓ Reset {reset_count} server(s)")
        return True
    
    def check_claude_running(self):
        """Check if Claude Desktop is running"""
        try:
            import subprocess
            result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq Claude.exe'], 
                                  capture_output=True, text=True)
            if 'Claude.exe' in result.stdout:
                print("\n⚠️ WARNING: Claude Desktop appears to be running!")
                print("Please close Claude Desktop before updating the configuration.")
                response = input("Continue anyway? (y/N): ")
                return response.lower() == 'y'
        except:
            pass
        return True
    
    def configure_proxy(self):
        """Configure all MCP servers to use MCPSentinel proxy"""
        print("MCPSentinel Proxy Configuration")
        print("=" * 60)
        
        # Check if Claude is running
        if not self.check_claude_running():
            print("\nConfiguration cancelled.")
            return False
        
        # Validate environment
        if not self.validate_environment():
            return False
            
        # Backup current configuration
        self.backup_config()
        
        # Read configuration
        print(f"\nReading configuration from: {self.claude_config_path}")
        with open(self.claude_config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        print(f"Config loaded successfully")
        print(f"Found mcpServers: {list(config.get('mcpServers', {}).keys())}")
            
        # Update MCP servers
        mcp_servers = config.get("mcpServers", {})
        updated_count = 0
        
        print("\nUpdating MCP server configurations:")
        for server_name, server_config in mcp_servers.items():
            if self.update_server_config(server_name, server_config):
                print(f"  ✓ {server_name}")
                updated_count += 1
            else:
                print(f"  ⚠ {server_name} - skipped")
                
        # Save updated configuration
        print("\nSaving configuration...")
        print(f"Final config preview:")
        print(json.dumps(config, indent=2)[:500] + "..." if len(json.dumps(config)) > 500 else json.dumps(config, indent=2))
        
        try:
            # Write to temporary file first
            temp_file = self.claude_config_path.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)
            
            # Verify the temporary file was written correctly
            with open(temp_file, 'r', encoding='utf-8') as f:
                verify_config = json.load(f)
            
            if verify_config == config:
                # Replace the original file
                import shutil
                shutil.move(str(temp_file), str(self.claude_config_path))
                print(f"✓ Configuration saved successfully")
            else:
                print("❌ Error: Configuration verification failed")
                return False
                
        except Exception as e:
            print(f"❌ Error saving configuration: {e}")
            print("\nTroubleshooting:")
            print("1. Make sure Claude Desktop is completely closed")
            print("2. Run this script as Administrator")
            print("3. Check if the config file is read-only")
            return False
            
        # Verify the final file
        try:
            with open(self.claude_config_path, 'r', encoding='utf-8') as f:
                final_config = json.load(f)
            
            # Check if our changes are in the final config
            final_servers = final_config.get('mcpServers', {})
            changes_applied = False
            for server_name, server_config in final_servers.items():
                if server_config.get('command') == self.python_command:
                    changes_applied = True
                    break
            
            if not changes_applied:
                print("⚠️ Warning: Changes may not have been applied correctly")
                print("The config file was saved but doesn't contain expected changes")
            else:
                print("✓ Changes verified in the configuration file")
                
        except Exception as e:
            print(f"⚠️ Warning: Could not verify changes: {e}")
            
        print(f"\n✓ Updated {updated_count} server(s)")
        
        # Display next steps
        print("\nNext steps:")
        print("1. Close Claude Desktop completely")
        print("2. Kill any remaining Python processes:")
        print("   taskkill /F /IM python.exe")
        print("3. Restart Claude Desktop")
        print("4. Run baseline builder: python mcp_baseline_builder.py")
        print("5. Start monitoring: python realtime_monitor.py")
        
        return True
    
    def restore_backup(self):
        """Restore configuration from backup"""
        backup_path = self.claude_config_path.with_suffix(self.backup_suffix)
        
        if not backup_path.exists():
            print("Error: No backup found")
            return False
            
        # Copy backup to main config
        with open(backup_path, 'r', encoding='utf-8') as f:
            config_data = f.read()
            
        with open(self.claude_config_path, 'w', encoding='utf-8') as f:
            f.write(config_data)
            
        print(f"✓ Configuration restored from backup")
        return True


def is_admin():
    """Check if running with administrator privileges"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def run_as_admin():
    """Re-run the script with administrator privileges"""
    if is_admin():
        return True
    else:
        # Re-run the program with admin rights
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join(sys.argv), None, 1
        )
        return False


def main():
    """Main execution"""
    # Check for admin rights if having issues
    if "--admin" in sys.argv and not is_admin():
        print("Requesting administrator privileges...")
        if not run_as_admin():
            return
    
    configurator = ProxyConfigurator()
    
    # Check for command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "--restore":
            configurator.restore_backup()
            return
        elif sys.argv[1] == "--reset":
            configurator.reset_all_configs()
            return
            
    # Configure proxy
    configurator.configure_proxy()


if __name__ == "__main__":
    main()