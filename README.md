# Xiaomi Photo Recovery

从仍可访问的小米 / Android 缓存、缩略图和回收站中提取媒体的 Python 命令行工具。

**能力边界：**不扫描未分配磁盘空间，不恢复已覆盖数据，不绕过设备锁或 Android 应用沙箱。缓存中可能只有低分辨率缩略图，无法据此重建原始照片。微信 `.dat` 支持的是代码实现的 XOR 格式，不代表兼容所有微信版本。ADB 导入需要设备授权和源目录读取权限；具体机型、系统版本的可访问范围不同。

## 恢复源

| 来源 | 路径 | 说明 |
|------|------|------|
| 小米图库缓存 | `gallery_disk_cache/` | 默认恢复源 |
| DCIM 缩略图 | `DCIM/.thumbnails/` | 系统缩略图缓存 |
| 微信缓存 | `com.tencent.mm/MicroMsg/` | 聊天图片/视频/表情（自动解密 .dat） |
| QQ 缓存 | `com.tencent.mobileqq/Tencent/MobileQQ/` | 聊天图片/视频/照片 |
| 浏览器缓存 | Chrome / Samsung / Firefox cache | 网页图片缓存 |
| 回收站 | `.Trash-*` / MIUI 回收站 | 未彻底删除的文件 |

## 默认输出目录

- Android / Termux：`/storage/emulated/0/Recovery/<设备名-日期>/`
- 桌面端：`<当前工作目录>/Recovery/<设备名-日期>/`

## 功能

- 递归扫描多个缓存目录
- 按文件头识别图片/视频（JPEG/PNG/GIF/WebP/HEIC/HEIF/MP4/MOV/3GP）
- 自动补全正确扩展名
- 微信 .dat 加密文件自动解密
- 原始缩略图解码（RGB565/RGBA8888）
- 尽量提取 EXIF / 视频元数据
- 设备级去重（同设备同内容不重复恢复）
- 恢复结果质量分层
- 生成 `manifest.json` / `manifest.csv`

## 依赖

- Python 3.11+
- Pillow
- `ffprobe`（可选，存在时可提取更多视频元数据）
- `adb`（使用 from-adb 命令时需要）

## 安装

```bash
git clone https://github.com/nullinject/xiaomi-photo-recovery.git
cd xiaomi-photo-recovery
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install -r requirements-dev.lock
python -m pip install --no-deps -e .
```

## 无手机演示：合成图片

```bash
python examples/synthetic_demo.py
```

程序在临时目录生成一张无个人信息的 PNG，将其当作无扩展名缓存文件恢复，
核对恢复文件与原图字节完全一致，并验证重复恢复会被跳过。无需 ADB、手机或网络；
临时文件和索引在结束后自动清理。该演示验证缓存提取流程，不证明任意设备上的恢复成功率。

## 命令

### 一键 ADB 恢复（推荐）

连接手机后运行，自动拉取所有缓存目录并恢复：

```bash
xiaomi-recovery from-adb --output ~/Desktop/recovery
```

参数：

- `--device-serial` — 指定设备序列号（单设备时自动检测）
- `--device-name` — 指定设备名
- `--only-sources wechat,qq` — 只运行指定来源
- `--keep-temp` — 保留临时目录以便排错
- `--dry-run` — 只扫描不复制

### 单独恢复命令

```bash
# 恢复小米图库缓存
xiaomi-recovery --source /path/to/gallery_disk_cache

# 恢复 DCIM 缩略图
xiaomi-recovery recover-dcim-thumbnails --source /path/to/.thumbnails

# 解码原始缩略图
xiaomi-recovery decode-raw-thumbnails --source /path/to/gallery_disk_cache --output /path/to/output
```

### 历史索引管理

```bash
xiaomi-recovery index-existing --device-serial SERIAL --device-name "Device" --dir /path/to/restored
```

## 设备级去重

历史索引默认存放在：`~/.xiaomi-photo-recovery/recovery_index.db`

- 同一设备（device serial 相同）且内容相同（sha256 相同）的文件不会重复恢复
- 不同设备即使内容相同，也会分别保留各自的恢复记录

## 测试

```bash
python3 -m pytest tests -v
```

## 数据与验证

恢复索引、清单与输出可能包含设备序列号、原始路径及媒体元数据，应保留在本机。
`--dry-run` 不复制媒体，但仍可能创建报告、目录与索引，不是完全无写入的模式。
本仓库仅提供合成测试数据，不包含真实手机照片、聊天文件或设备备份。

```bash
python -m pytest -q
python examples/synthetic_demo.py
```

支持 Python 3.11+。GitHub Actions 执行单元测试和合成演示；ADB 真机行为另行验证。

[MIT License](LICENSE) · [安全与数据说明](SECURITY.md)
