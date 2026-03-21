from pydantic import BaseModel


class Config(BaseModel):
    """osugreek插件配置"""
    # RGB分离强度 (范围1-20, 默认4)
    osugreek_chromatic_intensity: int = 4
    # 故障效果强度 (范围0-5, 默认0, 0表示无故障效果)
    osugreek_glitch_intensity: int = 0