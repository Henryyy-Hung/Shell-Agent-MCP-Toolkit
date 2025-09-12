from typing import Annotated
from mcp.server.fastmcp import FastMCP
from pydantic import Field
import warnings
from mcp_shell_toolkit.clients.mobaxterm import RemoteShell

warnings.filterwarnings("ignore", category=UserWarning, module="pywinauto.application")

def create_server() -> FastMCP:
    mcp_server = FastMCP(name="hw-mcp-demo")

    @mcp_server.tool(
        title="写入远程终端",
        description="在远程终端中执行命令，并返回输出结果",
    )
    def write_to_remote_shell(
            command: Annotated[str, Field(description="要执行的命令")],
    ) -> str:
        shell = RemoteShell(r"C:\Users\henry\Desktop")
        try:
            output = shell.send_command(command, timeout=600)
        finally:
            shell.close()
        return output

    return mcp_server


def main():
    print("Starting MCP server...")
    mcp = create_server()
    mcp.run()
