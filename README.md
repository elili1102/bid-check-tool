# 标书技术评分检查工具

自动解析评分标准与应答文件，智能检查标书质量并生成可视化报告。

## 安装依赖

```bash
pip install python-docx openpyxl
```

Python 3.10+ 推荐。无需额外安装 Flask 或其他 Web 框架（Web 界面基于内置 `http.server`）。

## 使用方式

### 命令行模式

```bash
# 基本用法：只传应答文件
python bid_check.py --response response.docx

# 传评分标准 + 应答文件
python bid_check.py --criteria scoring.xlsx --response response.docx

# 传评分标准 + 应答文件 + 技术文件
python bid_check.py -c scoring.xlsx -r response.docx -t tech.docx

# 指定输出路径
python bid_check.py --response response.docx --output ./my_report.html

# 只输出 JSON（不生成 HTML）
python bid_check.py --response response.docx --format json

# 同时输出 HTML 和 JSON
python bid_check.py --response response.docx --format both

# 显示详细检查过程
python bid_check.py --response response.docx --verbose

# 禁用彩色输出
python bid_check.py --response response.docx --no-color
```

### Web 界面模式

```bash
python bid_check.py --web
python bid_check.py --web --port 8080
```

启动后在浏览器访问 `http://localhost:5000`，通过页面上传文件并完成检查。

### Python API 调用

```python
from parsers import parse_docx, parse_xlsx
from analyzer import analyze_bid
from report_generator import generate_html_report

# 解析文件
response_data = parse_docx('response.docx')
criteria_data = parse_xlsx('scoring.xlsx')    # 可选
technical_data = parse_docx('tech.docx')      # 可选

# 分析
result = analyze_bid(criteria_data, response_data, technical_data)

# 生成 HTML 报告
html = generate_html_report(result)

# 获取摘要信息
summary = result['summary']
score = result['score_estimate']
critical_issues = result['critical_issues']
warnings = result['warnings']
```

## 检查维度

| 维度 | 说明 |
|------|------|
| 结构完整性 | 检查标书是否包含必要的章节（封面、目录、技术方案、商务报价等） |
| 内容质量 | 分析各评分要素的应答深度与完整性，评估得分区间 |
| 格式规范 | 检查页眉页脚、字体字号、页码、目录等格式要求 |
| 低级错误 | 发现错别字、数据矛盾、时间逻辑错误、金额不一致等致命问题 |
| 交叉一致性 | 比对技术文件与商务文件之间的数据一致性（人员、业绩、金额等） |
| 评分分析 | 逐项对照评分标准，给出每项的满足度评估与得分预估 |

## 输出格式

### HTML 报告
- 默认输出至 `output/report_<timestamp>.html`
- 包含评分总览、逐项分析、硬伤问题、扣分风险、改进建议
- 可直接在浏览器打开查看

### JSON 结果
- 使用 `--format json` 或 `--format both` 输出
- 包含完整的结构化分析数据，便于程序化处理
- 字段说明：
  - `summary`：汇总统计
  - `score_estimate`：得分预估（min/max/details）
  - `critical_issues`：硬伤问题列表
  - `warnings`：扣分风险列表
  - `suggestions`：改进建议列表
  - `criteria_analysis`：各评分要素详细分析
  - `completeness_check`：章节完整性检查结果
  - `cross_checks`：交叉一致性检查结果

## 注意事项

1. **文件编码**：工具支持 `.docx`（Word 2007+）和 `.xlsx`（Excel 2007+）格式，不支持旧版 `.doc` / `.xls`
2. **评分标准格式**：xlsx 文件应包含"评审要素"、"评分标准"、"分值"等表头列，工具会自动识别
3. **大文件处理**：超大标书（数百页）可能耗时较长，建议使用 `--verbose` 查看进度
4. **结果参考性**：工具基于文本解析和规则匹配，最终评分以评标委员会人工评审为准
5. **中文支持**：终端输出默认使用彩色显示，Windows 10+ 原生支持 ANSI 颜色，旧版本可加 `--no-color` 禁用
6. **模块独立**：`bid_check.py` 为命令行入口，可独立运行；Web 模式需依赖 `app.py`
