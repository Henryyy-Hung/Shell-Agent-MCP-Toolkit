import os
import re
import time
import uuid
import threading
from typing import List

from pywinauto import Application, findwindows
from pywinauto.keyboard import send_keys
import tiktoken

from remote_shell_toolkit.configs import RemoteShellConfig
from remote_shell_toolkit.types import RemoteShellType


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
        self._thread = None

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

    def start(self) -> None:
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._tail, daemon=True)
        self._thread.start()

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

    def read_all_content(self) -> List[str]:
        with open(self.log_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            clean = self._clean_ansi(content)
            return clean.split('\n')

    def read_tailed_content(self) -> List[str]:
        with self._lock:
            raw_text = ''.join(self._lines)
            lines = [i.strip('\r') for i in raw_text.split('\n')]
            return lines

    def clear_tailed_content(self):
        with self._lock:
            self._lines.clear()

    def stop(self):
        """停止日志监听线程"""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=1)
        self._thread = None


class RemoteShellClient:

    START_RECORD_MARKER = ">>>>>> Start Recording"
    END_RECORD_MARKER = ">>>>>> End Recording"

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
        self.log_dir = log_dir
        self.tailer = LogTailer(log_dir)

    def get_history(self, max_tokens: int = 1024, model_name: str = "gpt-4"):
        """
        精确限制 tokens，保留尽可能多的关键信息（最新的命令和输出）。
        Args:
            max_tokens: 最大 token 数
            model_name: 模型对应的 tokenizer 名称
        """
        enc = tiktoken.encoding_for_model(model_name)
        lines = self.tailer.read_all_content()
        # 从最新的行开始反向拼接
        result_lines = []
        total_tokens = 0
        for line in reversed(lines):
            if not line.strip():
                continue  # 去掉纯空行
            # 计算新增行的tokens
            line_tokens = len(enc.encode(line)) + 1  # +1 代表换行符近似
            if total_tokens + line_tokens > max_tokens:
                break
            result_lines.append(line)
            total_tokens += line_tokens
        # 反转为正常时间顺序
        result_lines.reverse()
        return "remote shell log\n\n```plaintext\n" + "\n".join(result_lines) + "\n```"

    def start_record(self) -> None:
        """开始录制日志"""
        self.injector.inject(f"printf '{self.START_RECORD_MARKER}\\n'")

    def stop_record(self) -> str:
        """停止录制日志"""
        lines = reversed(self.tailer.read_all_content())
        recording: List[str] = []
        for line in lines:
            if self.START_RECORD_MARKER == line:
                return '\n'.join(reversed(recording))
            recording.append(line)
        time.sleep(0.05)
        self.injector.inject(f"printf '{self.END_RECORD_MARKER}\\n'")
        return '\n'.join(recording)

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

        try:
            self.tailer.start()
            self.tailer.clear_tailed_content()
            self.injector.inject("")
            time.sleep(0.2)
            self.injector.inject(wrapped_cmd)
            start_time = time.time()
            while True:
                if time.time() - start_time > timeout * 1000:
                    raise TimeoutError("命令输出等待超时")
                started = False
                captured = []
                lines = self.tailer.read_tailed_content()
                for line in lines:
                    if not started and start_marker in line:
                        started = True
                        captured.clear()
                        captured.append(line.replace(wrapped_cmd, cmd).strip())
                        continue
                    if started:
                        if start_marker == line:
                            continue
                        if end_marker == line:
                            result = '\n'.join([i for i in captured if i.strip() != ""])
                            return f"""remote shell log\n\n```plaintext\n{result}\n```"""
                        captured.append(line)
                time.sleep(0.5)
        finally:
            self.tailer.stop()


if __name__ == "__main__":
    current_shell_type: RemoteShellType = RemoteShellConfig.get_current_shell_type()
    log_dir: str = RemoteShellConfig.get_current_shell_log_dir()
    remote_shell_client = RemoteShellClient(current_shell_type, log_dir)
    output = remote_shell_client.send_command("uname -a")
    print(output)
