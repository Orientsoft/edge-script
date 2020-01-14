# 构建Edge应用

以人脸计数为例说明如何构建Edge应用并打包。  

## K8S Device

这一步可以在AI Edge Web界面上完成，这里只是原理的说明。  
修改```face-det-device-instance.yaml```：  

```yaml
apiVersion: devices.kubeedge.io/v1alpha1
kind: Device
metadata:
  name: face-det-01 # 设备名
  labels:
    description: FaceDetector # 设备描述
    model: devicemodel
spec:
  deviceModelRef:
    name: devicemodel
  nodeSelector:
    nodeSelectorTerms:
    - matchExpressions:
      - key: ''
        operator: In
        values:
        - pi-node-4 # 节点名字
status:
  twins:
    - propertyName: payload
      desired:
        metadata:
          type: string
        value: 'e30K'
```

在K8S节点上执行：  

```
kubectl apply -f face-det-device-instance.yaml
```

## 开发调试环境

准备树莓派，配置摄像头和显示，安装Docker，部署KubeEdge。  
在```/home/pi```下建立```project```目录。  

启动容器：  

```
docker run -it --privileged -v /dev/video0:/dev/video0 -v /home/pi/project:/root/host_project --name pytorch -v /tmp/.X11-unix:/tmp/.X11-unix -e DISPLAY=unix$DISPLAY -e GDK_SCALE -e GDK_DPI_SCALE --network=host registry.mooplab.com:8443/kubeedge/pi4_pytorch:20200108 /bin/bash
```

这样就进入了交互式的容器环境，可以进行程序的调试，项目目录挂载到了/root/host_project下，容器中是root账号（Demo使用root账号方便开发测试，生产环境需要切换到普通用户）。  
容器中安装了python、opencv、pytorch，其他包可以自行安装。  
容器中要使用pip3和python3来调用Python 3.7执行环境。  

## AI应用开发

开发可以在树莓派的project目录中进行，由于它被挂载到了调试容器中，可以很方便的在容器中进行调试。  

原则上应用随便怎么做都可以，最终结果要封装成函数库的形式。  
建议将AI应用封装成一个类，摄像头、模型的初始化在```__init__()```中完成，再封装一个具体的算法执行函数。  

Tips. 要注意opencv的VideoCapture类自带Buffer，如果需要间隔一定时间再取帧检测，应该新开一个线程（或进程）去读空Buffer，以保证检测帧一定是最新。  

可以参考```FaceDetector.py```：  

```python
import cv2
import time
from threading import Thread
from multiprocessing import Process, Queue

# 清空视频Buffer
# 队列里面有且只有最新帧
def flush_buffer(q):
    cap = cv2.VideoCapture(0)

    while True:
        try:
            time.sleep(0.01)

            while q.qsize() > 1:
                q.get_nowait()
            
            ret, frame = cap.read()

            if ret:
                q.put(frame)
        except:
            pass

class FaceDetector:
    def __init__(self):
        self.q = Queue()

        # 启动清空Buffer线程
        self.cap_thread = Thread(target=flush_buffer, args=(self.q,))
        self.cap_thread.start()

        # 初始化检测模型
        self.face_det = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')

    def detect(self):
        try:
            # 从队列取出帧
            frame = self.q.get()
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # 执行模型
            faces = self.face_det.detectMultiScale(
                gray,
                scaleFactor=1.15,
                minNeighbors=5,
                minSize=(5, 5),
                flags=cv2.IMREAD_GRAYSCALE
            )

            # 绘制检测框
            for x, y, w, h in faces:
                frame = cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 0, 255), 1)

            cv2.imshow('face-det', frame)
            cv2.waitKey(1)

            # 返回结果框
            return faces
        except:
            return []
```

## mapper开发

AI程序通过Mapper与KubeEdge通信。  
Mapper会每隔一段时间调用```sync_twin()```函数，在该函数中，执行AI模型，获取结果，拼装成消息发送到MQTT。  
Mapper的其他部分应用开发者不必关心。  

参考```face-det-mapper.py```：  

```python
async def sync_twin():
    # 准备结果消息体
    twin_update_body = deepcopy(TwinUpdateTemplate)

    # 执行模型
    bboxes = det.detect()

    # 将结果拼成JSON
    result_dict = {
        'count': len(bboxes)
    }
    result_json = json.dumps(result_dict)

    # 将JSON串BASE64编码，完成消息体
    twin_update_body['twin']['payload']['actual']['value'] = '{}'.format(str(base64.b64encode(result_json.encode('utf-8')), 'utf-8'))
    twin_update_body['twin']['payload']['metadata']['type'] = 'Updated'

    # 发送消息
    msg_info = client.publish(
        '{}{}{}'.format(device_prefix, device_id, twin_update_suffix),
        payload=json.dumps(twin_update_body)
    )
    msg_info.wait_for_publish()
```

在调试容器中，执行启动Mapper的命令，就可以进行调试：  

```shell
cd /root
cd host-project/face-det
python3 face-det-mapper.py
```

调试完成就可以拷贝代码到容器内部存储，准备打包：  

```shell
cd /root
cp -fr host-project project
```

## 应用打包

首先提交容器的当前状态，注意容器名字：  

```shell
docker commit -a "YOUR_NAME" -m "WHAT_DID_YOU_DO" pytorch YOUR_IMAGE_NAME:TAG
```

注意由于我们的镜像是commit得到的，并没有包含ENTRYPOINT，因此需要用dockerfile重新打包一次。首先编辑```opencv_face_det.dockerfile```并修改```FROM```、```WORKDIR```、```ENTRYPOINT```等字段。  

然后构建镜像并推送到registry：  

```shell
docker build -f opencv_face_det.dockerfile -t registry.mooplab.com:8443/kubeedge/YOUR_IMAGE_NAME:TAG .
docker push registry.mooplab.com:8443/kubeedge/YOUR_IMAGE_NAME:TAG
```

这样就完成了Edge应用构建和打包的所有流程，利用registry上的镜像URL就可以在AI Edge的Web界面上进一步部署项目。  
