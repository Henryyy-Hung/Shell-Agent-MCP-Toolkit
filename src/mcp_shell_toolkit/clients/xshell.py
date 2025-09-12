import os
import re
import time
import uuid
import threading
from pywinauto import Application, findwindows
from pywinauto.keyboard import send_keys


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


class CommandInjector:
    def __init__(self, window_finder=None):
        self.window_finder = window_finder or XshellWindowFinder()
        self.window_finder.connect()
        self.terminal = self.window_finder.get_terminal_ctrl()

    def inject(self, cmd: str):
        self.terminal.set_focus()
        time.sleep(0.05)
        send_keys(cmd, with_spaces=True, pause=0.01)
        time.sleep(0.05)
        send_keys("{ENTER}")


class LogTailer:
    ANSI_ESCAPE = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')

    def __init__(self, log_dir: str):
        self.log_file = self._find_latest_log(log_dir)
        if not self.log_file:
            raise FileNotFoundError("未找到 .log 文件，请确认 Xshell 是否设置了日志记录目录")
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

    def _tail(self):
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

    def read_all(self):
        with self._lock:
            return list(self._lines)

    def clear(self):
        with self._lock:
            self._lines.clear()

    def stop(self):
        self._stop_event.set()
        self._thread.join(timeout=1)


class RemoteShell:
    def __init__(self, log_dir: str,
                 injector: CommandInjector = None,
                 tailer: LogTailer = None):
        self.injector = injector or CommandInjector()
        self.tailer = tailer or LogTailer(log_dir)

    def send_command(self, cmd: str, timeout: float = 10.0) -> str:
        uid = uuid.uuid4().hex[:8]
        start_marker = f"Agent Mode Start {uid}"
        end_marker = f"Agent Mode End {uid}"

        self.tailer.clear()

        self.injector.inject(f"echo {start_marker}")
        self.injector.inject(cmd)
        self.injector.inject(f"echo {end_marker}")

        start_time = time.time()
        started = False
        captured = []

        while True:
            if time.time() - start_time > timeout:
                raise TimeoutError("命令输出等待超时")

            lines = self.tailer.read_all()
            for line in lines:
                if start_marker in line:
                    started = True
                    captured.clear()
                    continue
                if end_marker in line and started:
                    output = "".join(captured)
                    clean_lines = [
                        ln for ln in output.splitlines()
                        if ln.strip()
                    ]
                    return "\n".join(clean_lines).strip()
                if started:
                    captured.append(line)

            time.sleep(0.01)

    def close(self):
        self.tailer.stop()


if __name__ == "__main__":
    # log_dir 是 Xshell 保存会话日志的目录（需要提前在 Xshell 中开启日志记录）
    shell = RemoteShell(log_dir=r"C:\Users\henry\Documents\NetSarang Computer\8\Xshell\Logs")
    try:
        out = shell.send_command("ls -l", timeout=5)
        print("命令输出:\n", out)
    finally:
        shell.close()
