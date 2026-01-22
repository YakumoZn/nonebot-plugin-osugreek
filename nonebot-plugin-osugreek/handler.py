from nonebot import on_message, get_plugin_config
from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot_plugin_localstore import get_plugin_cache_dir
from PIL import Image, ImageChops
import aiohttp
import asyncio
import time
import random
from io import BytesIO
from pathlib import Path
from .config import Config


plugin_config = get_plugin_config(Config)
osugreek = on_message(priority=5, block=False)

# 希腊字母图片目录
GREEK_IMAGE_DIR = Path(__file__).parent / "images"
GREEK_IMAGE_DIR.mkdir(exist_ok=True)

# 临时缓存目录
TEMP_CACHE_DIR = get_plugin_cache_dir()
TEMP_CACHE_DIR.mkdir(exist_ok=True)


def add_chromatic_aberration(image: Image.Image, intensity: int = None) -> Image.Image:
    """色散效果"""
    if intensity is None:
        intensity = plugin_config.osugreek_chromatic_intensity
    intensity = max(1, min(10, intensity))

    r, g, b = image.split()[:3]
    r_offset = ImageChops.offset(r, -intensity, -intensity)
    b_offset = ImageChops.offset(b, intensity, intensity)

    if len(image.split()) == 4:  # RGBA图片
        a = image.split()[3]
        return Image.merge("RGBA", (r_offset, g, b_offset, a))
    else:  # RGB图片
        return Image.merge("RGB", (r_offset, g, b_offset))


def resize_greek_image(greek_img: Image.Image, original_width: int, original_height: int) -> Image.Image:
    """调整字母图片大小"""
    greek_w, greek_h = greek_img.size
    min_original_dimension = min(original_width, original_height)
    target_size = int(min_original_dimension * 1.8)

    scale_ratio = target_size / max(greek_w, greek_h)
    new_width = int(greek_w * scale_ratio)
    new_height = int(greek_h * scale_ratio)

    if new_width < 200:
        new_width = 200
        new_height = int(greek_h * (200 / greek_w))

    return greek_img.resize((new_width, new_height), Image.Resampling.LANCZOS)


async def cleanup_temp_file(file_path: Path, delay: float = 5.0):
    """清理临时文件"""
    await asyncio.sleep(delay)
    try:
        if file_path.exists():
            file_path.unlink()
    except Exception:
        pass


def generate_temp_filename() -> str:
    """生成唯一的临时文件名"""
    timestamp = int(time.time() * 1000)
    random_suffix = random.randint(1000, 9999)
    return f"processed_{timestamp}_{random_suffix}.png"


@osugreek.handle()
async def handle_osugreek(bot: Bot, event: MessageEvent):
    msg_text = event.get_plaintext().strip()

    if not (msg_text.startswith("/osugreek ") or msg_text.startswith("/希腊字母 ")):
        return

    greek_name = msg_text[10:].strip() if msg_text.startswith("/osugreek ") else msg_text[5:].strip()

    if not greek_name:
        await bot.send(event, "用法：/osugreek <希腊字母名称> 或 /希腊字母 <希腊字母名称>\n例如：/osugreek epsilon 或 /希腊字母 epsilon")
        return

    image_msg = None
    for seg in event.message:
        if seg.type == "image":
            image_msg = seg
            break

    if not image_msg and hasattr(event, 'reply') and event.reply:
        for seg in event.reply.message:
            if seg.type == "image":
                image_msg = seg
                break

    if not image_msg:
        await bot.send(event, "请发送一张图片或回复一张图片")
        return

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(image_msg.data["url"]) as resp:
                if resp.status != 200:
                    await bot.send(event, "图片下载失败")
                    return
                img_data = await resp.read()
    except Exception as e:
        await bot.send(event, f"图片下载失败: {e}")
        return

    temp_output_path = None
    try:
        original_img = Image.open(BytesIO(img_data)).convert("RGBA")
        chromatic_img = add_chromatic_aberration(original_img)

        greek_img_path = GREEK_IMAGE_DIR / f"{greek_name}.png"
        if not greek_img_path.exists():
            available = [f.stem for f in GREEK_IMAGE_DIR.glob("*.png")]
            await bot.send(event, f"未找到 {greek_name}.png\n可用的有: {', '.join(available)}")
            return

        greek_img = Image.open(greek_img_path).convert("RGBA")
        greek_img = resize_greek_image(greek_img, original_img.width, original_img.height)

        orig_w, orig_h = chromatic_img.size
        greek_w, greek_h = greek_img.size
        x = (orig_w - greek_w) // 2
        y = (orig_h - greek_h) // 2

        combined = Image.new("RGBA", chromatic_img.size)
        combined.paste(chromatic_img, (0, 0))
        combined.paste(greek_img, (x, y), greek_img)

        temp_filename = generate_temp_filename()
        temp_output_path = TEMP_CACHE_DIR / temp_filename
        combined.save(temp_output_path, format="PNG")

        await bot.send(event, MessageSegment.image(f"file:///{temp_output_path.absolute()}"))

    except Exception as e:
        await bot.send(event, f"图片处理失败: {e}")
        return
    finally:
        if temp_output_path and temp_output_path.exists():
            asyncio.create_task(cleanup_temp_file(temp_output_path))