"""
媒体素材预处理（一次性，需已存在 backend/media/avatar/<name>.jpg 真人原图）：
- 头像：居中偏上方形裁剪 + 缩放为 256x256（WeChat 风格圆形头像）
- 发照片素材：同一张真人图派生 3 种取景（原比例 / 3:4 / 方形），避免占位渐变图

用法：cd backend && python tools/process_media.py
"""
from pathlib import Path

from PIL import Image, ImageOps

MEDIA = Path(__file__).resolve().parent.parent / "media"
AVATAR_SIZE = 256
PHOTO_QUALITY = 85

# 人设 -> (原图, 目标目录, 目标文件名前缀, 是否派生"发照片"素材)
# (人设, 原图, 目标目录, 文件名前缀, 起始序号, 是否派生"发照片"素材)
JOBS = [
    ("ajing",  "avatar/ajing.jpg",  "avatar", "ajing",  1, False),  # 吊着不给：不需要素材
    ("taotao", "avatar/taotao.jpg", "life",   "photo",  1, True),   # 自拍
    ("xiaoyu", "avatar/xiaoyu.jpg", "tea",    "photo",  1, True),   # 茶女
    ("xueer",  "avatar/xueer.jpg",  "life",   "photo",  4, True),   # 甜美
]


def _open(name: str, rel: str) -> Image.Image:
    img = Image.open(MEDIA / rel)
    img = ImageOps.exif_transpose(img)
    if img.mode != "RGB":
        img = img.convert("RGB")
    return img


def _square_avatar(img: Image.Image, size: int = AVATAR_SIZE) -> Image.Image:
    """取尽量靠上的人脸区域：竖图裁顶部靠下一点，横图取居中条幅。"""
    w, h = img.size
    side = min(w, h)
    if h >= w:  # 竖图/方图：偏上取景，防止切掉头顶
        y0 = int(h * 0.06)
        y0 = min(y0, h - side)
        box = (0, y0, side, y0 + side)
    else:       # 横图：上下满幅居中
        x0 = (w - side) // 2
        box = (x0, 0, x0 + side, side)
    return img.crop(box).resize((size, size), Image.LANCZOS)


def _cover(img: Image.Image, ratio: tuple[int, int]) -> Image.Image:
    """按目标比例 cover 裁剪，竖图偏上、横图居中。"""
    rw, rh = ratio
    w, h = img.size
    target = rh / rw
    cur = h / w
    if cur > target:  # 太瘦 -> 裁高度
        hc = int(w * target)
        y0 = int((h - hc) * 0.12)
        box = (0, y0, w, y0 + hc)
    else:             # 太宽 -> 裁宽度（居中）
        wc = int(h / target)
        x0 = (w - wc) // 2
        box = (x0, 0, x0 + wc, h)
    return img.crop(box)


def _save(img: Image.Image, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, "JPEG", quality=PHOTO_QUALITY, optimize=True)


def main() -> None:
    # 1) 先由原图派生"发照片"素材（此时 avatar/*.jpg 仍是原图）
    for persona, src, folder, prefix, start, with_photos in JOBS:
        if not with_photos:
            continue
        img = _open(persona, src)
        variants = [
            img.copy(),                       # 原比例整图
            _cover(img, (3, 4)),              # 3:4 相册照
            _cover(img, (1, 1)),              # 方形特写
        ]
        for i, v in enumerate(variants, start=start):
            v.thumbnail((1280, 1280), Image.LANCZOS)
            _save(v, MEDIA / folder / f"{prefix}{i}.jpg")
        print(f"生成 {folder}/{prefix}{start}..{start+2}.jpg <- {persona}.jpg 原图")

    # 2) 头像统一覆盖为 256x256 方形
    for persona, src, _folder, _prefix, _start, _w in JOBS:
        img = _open(persona, src)
        _save(_square_avatar(img), MEDIA / "avatar" / f"{persona}.jpg")
        print(f"头像 avatar/{persona}.jpg -> {AVATAR_SIZE}x{AVATAR_SIZE}")


if __name__ == "__main__":
    main()
