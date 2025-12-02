# 🎉 开始使用 - 抖音评论爬虫

欢迎使用抖音视频评论爬虫！本文档将帮助你快速上手。

## 📦 项目已包含的文件

✅ **核心文件**
- `douyin_comment_scraper.py` - 主爬虫程序（320行代码）
- `quick_start.py` - 交互式启动脚本（推荐新手使用）
- `example.py` - 4个完整使用示例
- `config.py` - 配置文件

✅ **文档文件**
- `README.md` - 完整技术文档
- `使用指南.md` - 详细中文教程
- `TEST_GUIDE.md` - 测试指南
- `PROJECT_STRUCTURE.md` - 项目结构说明
- `START_HERE.md` - 本文件

✅ **配置文件**
- `requirements.txt` - Python依赖包
- `install.sh` - 自动安装脚本
- `.gitignore` - Git配置

---

## 🚀 三步开始使用

### 第一步：安装依赖

**方式A: 自动安装（推荐）**
```bash
bash install.sh
```

**方式B: 手动安装**
```bash
pip3 install -r requirements.txt
```

需要安装的包：
- selenium (浏览器自动化)
- pandas (数据处理)
- openpyxl (Excel支持)
- webdriver-manager (驱动管理)

### 第二步：获取视频链接

1. 打开抖音网页版: https://www.douyin.com
2. 找到想要爬取评论的视频
3. 复制视频链接（类似：`https://www.douyin.com/video/1234567890`）

### 第三步：运行爬虫

**最简单的方式（推荐）：**
```bash
python3 quick_start.py
```

然后按提示输入：
- 视频链接
- 评论数量（建议先输入20测试）
- 是否无头模式（建议选n，可以看到浏览器运行）

**就这么简单！** 🎊

---

## 📚 更多使用方式

### 方式1: 运行示例代码

```bash
# 编辑 example.py，修改其中的视频链接
vim example.py

# 运行示例
python3 example.py
```

### 方式2: 编写自己的脚本

创建文件 `my_scraper.py`:

```python
from douyin_comment_scraper import DouyinCommentScraper

# 创建爬虫
scraper = DouyinCommentScraper(headless=False)

try:
    # 爬取评论（替换为你的视频链接）
    comments = scraper.scrape_comments(
        video_url="https://www.douyin.com/video/你的视频ID",
        max_comments=100,
        scroll_times=10
    )
    
    # 打印结果
    print(f"成功爬取 {len(comments)} 条评论")
    
    # 保存数据
    scraper.save_to_json('comments.json')
    scraper.save_to_csv('comments.csv')
    
finally:
    scraper.close()
```

运行：
```bash
python3 my_scraper.py
```

---

## 🎯 参数说明

### DouyinCommentScraper()

```python
scraper = DouyinCommentScraper(headless=False)
```

- `headless=False`: 显示浏览器窗口（推荐调试时使用）
- `headless=True`: 后台运行，不显示窗口（适合自动化）

### scrape_comments()

```python
comments = scraper.scrape_comments(
    video_url="视频链接",
    max_comments=100,    # 最多爬取100条
    scroll_times=10      # 滚动10次加载更多
)
```

---

## 📊 输出文件

运行成功后会生成：

- `douyin_comments.json` - JSON格式数据
- `douyin_comments.csv` - CSV格式（可用Excel打开）
- `douyin_comments.xlsx` - Excel格式（如果启用）

---

## ⚠️ 重要提示

1. **Chrome浏览器**: 必须安装Chrome或Chromium浏览器
2. **网络连接**: 需要稳定的网络访问抖音
3. **合法使用**: 仅供学习研究，请遵守法律法规
4. **频率控制**: 不要过于频繁爬取，避免被限制
5. **关闭浏览器**: 使用后务必调用 `scraper.close()`

---

## ❓ 遇到问题？

### 常见问题快速解决

**Q1: 提示 "No module named 'selenium'"**

A: 安装依赖包
```bash
pip3 install -r requirements.txt
```

**Q2: 找不到Chrome浏览器**

A: 安装Chrome
- Windows/Mac: https://www.google.com/chrome/
- Linux: `bash install.sh` 会提示安装命令

**Q3: 未找到评论**

A: 可能的原因
- 视频没有评论
- 需要登录账号
- 页面加载未完成

解决：使用 `headless=False` 查看实际情况

**Q4: 评论数量少于预期**

A: 增加滚动次数
```python
scroll_times=20  # 增加到20次
```

### 查看详细文档

- **完整教程**: `cat 使用指南.md`
- **技术文档**: `cat README.md`
- **测试指南**: `cat TEST_GUIDE.md`

---

## 📁 项目结构

```
douyin-comment-scraper/
├── douyin_comment_scraper.py  # 主程序 ⭐
├── quick_start.py             # 快速启动 ⭐
├── example.py                 # 使用示例
├── config.py                  # 配置文件
├── requirements.txt           # 依赖包
├── README.md                  # 技术文档
├── 使用指南.md                # 中文教程 ⭐
└── START_HERE.md             # 本文件 ⭐
```

---

## 🎓 学习路径

### 第1天：入门
1. 安装依赖：`bash install.sh`
2. 运行快速启动：`python3 quick_start.py`
3. 查看输出文件：`cat douyin_comments.json`

### 第2天：进阶
1. 阅读示例：`cat example.py`
2. 修改配置：`vim config.py`
3. 编写自己的脚本

### 第3天：高级
1. 批量爬取多个视频
2. 数据分析和可视化
3. 定时任务和自动化

---

## 💡 使用技巧

1. **首次使用**: 从少量评论开始测试（20条）
2. **观察过程**: 使用 `headless=False` 看浏览器操作
3. **增加数量**: 确认正常后再增加评论数量
4. **保存数据**: 同时保存JSON和CSV格式备份
5. **遵守规则**: 合理控制频率，尊重平台规则

---

## 🎉 立即开始

**现在就运行第一个爬虫：**

```bash
# 1. 安装依赖
pip3 install -r requirements.txt

# 2. 运行快速启动脚本
python3 quick_start.py

# 3. 按提示输入视频链接和参数

# 4. 等待爬取完成

# 5. 查看结果
cat douyin_comments.json
```

---

## 📞 获取帮助

遇到问题？按顺序尝试：

1. 📖 查看 `使用指南.md` 的常见问题部分
2. 🔍 查看 `TEST_GUIDE.md` 测试是否正常
3. 📝 查看 `README.md` 的API文档
4. 💻 查看 `page_source.html` 调试页面结构

---

## ✅ 准备好了吗？

现在你已经了解了所有基础知识，可以开始使用了！

**推荐第一步：**
```bash
python3 quick_start.py
```

**祝使用愉快！** 🚀

---

*最后更新: 2025-12-02*  
*项目版本: v1.0.0*  
*代码行数: 1700+ 行*
