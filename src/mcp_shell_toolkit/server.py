from typing import Annotated, Dict, List
from mcp.server.fastmcp import FastMCP
from pydantic import Field
import warnings
from mcp_shell_toolkit.clients.remote_shell_client import RemoteShellClient
from mcp_shell_toolkit.configs import RemoteShellConfig
from mcp_shell_toolkit.types import RemoteShellType

warnings.filterwarnings("ignore", category=UserWarning, module="pywinauto.application")


def create_server() -> FastMCP:

    mcp_server = FastMCP(name="remote_shell_toolkit")

    @mcp_server.tool(
        title="获取当前远程终端元信息",
        description="获取远程终端所在系统的信息"
    )
    def get_sys_info() -> str:
        return write_to_remote_shell("uname -a")

    @mcp_server.tool(
        title="获取当前远程终端交互历史",
        description="获取当前远程终端的交互历史记录"
    )
    def get_history() -> str:
        current_shell_type: RemoteShellType = RemoteShellConfig.get_current_shell_type()
        log_dir: str = RemoteShellConfig.get_current_shell_log_dir()
        remote_shell_client = RemoteShellClient(current_shell_type, log_dir)
        return remote_shell_client.get_history()

    @mcp_server.tool(
        title="写入远程终端",
        description="在远程终端中执行命令，并返回输出结果",
    )
    def write_to_remote_shell(
            command: Annotated[str, Field(description="要执行的命令")],
    ) -> str:
        current_shell_type: RemoteShellType = RemoteShellConfig.get_current_shell_type()
        log_dir: str = RemoteShellConfig.get_current_shell_log_dir()
        remote_shell_client = RemoteShellClient(current_shell_type, log_dir)
        return remote_shell_client.send_command(command)

    @mcp_server.tool(
        title="开始录制",
        description="开始录制远程终端的日志"
    )
    def start_record() -> None:
        current_shell_type: RemoteShellType = RemoteShellConfig.get_current_shell_type()
        log_dir: str = RemoteShellConfig.get_current_shell_log_dir()
        remote_shell_client = RemoteShellClient(current_shell_type, log_dir)
        remote_shell_client.start_record()

    @mcp_server.tool(
        title="停止录制",
        description="停止录制远程终端的日志"
    )
    def stop_record() -> str:
        current_shell_type: RemoteShellType = RemoteShellConfig.get_current_shell_type()
        log_dir: str = RemoteShellConfig.get_current_shell_log_dir()
        remote_shell_client = RemoteShellClient(current_shell_type, log_dir)
        return remote_shell_client.stop_record()

    @mcp_server.tool(
        title="检索记忆",
        description="检索与输入内容相关的记忆"
    )
    def get_sop_list() -> List[Dict[str, str]]:
        return [
            {"id": "Cloud SOP 换包", "description": "更换CloudSop框架的部署包"},
        ]

    @mcp_server.tool(
        title="获取记忆详情",
        description="获取指定记忆的详细内容"
    )
    def get_sop() -> str:
        return ""

    return mcp_server


def main():
    print("Starting MCP server...")
    mcp = create_server()
    mcp.run()


if __name__ == "__main__":
    main()
