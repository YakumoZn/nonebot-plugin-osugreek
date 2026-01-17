from nonebot.plugin import PluginMetadata
from .handler import osugreek

__version__ = "1.0.0"
__plugin_meta__ = PluginMetadata(
    name="osugreek",
    description="在图片中央贴上希腊字母并添加色散效果的插件",
    usage="/osugreek <希腊字母> 或 /希腊字母 <希腊字母>",
    type="application",
    homepage="https://github.com/yourusername/osugreek",
    supported_adapters={"~onebot.v11"},
    extra={"author": "YourName"}
)

osugreek = osugreek