#!/usr/bin/env python3
"""
Simple Topic-based Anomaly Detector for MCP
Detects topic changes in MCP requests
"""

import json
import re
from collections import defaultdict, Counter
from datetime import datetime
from typing import Dict, List, Set, Optional
import logging

class SimpleTopicAnomalyDetector:
    """Topic-based anomaly detector for MCP requests"""
    
    def __init__(self, sensitivity: float = 0.8):
        """
        Args:
            sensitivity: Detection sensitivity (0.0-1.0). Higher values detect more anomalies
        """
        self.tool_topics = defaultdict(Counter)  # Topic history per tool
        self.tool_keywords = defaultdict(set)    # Keyword set per tool
        self.sensitivity = sensitivity
        self.min_history = 3  # Minimum history required
        
        # Logging setup
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def extract_topics(self, text: str) -> Set[str]:
        """Extract main topics (keywords) from text"""
        # Convert to lowercase
        text = text.lower()
        
        # Split camelCase (e.g., CustomerSupport → customer support)
        text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
        
        # Replace symbols with spaces
        text = re.sub(r'[^a-z0-9\s]', ' ', text)
        
        # Extract words (2+ characters)
        words = [w for w in text.split() if len(w) >= 2]
        
        # Remove common stopwords
        stopwords = {'the', 'is', 'at', 'to', 'for', 'of', 'and', 'or', 'in', 'on', 'by', 'with', 'from'}
        words = [w for w in words if w not in stopwords]
        
        return set(words)
    
    def learn(self, request: dict):
        """Learn from normal request patterns"""
        tool_name, query_text = self._extract_info(request)
        if not tool_name or not query_text:
            return
        
        topics = self.extract_topics(query_text)
        
        # Record topics
        for topic in topics:
            self.tool_topics[tool_name][topic] += 1
            self.tool_keywords[tool_name].add(topic)
        
        self.logger.debug(f"Learned topics for {tool_name}: {topics}")
    
    def detect_anomaly(self, request: dict) -> Dict:
        """Detect anomalies in request"""
        tool_name, query_text = self._extract_info(request)
        if not tool_name or not query_text:
            return {
                'is_anomaly': False, 
                'reason': 'Invalid request format',
                'tool': tool_name or 'unknown',
                'query': query_text or '',
                'confidence': 0.0,
                'current_topics': [],
                'new_topics': [],
                'known_topics': [],
                'common_topics': [],
                'timestamp': request.get('timestamp', '')
            }
        
        # Skip if insufficient history
        if sum(self.tool_topics[tool_name].values()) < self.min_history:
            return {
                'is_anomaly': False,
                'reason': f'Insufficient history for {tool_name}',
                'confidence': 0.0,
                'tool': tool_name,
                'query': query_text,
                'current_topics': [],
                'new_topics': [],
                'known_topics': [],
                'common_topics': [],
                'timestamp': request.get('timestamp', '')
            }
        
        # Extract current query topics
        current_topics = self.extract_topics(query_text)
        
        # Check overlap with known topics
        known_topics = self.tool_keywords[tool_name]
        overlap = current_topics.intersection(known_topics)
        
        # Calculate new topic ratio
        if not current_topics:
            new_topic_ratio = 0
        else:
            new_topic_ratio = 1 - (len(overlap) / len(current_topics))
        
        # Anomaly determination
        is_anomaly = new_topic_ratio >= self.sensitivity
        
        # Identify new topics
        new_topics = current_topics - known_topics
        
        # Find most common existing topics
        top_existing_topics = self.tool_topics[tool_name].most_common(5)
        
        result = {
            'is_anomaly': is_anomaly,
            'confidence': new_topic_ratio,
            'tool': tool_name,
            'query': query_text,
            'current_topics': list(current_topics),
            'new_topics': list(new_topics),
            'known_topics': list(overlap),
            'common_topics': [t[0] for t in top_existing_topics],
            'timestamp': request.get('timestamp', '')
        }
        
        if is_anomaly:
            result['reason'] = f"Unusual topic detected: {', '.join(new_topics)}"
        else:
            result['reason'] = "Query matches known topics"
        
        return result
    
    def _extract_info(self, request: dict) -> tuple:
        """Extract tool name and query text from request"""
        try:
            parsed = request.get('parsed', {})
            params = parsed.get('params', {})
            tool_name = params.get('name', '')
            args = params.get('arguments', {})
            
            # Extract query text from various field names
            query_text = None
            for field in ['query', 'q', 'search', 'text', 'sql', 'command', 'prompt', 'pattern', 'message']:
                if field in args:
                    query_text = str(args[field])
                    break
            
            # Handle special cases (block_id, cve_id, etc.)
            if not query_text:
                if 'block_id' in args:
                    query_text = f"block operation {args['block_id'][:8]}"
                elif 'cve_id' in args:
                    query_text = f"cve lookup {args['cve_id']}"
                elif 'path' in args:
                    query_text = f"file operation {args.get('path', '')}"
                elif isinstance(args, str):
                    query_text = args
                else:
                    # Generate meaningful text from other parameters
                    parts = []
                    for key, value in args.items():
                        if isinstance(value, str):
                            parts.append(f"{key} {value}")
                    query_text = ' '.join(parts) if parts else None
            
            return tool_name, query_text
        except:
            return None, None
    
    def get_summary(self) -> Dict:
        """Get summary of learned content"""
        summary = {}
        for tool, topics in self.tool_topics.items():
            summary[tool] = {
                'total_requests': sum(topics.values()),
                'unique_topics': len(topics),
                'top_topics': topics.most_common(10)
            }
        return summary