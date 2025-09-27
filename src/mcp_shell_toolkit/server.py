from typing import Annotated
from mcp.server.fastmcp import FastMCP
from pydantic import Field
import warnings
from mcp_shell_toolkit.clients.remote_shell_client import RemoteShellClient
from mcp_shell_toolkit.configs import RemoteShellConfig

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
        current_shell_type = RemoteShellConfig.CURRENT_SHELL
        log_dir = RemoteShellConfig.get_current_shell_log_dir()
        remote_shell_client = RemoteShellClient(current_shell_type, log_dir)
        try:
            output = remote_shell_client.send_command(command)
        finally:
            remote_shell_client.close()
        return output

    return mcp_server


def main():
    print("Starting MCP server...")
    mcp = create_server()
    mcp.run()


if __name__ == "__main__":
    main()
