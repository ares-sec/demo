from pymodbus.client import ModbusTcpClient
import time

#client = ModbusTcpClient('10.10.5.242')
client = ModbusTcpClient(host='10.10.101.32', port='502', unit_id=0)

address = 18

client.write_coil(address, 1)
result = client.read_coils(address, 1)
print("%M", address, "=", result.bits[0])
time.sleep(3)


client.close()