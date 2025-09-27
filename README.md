# Shell Agent MCP工具集

此项目为ShellAgent的MCP工具集，包含了:

- **操作引擎**：用在远程终端于执行脚本并获取结果。
- **知识引擎**：用于存储和检索任务相关信息。
- **需求提取**：用于解析和理解用户需求。

框架知识可以在[FastMCP官方文档](https://gofastmcp.com/servers/context)学习。

## 1 快速启动

### 1.1 配置环境变量

在根目录下创建`.env`文件，添加以下内容：

```dotenv
# Current Remote Shell, can be 'mobaxterm', 'xshell', default is 'mobaxterm'
CURRENT_SHELL='mobaxterm'
# Log directory for MobaXterm
MOBAXTERM_LOG_DIR='C:\Users\henry\.shell-agent\mobaxterm'
# Log directory for Xshell
XSHELL_LOG_DIR='C:\Users\henry\.shell-agent\xshell'
```

### 1.2 安装依赖

```bash
uv sync
```

### 1.3 启动MCP服务器

```bash
uv run hw-mcp-shell-toolkit
```

### 1.4 使用MCP调试工具并进入开发模式

```bash
uv run mcp dev ./src/mcp_shell_toolkit/__main__.py
```

## 2 构建项目

### 2.1 生成wheel文件

```bash
uv build
```

### 2.2 生成可执行文件

```bash
pyinstaller --onefile --name mcp_shell_toolkit src/mcp_shell_toolkit/server.py
```

## 3 接入服务

### 3.1 cline配置

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
        "C:\\Users\\henry\\PycharmProjects\\mcp-shell-toolkit",
        "run",
        "hw-mcp-shell-toolkit"
      ]
    }
  }
}
```