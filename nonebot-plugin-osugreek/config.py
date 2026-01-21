from pydantic import BaseModel


class Config(BaseModel):
    """osugreek插件配置"""
    # RGB分离强度 diff=4，min1 max10 :3
    osugreek_chromatic_intensity: int = 4