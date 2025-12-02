# 项目结构说明

```
douyin-comment-scraper/
│
├── douyin_comment_scraper.py    # 主爬虫类（核心代码）
│   ├── DouyinCommentScraper     # 爬虫类
│   ├── scrape_comments()        # 爬取评论方法
│   └── save_to_json/csv/excel() # 数据导出方法
│
├── quick_start.py               # 交互式启动脚本（推荐新手）
│   └── 命令行交互界面
│
├── example.py                   # 使用示例代码
│   ├── example_basic()          # 基础使用示例
│   ├── example_with_config()    # 配置文件示例
│   ├── example_batch_scrape()   # 批量爬取示例
│   └── example_custom_analysis() # 数据分析示例
│
├── config.py                    # 配置文件
│   ├── 浏览器配置
│   ├── 爬虫配置
│   └── 输出配置
│
├── requirements.txt             # Python依赖包列表
│   ├── selenium                 # 浏览器自动化
│   ├── pandas                   # 数据处理
│   ├── openpyxl                 # Excel支持
│   └── webdriver-manager        # 驱动管理
│
├── install.sh                   # 自动安装脚本（Linux/Mac）
│
├── README.md                    # 项目说明文档（英文为主）
├── 使用指南.md                   # 详细使用指南（中文）
├── PROJECT_STRUCTURE.md         # 本文件
├── LICENSE                      # 开源协议
└── .gitignore                   # Git忽略文件配置
```

## 📄 文件说明

### 核心文件

#### `douyin_comment_scraper.py`
- **作用**: 主爬虫实现
- **类**: DouyinCommentScraper
- **主要功能**:
  - 初始化Chrome浏览器
  - 访问抖音视频页面
  - 滚动加载评论
  - 解析评论数据
  - 导出多种格式

#### `quick_start.py`
- **作用**: 交互式启动脚本
- **适合**: 新手用户
- **特点**: 
  - 命令行交互
  - 实时输入参数
  - 简单易用

#### `example.py`
- **作用**: 各种使用场景示例
- **包含**:
  1. 基础爬取
  2. 配置文件使用
  3. 批量处理
  4. 数据分析

#### `config.py`
- **作用**: 集中配置管理
- **可配置项**:
  - 是否无头模式
  - 最大评论数
  - 滚动次数
  - 输出格式选择

### 依赖文件

#### `requirements.txt`
Python依赖包：
- `selenium` - 浏览器自动化框架
- `pandas` - 数据处理和分析
- `openpyxl` - Excel文件读写
- `webdriver-manager` - 自动管理ChromeDriver

#### `install.sh`
自动化安装脚本，包括：
- Python版本检查
- Chrome安装检查
- 依赖包安装
- 虚拟环境创建（可选）

### 文档文件

#### `README.md`
- 项目概述
- 快速开始
- API文档
- 常见问题

#### `使用指南.md`
- 详细的中文使用教程
- 问题排查指南
- 进阶使用技巧

## 🎯 使用流程

### 新手推荐流程

```
1. 安装依赖
   bash install.sh
   或
   pip install -r requirements.txt

2. 运行交互式脚本
   python3 quick_start.py

3. 按提示输入信息
   - 视频链接
   - 评论数量
   - 保存格式
```

### 开发者推荐流程

```
1. 查看示例代码
   cat example.py

2. 修改配置
   vim config.py

3. 编写自定义脚本
   使用 DouyinCommentScraper 类

4. 运行测试
   python3 your_script.py
```

## 📦 输出文件

运行爬虫后会生成：

```
douyin_comments.json    # JSON格式评论数据
douyin_comments.csv     # CSV格式（可用Excel打开）
douyin_comments.xlsx    # Excel格式（如果启用）
page_source.html        # 页面源码（调试用）
```

## 🔧 自定义开发

### 扩展爬虫类

```python
from douyin_comment_scraper import DouyinCommentScraper

class MyCustomScraper(DouyinCommentScraper):
    def custom_method(self):
        # 添加自定义功能
        pass
```

### 修改CSS选择器

如果抖音页面结构变化，修改 `douyin_comment_scraper.py` 中的：

```python
comment_selectors = [
    '[class*="comment-item"]',
    '[class*="CommentItem"]',
    # 添加新的选择器
    '[data-e2e="your-selector"]',
]
```

### 添加新的导出格式

```python
def save_to_mongodb(self):
    # 保存到MongoDB
    pass

def save_to_mysql(self):
    # 保存到MySQL
    pass
```

## 💡 最佳实践

1. **首次使用**: 先用 `quick_start.py` 测试
2. **批量处理**: 使用 `example.py` 的批量示例
3. **自动化**: 修改 `config.py` 后编写脚本
4. **调试**: 使用 `headless=False` 观察过程
5. **生产**: 配置 `headless=True` 后台运行

## 🔄 版本更新

如需更新项目：

```bash
git pull origin main
pip install -r requirements.txt --upgrade
```

## 📞 技术支持

- 查看文档: `README.md`, `使用指南.md`
- 查看示例: `example.py`
- 查看源码: `douyin_comment_scraper.py`
- 提交Issue: GitHub Issues

---

**项目版本**: v1.0.0  
**最后更新**: 2025-12-02
