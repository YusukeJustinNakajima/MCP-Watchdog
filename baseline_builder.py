#!/usr/bin/env python3
"""
MCP Baseline Builder
Builds baseline from actual session data
"""

import json
import os
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime
import pickle
from typing import Dict, List, Set

# Import existing detector
from mcp_anomaly_detector import SimpleTopicAnomalyDetector


class BaselineBuilder:
    """Build baseline from MCP session data"""
    
    def __init__(self, data_dir: str = "./mcp_captured_data"):
        self.data_dir = Path(data_dir)
        self.detector = SimpleTopicAnomalyDetector(sensitivity=0.7)
        self.stats = defaultdict(lambda: {
            'total_calls': 0,
            'unique_queries': set(),
            'tools': Counter(),
            'sessions': set()
        })
        
    def build_baseline(self):
        """Build baseline from all sessions"""
        print("=== Building Baseline from Session Data ===\n")
        
        # Get session directories
        session_dirs = [d for d in self.data_dir.iterdir() if d.is_dir() and d.name.startswith('session_')]
        
        if not session_dirs:
            print(f"No session directories found in {self.data_dir}")
            return
        
        print(f"Found {len(session_dirs)} session directories")
        
        total_tools_calls = 0
        all_requests = []
        
        # Process each session
        for session_dir in sorted(session_dirs):
            session_name = session_dir.name
            service_name = session_name.split('_')[-1]  # Last part is service name
            
            requests_file = session_dir / "requests.jsonl"
            if not requests_file.exists():
                print(f"  Warning: No requests.jsonl in {session_name}")
                continue
            
            print(f"\nProcessing {session_name}...")
            session_tools_calls = 0
            
            # Read requests.jsonl
            with open(requests_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        data = json.loads(line.strip())
                        
                        # Extract only tools/call
                        if data.get('parsed', {}).get('method') == 'tools/call':
                            total_tools_calls += 1
                            session_tools_calls += 1
                            all_requests.append(data)
                            
                            # Collect statistics
                            params = data['parsed']['params']
                            tool_name = params.get('name', 'unknown')
                            
                            self.stats[service_name]['total_calls'] += 1
                            self.stats[service_name]['tools'][tool_name] += 1
                            self.stats[service_name]['sessions'].add(session_name)
                            
                            # Record query text if available
                            args = params.get('arguments', {})
                            query_text = self._extract_query_text(args)
                            if query_text:
                                self.stats[service_name]['unique_queries'].add(query_text)
                            
                            # Train detector
                            self.detector.learn(data)
                            
                    except json.JSONDecodeError as e:
                        print(f"  JSON decode error: {e}")
                    except Exception as e:
                        print(f"  Error processing line: {e}")
            
            print(f"  Found {session_tools_calls} tools/call requests")
        
        print(f"\n{'='*60}")
        print(f"Total tools/call requests processed: {total_tools_calls}")
        print(f"{'='*60}\n")
        
        # Display statistics
        self._display_statistics()
        
        # Display learned topics
        self._display_learned_topics()
        
        # Save baseline
        self._save_baseline()
        
        return all_requests
    
    def _extract_query_text(self, args: dict) -> str:
        """Extract query text from arguments"""
        # Check various field names
        for field in ['query', 'q', 'search', 'text', 'sql', 'command', 'prompt', 'pattern', 'message']:
            if field in args:
                return str(args[field])
        
        # Special cases
        if 'block_id' in args:
            return f"block:{args['block_id']}"
        
        if 'cve_id' in args:
            return f"cve:{args['cve_id']}"
            
        # Find any string value
        for key, value in args.items():
            if isinstance(value, str) and len(value) > 0:
                return f"{key}:{value}"
        
        return ""
    
    def _display_statistics(self):
        """Display collected statistics"""
        print("=== Service Statistics ===\n")
        
        for service, stats in sorted(self.stats.items()):
            print(f"Service: {service}")
            print(f"  Total calls: {stats['total_calls']}")
            print(f"  Unique queries: {len(stats['unique_queries'])}")
            print(f"  Sessions: {len(stats['sessions'])}")
            print(f"  Tools used:")
            
            for tool, count in stats['tools'].most_common():
                print(f"    - {tool}: {count} calls")
            
            # Display sample queries
            if stats['unique_queries']:
                print(f"  Sample queries:")
                for i, query in enumerate(list(stats['unique_queries'])[:3]):
                    print(f"    - {query[:60]}{'...' if len(query) > 60 else ''}")
            
            print()
    
    def _display_learned_topics(self):
        """Display learned topics"""
        print("=== Learned Topics by Tool ===\n")
        
        summary = self.detector.get_summary()
        for tool, info in sorted(summary.items()):
            print(f"Tool: {tool}")
            print(f"  Total requests: {info['total_requests']}")
            print(f"  Unique topics: {info['unique_topics']}")
            
            if info['top_topics']:
                print(f"  Top topics:")
                for topic, count in info['top_topics'][:10]:
                    print(f"    - {topic}: {count}")
            print()
    
    def _save_baseline(self):
        """Save baseline to file"""
        baseline_file = Path("mcp_baseline.pkl")
        
        baseline_data = {
            'detector': self.detector,
            'stats': dict(self.stats),
            'created_at': datetime.now().isoformat(),
            'total_sessions': len([d for d in self.data_dir.iterdir() if d.is_dir() and d.name.startswith('session_')])
        }
        
        with open(baseline_file, 'wb') as f:
            pickle.dump(baseline_data, f)
        
        print(f"Baseline saved to {baseline_file}")
        
        # Save human-readable JSON summary
        json_file = Path("mcp_baseline_summary.json")
        json_data = {
            'created_at': baseline_data['created_at'],
            'total_sessions': baseline_data['total_sessions'],
            'services': {}
        }
        
        for service, stats in self.stats.items():
            json_data['services'][service] = {
                'total_calls': stats['total_calls'],
                'unique_queries': len(stats['unique_queries']),
                'tools': dict(stats['tools']),
                'sample_queries': list(stats['unique_queries'])[:10]
            }
        
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)
        
        print(f"Summary saved to {json_file}")


def test_anomaly_detection(baseline_file: str = "mcp_baseline.pkl"):
    """Test anomaly detection with saved baseline"""
    print("\n=== Testing Anomaly Detection ===\n")
    
    # Load baseline
    with open(baseline_file, 'rb') as f:
        baseline_data = pickle.load(f)
    
    detector = baseline_data['detector']
    
    # Test cases
    test_cases = [
        # Normal: existing pattern
        {
            "timestamp": "2025-07-23T10:00:00",
            "parsed": {
                "method": "tools/call",
                "params": {
                    "name": "API-post-search",
                    "arguments": {"query": "Customer Service Guidelines"}
                }
            }
        },
        # Anomaly: new topic
        {
            "timestamp": "2025-07-23T10:00:01",
            "parsed": {
                "method": "tools/call",
                "params": {
                    "name": "API-post-search",
                    "arguments": {"query": "Database Administration Manual"}
                }
            }
        },
        # Anomaly: security-related
        {
            "timestamp": "2025-07-23T10:00:02",
            "parsed": {
                "method": "tools/call",
                "params": {
                    "name": "search_files",
                    "arguments": {"pattern": "password.txt"}
                }
            }
        },
        # Normal: block ID
        {
            "timestamp": "2025-07-23T10:00:03",
            "parsed": {
                "method": "tools/call",
                "params": {
                    "name": "API-get-block-children",
                    "arguments": {"block_id": "12345678-abcd-efgh-ijkl-1234567890ab"}
                }
            }
        },
        # Anomaly: SQL injection pattern
        {
            "timestamp": "2025-07-23T10:00:04",
            "parsed": {
                "method": "tools/call",
                "params": {
                    "name": "query",
                    "arguments": {"sql": "SELECT * FROM users WHERE admin=1; DROP TABLE users;--"}
                }
            }
        },
        # Normal: CVE lookup
        {
            "timestamp": "2025-07-23T10:00:05",
            "parsed": {
                "method": "tools/call",
                "params": {
                    "name": "get_cve",
                    "arguments": {"cve_id": "CVE-2025-5777", "concise": False}
                }
            }
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest Case {i}:")
        result = detector.detect_anomaly(test_case)
        
        tool = result.get('tool', 'unknown')
        query = result.get('query', 'N/A')
        
        print(f"  Tool: {tool}")
        print(f"  Query: {query[:60]}{'...' if len(query) > 60 else ''}")
        print(f"  Result: {'ANOMALY' if result['is_anomaly'] else 'NORMAL'}")
        print(f"  Confidence: {result['confidence']:.1%}")
        
        if result.get('new_topics'):
            print(f"  New topics: {', '.join(result['new_topics'])}")
        
        print(f"  Reason: {result['reason']}")


def main():
    """Main execution"""
    # Build baseline
    builder = BaselineBuilder()
    all_requests = builder.build_baseline()
    
    # Test anomaly detection
    if Path("mcp_baseline.pkl").exists():
        test_anomaly_detection()


if __name__ == "__main__":
    main()