#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Real-time MCP monitoring with anomaly detection
"""
import time
import os
import json
import pickle
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional
import sys

# Import detector from same directory
try:
    from mcp_anomaly_detector import SimpleTopicAnomalyDetector
except ImportError:
    print("Error: mcp_anomaly_detector.py not found. Please ensure it's in the same directory.")
    sys.exit(1)


class MCPRealtimeMonitor:
    """Real-time MCP monitor with anomaly detection"""
    
    def __init__(self, baseline_file: str = "mcp_baseline.pkl"):
        self.data_dir = Path("mcp_captured_data")
        self.seen_files = set()
        self.seen_content = {}
        self.detector = None
        self.anomaly_log = []
        self.stats = {
            'total_requests': 0,
            'total_anomalies': 0,
            'anomalies_by_tool': {}
        }
        
        # Load baseline
        self.load_baseline(baseline_file)
        
        # Color codes (Windows support)
        self.colors = {
            'red': '\033[91m',
            'green': '\033[92m',
            'yellow': '\033[93m',
            'blue': '\033[94m',
            'magenta': '\033[95m',
            'cyan': '\033[96m',
            'reset': '\033[0m',
            'bold': '\033[1m'
        }
        
        # Enable color codes on Windows
        if os.name == 'nt':
            os.system('color')
    
    def load_baseline(self, baseline_file: str):
        """Load baseline from file"""
        baseline_path = Path(baseline_file)
        
        if baseline_path.exists():
            try:
                with open(baseline_path, 'rb') as f:
                    baseline_data = pickle.load(f)
                    self.detector = baseline_data['detector']
                    print(f"✓ Baseline loaded from {baseline_file}")
                    
                    # Display learned topics summary
                    summary = self.detector.get_summary()
                    print(f"  - Learned tools: {len(summary)}")
                    total_requests = sum(info['total_requests'] for info in summary.values())
                    print(f"  - Total requests in baseline: {total_requests}")
                    
            except Exception as e:
                print(f"Warning: Error loading baseline: {e}")
                print("  Creating new detector...")
                self.detector = SimpleTopicAnomalyDetector(sensitivity=0.7)
        else:
            print(f"Warning: Baseline file not found: {baseline_file}")
            print("  Creating new detector...")
            self.detector = SimpleTopicAnomalyDetector(sensitivity=0.7)
            print("  Run 'python mcp_baseline_builder.py' to create a baseline.")
    
    def colorize(self, text: str, color: str, bold: bool = False) -> str:
        """Add color to text"""
        result = self.colors.get(color, '')
        if bold:
            result += self.colors['bold']
        result += text + self.colors['reset']
        return result
    
    def check_anomaly(self, data: dict) -> Optional[Dict]:
        """Check request for anomalies"""
        if not self.detector:
            return None
            
        # Only check tools/call
        if data.get('parsed', {}).get('method') != 'tools/call':
            return None
            
        try:
            result = self.detector.detect_anomaly(data)
            
            # Update statistics
            self.stats['total_requests'] += 1
            
            if result['is_anomaly']:
                self.stats['total_anomalies'] += 1
                tool = result.get('tool', 'unknown')
                self.stats['anomalies_by_tool'][tool] = self.stats['anomalies_by_tool'].get(tool, 0) + 1
                self.anomaly_log.append({
                    'timestamp': datetime.now(),
                    'result': result,
                    'data': data
                })
                
            return result
            
        except Exception as e:
            print(f"Error in anomaly detection: {e}")
            return None
    
    def format_anomaly_alert(self, result: Dict) -> str:
        """Format anomaly alert message"""
        alert_lines = []
        
        # Header
        severity = "HIGH" if result['confidence'] > 0.9 else "MEDIUM"
        header = f"{'='*60}\nANOMALY DETECTED - {severity} SEVERITY\n{'='*60}"
        alert_lines.append(self.colorize(header, 'red', bold=True))
        
        # Details
        alert_lines.append(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        alert_lines.append(f"Tool: {self.colorize(result['tool'], 'yellow')}")
        alert_lines.append(f"Query: {self.colorize(result['query'][:100], 'cyan')}")
        alert_lines.append(f"Confidence: {self.colorize(f'{result["confidence"]:.1%}', 'red', bold=True)}")
        
        # New topics
        if result.get('new_topics'):
            new_topics = ', '.join(result['new_topics'])
            alert_lines.append(f"New Topics: {self.colorize(new_topics, 'magenta', bold=True)}")
        
        # Reason
        alert_lines.append(f"Reason: {result['reason']}")
        
        # Similar normal queries
        if result.get('common_topics'):
            common = ', '.join(result['common_topics'][:3])
            alert_lines.append(f"Expected topics: {self.colorize(common, 'green')}")
        
        alert_lines.append('='*60)
        
        return '\n'.join(alert_lines)
    
    def monitor(self):
        """Main monitoring loop"""
        print(self.colorize("\nReal-time MCP Monitor with Anomaly Detection", 'cyan', bold=True))
        print("=" * 60)
        print("Watching for new sessions and detecting anomalies...")
        print(f"Anomaly detection: {self.colorize('ENABLED', 'green') if self.detector else self.colorize('DISABLED', 'red')}")
        print("Press Ctrl+C to stop\n")
        
        # Initialize existing files
        if self.data_dir.exists():
            for f in self.data_dir.rglob("*.jsonl"):
                self.seen_files.add(f)
                try:
                    with open(f, 'r', encoding='utf-8') as file:
                        self.seen_content[f] = sum(1 for _ in file)
                except:
                    self.seen_content[f] = 0
        
        try:
            while True:
                if self.data_dir.exists():
                    # Check for new files
                    for f in self.data_dir.rglob("*.jsonl"):
                        if f not in self.seen_files:
                            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] {self.colorize('NEW FILE:', 'yellow')} {f.relative_to(self.data_dir)}")
                            self.seen_files.add(f)
                            self.seen_content[f] = 0
                        
                        # Check for new content in existing files
                        try:
                            with open(f, 'r', encoding='utf-8') as file:
                                lines = file.readlines()
                                current_count = len(lines)
                                
                                if current_count > self.seen_content.get(f, 0):
                                    # Process new lines
                                    for line in lines[self.seen_content.get(f, 0):]:
                                        try:
                                            data = json.loads(line)
                                            self.process_data(data)
                                            
                                        except json.JSONDecodeError:
                                            print(f"[{datetime.now().strftime('%H:%M:%S')}] Invalid JSON: {line[:100]}")
                                        except Exception as e:
                                            print(f"[{datetime.now().strftime('%H:%M:%S')}] Error: {e}")
                                    
                                    self.seen_content[f] = current_count
                                    
                        except Exception as e:
                            pass
                
                time.sleep(0.5)  # Check every 500ms
                
        except KeyboardInterrupt:
            self.show_summary()
    
    def process_data(self, data: dict):
        """Process data and check for anomalies"""
        timestamp = data.get('timestamp', '')
        direction = data.get('direction', '')
        
        if data.get('parsed'):
            method = data['parsed'].get('method', '')
            id_val = data['parsed'].get('id', '')
            
            # Process requests
            if direction == 'request':
                # Normal display
                if method == 'tools/call':
                    # Anomaly detection
                    anomaly_result = self.check_anomaly(data)
                    
                    if anomaly_result and anomaly_result['is_anomaly']:
                        # Display anomaly alert
                        print(f"\n{self.format_anomaly_alert(anomaly_result)}")
                    else:
                        # Display normal request (concise)
                        params = data['parsed'].get('params', {})
                        tool_name = params.get('name', 'unknown')
                        args = params.get('arguments', {})
                        
                        # Extract query text
                        query_preview = ""
                        for field in ['query', 'pattern', 'sql', 'text']:
                            if field in args:
                                query_preview = str(args[field])[:50]
                                break
                        
                        status_icon = self.colorize("✓", 'green') if anomaly_result and not anomaly_result['is_anomaly'] else ""
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] {status_icon} → {tool_name}: {query_preview}...")
                else:
                    # Non-tools/call methods
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] → {method} (id: {id_val})")
            
            # Process responses (only show errors)
            elif direction == 'response' and 'error' in data['parsed']:
                error = data['parsed']['error']
                print(f"[{datetime.now().strftime('%H:%M:%S')}] {self.colorize('← ERROR:', 'red')} {error['message']}")
    
    def show_summary(self):
        """Display monitoring summary"""
        print("\n\n" + "="*60)
        print(self.colorize("Monitoring Summary", 'cyan', bold=True))
        print("="*60)
        
        # Session information
        if self.data_dir.exists():
            sessions = list(self.data_dir.glob("session_*"))
            print(f"Total sessions: {len(sessions)}")
            
            if sessions:
                latest = max(sessions, key=lambda p: p.stat().st_mtime)
                print(f"Latest session: {latest.name}")
        
        # Anomaly detection statistics
        print(f"\n{self.colorize('Anomaly Detection Statistics:', 'yellow')}")
        print(f"Total requests analyzed: {self.stats['total_requests']}")
        print(f"Total anomalies detected: {self.colorize(str(self.stats['total_anomalies']), 'red', bold=True)}")
        
        if self.stats['total_requests'] > 0:
            anomaly_rate = (self.stats['total_anomalies'] / self.stats['total_requests']) * 100
            print(f"Anomaly rate: {self.colorize(f'{anomaly_rate:.1f}%', 'red' if anomaly_rate > 10 else 'green')}")
        
        # Anomalies by tool
        if self.stats['anomalies_by_tool']:
            print(f"\n{self.colorize('Anomalies by tool:', 'yellow')}")
            for tool, count in sorted(self.stats['anomalies_by_tool'].items(), key=lambda x: x[1], reverse=True):
                print(f"  - {tool}: {count}")
        
        # Recent anomalies
        if self.anomaly_log:
            print(f"\n{self.colorize('Recent anomalies:', 'yellow')}")
            for entry in self.anomaly_log[-5:]:  # Last 5
                result = entry['result']
                print(f"  - [{entry['timestamp'].strftime('%H:%M:%S')}] {result['tool']}: {result['query'][:40]}...")
        
        # Save anomaly log
        if self.anomaly_log:
            log_file = f"anomaly_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump([{
                    'timestamp': entry['timestamp'].isoformat(),
                    'tool': entry['result']['tool'],
                    'query': entry['result']['query'],
                    'confidence': entry['result']['confidence'],
                    'new_topics': entry['result'].get('new_topics', []),
                    'reason': entry['result']['reason']
                } for entry in self.anomaly_log], f, indent=2, ensure_ascii=False)
            print(f"\n✓ Anomaly log saved to: {log_file}")


def main():
    """Main execution"""
    monitor = MCPRealtimeMonitor()
    monitor.monitor()


if __name__ == "__main__":
    main()