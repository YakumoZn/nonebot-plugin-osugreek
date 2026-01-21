# nonebot-plugin-osugreek
<h1 align="center">✨ 4k希腊字母BG生成器 ✨</h1>
<p align="center">
_✨ 在图片上添加osu!mania 4k神秘希腊字母的 NoneBot2 插件，可批量生产练习图BG ✨_
</p>
<p align="center">
  <a href="https://raw.githubusercontent.com/cscs181/QQ-Github-Bot/master/LICENSE">
    <img src="https://img.shields.io/github/license/cscs181/QQ-Github-Bot.svg" alt="license">
  </a>
  <a href="https://pypi.python.org/pypi/nonebot-plugin-analysis-bilibili">
    <img src="https://img.shields.io/pypi/v/nonebot-plugin-analysis-bilibili.svg" alt="pypi">
  </a>
  <img src="https://img.shields.io/badge/python-3.8+-blue.svg" alt="python">
</p>


## 介绍

- 在图片中央贴上神秘的4k希腊字母
- 顺便添加色散视觉效果


## 快速安装
<details><summary> 本插件依赖以下库：</summary>
  
```shell  
nonebot2 >= 2.0.0
  
Pillow >= 9.0.0

aiohttp >= 3.8.0
```

</details>

### 使用 nb-cli (暂留空)

```shell
nb plugin install nonebot-plugin-osugreek
```

### 通过 pip 安装

```shell
pip install nonebot-plugin-osugreek
```

### 从 GitHub 安装

```shell
https://github.com/YakumoZn/nonebot-plugin-osugreek.git
```


## 使用

### 基础命令

```shell
/osugreek <希腊字母名称>
```
或
```shell
/希腊字母 <希腊字母名称>
```

### 使用方式
- 回复图片消息并输入：/osugreek <希腊字母名称>

<details> 
<summary><strong>示例</strong></summary>

![](https://i.ibb.co/xTL64vr/228922e3afd8a362ad5612a0645951b7.jpg)
*我得了一种看见希腊字母就会笑的病*
</details>


### 其他


<details><summary><strong>配置</strong></summary>


在 `.env` 文件中可以设置以下配置项：

```env
# 色散强度（范围1-10，默认4）
OSUGREEK_CHROMATIC_INTENSITY=4
```
</details>
<details><summary><strong>图片</strong></summary>

  
- 默认提取 **images/** 目录内的所有PNG格式文件
- 如果需要添加或修改新的希腊字母，只需将 PNG 图片放入 images/ 目录即可

</details>
