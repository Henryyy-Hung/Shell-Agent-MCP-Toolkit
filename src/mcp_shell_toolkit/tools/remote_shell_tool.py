from mcp.server import FastMCP
from mcp_shell_toolkit.clients.remote_shell_client import RemoteShellClient


class RemoteShellTool:

    def __init__(self, mcp: FastMCP):
        self.mcp = mcp

    @staticmethod
    def write_to_remote_shell(command: str) -> str:
        shell = RemoteShellClient(r"C:\Users\henry\Desktop")
        try:
            output = shell.send_command(command, timeout=600)
        finally:
            shell.close()
        return output