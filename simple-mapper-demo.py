import json
import yaml
import asyncio
from copy import deepcopy

import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish
import paho.mqtt.subscribe as subscribe

# consts
config_path = 'simple-mapper-demo.yaml'

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

    # connect_future.set_result('connected')

# a default message handler for unmatched message
def on_message(client, userdata, msg):
    print(msg.topic+' '+str(msg.payload))

# result message handler
def on_result(client, userdata, msg):
    print(msg.payload)

    global twin_result_future
    twin_result_future.set_result(json.loads(msg.payload))

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect(mqtt_broker_host, mqtt_broker_port, 60)
client.loop_start()

# work flow

def update_device_state(state):
    print('update_device_state()')

    device_state = deepcopy(DeviceStateTemplate)
    device_state['state'] = device_state['state'].format(state)

    msg_info = client.publish(
        '{}{}{}'.format(device_prefix, device_id, state_update_suffix),
        payload=json.dumps(device_state)
    )

    msg_info.wait_for_publish()

async def sync_twin():
    print('sync_twin()')

    global twin_result_future
    twin_result_future = asyncio.Future()

    twin_update_body = deepcopy(TwinUpdateTemplate)
    twin_update_body['twin']['powerStatus']['actual']['value'] = 'unknown'
    twin_update_body['twin']['powerStatus']['metadata']['type'] = 'Updated'

    msg_info = client.publish(
        '{}{}{}'.format(device_prefix, device_id, twin_get_suffix),
        payload=json.dumps(twin_update_body)
    )
    msg_info.wait_for_publish()

    print('sent')

    # twin_result = await twin_result_future
    twin_result = await twin_result_future

    print(twin_result)

    expected = twin_result['twin']['powerStatus']['expected']
    # actual = twin_result['twin']['powerStatus']['actual']

    if expected is not None:
        twin_update_body = deepcopy(TwinUpdateTemplate)

        # TODO : do actual work

        twin_update_body['twin']['powerStatus']['actual']['value'] = expected['value']
        twin_update_body['twin']['powerStatus']['metadata']['type'] = 'Updated'

        msg_info = client.publish(
            '{}{}{}'.format(device_prefix, device_id, twin_update_suffix),
            payload=json.dumps(twin_update_body)
        )
        msg_info.wait_for_publish()

# main
async def main():
    # connected = await connect_future

    update_device_state('online')

    while True:
        await sync_twin()
        await asyncio.sleep(1)

if __name__ == '__main__':
    asyncio.run(main())
