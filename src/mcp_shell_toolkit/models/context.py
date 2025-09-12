from pydantic import BaseModel, Field


class ShellContext(BaseModel):
    log_directory: str = Field(..., description="日志目录")
    system_info: str = Field(..., description="系统信息")
    user: str = Field(..., description="当前用户")