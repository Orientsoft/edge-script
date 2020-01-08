import cv2

class FaceDetector:
    def __init__(self):
        self.cap = cv2.VideoCapture(0)
        self.face_det = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')

    def detect(self):
        ret, frame = self.cap.read()
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

        cv2.imshow('video', frame)
        cv2.waitKey(1)
