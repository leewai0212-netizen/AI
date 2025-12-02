# 快速参考卡 - 抖音评论爬虫

## 📋 一页速查表

### 🚀 安装 (首次使用)
```bash
pip3 install -r requirements.txt
```

### 🎯 三种使用方式

#### 方式1: 交互式（最简单）⭐
```bash
python3 quick_start.py
```

#### 方式2: 快速脚本
```python
from douyin_comment_scraper import DouyinCommentScraper

scraper = DouyinCommentScraper(headless=False)
try:
    comments = scraper.scrape_comments(
        video_url="你的视频链接",
        max_comments=100,
        scroll_times=10
    )
    scraper.save_to_json()
    scraper.save_to_csv()
finally:
    scraper.close()
```

#### 方式3: 查看示例
```bash
python3 example.py
```

---

### 📖 重要参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `headless` | False | True=后台运行，False=显示浏览器 |
| `max_comments` | 100 | 最大爬取评论数量 |
| `scroll_times` | 10 | 滚动次数（越多评论越多） |

---

### 💾 保存方法

```python
scraper.save_to_json('comments.json')   # JSON格式
scraper.save_to_csv('comments.csv')     # CSV格式
scraper.save_to_excel('comments.xlsx')  # Excel格式
```

---

### 📊 数据格式

```python
{
    'index': 1,           # 序号
    'username': '用户名',  # 用户
    'content': '评论内容', # 内容
    'likes': 123,         # 点赞数
    'time': '2天前'        # 时间
}
```

---

### ❓ 常见问题快速解决

| 问题 | 解决方法 |
|------|----------|
| 未找到Chrome | 安装Chrome浏览器 |
| selenium未安装 | `pip3 install -r requirements.txt` |
| 未找到评论 | 设置 `headless=False` 查看页面 |
| 评论数量少 | 增加 `scroll_times` 参数 |
| 遇到验证码 | 使用 `headless=False` 手动完成 |

---

### 📁 文件速查

| 文件 | 用途 |
|------|------|
| `quick_start.py` | 交互式启动（推荐新手） |
| `example.py` | 4个使用示例 |
| `config.py` | 配置文件 |
| `使用指南.md` | 详细中文教程 |
| `START_HERE.md` | 快速开始 |

---

### 🔧 配置修改

编辑 `config.py`:
```python
MAX_COMMENTS = 200    # 改为200条
SCROLL_TIMES = 20     # 增加滚动次数
HEADLESS = True       # 改为后台运行
```

---

### 📞 获取帮助

1. 基础使用 → `START_HERE.md`
2. 详细教程 → `使用指南.md`
3. 技术文档 → `README.md`
4. 测试调试 → `TEST_GUIDE.md`

---

### ⚡ 立即开始

```bash
# 1. 安装
pip3 install -r requirements.txt

# 2. 运行
python3 quick_start.py

# 3. 输入视频链接，完成！
```

---

**打印本页备查！** 📄
