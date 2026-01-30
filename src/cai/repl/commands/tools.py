"""
Tools command for CAI REPL.
This module provides commands for displaying available tools.
"""

import inspect
from typing import List, Optional, Any, Dict

from rich.console import Console
from rich.table import Table

from cai.repl.commands.base import Command, register_command
from cai.sdk.agents import Agent, FunctionTool
from cai.sdk.agents.simple_agent_manager import AGENT_MANAGER

console = Console()


class ToolsCommand(Command):
    """Command for displaying available tools."""

    def __init__(self):
        """Initialize the tools command."""
        super().__init__(
            name="/tools",
            description="Display available tools in table format",
            aliases=["/t"]
        )

    def _extract_params_from_schema(self, params_schema: Dict[str, Any]) -> str:
        """Extract parameter information from JSON schema.

        Args:
            params_schema: The JSON schema for tool parameters

        Returns:
            Formatted string describing the parameters
        """
        if not params_schema:
            return "None"
        
        properties = params_schema.get("properties", {})
        required = params_schema.get("required", [])
        
        if not properties:
            return "None"
        
        param_list = []
        for param_name, param_info in properties.items():
            param_type = param_info.get("type", "any")
            is_required = param_name in required
            
            # Format: param_name (type) [required/optional]
            param_str = f"{param_name}: {param_type}"
            if is_required:
                param_str += " [required]"
            else:
                param_str += " [optional]"
            
            param_list.append(param_str)
        
        return "\n".join(param_list)

    def _get_current_agent(self) -> Optional[Agent]:
        """Get the current active agent.

        Returns:
            The current agent instance or None
        """
        try:
            return AGENT_MANAGER.get_current_agent()
        except Exception:
            return None

    async def _get_agent_tools(self, agent: Agent) -> List[FunctionTool]:
        """Get all function tools from an agent.

        Args:
            agent: The agent instance

        Returns:
            List of FunctionTool instances
        """
        all_tools = await agent.get_all_tools()
        # Filter to only FunctionTool instances
        return [tool for tool in all_tools if isinstance(tool, FunctionTool)]

    def handle(self, args: Optional[List[str]] = None) -> bool:
        """Handle the tools command.

        Args:
            args: Optional list of command arguments

        Returns:
            True if the command was handled successfully, False otherwise
        """
        # Get the current agent
        agent = self._get_current_agent()
        
        if not agent:
            console.print("[red]Error: No active agent found.[/red]")
            console.print("[dim]Use /agent select <name> to select an agent first.[/dim]")
            return False
        
        # Get agent tools
        import asyncio
        try:
            tools = asyncio.get_event_loop().run_until_complete(
                self._get_agent_tools(agent)
            )
        except RuntimeError:
            # If there's no event loop, create one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            tools = loop.run_until_complete(self._get_agent_tools(agent))
        
        if not tools:
            console.print(f"[yellow]Agent '{agent.name}' has no tools available.[/yellow]")
            return True
        
        # Create tools table
        tools_table = Table(title=f"Available Tools for Agent: {agent.name}")
        tools_table.add_column("Tool Name", style="cyan", no_wrap=True)
        tools_table.add_column("Params", style="yellow")
        tools_table.add_column("Tool Purpose", style="green")
        
        # Add tools to table
        for tool in tools:
            tool_name = tool.name
            tool_purpose = tool.description or "No description available"
            params_str = self._extract_params_from_schema(tool.params_json_schema)
            
            tools_table.add_row(tool_name, params_str, tool_purpose)
        
        console.print(tools_table)
        console.print(f"\n[dim]Total tools: {len(tools)}[/dim]")
        
        return True


# Register the command
register_command(ToolsCommand())
