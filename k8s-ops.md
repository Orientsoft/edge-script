# K8S操作

## 1. 启动Listener
kopf-listener是在K8S Master端，用于监听Device Event的程序。  

首先准备好kopf-listener.yaml配置文件：
```
nsq_url: '192.168.0.186:30150'
topic: 'device_event'
```

再启动Listener即可：  
```
python kopf-listener.py
```

所有的设备事件均会被发送到指定NSQ服务的device_event topic。  
整个系统只需启动一个listener即可。  

## 2. 建立设备
首先创建设备Model和Instance的描述文件，可以参考[这里](https://github.com/kubeedge/examples/tree/master/led-raspberrypi/sample-crds)。  

准备好描述文件之后，在K8S Master执行以下命令：  
```
kubectl apply -f led-light-device-model.yaml
kubectl apply -f led-light-device-instance.yaml
```
则设备已经在Master建立好，可以等待Edge Mapper了。  

## 3. 启动Edge节点
在节点上需要启动KubeEdge的Edge端程序，对于树莓派等系统可以直接使用官方发布的[预编译包](https://github.com/kubeedge/kubeedge/releases/download/v1.1.0/kubeedge-v1.1.0-linux-arm.tar.gz)。  

解压预编译包之后，首先需要将Cloud端生成的certs文件放置到合适的位置，比如kubeedge下的certs目录。  
配置```edge/conf/edge.yaml```文件（需要修改的地方节选）：  
```
internal-server: tcp://127.0.0.1:1884 # internal mqtt broker url.
mode: 0 # 0: internal mqtt broker enable only. 1: internal and external mqtt broker enable. 2: external mqtt broker enable only.

edgehub:
    websocket:
        url: wss://122.51.189.210:10000/e632aba927ea4ac2b575ec1603d56f10/fb4ebb70-2783-42b8-b3ef-63e2fd6d242e/events
        certfile: /home/pi/software/kubeedge/certs/edge.crt
        keyfile: /home/pi/software/kubeedge/certs/edge.key

    controller:
        protocol: websocket # websocket, quic
        heartbeat: 15  # second
        project-id: e632aba927ea4ac2b575ec1603d56f10
        node-id: pi-node-4

edged:
    hostname-override: pi-node-4
    interface-name: wlan0
    podsandbox-image: kubeedge/pause-arm:3.1 # kubeedge/pause:3.1 for x86 arch , kubeedge/pause-arm:3.1 for arm arch, kubeedge/pause-arm64 for arm64 arch
```

准备好之后启动edgecore即可：  
```
sudo nohup ./edgecore > edgecore.log &
```
可以考虑用systemctl将edgecore变成服务随系统启动。  

## 4. 启动Mapper
K8S Master上看到的设备，在设备端的实现就是Mapper。  
目前给出了一个示例```simple-mapper-demo.py```。其核心在于sync_twin()函数，需要获取Twin的期望值，调用相关的实际操作，并填写实际值。  

直接用Python执行mapper即可：  
```
python simple-mapper-demo.py
```
