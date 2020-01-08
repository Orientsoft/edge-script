import cv2
import time
from threading import Thread
from multiprocessing import Process, Queue

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
        # self.cap_proc = Process(target=flush_buffer, args=(self.q,))
        # self.cap_proc.start()

        self.cap_thread = Thread(target=flush_buffer, args=(self.q,))
        self.cap_thread.start()

        self.face_det = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')

    def detect(self):
        try:
            frame = self.q.get()
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            faces = self.face_det.detectMultiScale(
                gray,
                scaleFactor=1.15,
                minNeighbors=5,
                minSize=(5, 5),
                flags=cv2.IMREAD_GRAYSCALE
            )

            for x, y, w, h in faces:
                frame = cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 0, 255), 1)

            # cv2.imshow('face-det', frame)
            cv2.waitKey(1)

            return faces
        except:
            return []
