"""
Shared Tools Registry for MAF Workflows
This is the source of truth for all local deterministic tools.
"""
import sys
from pathlib import Path
from typing import Any, Callable, Dict, Optional


class SharedToolsRegistry:
    """Registry for local deterministic tools."""
    
    def __init__(self):
        self._tools: Dict[str, Callable] = {}
    
    def register_tool(self, name: str, func: Callable) -> None:
        """Register a tool with the given name."""
        self._tools[name] = func
    
    def get_tool(self, name: str) -> Callable:
        """Get a tool by name."""
        if name not in self._tools:
            raise KeyError(f"Tool '{name}' not found in registry")
        return self._tools[name]
    
    def list_tools(self) -> list:
        """List all registered tool names."""
        return sorted(self._tools.keys())
    
    def has_tool(self, name: str) -> bool:
        """Check if a tool is registered."""
        return name in self._tools


def get_registry() -> SharedToolsRegistry:
    """Get or create the shared tools registry instance."""
    registry = SharedToolsRegistry()
    
    # Auto-discover and register tools from shared_tools directory
    shared_tools_dir = Path(__file__).parent
    
    # Import and register tools from social_signal_tools
    try:
        # Try relative import first (when used as package)
        from . import social_signal_tools
        if hasattr(social_signal_tools, 'register_tools'):
            social_signal_tools.register_tools(registry)
    except (ImportError, ValueError):
        # Fallback to absolute import (when loaded directly)
        try:
            sys.path.insert(0, str(shared_tools_dir))
            import social_signal_tools
            if hasattr(social_signal_tools, 'register_tools'):
                social_signal_tools.register_tools(registry)
        except ImportError:
            pass
    
    # Add more tool modules here as needed
    
    return registry


def call_tool(
    tool_name: str,
    args: Optional[dict] = None,
    workflow_tools_dir: Optional[str] = None
) -> Any:
    """
    Call a tool by name with the given arguments.
    
    Args:
        tool_name: Name of the tool to call
        args: Dictionary of arguments to pass to the tool
        workflow_tools_dir: Optional workflow-specific tools directory (unused for now)
        
    Returns:
        Result of the tool execution
    """
    registry = get_registry()
    tool = registry.get_tool(tool_name)
    return tool(**(args or {}))


def list_tools(workflow_tools_dir: Optional[str] = None) -> list:
    """
    List all registered tool names.
    
    Args:
        workflow_tools_dir: Optional workflow-specific tools directory (unused for now)
        
    Returns:
        List of tool names
    """
    registry = get_registry()
    return registry.list_tools()


if __name__ == "__main__":
    # Allow running as standalone to list tools
    registry = get_registry()
    print("Registered tools:")
    for tool_name in registry.list_tools():
        print(f"  - {tool_name}")
