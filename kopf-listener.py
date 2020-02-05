import os
import json
import yaml
import multiprocessing as mp
import traceback
import base64

import kopf
import nsq
from nsq import Writer, Error
import tornado.ioloop

# consts
config_path = 'kopf-listener.yaml'

domain = 'devices.kubeedge.io'
version = 'v1alpha1'
reconnect_interval = 5.

# configs
with open(config_path, 'r') as config_file:
    config = yaml.load(config_file)

    topic = config['topic']

# configs
nsq_url = os.environ['NSQ_URL']

# global vars
q = mp.Queue()

# leave expensive ops such as json.dumps() and encode() in writer,
# since we could start multiple writers
def start_writer(q):
    writer = Writer([nsq_url])

    def pub_worker():
        try:
            while True:
                event = q.get(block=False) # will raise Queue.Empty exception

                event_json = {}

                # parse payload
                if 'desired' in event['object']['status']['twins'][0].keys():
                    desired_value = event['object']['status']['twins'][0]['desired']['value']
                    decoded_value = str(base64.b64decode(desired_value.encode('utf-8')), 'utf-8')
                    event_json['desired'] = json.loads(decoded_value)

                    # event['object']['status']['twins'][0]['desired']['value'] = json.loads(decoded_value)
                if 'reported' in event['object']['status']['twins'][0].keys():
                    reported_value = event['object']['status']['twins'][0]['reported']['value']
                    decoded_value = str(base64.b64decode(reported_value.encode('utf-8')), 'utf-8')
                    event_json['reported'] = json.loads(decoded_value)

                    # event['object']['status']['twins'][0]['reported']['value'] = json.loads(decoded_value)

                event_json['ts'] = event['object']['metadata']['creationTimestamp']
                event_json['device'] = event['object']['metadata']['name']
                event_json['node'] = event['object']['spec']['nodeSelector']['nodeSelectorTerms'][0]['matchExpressions'][0]['values'][0]

                writer.pub(topic, json.dumps(event_json).encode())
        except mp.queues.Empty:
            pass
        except:
            traceback.print_exc()

    tornado.ioloop.PeriodicCallback(pub_worker, 10).start()
    nsq.run()

writer_process = mp.Process(target=start_writer, args=(q,))
writer_process.start()

# k8s operator
@kopf.on.event(domain, version, 'devices')
def event_handler(event, **kwargs):
    q.put(event)
