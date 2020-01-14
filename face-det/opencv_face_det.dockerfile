FROM registry.mooplab.com:8443/kubeedge/pi4_pytorch:20200113

LABEL maintainer="mooplab"

ENV  TERM linux

RUN rm -rf /var/lib/apt/lists/*

WORKDIR /root/project/face-det

RUN PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:$WORKDIR
RUN export PATH

ENTRYPOINT ["python3", "./face-det-mapper.py"]

