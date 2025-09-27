from dotenv import load_dotenv
import os

from mcp_shell_toolkit.types import RemoteShellType

load_dotenv()


class RemoteShellConfig:
    # 当前使用的终端类型，默认为 MobaXterm
    CURRENT_SHELL: RemoteShellType = os.getenv("CURRENT_SHELL", RemoteShellType.MobaXterm)

    # MobaXterm 的日志文件夹路径
    MOBAXTERM_LOG_DIR: str | None = os.getenv("MOBAXTERM_LOG_DIR", None)

    # Xshell 的日志文件夹路径
    XSHELL_LOG_DIR: str | None = os.getenv("XSHELL_LOG_DIR", None)

    @classmethod
    def get_current_shell_log_dir(cls) -> str | None:
        if cls.CURRENT_SHELL == RemoteShellType.MobaXterm:
            return cls.MOBAXTERM_LOG_DIR
        elif cls.CURRENT_SHELL == RemoteShellType.XShell:
            return cls.XSHELL_LOG_DIR
        return None
