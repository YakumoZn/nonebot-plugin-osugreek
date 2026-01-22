from nonebot.plugin import PluginMetadata
from .handler import osugreek
from .config import Config

__version__ = "1.0.6"
__plugin_meta__ = PluginMetadata(
    name="osugreek",
    description="在图片中央贴上神秘4k希腊字母并添加色散效果的插件",
    usage="/osugreek <希腊字母> 或 /希腊字母 <希腊字母>",
    type="application",
    homepage="https://github.com/YakumoZn/nonebot-plugin-osugreek",
    supported_adapters={"~onebot.v11"},
    config=Config,  
    extra={"author": "YakumoZn"}
)

osugreek = osugreek