from pathlib import Path
from typing import Annotated, Dict, List
from mcp.server.fastmcp import FastMCP
from pydantic import Field
import warnings
from remote_shell_toolkit.clients.remote_shell_client import RemoteShellClient
from remote_shell_toolkit.configs import RemoteShellConfig
from remote_shell_toolkit.types import RemoteShellType
import os
import json

warnings.filterwarnings("ignore", category=UserWarning, module="pywinauto.application")


def create_server() -> FastMCP:

    mcp_server = FastMCP(name="remote_shell_toolkit")

    @mcp_server.tool(
        title="获取当前远程终端元信息",
        description="获取必要信息，包括 系统时间， 工作目录， 操作系统"
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
    def stop_record(
            sop_name: Annotated[str, Field(description="标准操作流程名称")],
            sop_description: Annotated[str, Field(description="标准操作流程描述")],
    ) -> str:
        current_shell_type: RemoteShellType = RemoteShellConfig.get_current_shell_type()
        log_dir: str = RemoteShellConfig.get_current_shell_log_dir()
        remote_shell_client = RemoteShellClient(current_shell_type, log_dir)
        result = remote_shell_client.stop_record()
        # 写入同一目录下的./data下的sop.json文件中
        sop_data_path = os.path.join(Path.cwd(), "./sop.json")
        if not os.path.exists(sop_data_path):
            with open(sop_data_path, "w", encoding="utf-8") as f:
                json.dump([], f, ensure_ascii=False, indent=4)
        with open(sop_data_path, "r", encoding="utf-8") as f:
            sop_list = json.load(f)
        sop_list.append({
            "id": sop_name,
            "description": sop_description,
            "content": result
        })
        with open(sop_data_path, "w", encoding="utf-8") as f:
            json.dump(sop_list, f, ensure_ascii=False, indent=4)
        return result

    @mcp_server.tool(
        title="检索记忆",
        description="检索与输入内容相关的记忆"
    )
    def get_sop_list() -> List[Dict[str, str]]:
        """
        返回可用的 SOP 列表，每项包含 id 和 description。
        如果 sop.json 不存在或内容格式不正确，返回空列表。
        """
        sop_data_path = os.path.join(Path.cwd(), "sop.json")
        if not os.path.exists(sop_data_path):
            return []
        with open(sop_data_path, "r", encoding="utf-8") as f:
            sop_list = json.load(f)
        result: List[Dict[str, str]] = []
        for item in sop_list:
            sid = str(item.get("id", "")) if isinstance(item, dict) else ""
            desc = str(item.get("description", "")) if isinstance(item, dict) else ""
            if sid or desc:  # 只包含至少有一个标识或描述的项
                result.append({"id": sid, "description": desc})
        return result

    @mcp_server.tool(
        title="获取记忆详情",
        description="获取指定记忆的详细内容"
    )
    def get_sop(
            sop_id: Annotated[str, Field(description="要获取的 SOP 的 id")]
    ) -> str:
        sop_data_path = os.path.join(Path.cwd(), "sop.json")
        if not os.path.exists(sop_data_path):
            return f"sop 数据文件未找到: {sop_data_path}"
        with open(sop_data_path, "r", encoding="utf-8") as f:
            sop_list = json.load(f)
        if not isinstance(sop_list, list):
            return "sop 数据格式不正确，期待一个列表。"
        for item in sop_list:
            if not isinstance(item, dict):
                continue
            if str(item.get("id", "")) == sop_id:
                return str(item.get("content", item.get("description", "")))
        return f"未找到 id 为 '{sop_id}' 的 SOP。"

    return mcp_server


def main():
    print("Starting MCP server...")
    mcp = create_server()
    mcp.run()


if __name__ == "__main__":
    main()
