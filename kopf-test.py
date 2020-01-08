import kopf

@kopf.on.event('devices.kubeedge.io', 'v1alpha1', 'devices')
def event_handler(event, **kwargs):
    print(event)
