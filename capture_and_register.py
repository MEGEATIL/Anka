import os, json, time
import numpy as np
import cv2
from face_recognition_module import FaceAuthenticator

faces_dir = 'faces'
if not os.path.exists(faces_dir):
    os.makedirs(faces_dir)

fa = FaceAuthenticator()
print(f'Known names: {fa.known_face_names}')

# Debug: capture 5 frames, save and compute distances
print('\n--- DEBUG: Capturing 5 frames and comparing to stored encodings ---')
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print('ERROR: camera open failed')
    raise SystemExit(1)

for i in range(1,6):
    # wait and capture
    ret = False
    for _ in range(10):
        ret, frame = cap.read()
        if ret:
            break
        time.sleep(0.1)
    if not ret:
        print(f'Frame {i}: capture failed')
        continue
    path = os.path.join(faces_dir, f'debug_{i}.jpg')
    cv2.imwrite(path, frame)
    enc = fa.get_face_encoding(frame)
    if enc is None:
        print(f'Frame {i}: no encoding extracted (saved to {path})')
        continue
    # compare to stored encodings
    for j, stored in enumerate(fa.known_face_encodings):
        d = float(np.linalg.norm(enc - stored))
        name = fa.known_face_names[j] if j < len(fa.known_face_names) else f'#{j}'
        print(f'Frame {i} -> {name}: distance = {d:.4f}')

cap.release()

# Controlled re-registration: 20 photos, save each, compute avg encoding
print('\n--- Re-registering: capturing 20 photos (look at camera) ---')
input('Press Enter when ready to start capturing 20 photos...')
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print('ERROR: camera open failed for registration')
    raise SystemExit(1)

encodings = []
count = 0
for i in range(1,21):
    ret = False
    for _ in range(20):
        ret, frame = cap.read()
        if ret:
            break
        time.sleep(0.05)
    if not ret:
        print(f'Register frame {i}: capture failed')
        continue
    img_path = os.path.join(faces_dir, f'register_{i}.jpg')
    cv2.imwrite(img_path, frame)
    enc = fa.get_face_encoding(frame)
    if enc is not None:
        encodings.append(enc)
        count += 1
        print(f'Register photo {i}/{20} saved + encoding OK ({img_path})')
    else:
        print(f'Register photo {i}/{20} saved but no encoding ({img_path})')
    time.sleep(0.2)

cap.release()

if not encodings:
    print('No encodings extracted during registration; aborting save')
    raise SystemExit(1)

avg_enc = np.mean(encodings, axis=0)
# replace existing 'Mehmet Ege' or append
name = 'Mehmet Ege'
if name in fa.known_face_names:
    idx = fa.known_face_names.index(name)
    fa.known_face_encodings[idx] = avg_enc
    print(f'Replaced encoding for existing name {name} at index {idx}')
else:
    fa.known_face_encodings.append(avg_enc)
    fa.known_face_names.append(name)
    print(f'Appended new encoding for {name}')

fa.save_face_encodings()
print('Re-registration complete. New stored count:', len(fa.known_face_encodings))

# Post-registration sanity: compare one live frame to new average
cap = cv2.VideoCapture(0)
ret = False
for _ in range(10):
    ret, frame = cap.read()
    if ret:
        break
    time.sleep(0.1)
if not ret:
    print('Post-check capture failed')
else:
    enc = fa.get_face_encoding(frame)
    if enc is None:
        print('Post-check: no encoding from live frame')
    else:
        d = float(np.linalg.norm(enc - avg_enc))
        print(f'Post-check distance to new avg encoding: {d:.4f} (threshold 0.6)')
        post_path = os.path.join(faces_dir, 'post_check.jpg')
        cv2.imwrite(post_path, frame)
        print('Saved post-check image to', post_path)

