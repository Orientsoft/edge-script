docker run -it --privileged -v /dev/video0:/dev/video0 -v /home/pi/project:/root/host_project --name pytorch -v /tmp/.X11-unix:/tmp/.X11-unix -e DISPLAY=unix$DISPLAY -e GDK_SCALE -e GDK_DPI_SCALE --network=host registry.mooplab.com:8443/kubeedge/pi4_pytorch:20200107 /bin/bash