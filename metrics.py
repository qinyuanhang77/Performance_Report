"""
性能指标计算模块
"""
import math
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from jtl_parser import JTLData, Sample


@dataclass
class LabelStats:
    """单个请求标签的统计信息"""
    label: str
    count: int = 0
    success_count: int = 0
    error_count: int = 0
    min_rt: int = 0
    max_rt: int = 0
    sum_rt: int = 0
    rt_values: List[int] = field(default_factory=list)  # 用于计算百分位数
    bytes_total: int = 0
    sent_bytes_total: int = 0
    error_messages: List[str] = field(default_factory=list)
    # 新增指标
    latency_values: List[int] = field(default_factory=list)  # 首次响应时间
    connect_time_values: List[int] = field(default_factory=list)  # 连接时间
    idle_time_values: List[int] = field(default_factory=list)  # 空闲时间
    url_set: set = field(default_factory=set)  # URL 集合
    sample_data: List[dict] = field(default_factory=list)  # 样本详情（用于展示）
    response_messages: dict = field(default_factory=dict)  # HTTP 状态消息计数
    avg_concurrent_threads: float = 0  # 平均并发线程数


@dataclass
class TimeSeriesPoint:
    """时间点上的指标"""
    timestamp: int
    count: int = 0
    avg_rt: float = 0
    error_count: int = 0
    throughput: float = 0  # requests per second


@dataclass
class Metrics:
    """整体性能指标"""
    # 基本信息
    start_time: int = 0
    end_time: int = 0
    duration_seconds: float = 0
    total_samples: int = 0

    # 整体统计
    total_success: int = 0
    total_errors: int = 0
    error_rate: float = 0.0

    # 响应时间统计 (ms)
    avg_rt: float = 0.0
    min_rt: int = 0
    max_rt: int = 0
    median_rt: float = 0.0
    p90_rt: float = 0.0
    p95_rt: float = 0.0
    p99_rt: float = 0.0

    # 吞吐量
    throughput: float = 0.0  # req/s
    bytes_per_second: float = 0.0
    sent_bytes_per_second: float = 0.0

    # 按标签分组统计
    label_stats: Dict[str, LabelStats] = field(default_factory=dict)

    # 时间序列数据 (用于图表)
    time_series: List[TimeSeriesPoint] = field(default_factory=list)

    # 错误统计
    error_summary: Dict[str, int] = field(default_factory=dict)

    # 新增整体统计
    avg_latency: float = 0.0
    avg_connect_time: float = 0.0
    avg_idle_time: float = 0.0
    unique_urls: int = 0
    avg_concurrent_threads: float = 0.0
    response_code_summary: Dict[str, int] = field(default_factory=dict)


def percentile(sorted_values: List[int], p: float) -> float:
    """计算百分位数"""
    if not sorted_values:
        return 0.0
    n = len(sorted_values)
    k = (n - 1) * p / 100
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return sorted_values[int(k)]
    return sorted_values[int(f)] * (c - k) + sorted_values[int(c)] * (k - f)


def calculate_metrics(data: JTLData) -> Metrics:
    """计算所有性能指标"""
    metrics = Metrics()

    if not data.samples:
        return metrics

    metrics.start_time = data.start_time
    metrics.end_time = data.end_time
    metrics.duration_seconds = max((data.end_time - data.start_time) / 1000.0, 1)

    all_rts = []
    label_groups: Dict[str, List[Sample]] = defaultdict(list)

    for sample in data.samples:
        all_rts.append(sample.elapsed)
        label_groups[sample.label].append(sample)

        if sample.success:
            metrics.total_success += 1
        else:
            metrics.total_errors += 1
            if sample.failure_message:
                metrics.error_summary[sample.failure_message] = metrics.error_summary.get(sample.failure_message, 0) + 1

    metrics.total_samples = len(data.samples)
    metrics.error_rate = (metrics.total_errors / metrics.total_samples) * 100 if metrics.total_samples > 0 else 0

    # 响应时间统计
    all_rts_sorted = sorted(all_rts)
    metrics.min_rt = min(all_rts)
    metrics.max_rt = max(all_rts)
    metrics.avg_rt = sum(all_rts) / len(all_rts)
    metrics.median_rt = percentile(all_rts_sorted, 50)
    metrics.p90_rt = percentile(all_rts_sorted, 90)
    metrics.p95_rt = percentile(all_rts_sorted, 95)
    metrics.p99_rt = percentile(all_rts_sorted, 99)

    # 吞吐量
    metrics.throughput = metrics.total_samples / metrics.duration_seconds

    # 按标签分组统计
    for label, samples in label_groups.items():
        stats = LabelStats(label=label)
        rts = []
        latencies = []
        connect_times = []
        idle_times = []
        urls = set()
        thread_counts = []
        response_msgs = {}
        sample_counts = []
        error_counts = []

        for s in samples:
            stats.count += 1
            rts.append(s.elapsed)
            stats.bytes_total += s.bytes
            stats.sent_bytes_total += s.sent_bytes

            if s.success:
                stats.success_count += 1
            else:
                stats.error_count += 1
                if s.failure_message:
                    stats.error_messages.append(s.failure_message)

            # 新增指标
            if s.latency > 0:
                latencies.append(s.latency)
            if s.connect_time > 0:
                connect_times.append(s.connect_time)
            if s.idle_time > 0:
                idle_times.append(s.idle_time)
            if s.url:
                urls.add(s.url)
            if s.all_threads > 0:
                thread_counts.append(s.all_threads)
            if s.response_message:
                response_msgs[s.response_message] = response_msgs.get(s.response_message, 0) + 1
            if s.sample_count > 0:
                sample_counts.append(s.sample_count)
            if s.error_count > 0:
                error_counts.append(s.error_count)

            # 存储样本详情（限制数量）
            if len(stats.sample_data) < 100:
                stats.sample_data.append({
                    'url': s.url,
                    'query_string': s.query_string,
                    'response_data': s.response_data[:10000] if s.response_data else '',  # 保留最多 10KB 用于展示
                    'latency': s.latency,
                    'connect_time': s.connect_time,
                    'idle_time': s.idle_time,
                    'response_message': s.response_message,
                })

        stats.rt_values = sorted(rts)
        stats.sum_rt = sum(rts)
        stats.min_rt = min(rts)
        stats.max_rt = max(rts)
        stats.latency_values = sorted(latencies) if latencies else [0]
        stats.connect_time_values = sorted(connect_times) if connect_times else [0]
        stats.idle_time_values = sorted(idle_times) if idle_times else [0]
        stats.url_set = urls
        stats.response_messages = response_msgs
        stats.avg_concurrent_threads = sum(thread_counts) / len(thread_counts) if thread_counts else 0
        stats.total_sample_count = sum(sample_counts) if sample_counts else stats.count
        stats.total_error_count = sum(error_counts) if error_counts else stats.error_count

        metrics.label_stats[label] = stats

    # 计算整体 latency、connect_time、idle_time 平均值和并发线程数
    all_latency = [s.latency for s in data.samples if s.latency > 0]
    all_connect = [s.connect_time for s in data.samples if s.connect_time > 0]
    all_idle = [s.idle_time for s in data.samples if s.idle_time > 0]
    all_urls = set(s.url for s in data.samples if s.url)
    all_threads = [s.all_threads for s in data.samples if s.all_threads > 0]
    all_response_codes = {}
    for s in data.samples:
        if s.response_code:
            all_response_codes[s.response_code] = all_response_codes.get(s.response_code, 0) + 1

    metrics.avg_latency = sum(all_latency) / len(all_latency) if all_latency else 0
    metrics.avg_connect_time = sum(all_connect) / len(all_connect) if all_connect else 0
    metrics.avg_idle_time = sum(all_idle) / len(all_idle) if all_idle else 0
    metrics.avg_concurrent_threads = sum(all_threads) / len(all_threads) if all_threads else 0
    metrics.unique_urls = len(all_urls)
    metrics.response_code_summary = all_response_codes

    # 生成时间序列数据 (按秒聚合)
    time_buckets: Dict[int, List[Sample]] = defaultdict(list)
    for sample in data.samples:
        bucket = sample.timestamp // 1000  # 按秒聚合
        time_buckets[bucket].append(sample)

    for ts in sorted(time_buckets.keys()):
        samples_in_bucket = time_buckets[ts]
        rts = [s.elapsed for s in samples_in_bucket]
        errors = sum(1 for s in samples_in_bucket if not s.success)

        point = TimeSeriesPoint(
            timestamp=ts * 1000,
            count=len(samples_in_bucket),
            avg_rt=sum(rts) / len(rts) if rts else 0,
            error_count=errors,
            throughput=len(samples_in_bucket)  # 每秒请求数
        )
        metrics.time_series.append(point)

    return metrics


def generate_summary_text(metrics: Metrics) -> str:
    """生成文本摘要"""
    lines = [
        "=" * 60,
        "性能测试报告摘要",
        "=" * 60,
        f"测试持续时间：{metrics.duration_seconds:.2f} 秒",
        f"总样本数：{metrics.total_samples}",
        f"成功：{metrics.total_success} | 失败：{metrics.total_errors} | 错误率：{metrics.error_rate:.2f}%",
        "",
        "响应时间 (ms):",
        f"  平均值：{metrics.avg_rt:.2f}",
        f"  最小值：{metrics.min_rt}",
        f"  最大值：{metrics.max_rt}",
        f"  中位数：{metrics.median_rt:.2f}",
        f"  P90: {metrics.p90_rt:.2f}",
        f"  P95: {metrics.p95_rt:.2f}",
        f"  P99: {metrics.p99_rt:.2f}",
        "",
        f"吞吐量：{metrics.throughput:.2f} req/s",
        "=" * 60,
    ]

    if metrics.label_stats:
        lines.append("\n按接口统计:")
        lines.append("-" * 60)
        for label, stats in metrics.label_stats.items():
            error_rate = (stats.error_count / stats.count * 100) if stats.count > 0 else 0
            lines.append(f"\n{label}")
            lines.append(f"  请求数：{stats.count} | 错误率：{error_rate:.2f}%")
            if stats.rt_values:
                avg = sum(stats.rt_values) / len(stats.rt_values)
                p95 = percentile(stats.rt_values, 95)
                lines.append(f"  平均 RT: {avg:.2f}ms | P95: {p95:.2f}ms")

    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    from jtl_parser import parse_jtl

    if len(sys.argv) > 1:
        data = parse_jtl(sys.argv[1])
        metrics = calculate_metrics(data)
        print(generate_summary_text(metrics))
    else:
        print("用法：python metrics.py <jtl 文件>")
