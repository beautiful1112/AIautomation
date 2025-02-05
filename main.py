import asyncio
import yaml
from log_collector.collector import SSHLogCollector
from log_processor.processor import process_log
from ai_analyzer.poe_client import POEClient
from device_manager.cisco_manager import apply_repair

async def handle_log(log_line, processor, poe_client, cisco_manager):
    # 处理日志
    processed_log = processor.process_log(log_line)
    if not processed_log:
        return

    # AI 分析
    analysis = await poe_client.analyze_log(processed_log)
    print(f"AI Analysis: {analysis}")

    # 获取修复建议
    repair_suggestion = await poe_client.get_repair_suggestion(analysis)
    if repair_suggestion:
        print(f"\nRepair Suggestion: {repair_suggestion}")
        user_input = input("\nApply these changes? (yes/no): ")
        
        if user_input.lower() == 'yes':
            # 将建议转换为命令列表
            commands = repair_suggestion.strip().split('\n')
            success, output = await cisco_manager.apply_configuration(commands)
            if success:
                print("Changes applied successfully")
            else:
                print(f"Failed to apply changes: {output}")

async def main():
    # 加载配置
    with open('config/config.yml', 'r') as f:
        config = yaml.safe_load(f)

    # 初始化组件
    processor = LogProcessor()
    poe_client = POEClient(config['poe']['api_key'], config['poe']['bot_name'])
    cisco_manager = CiscoManager(config['cisco_device'])

    # 创建日志处理回调
    callback = lambda log: handle_log(log, processor, poe_client, cisco_manager)

    # 启动日志读取器
    reader = SyslogReader(config['rsyslog']['log_file'], callback)
    reader.start()

    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        reader.stop()

if __name__ == "__main__":
    asyncio.run(main())