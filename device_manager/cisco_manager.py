from netmiko import ConnectHandler

def connect_to_device(device_info):
    return ConnectHandler(**device_info)

def send_config(connection, config_commands):
    return connection.send_config_set(config_commands)

def apply_repair(device_info, repair_commands):
    try:
        with connect_to_device(device_info) as connection:
            result = send_config(connection, repair_commands)
            print(f"Repair applied successfully: {result}")
            return True
    except Exception as e:
        print(f"Error applying repair: {str(e)}")
        return False