# 抖音视频评论爬虫

一个功能完整的Python爬虫工具，用于爬取抖音视频的评论数据。

## ✨ 特性

- 🚀 基于Selenium的自动化爬虫
- 🔄 支持滚动加载更多评论
- 💾 支持导出为JSON、CSV、Excel格式
- 🛡️ 内置反检测机制
- ⚙️ 灵活的配置选项
- 📊 支持批量爬取多个视频

## 📋 环境要求

- Python 3.7+
- Chrome浏览器
- ChromeDriver（会自动管理）

## 🔧 安装

### 1. 克隆或下载项目

```bash
git clone <repository-url>
cd <project-directory>
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 安装Chrome浏览器

确保系统已安装Chrome浏览器。如果没有安装：

- **Windows/Mac**: 从 [Google Chrome官网](https://www.google.com/chrome/) 下载安装
- **Linux**: 
  ```bash
  wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
  sudo dpkg -i google-chrome-stable_current_amd64.deb
  sudo apt-get install -f
  ```

## 🚀 快速开始

### 基础使用

```python
from douyin_comment_scraper import DouyinCommentScraper

# 创建爬虫实例
scraper = DouyinCommentScraper(headless=False)

try:
    # 爬取评论
    comments = scraper.scrape_comments(
        video_url="https://www.douyin.com/video/1234567890",
        max_comments=100,
        scroll_times=10
    )
    
    # 保存数据
    scraper.save_to_json('comments.json')
    scraper.save_to_csv('comments.csv')
    
finally:
    scraper.close()
```

### 运行示例

项目包含多个使用示例，可以直接运行：

```bash
python example.py
```

## 📖 详细使用说明

### DouyinCommentScraper 类

#### 初始化参数

```python
scraper = DouyinCommentScraper(headless=False)
```

- `headless` (bool): 是否使用无头模式（不显示浏览器窗口）
  - `False`: 显示浏览器窗口（默认，推荐用于调试）
  - `True`: 后台运行，不显示窗口

#### 主要方法

##### 1. scrape_comments()

爬取视频评论

```python
comments = scraper.scrape_comments(
    video_url="https://www.douyin.com/video/1234567890",
    max_comments=100,
    scroll_times=10
)
```

**参数说明:**
- `video_url` (str): 抖音视频链接
- `max_comments` (int): 最大爬取评论数量，默认100
- `scroll_times` (int): 页面滚动次数，默认10（每次滚动会加载更多评论）

**返回值:** 评论列表，每条评论包含:
```python
{
    'index': 1,                    # 序号
    'username': '用户名',          # 评论用户
    'content': '评论内容',         # 评论文本
    'likes': 123,                  # 点赞数
    'time': '2天前'                # 发布时间
}
```

##### 2. save_to_json()

保存评论为JSON格式

```python
scraper.save_to_json('comments.json')
```

##### 3. save_to_csv()

保存评论为CSV格式

```python
scraper.save_to_csv('comments.csv')
```

##### 4. save_to_excel()

保存评论为Excel格式

```python
scraper.save_to_excel('comments.xlsx')
```

##### 5. close()

关闭浏览器（重要！）

```python
scraper.close()
```

## 📝 使用示例

### 示例1: 基础爬取

```python
from douyin_comment_scraper import DouyinCommentScraper

scraper = DouyinCommentScraper(headless=False)

try:
    comments = scraper.scrape_comments(
        video_url="https://www.douyin.com/video/7234567890123456789",
        max_comments=50,
        scroll_times=5
    )
    
    print(f"共爬取 {len(comments)} 条评论")
    
    scraper.save_to_json()
    scraper.save_to_csv()
    
finally:
    scraper.close()
```

### 示例2: 批量爬取

```python
video_urls = [
    "https://www.douyin.com/video/7234567890123456789",
    "https://www.douyin.com/video/7234567890123456790",
]

scraper = DouyinCommentScraper()

try:
    for idx, url in enumerate(video_urls, 1):
        comments = scraper.scrape_comments(url, max_comments=30)
        scraper.save_to_json(f'comments_{idx}.json')
finally:
    scraper.close()
```

### 示例3: 数据分析

```python
scraper = DouyinCommentScraper()

try:
    comments = scraper.scrape_comments(
        video_url="https://www.douyin.com/video/7234567890123456789",
        max_comments=100
    )
    
    # 统计分析
    total_likes = sum(c['likes'] for c in comments)
    avg_likes = total_likes / len(comments)
    
    # 找出最热评论
    top_comment = max(comments, key=lambda x: x['likes'])
    
    print(f"总评论: {len(comments)}")
    print(f"平均点赞: {avg_likes:.2f}")
    print(f"最热评论: {top_comment['content']}")
    
finally:
    scraper.close()
```

## ⚙️ 配置说明

可以通过修改 `config.py` 文件来调整默认配置：

```python
# 浏览器配置
HEADLESS = False           # 是否无头模式
WINDOW_SIZE = "1920,1080"  # 窗口大小

# 爬虫配置
MAX_COMMENTS = 100         # 最大评论数
SCROLL_TIMES = 10          # 滚动次数

# 输出配置
OUTPUT_JSON = True         # 输出JSON
OUTPUT_CSV = True          # 输出CSV
OUTPUT_EXCEL = False       # 输出Excel
```

## 🔍 获取视频链接

1. 打开抖音网页版: https://www.douyin.com
2. 搜索或找到目标视频
3. 点击视频进入详情页
4. 复制浏览器地址栏的URL

**支持的URL格式:**
- `https://www.douyin.com/video/1234567890`
- `https://www.douyin.com/share/video/1234567890`

## 📊 输出文件格式

### JSON格式
```json
[
  {
    "index": 1,
    "username": "用户A",
    "content": "这个视频太棒了！",
    "likes": 123,
    "time": "2天前"
  }
]
```

### CSV格式
```csv
index,username,content,likes,time
1,用户A,这个视频太棒了！,123,2天前
```

## ⚠️ 注意事项

1. **遵守法律法规**: 请遵守相关法律法规和抖音平台的使用条款
2. **合理使用**: 不要过于频繁地爬取，避免给服务器造成压力
3. **数据使用**: 爬取的数据仅供学习和研究使用，请勿用于商业用途
4. **反爬机制**: 抖音有较强的反爬机制，可能需要：
   - 登录账号
   - 手动滑动验证码
   - 适当增加延时
5. **浏览器关闭**: 使用完毕后务必调用 `scraper.close()` 关闭浏览器

## 🐛 常见问题

### 1. ChromeDriver版本不匹配

**问题**: 提示ChromeDriver版本与Chrome不匹配

**解决**: 使用webdriver-manager自动管理：
```python
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)
```

### 2. 找不到评论元素

**问题**: 提示"未找到评论元素"

**原因**: 
- 页面结构变化
- 需要登录
- 页面加载未完成

**解决**:
1. 设置 `headless=False` 查看实际页面
2. 增加等待时间
3. 检查是否需要登录
4. 查看保存的 `page_source.html` 文件分析页面结构

### 3. 评论数量少于预期

**问题**: 爬取的评论数量少于设置的max_comments

**原因**: 
- 视频本身评论就不多
- 滚动次数不够

**解决**: 增加 `scroll_times` 参数

### 4. 遇到验证码

**问题**: 需要滑动验证码

**解决**: 
1. 使用非无头模式 (`headless=False`)
2. 手动完成验证码
3. 程序会继续执行

## 📜 许可证

本项目仅供学习和研究使用。

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📧 联系方式

如有问题，请通过Issue联系。

---

**免责声明**: 本工具仅供学习和研究使用，使用者需自行承担使用风险，开发者不对任何因使用本工具而产生的问题负责。
