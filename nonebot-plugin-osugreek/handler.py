from nonebot import get_plugin_config, require, on_command
from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from PIL import Image, ImageChops, ImageFilter
import aiohttp
import asyncio
import time
import random
from io import BytesIO
from pathlib import Path

require("nonebot_plugin_localstore")
_Ecache_dir = None


def _get_cache_dir() -> Path:
    """获取当前插件的缓存目录"""
    global _Ecache_dir
    if _Ecache_dir is None: 
        import nonebot_plugin_localstore as store
        _Ecache_dir = store.get_plugin_cache_dir()
        _Ecache_dir.mkdir(parents=True, exist_ok=True)
    return _Ecache_dir


from .config import Config

plugin_config = get_plugin_config(Config)
osugreek = on_command("osugreek", aliases={"希腊字母"}, priority=5, block=False)

# 希腊字母图片目录
GREEK_IMAGE_DIR = Path(__file__).parent / "images"
GREEK_IMAGE_DIR.mkdir(exist_ok=True)


def add_chromatic_aberration(image: Image.Image, intensity: int = None) -> Image.Image:
    """色散效果"""
    if intensity is None:
        intensity = plugin_config.osugreek_chromatic_intensity
    
    # 强度范围到1-20
    intensity = max(1, min(20, intensity))
    
    r, g, b = image.split()[:3]
    
    r_offset = ImageChops.offset(r, -intensity, -intensity)
    g_offset = ImageChops.offset(g, 0, 0)
    b_offset = ImageChops.offset(b, intensity, intensity)
    
    if len(image.split()) == 4:
        a = image.split()[3]
        return Image.merge("RGBA", (r_offset, g_offset, b_offset, a))
    else:
        return Image.merge("RGB", (r_offset, g_offset, b_offset))


def add_glitch_effect(image: Image.Image, intensity: int = None) -> Image.Image:
    """故障效果"""
    if intensity is None:
        intensity = plugin_config.osugreek_glitch_intensity
    
    # 强度范围0-5
    intensity = max(0, min(5, intensity))
    
    if intensity == 0:
        return image.copy()
    
    width, height = image.size
    glitched = image.copy()
    
    # 根据强度决定故障效果的程度
    if intensity >= 1:
        # 水平偏移故障
        num_shifts = min(3, max(1, intensity))
        for _ in range(num_shifts):
            max_shift = max(5, int(width * 0.1 * intensity / 5))
            shift_amount = random.randint(2, max_shift)
            shift_direction = random.choice([-1, 1])
            
            min_shift_height = height // 20
            max_shift_height = height // 6 + (height // 12) * (intensity - 1)
            shift_height = random.randint(min_shift_height, max_shift_height)
            shift_y = random.randint(0, height - shift_height)
            
            region = glitched.crop((0, shift_y, width, shift_y + shift_height))
            glitched.paste(region, (shift_amount * shift_direction, shift_y))
        
    if intensity >= 2:
        # 噪点效果
        base_noise = 50
        noise_intensity = base_noise * (intensity ** 2)
        for _ in range(noise_intensity):
            x = random.randint(0, width - 1)
            y = random.randint(0, height - 1)
            color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255), 255)
            glitched.putpixel((x, y), color)
        
        # 噪点块效果
        if intensity >= 3:
            num_blocks = random.randint(1, intensity - 1)
            for _ in range(num_blocks):
                block_width = random.randint(5, 20)
                block_height = random.randint(5, 20)
                block_x = random.randint(0, width - block_width)
                block_y = random.randint(0, height - block_height)
                
                for bx in range(block_width):
                    for by in range(block_height):
                        if random.random() < 0.7:
                            px = min(block_x + bx, width - 1)
                            py = min(block_y + by, height - 1)
                            color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255), 255)
                            glitched.putpixel((px, py), color)
    
    if intensity >= 3:
        # 扫描线效果
        scanline_spacing = random.randint(8 - intensity, 15 - intensity)
        scanline_probability = 0.15 + (intensity - 3) * 0.05
        
        for y in range(0, height, scanline_spacing):
            if random.random() < scanline_probability:
                line_height = random.randint(1, 2)
                line_region = glitched.crop((0, y, width, y + line_height))
                # 扫描线亮度随强度变化
                brightness = 150 + (intensity - 3) * 25
                line_region = ImageChops.multiply(line_region, Image.new("RGBA", (width, line_height), (brightness, brightness, brightness, 255)))
                glitched.paste(line_region, (0, y))
                
    if intensity >= 4:
        # 扭曲效果
        # 高斯模糊
        blur_radius = 0.5 + (intensity - 4) * 0.5
        glitched = glitched.filter(ImageFilter.GaussianBlur(radius=blur_radius))
        
        # 颜色偏移扭曲
        if intensity >= 5:
            if len(glitched.split()) >= 3:
                r, g, b = glitched.split()[:3]
                offset_x = random.randint(-3, 3)
                offset_y = random.randint(-3, 3)
                
                r_offset = ImageChops.offset(r, offset_x, offset_y)
                b_offset = ImageChops.offset(b, -offset_x, -offset_y)
                
                if len(glitched.split()) == 4:
                    a = glitched.split()[3]
                    glitched = Image.merge("RGBA", (r_offset, g, b_offset, a))
                else:
                    glitched = Image.merge("RGB", (r_offset, g, b_offset))
    
    return glitched


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
    command_parts = msg_text.split()
    
    greek_name = ""
    chromatic_intensity = None
    glitch_intensity = None
    
    if len(command_parts) > 1:
        greek_name = command_parts[1]
    
    param_index = 2
    if param_index < len(command_parts) and command_parts[param_index].isdigit():
        chromatic_intensity = int(command_parts[param_index])
        param_index += 1
    
    if param_index < len(command_parts) and command_parts[param_index].isdigit():
        glitch_intensity = int(command_parts[param_index])
    
    if greek_name == "help" or not greek_name:
        help_text = "用法：/osugreek <希腊字母名称> [色散强度] [故障强度] 或 /希腊字母 <希腊字母名称> [色散强度] [故障强度]\n参数说明: \n-色散强度: 将图片RGB分离。范围[1,20], 不填则默认4。\n-故障强度: 将图片应用故障效果。强度决定故障效果的程度。范围[0,5], 不填则默认0。"
        await bot.send(event, help_text)
        available = [f.stem for f in GREEK_IMAGE_DIR.glob("*.png")]
        available.sort()
        await bot.send(event, f"可用的希腊字母名称有: {', '.join(available)}")
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
        
        # 应用色散效果
        chromatic_img = add_chromatic_aberration(
            original_img, 
            intensity=chromatic_intensity
        )
        
        # 应用故障效果（如果指定了强度）
        if glitch_intensity is not None and glitch_intensity > 0:
            chromatic_img = add_glitch_effect(chromatic_img, glitch_intensity)
        
        # 加载并叠加希腊字母
        greek_img_path = GREEK_IMAGE_DIR / f"{greek_name}.png"
        if not greek_img_path.exists():
            available = [f.stem for f in GREEK_IMAGE_DIR.glob("*.png")]
            available.sort()
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
        temp_output_path = _get_cache_dir() / temp_filename
        combined.save(temp_output_path, format="PNG")
        await bot.send(event, MessageSegment.image(f"file:///{temp_output_path.absolute()}"))
    except Exception as e:
        await bot.send(event, f"图片处理失败: {str(e)}")
        return
    finally:
        if temp_output_path and temp_output_path.exists():
            asyncio.create_task(cleanup_temp_file(temp_output_path))