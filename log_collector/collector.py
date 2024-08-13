import paramiko
import time

class SSHLogCollector:
    def __init__(self, hostname, username, password):
        self.hostname = hostname
        self.username = username
        self.password = password

    def collect_logs(self):
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(self.hostname, username=self.username, password=self.password)

        stdin, stdout, stderr = ssh.exec_command("tail -f /var/log/cisco.log")
        while True:
            line = stdout.readline()
            if line:
                yield line.strip()
            else:
                time.sleep(0.1)

        ssh.close()

# 使用示例
# collector = SSHLogCollector('ubuntu_vm_ip', 'username', 'password')
# for log in collector.collect_logs():
#     print(log)