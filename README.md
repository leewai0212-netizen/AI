# 抖音视频评论爬虫

使用 Python + Playwright 爬取抖音视频评论的工具。

## ✨ 功能特点

- 🔗 支持短链接和完整链接
- 📊 自动滚动加载更多评论
- 💾 支持导出 Excel 和 JSON 格式
- 🎨 美观的终端进度显示
- 🛡️ 内置反检测机制

## 📦 安装依赖

```bash
# 1. 安装 Python 依赖
pip install -r requirements.txt

# 2. 安装 Playwright 浏览器 (首次运行必须)
playwright install chromium
```

## 🚀 使用方法

### 基本用法

```bash
# 使用短链接
python douyin_comments_scraper.py https://v.douyin.com/xxxxx/

# 使用完整链接
python douyin_comments_scraper.py https://www.douyin.com/video/7123456789012345678
```

### 高级选项

```bash
# 指定最大评论数量 (默认100条)
python douyin_comments_scraper.py VIDEO_URL -n 500

# 显示浏览器窗口 (用于手动处理验证码)
python douyin_comments_scraper.py VIDEO_URL --no-headless

# 只导出 Excel
python douyin_comments_scraper.py VIDEO_URL -o excel

# 只导出 JSON
python douyin_comments_scraper.py VIDEO_URL -o json
```

### 在代码中使用

```python
import asyncio
from douyin_comments_scraper import scrape_douyin_comments

# 爬取评论
asyncio.run(scrape_douyin_comments(
    video_url="https://v.douyin.com/xxxxx/",
    max_comments=200,
    headless=True,
    output_format='both'
))
```

## 📁 输出文件

程序会自动生成以时间戳命名的文件：

- `douyin_comments_YYYYMMDD_HHMMSS.xlsx` - Excel 格式
- `douyin_comments_YYYYMMDD_HHMMSS.json` - JSON 格式

### Excel 文件包含的字段

| 字段 | 说明 |
|------|------|
| 用户昵称 | 评论者的抖音昵称 |
| 评论内容 | 评论的具体内容 |
| 点赞数 | 该评论获得的点赞数 |
| 发布时间 | 评论发布时间 |
| 视频标题 | 被评论视频的标题 |
| 视频作者 | 视频发布者 |
| 视频链接 | 原视频链接 |
| 采集时间 | 数据采集的时间 |

## ⚠️ 注意事项

1. **反爬机制**: 抖音有反爬虫机制，请适度使用，避免频繁请求
2. **验证码处理**: 如果遇到验证码，使用 `--no-headless` 参数手动验证
3. **登录状态**: 某些评论可能需要登录才能查看
4. **网络环境**: 确保网络环境稳定，建议使用代理
5. **合规使用**: 请遵守相关法律法规，仅用于学习研究

## 🔧 故障排除

### 问题: 浏览器启动失败

```bash
# 重新安装 Playwright 浏览器
playwright install chromium --with-deps
```

### 问题: 无法获取评论

1. 尝试使用 `--no-headless` 参数查看实际页面
2. 检查视频链接是否有效
3. 视频可能已被删除或设置为私密

### 问题: 评论数量不足

抖音可能限制了评论加载，或视频评论本身较少

## 📝 License

MIT License
