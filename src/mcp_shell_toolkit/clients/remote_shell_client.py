import os
import re
import time
import uuid
import threading
from pywinauto import Application, findwindows
from pywinauto.keyboard import send_keys

from mcp_shell_toolkit.configs import RemoteShellConfig
from mcp_shell_toolkit.types import RemoteShellType


class XshellWindowFinder:
    def __init__(self, exe_path=None):
        self.exe_path = exe_path
        self.app = None

    def connect(self):
        if self.exe_path and os.path.exists(self.exe_path):
            # 启动 Xshell
            self.app = Application(backend="win32").start(self.exe_path)
        else:
            # 通过窗口类名查找 Xshell 主窗口
            # 通常 Xshell 窗口类名为 "Xshell6" 或 "Xshell5"，你可以用 inspect.exe 或 pywinauto 自带的 print_control_identifiers() 来确认
            hwnds = findwindows.find_windows(title_re=".*Xshell.*")  # 根据实际版本调整
            if not hwnds:
                raise RuntimeError("未找到 Xshell 窗口")
            self.app = Application(backend="win32").connect(handle=hwnds[0])

    def get_terminal_ctrl(self):
        if not self.app:
            self.connect()
        main_win = self.app.window(title_re=".*Xshell.*")  # 换成实际的类名
        # main_win.print_control_identifiers()  # 调试用
        return main_win


class MobaXtermWindowFinder:
    def __init__(self, exe_path=None):
        self.exe_path = exe_path
        self.app = None

    def connect(self):
        if self.exe_path and os.path.exists(self.exe_path):
            self.app = Application(backend="win32").start(self.exe_path)
        else:
            hwnds = findwindows.find_windows(class_name="TMobaXtermForm")
            if not hwnds:
                raise RuntimeError("未找到 MobaXterm 窗口")
            self.app = Application(backend="win32").connect(handle=hwnds[0])

    def get_terminal_ctrl(self):
        if not self.app:
            self.connect()
        main_win = self.app.window(class_name="TMobaXtermForm")
        # 调试控件树
        # main_win.print_control_identifiers()
        return main_win


class CommandInjector:
    """使用 pywinauto 注入命令"""

    def __init__(self, window_finder=None):
        self.window_finder = window_finder or MobaXtermWindowFinder()
        self.window_finder.connect()
        self.terminal = self.window_finder.get_terminal_ctrl()

    def inject(self, cmd: str):
        # 聚焦窗口
        self.terminal.set_focus()
        time.sleep(0.01)
        # 输入命令
        send_keys(cmd, with_spaces=True, pause=0)  # 保证空格正常输入
        time.sleep(0.01)
        send_keys("{ENTER}")


class LogTailer:
    """持续读取最新日志文件并清洗 ANSI 转义字符。"""

    ANSI_ESCAPE = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')

    def __init__(self, log_dir: str):
        self.log_file = self._find_latest_log(log_dir)
        if not self.log_file:
            raise FileNotFoundError("未找到 .log 文件")
        self._lock = threading.Lock()
        self._lines = []
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._tail, daemon=True)
        self._thread.start()

    @staticmethod
    def _find_latest_log(log_dir: str):
        files = [
            os.path.join(log_dir, f)
            for f in os.listdir(log_dir)
            if f.lower().endswith(".log")
        ]
        return max(files, key=os.path.getmtime) if files else None

    @classmethod
    def _clean_ansi(cls, text: str) -> str:
        return cls.ANSI_ESCAPE.sub('', text)

    def read_full_log(self) -> str:
        with open(self.log_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            clean = self._clean_ansi(content)
            return clean

    def _tail(self) -> None:
        with open(self.log_file, 'r', encoding='utf-8', errors='ignore') as f:
            f.seek(0, os.SEEK_END)
            while not self._stop_event.is_set():
                line = f.readline()
                if not line:
                    time.sleep(0.05)
                    continue
                clean = self._clean_ansi(line)
                with self._lock:
                    self._lines.append(clean)

    def read_all(self) -> list[str]:
        with self._lock:
            raw_text = ''.join(self._lines)
            lines = [i.strip('\r') for i in raw_text.split('\n')]
            return lines

    def clear(self):
        with self._lock:
            self._lines.clear()

    def stop(self):
        self._stop_event.set()
        self._thread.join(timeout=1)


class RemoteShellClient:

    def __init__(self, remote_shell_type: RemoteShellType, log_dir: str) -> None:
        """通过远程终端执行命令并获取输出。
        Args:
            remote_shell_type (RemoteShellType): 远程终端类型
            log_dir (str): 远程终端日志文件目录
        Raises:
            ValueError: 不支持的远程终端类型
        """
        # 初始化命令注入器
        if remote_shell_type == RemoteShellType.XShell:
            self.injector = CommandInjector(window_finder=XshellWindowFinder())
        elif remote_shell_type == RemoteShellType.MobaXterm:
            self.injector = CommandInjector(window_finder=MobaXtermWindowFinder())
        else:
            raise ValueError("不支持的远程终端类型")
        if not os.path.isdir(log_dir):
            raise ValueError("无效的日志目录")
        # 初始化日志读取器
        self.tailer = LogTailer(log_dir)

    def get_history(self) -> str:
        """获取当前日志中的所有历史记录。
        Returns:
            str: 历史记录
        """
        content = self.tailer.read_full_log()
        return f"```log\n{content}\n```"

    def send_command(self, cmd: str, timeout: float = 60.0) -> str:
        """发送命令并等待输出结果。
        Args:
            cmd (str): 要执行的命令
            timeout (float): 等待命令输出的超时时间，单位秒
        Returns:
            str: 命令输出结果
        Raises:
            TimeoutError: 命令输出等待超时
        """
        uid = uuid.uuid4().hex[:8]
        start_marker = f">>>>>> Agent Session {uid} Start"
        end_marker = f">>>>>> Agent Session {uid} End"
        wrapped_cmd = (
            f"printf '{start_marker}\\n\\n'; " +
            f"{cmd}; " +
            f"printf '\\n{end_marker}' "
        )
        self.tailer.clear()
        self.injector.inject(wrapped_cmd)
        start_time = time.time()
        started = False
        captured = []
        while True:
            if time.time() - start_time > timeout * 1000:
                raise TimeoutError("命令输出等待超时")
            lines = self.tailer.read_all()
            for line in lines:
                if start_marker == line:
                    started = True
                    captured.clear()
                    continue
                if end_marker == line and started:
                    return '\n'.join(captured)
                if started:
                    captured.append(line)
            time.sleep(0.5)

    def close(self):
        self.tailer.stop()


if __name__ == "__main__":
    current_shell_type: RemoteShellType = RemoteShellConfig.get_current_shell_type()
    log_dir: str = RemoteShellConfig.get_current_shell_log_dir()
    remote_shell_client = RemoteShellClient(current_shell_type, log_dir)
    try:
        output = remote_shell_client.send_command("sleep 1; ls -la")
        print(output)
    finally:
        remote_shell_client.close()