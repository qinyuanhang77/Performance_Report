import os

content = r'''"""
JTL 文件解析器 - 自动检测 CSV/XML 格式
"""
import csv
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional


@dataclass
class Sample:
    """单个请求样本"""
    timestamp: int  # 毫秒时间戳
    elapsed: int    # 响应时间 (ms)
    label: str      # 请求名称
    response_code: str
    response_message: str  # HTTP 状态消息
    success: bool
    failure_message: str = ""
    thread_name: str = ""
    data_type: str = ""  # 数据类型
    bytes: int = 0
    sent_bytes: int = 0
    latency: int = 0  # 首次响应时间 (ms)
    connect_time: int = 0  # 连接时间 (ms)
    idle_time: int = 0  # 空闲时间 (ms)
    url: str = ""  # 请求 URL
    query_string: str = ""  # 请求参数
    response_data: str = ""  # 响应体内容
    sample_count: int = 0  # 样本数
    error_count: int = 0  # 错误数
    all_threads: int = 0  # 总线程数/并发用户数
    grp_threads: int = 0  # 线程组中的线程数


@dataclass
class JTLData:
    """解析后的 JTL 数据"""
    samples: List[Sample] = field(default_factory=list)
    format: str = ""  # "CSV" or "XML"
    start_time: int = 0
    end_time: int = 0


def detect_format(file_path: Path) -> str:
    """自动检测 JTL 文件格式"""
    with open(file_path, 'rb') as f:
        header = f.read(500)
        text = header.decode('utf-8', errors='ignore').strip()

        if text.startswith('<?xml') or text.startswith('<testResults'):
            return "XML"

        if 'timeStamp' in text or 'timestamp' in text:
            return "CSV"
        if ',' in text.split('\n')[0]:
            return "CSV"

    raise ValueError(f"无法识别的文件格式：{file_path}")


def parse_csv(file_path: Path) -> JTLData:
    """解析 CSV 格式 JTL 文件"""
    data = JTLData(format="CSV")

    with open(file_path, 'r', encoding='utf-8-sig', errors='ignore') as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []

        col_map = {}
        for h in headers:
            hl = h.lower().strip()
            if hl in ['timestamp', 'timestam', 'time']:
                col_map['timestamp'] = h
            elif hl in ['elapsed', 'elapsedtime', 'elapsed_ms', 'responsetime', 'rt']:
                col_map['elapsed'] = h
            elif hl in ['label', 'name', 'request', 'samplername']:
                col_map['label'] = h
            elif hl in ['responsecode', 'code', 'status', 'rc']:
                col_map['response_code'] = h
            elif hl in ['responsemessage', 'message', 'rm']:
                col_map['response_message'] = h
            elif hl in ['success', 'issuccess', 's']:
                col_map['success'] = h
            elif hl in ['failuremessage', 'assertionresults']:
                col_map['failure_message'] = h
            elif hl in ['threadname', 'thread', 'tn']:
                col_map['thread_name'] = h
            elif hl in ['datatype', 'type', 'dt']:
                col_map['data_type'] = h
            elif hl in ['bytes', 'bodybytes', 'bytessent', 'b']:
                col_map['bytes'] = h
            elif hl in ['sentbytes', 'sent', 'sby']:
                col_map['sent_bytes'] = h
            elif hl in ['latency', 'latencytime', 'lt']:
                col_map['latency'] = h
            elif hl in ['connect', 'connecttime', 'ct']:
                col_map['connect_time'] = h
            elif hl in ['idletime', 'idle', 'it']:
                col_map['idle_time'] = h
            elif hl in ['url', 'requesturl']:
                col_map['url'] = h
            elif hl in ['querystring', 'query']:
                col_map['query_string'] = h
            elif hl in ['responsedata', 'response', 'body']:
                col_map['response_data'] = h
            elif hl in ['samplecount', 'sample', 'sc']:
                col_map['sample_count'] = h
            elif hl in ['errorcount', 'errors', 'ec']:
                col_map['error_count'] = h
            elif hl in ['allthreads', 'threads', 'na']:
                col_map['all_threads'] = h
            elif hl in ['grpthreads', 'ng']:
                col_map['grp_threads'] = h

        for row in reader:
            try:
                ts_str = row.get(col_map.get('timestamp', 'timeStamp'), '0')
                ts = int(ts_str) if ts_str else 0
                elapsed_str = row.get(col_map.get('elapsed', 'elapsed'), '0')
                elapsed = int(elapsed_str) if elapsed_str else 0

                success_val = row.get(col_map.get('success', 'success'), 'true').strip()
                success = success_val.lower() in ('true', '1', 'yes')

                sample = Sample(
                    timestamp=ts,
                    elapsed=elapsed,
                    label=row.get(col_map.get('label', 'label'), 'unknown'),
                    response_code=row.get(col_map.get('response_code', 'responseCode'), ''),
                    response_message=row.get(col_map.get('response_message', 'responseMessage'), ''),
                    success=success,
                    failure_message=row.get(col_map.get('failure_message', 'failureMessage'), ''),
                    thread_name=row.get(col_map.get('thread_name', 'threadName'), ''),
                    data_type=row.get(col_map.get('data_type', 'dataType'), ''),
                    bytes=int(row.get(col_map.get('bytes', 'bytes'), 0) or 0),
                    sent_bytes=int(row.get(col_map.get('sent_bytes', 'sentBytes'), 0) or 0),
                    latency=int(row.get(col_map.get('latency', 'Latency'), 0) or 0),
                    connect_time=int(row.get(col_map.get('connect_time', 'Connect'), 0) or 0),
                    idle_time=int(row.get(col_map.get('idle_time', 'IdleTime'), 0) or 0),
                    url=row.get(col_map.get('url', 'URL'), ''),
                    query_string=row.get(col_map.get('query_string', 'queryString'), ''),
                    response_data=row.get(col_map.get('response_data', 'responseData'), ''),
                    sample_count=int(row.get(col_map.get('sample_count', 'sampleCount'), 0) or 0),
                    error_count=int(row.get(col_map.get('error_count', 'errorCount'), 0) or 0),
                    all_threads=int(row.get(col_map.get('all_threads', 'allThreads'), 0) or 0),
                    grp_threads=int(row.get(col_map.get('grp_threads', 'grpThreads'), 0) or 0),
                )
                if not sample.query_string and '?' in sample.url:
                    sample.query_string = sample.url.split('?', 1)[1]
                data.samples.append(sample)

                if data.start_time == 0 or ts < data.start_time:
                    data.start_time = ts
                if ts > data.end_time:
                    data.end_time = ts

            except (ValueError, KeyError):
                continue
    return data


def parse_xml(file_path: Path) -> JTLData:
    """解析 XML 格式 JTL 文件"""
    data = JTLData(format="XML")

    tree = ET.parse(file_path)
    root = tree.getroot()

    for elem in root.iter():
        if elem.tag == 'httpSample' or elem.tag == 'sample':
            try:
                ts = int(elem.get('ts', elem.get('timestamp', '0')) or '0')
                elapsed = int(elem.get('t', elem.get('elapsed', '0')) or '0')

                response_data_elem = elem.find('responseData')
                response_data = response_data_elem.text if response_data_elem is not None and response_data_elem.text else ''

                url = elem.get('u', elem.get('url', ''))
                if not url:
                    url_elem = elem.find('java.net.URL')
                    if url_elem is not None and url_elem.text:
                        url = url_elem.text

                query_string = ''
                query_string_elem = elem.find('queryString')
                if query_string_elem is not None:
                    if query_string_elem.text:
                        query_string = query_string_elem.text
                    elif query_string_elem.get('value'):
                        query_string = query_string_elem.get('value')

                if not query_string and '?' in url:
                    query_string = url.split('?', 1)[1]

                sample = Sample(
                    timestamp=ts,
                    elapsed=elapsed,
                    label=elem.get('lb', elem.get('label', 'unknown')),
                    response_code=elem.get('rc', elem.get('responseCode', '')),
                    response_message=elem.get('rm', elem.get('responseMessage', '')),
                    success=elem.get('s', 'true').lower() == 'true',
                    failure_message=elem.findtext('failureMessage', '') or '',
                    thread_name=elem.get('tn', elem.get('threadName', '')),
                    data_type=elem.get('dt', elem.get('dataType', '')),
                    bytes=int(elem.get('b', '0') or '0'),
                    sent_bytes=int(elem.get('sb', '0') or '0'),
                    latency=int(elem.get('lt', '0') or '0'),
                    connect_time=int(elem.get('ct', '0') or '0'),
                    idle_time=int(elem.get('it', '0') or '0'),
                    url=url,
                    query_string=query_string,
                    response_data=response_data[:50000] if response_data else '',
                    sample_count=int(elem.get('sc', '0') or '0'),
                    error_count=int(elem.get('ec', '0') or '0'),
                    all_threads=int(elem.get('na', '0') or '0'),
                    grp_threads=int(elem.get('ng', '0') or '0'),
                )
                data.samples.append(sample)

                if data.start_time == 0 or ts < data.start_time:
                    data.start_time = ts
                if ts > data.end_time:
                    data.end_time = ts

            except (ValueError, AttributeError):
                continue

    return data


def parse_jtl(file_path: str) -> JTLData:
    """解析 JTL 文件，自动检测格式"""
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"文件不存在：{file_path}")

    fmt = detect_format(path)

    if fmt == "CSV":
        return parse_csv(path)
    else:
        return parse_xml(path)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        data = parse_jtl(sys.argv[1])
        print(f"格式：{data.format}")
        print(f"样本数：{len(data.samples)}")
        print(f"时间范围：{data.start_time} - {data.end_time}")
    else:
        print("用法：python jtl_parser.py <jtl 文件>")
'''

with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'jtl_parser.py'), 'w', encoding='utf-8') as f:
    f.write(content)

print(f'Written {len(content)} bytes')
