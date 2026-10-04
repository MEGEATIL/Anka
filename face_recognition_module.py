import cv2
import numpy as np
import json
from deepface import DeepFace
from datetime import datetime
import os

class FaceAuthenticator:
    def __init__(self, faces_dir='faces', encoding_file='face_encodings.json'):
        self.faces_dir = faces_dir
        self.encoding_file = encoding_file
        self.known_face_encodings = []
        self.known_face_names = []
        self.load_face_encodings()
        
        if not os.path.exists(faces_dir):
            os.makedirs(faces_dir)
    
    def load_face_encodings(self):
        """Load saved encodings"""
        if os.path.exists(self.encoding_file):
            try:
                with open(self.encoding_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.known_face_encodings = [np.array(enc) for enc in data.get('encodings', [])]
                    self.known_face_names = data.get('names', [])
                    print(f"✅ {len(self.known_face_encodings)} yüz kodlaması yüklendi")
            except Exception as e:
                print(f"⚠️ Kodlama yükleme hatası: {e}")

    def save_face_encodings(self):
        data = {
            'encodings': [enc.tolist() for enc in self.known_face_encodings],
            'names': self.known_face_names,
            'timestamp': datetime.now().isoformat()
        }
        with open(self.encoding_file, 'w', encoding='utf-8') as f:
            json.dump(data, f)
        print(f"✅ Yüz kodlamaları kaydedildi")

    def get_face_encoding(self, frame):
        try:
            result = DeepFace.represent(frame, model_name='Facenet', enforce_detection=False)
            if result:
                return np.array(result[0]['embedding'])
        except Exception:
            pass
        return None

    def _cosine_similarity(self, a, b):
        # return cosine similarity in [ -1, 1 ]
        if a is None or b is None:
            return -1.0
        na = np.linalg.norm(a)
        nb = np.linalg.norm(b)
        if na == 0 or nb == 0:
            return -1.0
        return float(np.dot(a, b) / (na * nb))

    def verify_face(self, name, num_attempts=3, threshold=0.4):
        """Verify by cosine similarity. Higher is better. threshold ~0.4 recommended."""
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print('❌ Kamera açılamadı!')
            return False

        print(f'👤 {name} doğrulanıyor... ({num_attempts} deneme)')

        for attempt in range(num_attempts):
            ret, frame = cap.read()
            if not ret:
                continue
            encoding = self.get_face_encoding(frame)
            if encoding is not None and self.known_face_encodings:
                sims = [self._cosine_similarity(encoding, enc) for enc in self.known_face_encodings]
                best_idx = int(np.argmax(sims))
                best_sim = sims[best_idx]
                matched_name = self.known_face_names[best_idx] if best_idx < len(self.known_face_names) else f'#{best_idx}'
                print(f'Attempt {attempt+1}: best match {matched_name} with cosine {best_sim:.4f}')
                if matched_name.lower() == name.lower() and best_sim >= threshold:
                    print(f'✅ {name} başarılı doğrulama (cosine={best_sim:.4f})')
                    cap.release()
                    cv2.destroyAllWindows()
                    return True
                else:
                    print(f'❌ Deneme {attempt+1} başarısız (cosine={best_sim:.4f})')
                    cv2.imshow('Yüz Doğrulama', frame)
                    cv2.waitKey(800)
            cv2.waitKey(100)

        cap.release()
        cv2.destroyAllWindows()
        return False

    def register_face(self, name, num_photos=5):
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print('❌ Kamera açılamadı!')
            return False
        
        print(f"\n🎥 {name} için {num_photos} fotoğraf çekiliyor...")
        encodings = []
        count = 0
        
        while count < num_photos:
            ret, frame = cap.read()
            if ret:
                encoding = self.get_face_encoding(frame)
                if encoding is not None:
                    encodings.append(encoding)
                    count += 1
                    print(f'📸 Fotoğraf {count}/{num_photos} kaydedildi')
                    cv2.imshow('Yüz Kaydı', frame)
                    cv2.waitKey(300)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        cap.release()
        cv2.destroyAllWindows()
        
        if encodings:
            avg_encoding = np.mean(encodings, axis=0)
            self.known_face_encodings.append(avg_encoding)
            self.known_face_names.append(name)
            self.save_face_encodings()
            return True
        return False
