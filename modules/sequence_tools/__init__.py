from pathlib import Path

from modules.seq_basics._plumbing.register import register_tools, register_resources


def register_module(mcp) -> None:
    module_dir = Path(__file__).parent
    register_tools(mcp, module_dir / "tools")
    register_resources(mcp, module_dir / "data", "sequence_tools")