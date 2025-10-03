# Shell Agent MCP工具集

这个项目是 Shell Agent 的扩展工具集，旨在提供如下能力：
- **操作引擎**：用在远程终端于执行脚本并获取结果。
- **知识引擎**：用于存储和检索任务相关信息。

操作引擎的能力包括:
1. 获取当前远程终端系统信息（如操作系统、终端类型等）
2. 获取当前远程终端的会话记录（即，近期用户输入的命令和输出结果）
3. 对远程终端写入命令并获取结果

知识引擎的能力包括:
1. 录制远程终端会话并保存为脚本
2. 存储和检索任务相关信息


框架知识可以在[FastMCP官方文档](https://gofastmcp.com/servers/context)学习。

## 1 快速启动

### 1.1 配置环境变量

在根目录下创建`.env`文件，添加以下内容：

```dotenv
# 当前远程终端类型，可以是 'MobaXterm' 或 'Xshell'，默认是 'MobaXterm'
CURRENT_SHELL='MobaXterm'
# MobaXterm 日志文件目录
MOBAXTERM_LOG_DIR='C:\Users\henry\.shell-agent\mobaxterm'
# XShell 日志文件目录
XSHELL_LOG_DIR='C:\Users\henry\.shell-agent\xshell'
```

### 1.2 安装uv

```bash
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 1.3 安装依赖

```bash
uv sync
```

### 1.4 启动MCP服务器

```bash
uv run hw-remote-shell-toolkit
```

### 1.5 使用MCP调试工具并进入开发模式

```bash
uv run mcp dev ./src/remote_shell_toolkit/__main__.py
```

## 2 构建项目

### 2.1 生成wheel文件

```bash
uv build
```

### 2.2 生成可执行文件

```bash
pyinstaller --onefile --name remote_shell_toolkit --icon=assets/favicon.ico src/remote_shell_toolkit/server.py
```

## 3 接入服务

### 3.1 cline配置 - 调试

```json
{
  "mcpServers": {
    "hw-mcp-shell-toolkit": {
      "disabled": false,
      "timeout": 600,
      "type": "stdio",
      "command": "uv",
      "args": [
        "--directory",
        "D:\\ProgramData\\Visual Studio Code\\Shell-Agent\\Shell-Agent-MCP-Toolkit",
        "run",
        "hw-remote-shell-toolkit"
      ]
    }
  }
}
```

### 3.2 cline配置 - 部署

```json
{
  "mcpServers": {
    "hw-mcp-shell-toolkit": {
      "disabled": false,
      "timeout": 600,
      "type": "stdio",
      "command": "D:\\ProgramData\\Visual Studio Code\\Shell-Agent\\Shell-Agent-MCP-Toolkit\\dist\\remote_shell_toolkit.exe"
    }
  }
}
```