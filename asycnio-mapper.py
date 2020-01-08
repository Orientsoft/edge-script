import json
import socket
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
        'power-status': {
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

class AsyncioHelper:
    def __init__(self, loop, client):
        self.loop = loop
        self.client = client
        self.client.on_socket_open = self.on_socket_open
        self.client.on_socket_close = self.on_socket_close
        self.client.on_socket_register_write = self.on_socket_register_write
        self.client.on_socket_unregister_write = self.on_socket_unregister_write

    def on_socket_open(self, client, userdata, sock):
        print("Socket opened")

        def cb():
            print("Socket is readable, calling loop_read")
            client.loop_read()

        self.loop.add_reader(sock, cb)
        self.misc = self.loop.create_task(self.misc_loop())

    def on_socket_close(self, client, userdata, sock):
        print("Socket closed")
        self.loop.remove_reader(sock)
        self.misc.cancel()

    def on_socket_register_write(self, client, userdata, sock):
        print("Watching socket for writability.")

        def cb():
            print("Socket is writable, calling loop_write")
            client.loop_write()

        self.loop.add_writer(sock, cb)

    def on_socket_unregister_write(self, client, userdata, sock):
        print("Stop watching socket for writability.")
        self.loop.remove_writer(sock)

    async def misc_loop(self):
        print("misc_loop started")
        while self.client.loop_misc() == mqtt.MQTT_ERR_SUCCESS:
            try:
                await asyncio.sleep(1)
            except asyncio.CancelledError:
                break
        print("misc_loop finished")

class AsyncMqttExample:
    def __init__(self, loop):
        self.loop = loop

    def on_connect(self, client, userdata, flags, rc):
        twin_result_get_topic = '{}{}{}'.format(device_prefix, device_id, twin_result_get_suffix)
        print("Subscribing topic: {}".format(twin_result_get_topic))

        client.subscribe(twin_result_get_topic)
        client.message_callback_add(
            twin_result_get_topic,
            self.on_result
        )

    def on_result(self, client, userdata, msg):
        if not self.got_message:
            print("Got unexpected message: {}".format(msg.decode()))
        else:
            self.got_message.set_result(msg.payload)

    def on_disconnect(self, client, userdata, rc):
        self.disconnected.set_result(rc)

    def update_device_state(self, state):
        device_state = deepcopy(DeviceStateTemplate)
        device_state['state'] = device_state['state'].format(state)

        msg_info = self.client.publish(
            '{}{}{}'.format(device_prefix, device_id, state_update_suffix),
            payload=json.dumps(device_state)
        )

    async def sync_twin(self):
        twin_update_body = deepcopy(TwinUpdateTemplate)
        twin_update_body['twin']['power-status']['actual']['value'] = 'unknown'
        twin_update_body['twin']['power-status']['metadata']['type'] = 'Updated'

        self.got_message = self.loop.create_future()

        msg_info = self.client.publish(
            '{}{}{}'.format(device_prefix, device_id, twin_get_suffix),
            payload=json.dumps(twin_update_body)
        )

        twin_result = json.loads(await self.got_message)

        print(twin_result)

        expected = twin_result['twin']['power-status']['expected']

        if expected is not None:
            twin_update_body = deepcopy(TwinUpdateTemplate)
            twin_update_body['twin']['power-status']['actual']['value'] = expected['value']
            twin_update_body['twin']['power-status']['metadata']['type'] = 'Updated'

            msg_info = self.client.publish(
                '{}{}{}'.format(device_prefix, device_id, twin_update_suffix),
                payload=json.dumps(twin_update_body)
            )

        self.got_message = None

    async def main(self):
        self.disconnected = self.loop.create_future()
        self.got_message = None

        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_result
        self.client.on_disconnect = self.on_disconnect

        aioh = AsyncioHelper(self.loop, self.client)

        self.client.connect(mqtt_broker_host, mqtt_broker_port, 60)
        self.client.socket().setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 2048)

        self.update_device_state('online')

        await asyncio.sleep(5)

        while True:
            await self.sync_twin()
            await asyncio.sleep(1)

        self.client.disconnect()
        print("Disconnected: {}".format(await self.disconnected))

print("Starting")
loop = asyncio.get_event_loop()
loop.run_until_complete(AsyncMqttExample(loop).main())
loop.close()
print("Finished")
