from tools.builtin.read_file import ReadFileTool
from tools.builtin.write_file import WriteFileTool
from tools.builtin.edit_file import EditTool
from tools.grep import GrepTool
from tools.list_dir import ListDirTool
from tools.builtin.shell import ShellTool



__all__ = ["ReadFileTool", "WriteFileTool", "EditTool", "ListDirTool", "ShellTool", "GrepTool"]

def get_all_builtin_tools() -> list[type]:
    return [ReadFileTool,
            WriteFileTool,
            EditTool,
            ShellTool,
            ListDirTool,
            GrepTool]  # Add other built-in tools here as needed
            