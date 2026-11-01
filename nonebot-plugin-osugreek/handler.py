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

# 动图逐帧处理上限：超过就等间隔抽帧（总时长不变），避免超大动图耗死 bot。
MAX_ANIM_FRAMES = 150

# 动图体积上限：输出动图和输入基本同量级，太大读取和发送都会很慢，直接提示用户换小的。
MAX_ANIM_BYTES = 10 * 1024 * 1024

# 逐帧处理的像素预算（帧数 x 宽 x 高）：超了就整体等比缩小，保证单张动图的处理时间可控。
MAX_ANIM_PIXELS = 8_000_000

MB = 1024 * 1024

# alpha<128 视为透明。用 256 项 LUT 而不是 lambda：point() 传函数是逐像素 Python 回调，慢几十倍。
# 方向：低 alpha -> 255（标记成透明索引），高 alpha -> 0（保持原色）。
ALPHA_MASK_LUT = [255] * 128 + [0] * 128


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


def is_animated_image(image: Image.Image) -> bool:
    """是否是多帧动图（GIF / WebP / APNG）。"""
    return bool(getattr(image, "is_animated", False)) and getattr(image, "n_frames", 1) > 1


def prepare_overlay(overlay: Image.Image, width: int, height: int):
    """把字母图缩放到目标画布并算出居中位置，返回 (字母图, (x, y))。"""
    greek = resize_greek_image(overlay, width, height)
    return greek, ((width - greek.width) // 2, (height - greek.height) // 2)


async def cleanup_temp_file(file_path: Path, delay: float = 5.0):
    """清理临时文件"""
    await asyncio.sleep(delay)
    try:
        if file_path.exists():
            file_path.unlink()
    except Exception:
        pass


def generate_temp_filename(suffix: str = ".png") -> str:
    """生成唯一的临时文件名"""
    timestamp = int(time.time() * 1000)
    random_suffix = random.randint(1000, 9999)
    return f"processed_{timestamp}_{random_suffix}{suffix}"


def load_animation(im: Image.Image, max_frames: int = MAX_ANIM_FRAMES, max_pixels: int = MAX_ANIM_PIXELS):
    """拆动图为逐帧 RGBA，返回 (frames, durations_ms, loop)。

    - `seek` 后 Pillow 已按 disposal 把该帧合成到整块画布上，尺寸统一，可以直接贴字母；
    - 帧数超过 max_frames 时等间隔抽帧，被抽掉帧的时长并到保留帧上，总时长（播放速度）不变；
    - 帧数 x 面积超过 max_pixels 时整体等比缩小，避免单张动图要算十几秒；
    - 时长单位毫秒，缺失按 100ms（GIF 默认 10fps）。
    """
    total = int(getattr(im, "n_frames", 1) or 1)
    step = max(1, -(-total // max_frames))  # 向上取整：>150 帧才开始抽帧
    kept = -(-total // step)
    width, height = im.size
    scale = min(1.0, (max_pixels / max(1, kept * width * height)) ** 0.5)
    target = (max(1, int(width * scale)), max(1, int(height * scale))) if scale < 1 else None

    frames, durations = [], []
    for index in range(0, total, step):
        im.seek(index)
        frame = im.convert("RGBA")
        if target is not None and frame.size != target:
            frame = frame.resize(target, Image.Resampling.BILINEAR)
        frames.append(frame)

        # 实际播放时长：index..index+step 之间被抽掉的帧也要算进来
        duration = 0
        for probe in range(index, min(index + step, total)):
            im.seek(probe)
            duration += max(20, int(im.info.get("duration", 100) or 100))
        durations.append(duration)

    return frames, durations, int(im.info.get("loop", 0) or 0)


def render_frame(frame: Image.Image, greek_img: Image.Image, position, chromatic_intensity, glitch_intensity) -> Image.Image:
    """单帧：色散 + 故障 + 居中贴字母，返回新的 RGBA 帧。"""
    out = add_chromatic_aberration(frame, intensity=chromatic_intensity)
    if glitch_intensity is not None and glitch_intensity > 0:
        out = add_glitch_effect(out, glitch_intensity)
    out.paste(greek_img, position, greek_img)
    return out


def save_animated_gif(frames, path, durations, loop, source_format: str = None) -> None:
    """把 RGBA 帧序列编码成会动的 GIF。

    GIF 只有 256 色调色板加一个透明色，所以：
    - 每帧量化到 255 色，索引 255 留给透明像素（quantize 用不到它）；
    - 有透明像素时把 alpha<128 的位置填成索引 255，并声明 transparency=255；
    - disposal=2 配合整帧画面避免残影；duration 传列表逐帧保时长，loop 保留循环次数。

    量化档次按来源区分：GIF 源本来就是 256 色，FASTOCTREE 又快又几乎无损；
    WebP / APNG 这类真彩源才用较慢但更细腻的 MEDIANCUT + 抖动。
    """
    truecolor = source_format not in ("GIF", None)
    method, dither = (
        (Image.Quantize.MEDIANCUT, Image.Dither.FLOYDSTEINBERG)
        if truecolor
        else (Image.Quantize.FASTOCTREE, Image.Dither.NONE)
    )
    transparent = any(f.getchannel("A").getextrema()[0] < 255 for f in frames)

    paletted = []
    for frame in frames:
        quantized = frame.convert("RGB").quantize(colors=255, method=method, dither=dither)
        if transparent:
            quantized.paste(255, frame.getchannel("A").point(ALPHA_MASK_LUT))
        paletted.append(quantized)

    kwargs = {
        "save_all": True,
        "append_images": paletted[1:],
        "duration": durations,
        "loop": loop,
        "disposal": 2,
        "optimize": False,
    }
    if transparent:
        kwargs["transparency"] = 255
    paletted[0].save(path, format="GIF", **kwargs)


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
        source_img = Image.open(BytesIO(img_data))

        # 字母图只加载/缩放一次，动图逐帧复用
        greek_img_path = GREEK_IMAGE_DIR / f"{greek_name}.png"
        if not greek_img_path.exists():
            available = sorted(f.stem for f in GREEK_IMAGE_DIR.glob("*.png"))
            await bot.send(event, f"未找到 {greek_name}.png\n可用的有: {', '.join(available)}")
            return
        greek_overlay = Image.open(greek_img_path).convert("RGBA")

        if is_animated_image(source_img):
            # 动图：逐帧上效果 + 贴字母，再编码回动图 GIF（原来只取第一帧存 PNG，动图就死了）
            if len(img_data) > MAX_ANIM_BYTES:
                await bot.send(
                    event,
                    "这张动图太大了（%.1fMB），转成 GIF 后 OneBot 发不动。\n发 %dMB 以内的，或者少截几帧。"
                    % (len(img_data) / MB, MAX_ANIM_BYTES // MB),
                )
                return
            frames, durations, loop = load_animation(source_img)
            greek_frame, position = prepare_overlay(greek_overlay, *frames[0].size)
            temp_output_path = _get_cache_dir() / generate_temp_filename(".gif")
            save_animated_gif(
                [
                    render_frame(frame, greek_frame, position, chromatic_intensity, glitch_intensity)
                    for frame in frames
                ],
                temp_output_path,
                durations,
                loop,
                source_format=source_img.format,
            )
        else:
            # 静态图：结果还是 PNG，行为与旧版一致
            static_img = source_img.convert("RGBA")
            greek_img, position = prepare_overlay(greek_overlay, static_img.width, static_img.height)
            temp_output_path = _get_cache_dir() / generate_temp_filename()
            render_frame(static_img, greek_img, position, chromatic_intensity, glitch_intensity).save(
                temp_output_path, format="PNG"
            )
        await bot.send(event, MessageSegment.image(f"file:///{temp_output_path.absolute()}"))
    except Exception as e:
        await bot.send(event, f"图片处理失败: {str(e)}")
        return
    finally:
        if temp_output_path and temp_output_path.exists():
            asyncio.create_task(cleanup_temp_file(temp_output_path))