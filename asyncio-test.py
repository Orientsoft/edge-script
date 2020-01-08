#!/usr/bin/env python3

import json
from copy import deepcopy

import socket
import uuid
import paho.mqtt.client as mqtt
import asyncio

# config
mqtt_broker_host = '192.168.0.197'
mqtt_broker_port = 1883
device_id = 'led-light-instance-02'

client_id = 'paho-mqtt-python/issue72/' + str(uuid.uuid4())
topic = '$hw/events/device/led-light-instance-02/twin/get/result'
pub_topic = '$hw/events/device/led-light-instance-02/twin/get'
print("Using client_id / topic: " + client_id)

device_prefix = '$hw/events/device/'
state_update_suffix = '/state/update'
twin_update_suffix = '/twin/update'
twin_get_suffix = '/twin/get'
twin_result_get_suffix = '/twin/get/result'

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

    def on_message(self, client, userdata, msg):
        if not self.got_message:
            print("Got unexpected message: {}".format(msg.decode()))
        else:
            print(msg.payload)
            self.got_message.set_result(msg.payload)

    def on_disconnect(self, client, userdata, rc):
        self.disconnected.set_result(rc)

    def update_device_state(self, state):
        print('update_device_state()')

        device_state = deepcopy(DeviceStateTemplate)
        device_state['state'] = device_state['state'].format(state)

        msg_info = self.client.publish(
            '{}{}{}'.format(device_prefix, device_id, state_update_suffix),
            payload=json.dumps(device_state)
        )

    async def main(self):
        self.disconnected = self.loop.create_future()
        self.got_message = None

        self.client = mqtt.Client(client_id=client_id)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect

        aioh = AsyncioHelper(self.loop, self.client)

        self.client.connect('192.168.0.197', 1883, 60)
        self.client.socket().setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 2048)

        self.update_device_state('online')

        while True:
            await asyncio.sleep(5)

            print("Publishing {}".format(pub_topic))
            self.got_message = self.loop.create_future()

            twin_update_body = deepcopy(TwinUpdateTemplate)
            twin_update_body['twin']['powerStatus']['actual']['value'] = 'unknown'
            twin_update_body['twin']['powerStatus']['metadata']['type'] = 'Updated'

            self.client.publish(pub_topic, json.dumps(twin_update_body), qos=1)

            msg = await self.got_message
            print("Got response with {} bytes".format(len(msg)))

            self.got_message = None

        self.client.disconnect()
        print("Disconnected: {}".format(await self.disconnected))


print("Starting")
loop = asyncio.get_event_loop()
loop.run_until_complete(AsyncMqttExample(loop).main())
loop.close()
print("Finished")
