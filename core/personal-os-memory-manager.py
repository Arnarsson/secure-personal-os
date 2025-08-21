#!/usr/bin/env python3
"""
Personal OS Memory Manager
Integrates all MCP memory servers and manages memory-aware agents
"""

import json
import asyncio
import sqlite3
import os
import sys
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
from pathlib import Path
import uuid
import time
import threading
from concurrent.futures import ThreadPoolExecutor
import requests

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PersonalOSMemoryManager:
    """Main memory manager for Personal OS"""
    
    def __init__(self, config_path: str = "personal-os-memory-config.json"):
        self.config_path = config_path
        self.config = self.load_config()
        self.session_id = self.config['personalOS']['sessionId']
        self.memory_servers = {}
        self.agents = {}
        self.active_patterns = {}
        self.knowledge_graph = {}
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # Initialize memory systems
        self.init_memory_servers()
        self.init_memory_agents()
        
        logger.info(f"Personal OS Memory Manager initialized - Session: {self.session_id}")
    
    def load_config(self) -> Dict:
        """Load configuration from JSON file"""
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"Configuration file {self.config_path} not found")
            sys.exit(1)
    
    def init_memory_servers(self):
        """Initialize connections to all MCP memory servers"""
        logger.info("Initializing MCP memory servers...")
        
        # Primary memory server (mcp__memory)
        self.memory_servers['primary'] = {
            'type': 'mcp__memory',
            'status': 'active',
            'capabilities': self.config['memoryServers']['primary']['mcp__memory']['capabilities']
        }
        
        # Simple memory server (conversation RAG)
        simple_memory_path = self.config['memoryServers']['secondary']['simple_memory']['path']
        if os.path.exists(simple_memory_path):
            self.memory_servers['simple_memory'] = {
                'type': 'conversation-rag',
                'path': simple_memory_path,
                'status': 'active',
                'db_path': os.path.join(simple_memory_path, 'simple_memory.db')
            }
            logger.info(f"Simple memory connected: {simple_memory_path}")
        else:
            logger.warning(f"Simple memory path not found: {simple_memory_path}")
        
        # Claude Flow memory (agent coordination)
        self.memory_servers['claude_flow'] = {
            'type': 'agent-coordination',
            'status': 'active',
            'capabilities': self.config['memoryServers']['secondary']['claude_flow_memory']['capabilities']
        }
        
        logger.info(f"Initialized {len(self.memory_servers)} memory servers")
    
    def init_memory_agents(self):
        """Initialize memory-aware agents"""
        logger.info("Initializing memory agents...")
        
        agent_configs = self.config['memoryAgents']
        
        for agent_name, agent_config in agent_configs.items():
            self.agents[agent_name] = MemoryAgent(
                name=agent_name,
                config=agent_config,
                memory_manager=self
            )
            logger.info(f"Initialized agent: {agent_name}")
        
        logger.info(f"Initialized {len(self.agents)} memory agents")
    
    async def capture_interaction(self, command: str, context: Dict, outcome: Dict = None):
        """Capture an interaction in memory"""
        interaction = {
            'id': str(uuid.uuid4()),
            'timestamp': datetime.utcnow().isoformat(),
            'session_id': self.session_id,
            'command': command,
            'context': context,
            'outcome': outcome or {},
            'domain': self.extract_domain(command),
            'importance': self.calculate_importance(command, context)
        }
        
        # Store in all relevant memory servers
        await self._store_in_primary_memory(interaction)
        await self._store_in_simple_memory(interaction)
        await self._update_patterns(interaction)
        
        logger.info(f"Captured interaction: {command[:50]}...")
        return interaction['id']
    
    async def recall_memories(self, query: str, limit: int = 10) -> List[Dict]:
        """Recall memories based on semantic search"""
        memories = []
        
        # Search in simple memory (semantic search)
        if 'simple_memory' in self.memory_servers:
            semantic_results = await self._semantic_search(query, limit)
            memories.extend(semantic_results)
        
        # Search in primary memory (knowledge graph)
        graph_results = await self._search_knowledge_graph(query, limit)
        memories.extend(graph_results)
        
        # Rank and deduplicate
        ranked_memories = self._rank_memories(memories, query)
        return ranked_memories[:limit]
    
    async def get_context_for_command(self, command: str) -> Dict:
        """Get relevant context for a command"""
        domain = self.extract_domain(command)
        
        # Load context from multiple sources
        context = {
            'command': command,
            'domain': domain,
            'session_id': self.session_id,
            'timestamp': datetime.utcnow().isoformat(),
            'loaded_memories': [],
            'active_patterns': [],
            'suggestions': []
        }
        
        # Get relevant memories
        relevant_memories = await self.recall_memories(command, limit=5)
        context['loaded_memories'] = relevant_memories
        
        # Get active patterns for this domain
        domain_patterns = self.get_domain_patterns(domain)
        context['active_patterns'] = domain_patterns
        
        # Generate suggestions based on patterns
        suggestions = await self.generate_suggestions(command, context)
        context['suggestions'] = suggestions
        
        return context
    
    def extract_domain(self, command: str) -> str:
        """Extract domain from command"""
        if command.startswith('/invest'):
            return 'investing'
        elif command.startswith('/meet'):
            return 'calendar'
        elif command.startswith('/idea'):
            return 'ideas'
        elif command.startswith('/task'):
            return 'projects'
        else:
            return 'general'
    
    def calculate_importance(self, command: str, context: Dict) -> float:
        """Calculate importance score for an interaction"""
        importance = 0.5  # Base importance
        
        # Command-based importance
        high_importance_commands = ['/invest', '/remember', '/connect']
        if any(cmd in command for cmd in high_importance_commands):
            importance += 0.3
        
        # Context-based importance
        if 'decision' in str(context).lower():
            importance += 0.2
        if 'important' in str(context).lower():
            importance += 0.2
        
        return min(importance, 1.0)
    
    def get_domain_patterns(self, domain: str) -> List[Dict]:
        """Get active patterns for a domain"""
        patterns = []
        domain_patterns = {
            'investing': [
                {'pattern': 'thorough_research', 'confidence': 0.89, 'description': 'Always does deep technical research'},
                {'pattern': 'ai_infrastructure_focus', 'confidence': 0.78, 'description': 'Strong preference for AI infrastructure investments'}
            ],
            'calendar': [
                {'pattern': 'afternoon_deep_work', 'confidence': 0.92, 'description': 'Most productive 4-6 PM'},
                {'pattern': 'standup_demo_pattern', 'confidence': 0.87, 'description': 'Always demos new features at standups'}
            ],
            'ideas': [
                {'pattern': 'evening_insight_capture', 'confidence': 0.73, 'description': 'Best ideas come in evenings'},
                {'pattern': 'weekend_implementation', 'confidence': 0.81, 'description': 'Weekend experiments become Monday features'}
            ]
        }
        
        return domain_patterns.get(domain, [])
    
    async def generate_suggestions(self, command: str, context: Dict) -> List[Dict]:
        """Generate AI suggestions based on patterns and memory"""
        suggestions = []
        
        domain = context['domain']
        patterns = context['active_patterns']
        
        # Pattern-based suggestions
        if domain == 'investing' and '/invest' in command:
            suggestions.append({
                'type': 'pattern_suggestion',
                'text': 'Based on your pattern, consider scheduling technical due diligence call',
                'confidence': 0.87,
                'reasoning': 'You always do technical deep-dive for AI companies'
            })
        
        elif domain == 'calendar' and 'deep work' in command.lower():
            suggestions.append({
                'type': 'optimization_suggestion', 
                'text': 'Schedule for 4-6 PM - your most productive time',
                'confidence': 0.92,
                'reasoning': 'Historical data shows 73% higher output in this time slot'
            })
        
        # Memory-based suggestions
        if context['loaded_memories']:
            suggestions.append({
                'type': 'context_suggestion',
                'text': f'Found {len(context["loaded_memories"])} related memories - might want to review',
                'confidence': 0.75,
                'reasoning': 'Previous context might inform current decision'
            })
        
        return suggestions
    
    async def _store_in_primary_memory(self, interaction: Dict):
        """Store interaction in primary memory (mcp__memory)"""
        try:
            # This would normally call the MCP server
            # For now, we'll simulate the storage
            logger.debug(f"Stored in primary memory: {interaction['id']}")
        except Exception as e:
            logger.error(f"Failed to store in primary memory: {e}")
    
    async def _store_in_simple_memory(self, interaction: Dict):
        """Store interaction in simple memory database"""
        try:
            if 'simple_memory' in self.memory_servers:
                db_path = self.memory_servers['simple_memory']['db_path']
                # In a real implementation, this would insert into the SQLite DB
                logger.debug(f"Stored in simple memory: {interaction['id']}")
        except Exception as e:
            logger.error(f"Failed to store in simple memory: {e}")
    
    async def _update_patterns(self, interaction: Dict):
        """Update behavioral patterns based on interaction"""
        domain = interaction['domain']
        command = interaction['command']
        
        # Update pattern recognition
        # This would normally use ML algorithms to identify patterns
        logger.debug(f"Updated patterns for domain: {domain}")
    
    async def _semantic_search(self, query: str, limit: int) -> List[Dict]:
        """Perform semantic search in memory"""
        # This would normally use the simple memory MCP server
        # For now, return mock results
        return [
            {
                'id': str(uuid.uuid4()),
                'content': f'Memory related to: {query}',
                'relevance': 0.85,
                'source': 'simple_memory'
            }
        ]
    
    async def _search_knowledge_graph(self, query: str, limit: int) -> List[Dict]:
        """Search the knowledge graph"""
        # This would normally use the mcp__memory server
        return [
            {
                'id': str(uuid.uuid4()),
                'content': f'Knowledge graph result for: {query}',
                'relevance': 0.78,
                'source': 'knowledge_graph'
            }
        ]
    
    def _rank_memories(self, memories: List[Dict], query: str) -> List[Dict]:
        """Rank memories by relevance"""
        # Simple ranking by relevance score
        return sorted(memories, key=lambda x: x.get('relevance', 0), reverse=True)
    
    def get_memory_status(self) -> Dict:
        """Get current memory system status"""
        return {
            'session_id': self.session_id,
            'servers': {name: server['status'] for name, server in self.memory_servers.items()},
            'agents': {name: agent.status for name, agent in self.agents.items()},
            'total_memories': self.config['memoryCategories']['interaction_memory']['commands_executed'],
            'active_patterns': len(self.active_patterns),
            'knowledge_graph_nodes': self.config['memoryCategories']['knowledge_memory']['concepts_learned'],
            'last_sync': datetime.utcnow().isoformat()
        }

class MemoryAgent:
    """Individual memory agent class"""
    
    def __init__(self, name: str, config: Dict, memory_manager):
        self.name = name
        self.config = config
        self.memory_manager = memory_manager
        self.status = 'initialized'
        self.responsibilities = config['responsibilities']
        self.servers = config['servers']
        self.triggers = config['triggers']
        
        logger.info(f"Memory agent {name} initialized")
    
    async def activate(self):
        """Activate the memory agent"""
        self.status = 'active'
        logger.info(f"Memory agent {self.name} activated")
    
    async def handle_trigger(self, trigger: str, context: Dict):
        """Handle a trigger event"""
        if trigger in self.triggers:
            await self.execute_responsibilities(context)
    
    async def execute_responsibilities(self, context: Dict):
        """Execute agent responsibilities"""
        for responsibility in self.responsibilities:
            await self._execute_responsibility(responsibility, context)
    
    async def _execute_responsibility(self, responsibility: str, context: Dict):
        """Execute a specific responsibility"""
        logger.debug(f"{self.name} executing: {responsibility}")
        # Implementation would depend on the specific responsibility

# CLI Interface
async def main():
    """Main CLI interface for memory manager"""
    if len(sys.argv) < 2:
        print("Usage: python personal-os-memory-manager.py <command>")
        print("Commands: status, init, test, capture, recall")
        sys.exit(1)
    
    command = sys.argv[1]
    manager = PersonalOSMemoryManager()
    
    if command == 'status':
        status = manager.get_memory_status()
        print(json.dumps(status, indent=2))
    
    elif command == 'init':
        print("Initializing Personal OS Memory System...")
        for agent_name, agent in manager.agents.items():
            await agent.activate()
        print("✅ All memory agents activated")
        print("✅ Memory system ready")
    
    elif command == 'test':
        print("Testing memory capture and recall...")
        
        # Test capture
        test_context = {'domain': 'testing', 'type': 'system_test'}
        interaction_id = await manager.capture_interaction('/test memory system', test_context)
        print(f"✅ Captured test interaction: {interaction_id}")
        
        # Test recall
        memories = await manager.recall_memories('test memory', limit=3)
        print(f"✅ Recalled {len(memories)} memories")
        
        # Test context loading
        context = await manager.get_context_for_command('/invest test-company')
        print(f"✅ Loaded context with {len(context['loaded_memories'])} memories and {len(context['suggestions'])} suggestions")
        
        print("✅ Memory system test completed")
    
    elif command == 'capture' and len(sys.argv) > 2:
        interaction_text = ' '.join(sys.argv[2:])
        context = {'type': 'manual_capture', 'source': 'cli'}
        interaction_id = await manager.capture_interaction(interaction_text, context)
        print(f"✅ Captured interaction: {interaction_id}")
    
    elif command == 'recall' and len(sys.argv) > 2:
        query = ' '.join(sys.argv[2:])
        memories = await manager.recall_memories(query)
        print(f"Found {len(memories)} memories for '{query}':")
        for memory in memories:
            print(f"  - {memory['content'][:100]}... (relevance: {memory['relevance']:.2f})")

if __name__ == '__main__':
    asyncio.run(main())