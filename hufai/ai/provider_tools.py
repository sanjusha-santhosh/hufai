import frappe
from frappe import _
from typing import Dict, List, Callable, Any
import inspect

class ProviderToolRegistry:
    def __init__(self):
        self._tools = {}
        self._providers = {}
    
    def load_tools_from_database(self):
        """Load provider tools from AI Provider Tool doctype"""
        try:
            tools = frappe.get_all(
                "AI Provider Tool",
                filters={"enabled": 1, "expose_to_agents": 1},
                fields=["name", "tool_key", "provider", "tool_type", "schema"]
            )
            
            for tool in tools:
                provider_name = tool.provider
                tool_key = tool.tool_key
                
                if provider_name not in self._providers:
                    self._providers[provider_name] = {}
                
                # Get the implementation from AI Provider Tool
                tool_doc = frappe.get_doc("AI Provider Tool", tool.name)
                implementation = tool_doc.get_tool_implementation()
                
                if implementation:
                    self._providers[provider_name][tool_key] = implementation
                    frappe.logger().info(f"Loaded provider tool: {provider_name}.{tool_key}")
                    
        except Exception as e:
            frappe.log_error(f"Error loading provider tools from database: {str(e)}")
    
    def register_provider(self, provider_name: str, tool_factories: Dict[str, Callable]):
        """Register tools for a specific provider"""
        if provider_name not in self._providers:
            self._providers[provider_name] = {}
        
        self._providers[provider_name].update(tool_factories)
    
    def get_tools_for_provider(self, provider_name: str, agent_doc=None) -> List[Any]:
        """Get all available tools for a provider"""
        if provider_name not in self._providers:
            return []
        
        tools = []
        for tool_key, factory in self._providers[provider_name].items():
            try:
                tool = factory(agent_doc) if inspect.isfunction(factory) else factory
                if tool:
                    tools.append(tool)
            except Exception as e:
                frappe.log_error(f"Error creating provider tool {tool_key}: {str(e)}")
        
        return tools
    
    def get_tool(self, provider_name: str, tool_key: str, agent_doc=None):
        """Get specific tool by key"""
        if provider_name not in self._providers or tool_key not in self._providers[provider_name]:
            return None
        
        factory = self._providers[provider_name][tool_key]
        return factory(agent_doc) if inspect.isfunction(factory) else factory

# Global registry instance
provider_tool_registry = ProviderToolRegistry()

def register_provider_tools():
    """Register all provider tools - both hardcoded and from database"""
    # Load from database first
    provider_tool_registry.load_tools_from_database()
    
    # You can still register hardcoded tools as fallback
    from hufai.ai.speech_to_text import create_speech_to_text_tool
    
    # These will be overridden by database entries if they exist
    provider_tool_registry.register_provider("OpenAI", {
        "speech_to_text": create_speech_to_text_tool,
    })
    
    provider_tool_registry.register_provider("Google", {
        "speech_to_text": create_speech_to_text_tool,
    })

# Auto-register tools when module is imported
register_provider_tools()