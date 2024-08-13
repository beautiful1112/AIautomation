import re
import json
from datetime import datetime
def parse_log(log_line):
    pattern = r'<(\d+)>(\w+\s+\d+\s+\d+:\d+:\d+)\s+(\S+)\s+(%\S+):\s+(.+)'
    match = re.match(pattern, log_line)
    if match:
        priority, timestamp, hostname, facility, message = match.groups()
        return {
            'priority': priority,
            'timestamp': timestamp,
            'hostname': hostname,
            'facility': facility,
            'message': message
        }
    return None

def process_log(log_data):
    parsed_log = parse_log(log_data)
    if parsed_log:
        # 添加时间戳
        parsed_log['processed_time'] = datetime.now().isoformat()

        # 初步分类日志类型
        parsed_log['log_type'] = classify_log(parsed_log['message'])

        # 提取关键信息
        parsed_log['key_info'] = extract_key_info(parsed_log['message'])

        # 格式化日志消息，使其更易读
        parsed_log['formatted_message'] = format_message(parsed_log['message'])

        # 添加严重性级别
        parsed_log['severity'] = get_severity(parsed_log['priority'])

        # 将整个日志转换为 JSON 字符串，方便发送给 AI
        return json.dumps(parsed_log)
    return None

def classify_log(message):
    if "interface" in message.lower():
        return "INTERFACE"
    elif "configuration" in message.lower():
        return "CONFIGURATION"
    elif "security" in message.lower():
        return "SECURITY"
    elif "error" in message.lower():
        return "ERROR"
    else:
        return "OTHER"

def extract_key_info(message):
    # 这里可以使用正则表达式提取关键信息
    # 这只是一个简单的示例，您可能需要根据实际日志格式调整
    import re
    interface_match = re.search(r'interface (\S+)', message, re.IGNORECASE)
    if interface_match:
        return f"Interface: {interface_match.group(1)}"
    return "No key info extracted"

def format_message(message):
    # 简单的格式化，您可以根据需要进行更复杂的格式化
    return message.strip().capitalize()

def get_severity(priority):
    # 根据 syslog priority 确定严重性级别
    priority = int(priority)
    if priority <= 3:
        return "CRITICAL"
    elif priority <= 5:
        return "WARNING"
    else:
        return "INFO"