import json
import asyncio
from copy import deepcopy

import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish
import paho.mqtt.subscribe as subscribe

# config
mqtt_broker_host = '192.168.0.197'
mqtt_broker_port = 1883
device_id = 'led-light-instance-02'

# deep copy the template and fill actual values
# to create request body

DeviceStateTemplate = {
    'state': '{}'
}

TwinUpdateTemplate = {
    'twin': {
        'powerStatus': {
            'actual': {
                'value': '{}',
                'metadata': {
                    'timestamp': 0
                }
            },
            'metadata': {
                'type': 'Updated'
            }
        }
    }
}

device_prefix = '$hw/events/device/'
state_update_suffix = '/state/update'
twin_update_suffix = '/twin/update'
twin_get_suffix = '/twin/get'
twin_result_get_suffix = '/twin/get/result'

twin_result_future = asyncio.Future()
connect_future = asyncio.Future()

# mqtt

def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))
    # client.subscribe("$SYS/#")

    client.subscribe('{}{}{}'.format(device_prefix, device_id, twin_result_get_suffix))
    client.message_callback_add(
        '{}{}{}'.format(device_prefix, device_id, twin_result_get_suffix),
        on_result
    )

    client.subscribe('{}{}{}'.format(device_prefix, device_id, state_update_suffix))
    client.message_callback_add(
        '{}{}{}'.format(device_prefix, device_id, state_update_suffix),
        on_result
    )

    client.subscribe('{}{}{}'.format(device_prefix, device_id, twin_update_suffix))
    client.message_callback_add(
        '{}{}{}'.format(device_prefix, device_id, twin_update_suffix),
        on_result
    )

    client.subscribe('{}{}{}'.format(device_prefix, device_id, twin_get_suffix))
    client.message_callback_add(
        '{}{}{}'.format(device_prefix, device_id, twin_get_suffix),
        on_result
    )

    # connect_future.set_result('connected')

# a default message handler for unmatched message
def on_message(client, userdata, msg):
    print(msg.topic+' '+str(msg.payload))

# result message handler
def on_result(client, userdata, msg):
    print(msg.topic+' '+str(msg.payload)+'\n')

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect(mqtt_broker_host, mqtt_broker_port, 60)
client.loop_start()

# main
async def main():
    global twin_result_future
    
    while True:
        pass

if __name__ == '__main__':
    asyncio.run(main())
