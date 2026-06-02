# JMeter 报告生成器

将 JMeter 的 `.jtl` 文件转换为精美的 **Prometheus/Grafana 风格** HTML 性能报告。

## 目录结构

```
report/
├── input/              # 放入你的 JTL 文件到这里
│   └── test.jtl
├── output/             # 生成的 HTML 报告输出目录
│   ├── test_report.html
│   └── index.html      # 报告索引页面
├── 生成报告.bat         # 一键生成报告 (Windows)
└── ... (其他脚本文件)
```

## 一键生成报告

### Windows 用户

双击运行 **`生成报告.bat`**

或命令行运行:
```cmd
python batch_generator.py
```

### 使用步骤

1. 将你的 `.jtl` 文件放入 `input` 目录
2. 运行 `生成报告.bat`
3. 打开 `output/index.html` 查看所有报告

## 功能特点

- **自动扫描**: 自动发现 input 目录下所有 .jtl 文件
- **批量生成**: 一次运行生成所有报告
- **索引页面**: 自动生成报告列表索引
- **Grafana 风格**: 深色主题，专业美观
- **交互图表**: 支持缩放、平移、悬停提示
- **自动降采样**: 大数据量自动聚合，保证流畅

## 报告内容

1. **核心指标卡片** - 总请求数、持续时间、平均 RT、吞吐量、错误率、P95
2. **响应时间分布** - MIN/P50/P90/P95/P99/MAX 可视化
3. **4 个交互图表**:
   - 响应时间趋势 (支持缩放/平移)
   - 吞吐量 (req/s)
   - 错误率趋势
   - 各接口响应时间对比
4. **按接口统计表** - 每个请求的详细数据
5. **错误信息 Top 50** - 如果有错误

## 依赖

无需安装任何依赖，仅使用 Python 标准库！

```bash
pip install nothing
```

## 单文件模式

如果只需要为单个 JTL 文件生成报告:

```bash
python report_generator.py input/test.jtl -o output/custom_report.html
```

## JTL 文件格式

支持:
- CSV 格式 (推荐，JMeter 默认)
- XML 格式

工具会自动检测文件格式。

## 示例 JMeter 配置

在 JMeter 中生成 JTL 文件时推荐配置:

```properties
jmeter.save.saveservice.timestamp_format=milliseconds
jmeter.save.saveservice.response_time=true
jmeter.save.saveservice.success=true
jmeter.save.saveservice.label=true
jmeter.save.saveservice.thread_name=true
```
