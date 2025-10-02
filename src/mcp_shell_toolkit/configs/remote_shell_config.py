from dotenv import load_dotenv
import os

from mcp_shell_toolkit.types import RemoteShellType

load_dotenv()


class RemoteShellConfig:
    # 当前使用的终端类型，默认为 MobaXterm
    _CURRENT_SHELL: RemoteShellType = os.getenv("CURRENT_SHELL", RemoteShellType.MobaXterm)

    # MobaXterm 的日志文件夹路径
    _MOBAXTERM_LOG_DIR: str | None = os.getenv("MOBAXTERM_LOG_DIR", None)

    # Xshell 的日志文件夹路径
    _XSHELL_LOG_DIR: str | None = os.getenv("XSHELL_LOG_DIR", None)

    @classmethod
    def get_current_shell_type(cls) -> RemoteShellType:
        if cls._CURRENT_SHELL == RemoteShellType.MobaXterm:
            return RemoteShellType.MobaXterm
        elif cls._CURRENT_SHELL == RemoteShellType.XShell:
            return RemoteShellType.XShell
        else:
            raise ValueError("环境变量错误: 未知远程终端类型")

    @classmethod
    def get_current_shell_log_dir(cls) -> str:
        current_shell_type = cls.get_current_shell_type()
        current_shell_log_dir: str = ""
        if current_shell_type == RemoteShellType.MobaXterm:
            current_shell_log_dir = cls._MOBAXTERM_LOG_DIR
        elif current_shell_type == RemoteShellType.XShell:
            current_shell_log_dir = cls._XSHELL_LOG_DIR
        if current_shell_log_dir is None:
            raise ValueError(f"环境变量错误: 远程终端 {cls.get_current_shell_type()} 未配置日志文件夹目录")
        return current_shell_log_dir
