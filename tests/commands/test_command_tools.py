#!/usr/bin/env python3

"""
Test suite for the tools command functionality.
Tests the /tools command that displays available tools in table format.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from cai.repl.commands.base import Command
from cai.repl.commands.tools import ToolsCommand
from cai.sdk.agents import FunctionTool


class TestToolsCommand:
    """Test class for ToolsCommand functionality."""

    @pytest.fixture
    def tools_command(self):
        """Create a ToolsCommand instance for testing."""
        return ToolsCommand()

    @pytest.fixture
    def mock_console(self):
        """Create a mock console for testing output."""
        with patch("cai.repl.commands.tools.console") as mock_console:
            yield mock_console

    @pytest.fixture
    def mock_agent_manager(self):
        """Create a mock agent manager for testing."""
        with patch("cai.repl.commands.tools.AGENT_MANAGER") as mock_manager:
            yield mock_manager

    @pytest.fixture
    def mock_function_tool(self):
        """Create a mock FunctionTool for testing."""
        tool = Mock(spec=FunctionTool)
        tool.name = "test_tool"
        tool.description = "A test tool for testing purposes"
        tool.params_json_schema = {
            "type": "object",
            "properties": {
                "param1": {"type": "string"},
                "param2": {"type": "integer"},
            },
            "required": ["param1"],
        }
        return tool

    def test_command_initialization(self, tools_command):
        """Test that ToolsCommand initializes correctly."""
        assert isinstance(tools_command, Command)
        assert tools_command.name == "/tools"
        assert "Display available tools in table format" in tools_command.description
        assert "/t" in tools_command.aliases

    def test_extract_params_from_schema_with_params(self, tools_command):
        """Test parameter extraction from JSON schema with parameters."""
        schema = {
            "type": "object",
            "properties": {
                "target": {"type": "string"},
                "port": {"type": "integer"},
                "timeout": {"type": "number"},
            },
            "required": ["target"],
        }

        result = tools_command._extract_params_from_schema(schema)

        assert "target: string [required]" in result
        assert "port: integer [optional]" in result
        assert "timeout: number [optional]" in result

    def test_extract_params_from_schema_no_params(self, tools_command):
        """Test parameter extraction with no parameters."""
        schema = {}
        result = tools_command._extract_params_from_schema(schema)
        assert result == "None"

    def test_extract_params_from_schema_empty_properties(self, tools_command):
        """Test parameter extraction with empty properties."""
        schema = {"type": "object", "properties": {}}
        result = tools_command._extract_params_from_schema(schema)
        assert result == "None"

    def test_extract_params_from_schema_all_required(self, tools_command):
        """Test parameter extraction with all required parameters."""
        schema = {
            "type": "object",
            "properties": {
                "url": {"type": "string"},
                "method": {"type": "string"},
            },
            "required": ["url", "method"],
        }

        result = tools_command._extract_params_from_schema(schema)

        assert "url: string [required]" in result
        assert "method: string [required]" in result
        assert "[optional]" not in result

    def test_get_current_agent_success(self, tools_command, mock_agent_manager):
        """Test getting current agent successfully."""
        mock_agent = Mock()
        mock_agent_manager.get_current_agent.return_value = mock_agent

        result = tools_command._get_current_agent()

        assert result == mock_agent
        mock_agent_manager.get_current_agent.assert_called_once()

    def test_get_current_agent_exception(self, tools_command, mock_agent_manager):
        """Test getting current agent with exception."""
        mock_agent_manager.get_current_agent.side_effect = Exception("No agent")

        result = tools_command._get_current_agent()

        assert result is None

    @pytest.mark.asyncio
    async def test_get_agent_tools(self, tools_command, mock_function_tool):
        """Test getting tools from an agent."""
        mock_agent = Mock()
        mock_agent.get_all_tools = AsyncMock(return_value=[mock_function_tool])

        result = await tools_command._get_agent_tools(mock_agent)

        assert len(result) == 1
        assert result[0] == mock_function_tool

    @pytest.mark.asyncio
    async def test_get_agent_tools_filters_non_function_tools(self, tools_command, mock_function_tool):
        """Test that non-FunctionTool instances are filtered out."""
        mock_agent = Mock()
        mock_other_tool = Mock()  # Not a FunctionTool
        mock_agent.get_all_tools = AsyncMock(
            return_value=[mock_function_tool, mock_other_tool]
        )

        result = await tools_command._get_agent_tools(mock_agent)

        # Should only include the FunctionTool
        assert len(result) == 1
        assert result[0] == mock_function_tool

    def test_handle_no_active_agent(self, tools_command, mock_console, mock_agent_manager):
        """Test handling when no active agent is available."""
        mock_agent_manager.get_current_agent.side_effect = Exception("No agent")

        result = tools_command.handle()

        assert result is False
        # Should print error message
        assert mock_console.print.call_count >= 2

    def test_handle_agent_with_no_tools(
        self, tools_command, mock_console, mock_agent_manager
    ):
        """Test handling when agent has no tools."""
        mock_agent = Mock()
        mock_agent.name = "test_agent"
        mock_agent.get_all_tools = AsyncMock(return_value=[])
        mock_agent_manager.get_current_agent.return_value = mock_agent

        result = tools_command.handle()

        assert result is True
        # Should print message about no tools
        assert mock_console.print.call_count >= 1

    def test_handle_with_tools(
        self, tools_command, mock_console, mock_agent_manager, mock_function_tool
    ):
        """Test handling with tools available."""
        mock_agent = Mock()
        mock_agent.name = "test_agent"
        mock_agent.get_all_tools = AsyncMock(return_value=[mock_function_tool])
        mock_agent_manager.get_current_agent.return_value = mock_agent

        result = tools_command.handle()

        assert result is True
        # Should print table with tools
        assert mock_console.print.call_count >= 2

    def test_handle_with_multiple_tools(
        self, tools_command, mock_console, mock_agent_manager
    ):
        """Test handling with multiple tools."""
        tool1 = Mock(spec=FunctionTool)
        tool1.name = "nmap"
        tool1.description = "Network mapper tool"
        tool1.params_json_schema = {
            "properties": {"target": {"type": "string"}},
            "required": ["target"],
        }

        tool2 = Mock(spec=FunctionTool)
        tool2.name = "curl"
        tool2.description = "HTTP request tool"
        tool2.params_json_schema = {
            "properties": {"url": {"type": "string"}, "method": {"type": "string"}},
            "required": ["url"],
        }

        mock_agent = Mock()
        mock_agent.name = "security_agent"
        mock_agent.get_all_tools = AsyncMock(return_value=[tool1, tool2])
        mock_agent_manager.get_current_agent.return_value = mock_agent

        result = tools_command.handle()

        assert result is True
        # Should print table with multiple tools
        assert mock_console.print.call_count >= 2

    def test_handle_with_args(
        self, tools_command, mock_console, mock_agent_manager, mock_function_tool
    ):
        """Test handling with arguments (should be ignored)."""
        mock_agent = Mock()
        mock_agent.name = "test_agent"
        mock_agent.get_all_tools = AsyncMock(return_value=[mock_function_tool])
        mock_agent_manager.get_current_agent.return_value = mock_agent

        result = tools_command.handle(args=["some", "args"])

        assert result is True
        # Should still work and print the table
        assert mock_console.print.call_count >= 2

    def test_extract_params_with_no_type(self, tools_command):
        """Test parameter extraction when type is missing."""
        schema = {
            "type": "object",
            "properties": {
                "param1": {},  # No type specified
            },
            "required": [],
        }

        result = tools_command._extract_params_from_schema(schema)

        assert "param1: any [optional]" in result
