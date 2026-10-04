# -*- coding: utf-8 -*-
from flask import Flask, Response, request, render_template_string, redirect, url_for, session
from functools import wraps
import hmac
import logging
import time
import json
import os
import re
import threading

try:
    import cv2
except ImportError:
    cv2 = None

try:
    from pyngrok import ngrok
except ImportError:
    ngrok = None

app = Flask(__name__)
app.secret_key = os.environ.get('APP_SECRET') or os.urandom(24).hex()
app.config.update(
    TRUST_PROXY=False,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
)
SIFRE = os.environ.get('KAMERA_SIFRE')
logger = logging.getLogger(__name__)

# In-memory brute-force tracker: { ip: { 'count': int, 'blocked_until': timestamp, 'initial_block_done': bool } }
failed_attempts = {}
MAX_FAIL = 5
BLOCK_SECONDS = 600  # initial block: 600 saniye
NEXT_EXTEND_SECONDS = 100  # after initial block expired, each wrong adds 100s
MAX_TRACKED_IPS = 4_096

cap = None

ngrok_url = None


def get_camera():
    """Kamerayı yalnızca gerçekten kullanılırken açar; yoksa uygulama ayakta kalır."""
    global cap
    if cv2 is None:
        return None
    if cap is not None and cap.isOpened():
        return cap

    candidate = cv2.VideoCapture(0)
    if not candidate.isOpened():
        candidate.release()
        return None
    candidate.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
    candidate.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
    cap = candidate
    return cap


def kamera_yayin():
    camera = get_camera()
    if camera is None:
        return
    while True:
        ret, frame = camera.read()
        if not ret:
            continue
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 40]
        _, buffer = cv2.imencode('.jpg', frame, encode_param)
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
        time.sleep(0.03)


# Şifre kontrol dekoratörü - artık bloklu IP'lerde oturumu temizliyor
def sifreli_erisilir(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        ip = get_client_ip()
        if ip and is_blocked(ip):
            session.clear()
            return redirect(url_for('giris'))
        if 'giris_basarili' not in session or not session['giris_basarili']:
            return redirect(url_for('giris'))
        return f(*args, **kwargs)
    return decorated_function


def get_client_ip():
    xff = request.headers.get('X-Forwarded-For', '')
    if app.config.get('TRUST_PROXY') and xff:
        return xff.split(',')[0].strip()
    return request.remote_addr or 'unknown'


def is_blocked(ip):
    info = failed_attempts.get(ip)
    if not info:
        return False
    blocked_until = info.get('blocked_until')
    if blocked_until and time.time() < blocked_until:
        return True
    return False


def record_failure(ip):
    """Return values:
       - 'blocked' : currently blocked, do not extend
       - 'initial' : counted and initial block applied (600s)
       - 'after_initial' : initial already applied and now immediate 100s block applied
       - 'counted' : counted but not yet blocked
    """
    now = time.time()
    _prune_failed_attempts(now)
    info = failed_attempts.get(ip) or {
        'count': 0,
        'blocked_until': None,
        'initial_block_done': False,
        'last_seen': now,
    }
    info['last_seen'] = now

    # If currently blocked, do nothing (do not extend)
    if info.get('blocked_until') and now < info['blocked_until']:
        failed_attempts[ip] = info
        return 'blocked'

    # If initial block was already applied previously (and now expired), then any wrong attempt causes NEXT_EXTEND_SECONDS block
    if info.get('initial_block_done'):
        info['blocked_until'] = now + NEXT_EXTEND_SECONDS
        info['count'] = 0
        failed_attempts[ip] = info
        return 'after_initial'

    # Otherwise count failures toward initial block
    info['count'] = info.get('count', 0) + 1
    if info['count'] >= MAX_FAIL:
        info['blocked_until'] = now + BLOCK_SECONDS
        info['count'] = MAX_FAIL
        info['initial_block_done'] = True
        failed_attempts[ip] = info
        return 'initial'

    failed_attempts[ip] = info
    return 'counted'


def _prune_failed_attempts(now: float) -> None:
    """Sınırsız IP kaydıyla bellek tüketilmesini engeller."""
    stale = [
        ip for ip, info in failed_attempts.items()
        if now - float(info.get('last_seen', now)) > 3_600
        and not is_blocked(ip)
    ]
    for ip in stale:
        failed_attempts.pop(ip, None)
    if len(failed_attempts) > MAX_TRACKED_IPS:
        oldest = sorted(
            failed_attempts,
            key=lambda key: float(failed_attempts[key].get('last_seen', now)),
        )[:len(failed_attempts) - MAX_TRACKED_IPS]
        for ip in oldest:
            failed_attempts.pop(ip, None)


def reset_failures(ip):
    if ip in failed_attempts:
        failed_attempts.pop(ip, None)


# GİRİŞ SAYFASI
@app.route('/giris', methods=['GET', 'POST'])
def giris():
    if not SIFRE:
        return "Kamera sunucusu yapılandırılmadı. KAMERA_SIFRE ortam değişkenini ayarlayın.", 503
    ip = get_client_ip()

    # Ensure we always check the latest info from failed_attempts
    info = failed_attempts.get(ip, {})

    # If blocked_until has passed, just clear blocked_until but keep initial_block_done flag
    if info and info.get('blocked_until') and time.time() >= info['blocked_until']:
        info['blocked_until'] = None
        info['count'] = 0
        failed_attempts[ip] = info
        just_unblocked = True
    else:
        just_unblocked = False

    remaining = 0
    if info and info.get('blocked_until'):
        remaining = int(info['blocked_until'] - time.time())
        if remaining < 0:
            remaining = 0

    if request.method == 'POST':
        sifre = request.form.get('sifre', '')

        # Fetch fresh snapshot here to enforce block strictly
        current_info = failed_attempts.get(ip, {})
        if current_info.get('blocked_until') and time.time() < current_info.get('blocked_until'):
            remaining = int(current_info.get('blocked_until') - time.time())
            logger.warning("Kamera girişi geçici olarak engellendi; kalan saniye=%s", remaining)
            hata = f"Şu anda blokluyuz. {remaining} saniye bekleyin."
            return render_template_string(LOGIN_HTML, hata=hata, remaining=remaining)

        # Not blocked: normal password check
        if hmac.compare_digest(sifre, SIFRE):
            session['giris_basarili'] = True
            reset_failures(ip)
            logger.info("Kamera girişi başarılı")
            return redirect(url_for('anasayfa'))

        # Wrong password handling
        result = record_failure(ip)
        info = failed_attempts.get(ip, {})
        if result == 'blocked':
            remaining = int(info.get('blocked_until', 0) - time.time()) if info.get('blocked_until') else 0
            hata = f"Şu anda blokluyuz. {remaining} saniye bekleyin."
        elif result == 'initial':
            remaining = int(info.get('blocked_until', 0) - time.time())
            hata = f"Çok fazla başarısız deneme. {remaining} saniye bloke edildiniz (ilk blok)."
        elif result == 'after_initial':
            remaining = int(info.get('blocked_until', 0) - time.time())
            hata = f"İlk blok uygulandı; yanlış deneme sonrası {remaining} saniye bloke edildiniz."
        else:
            attempts_left = MAX_FAIL - info.get('count', 0)
            hata = f"Yanlış şifre! {attempts_left} deneme hakkı kaldı."
        logger.warning("Kamera girişi başarısız; durum=%s", result)
        return render_template_string(LOGIN_HTML, hata=hata, remaining=remaining)

    # GET
    if just_unblocked:
        # Inform user that initial block lifted
        msg = "Blok kaldırıldı. Tekrar deneyin."
        return render_template_string(LOGIN_HTML, hata=msg, remaining=0)

    if remaining > 0:
        msg = f"Çok fazla başarısız deneme. {remaining} saniye sonra tekrar deneyin."
    else:
        msg = None
    return render_template_string(LOGIN_HTML, hata=msg, remaining=remaining)


# ANA SAYFA
@app.route('/')
@sifreli_erisilir
def anasayfa():
    return render_template_string(HOME_HTML)


@app.route('/kamera')
@sifreli_erisilir
def kamera():
    if get_camera() is None:
        return {'ok': False, 'error': 'Kamera erişilemez veya izin verilmemiş.'}, 503
    return Response(kamera_yayin(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/url')
@sifreli_erisilir
def get_url():
    return {'url': ngrok_url}


@app.route('/cikis')
def cikis():
    session.clear()
    return redirect(url_for('giris'))


# HTML ŞABLONLARı - JS ile geri sayım ekleniyor
LOGIN_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Kamera Server - Giriş</title>
    <style>
        body { font-family: Arial, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .container { background: white; padding: 40px; border-radius: 10px; box-shadow: 0 10px 25px rgba(0,0,0,0.2); text-align: center; width: 320px; }
        h1 { color: #333; margin-bottom: 20px; }
        input { width: 100%; padding: 12px; margin: 10px 0; border: 1px solid #ddd; border-radius: 5px; box-sizing: border-box; font-size: 16px; }
        button { width: 100%; padding: 12px; background: #667eea; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; margin-top: 10px; }
        button:hover { background: #764ba2; }
        .hata { color: red; margin: 10px 0; font-weight: bold; }
        .countdown { color: #333; margin-top: 10px; }
    </style>
</head>
<body>
    <div class="container">
        <h1> Kamera Server</h1>
        {% if hata %}
            <p class="hata">{{ hata }}</p>
        {% endif %}
        <form method="POST" id="loginForm">
            <input type="password" name="sifre" placeholder="Şifre" required id="sifreInput">
            <button type="submit" id="submitBtn">Giriş Yap</button>
        </form>
        <p class="countdown" id="countdown" style="display: none;"></p>
    </div>

    <script>
        var remaining = {{ remaining or 0 }};
        function startCountdown(){
            if (remaining > 0) {
                document.getElementById('countdown').style.display = 'block';
                update();
                var t = setInterval(function(){
                    remaining -= 1;
                    if (remaining <= 0){
                        clearInterval(t);
                        document.getElementById('countdown').innerText = 'Blok kaldırıldı. Tekrar deneyin.';
                        return;
                    }
                    update();
                }, 1000);
            }
        }
        function update(){
            document.getElementById('countdown').innerText = 'Blok kalkıyor: ' + remaining + ' saniye';
        }
        startCountdown();
    </script>
</body>
</html>
'''

HOME_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Kamera Server</title>
    <style>
        body { font-family: Arial, sans-serif; background: #f0f0f0; padding: 20px; text-align: center; }
        .container { max-width: 600px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 5px 15px rgba(0,0,0,0.1); }
        h1 { color: #333; }
        img { max-width: 100%; border-radius: 5px; margin: 20px 0; }
        a { display: inline-block; margin-top: 20px; padding: 10px 20px; background: #667eea; color: white; text-decoration: none; border-radius: 5px; }
        a:hover { background: #764ba2; }
    </style>
</head>
<body>
    <div class="container">
        <h1> Canlı Kamera Yayını</h1>
        <img src="/kamera" style="width:100%; border: 2px solid #667eea;">
        <br>
        <a href="/cikis">Çıkış Yap</a>
    </div>
</body>
</html>
'''



# --- Face recognition support ---
from pathlib import Path
try:
    import face_recognition
    FACE_LIB='face_recognition'
except Exception:
    face_recognition = None
    FACE_LIB=None
import io

FACES_DIR = Path('faces')
KNOWN_FILE = FACES_DIR / 'encodings.json'
known_face_encodings = []
known_face_names = []

def ensure_faces_dir():
    FACES_DIR.mkdir(parents=True, exist_ok=True)

def save_known_faces():
    try:
        serializable_encodings = [
            value.tolist() if hasattr(value, 'tolist') else value
            for value in known_face_encodings
        ]
        KNOWN_FILE.write_text(
            json.dumps(
                {'encodings': serializable_encodings, 'names': known_face_names},
                ensure_ascii=False,
            ),
            encoding='utf-8',
        )
    except (OSError, TypeError, ValueError) as error:
        print(f"[WARN] save_known_faces failed: {type(error).__name__}")

def load_known_faces():
    global known_face_encodings, known_face_names
    ensure_faces_dir()
    if KNOWN_FILE.exists():
        try:
            data = json.loads(KNOWN_FILE.read_text(encoding='utf-8'))
            encodings = data.get('encodings', [])
            names = data.get('names', [])
            if not isinstance(encodings, list) or not isinstance(names, list):
                raise ValueError('Geçersiz yüz verisi biçimi')
            known_face_encodings = encodings
            known_face_names = [name for name in names if isinstance(name, str)]
            print(f"[OK] Loaded {len(known_face_names)} known faces")
        except (OSError, ValueError, json.JSONDecodeError) as error:
            print(f"[WARN] load_known_faces failed: {type(error).__name__}")

def enroll_face(name, samples=5):
    """Capture samples from the webcam and save encodings for `name`."""
    if not re.fullmatch(r"[A-Za-z0-9_ -]{1,64}", name or ""):
        return False
    camera = get_camera()
    if camera is None:
        return False
    ensure_faces_dir()
    person_dir = FACES_DIR / name
    person_dir.mkdir(parents=True, exist_ok=True)
    captured = 0
    encs = []
    for i in range(samples*3):
        ret, frame = camera.read()
        if not ret:
            time.sleep(0.1)
            continue
        # save raw image
        img_path = person_dir / f"{int(time.time())}_{captured}.jpg"
        try:
            import cv2
            cv2.imwrite(str(img_path), frame)
        except Exception:
            pass
        if FACE_LIB == 'face_recognition':
            try:
                rgb = frame[:, :, ::-1]
                locs = face_recognition.face_locations(rgb)
                if not locs:
                    continue
                enc = face_recognition.face_encodings(rgb, known_face_locations=locs)[0]
                encs.append(enc)
                captured += 1
            except Exception:
                continue
        else:
            # fallback: just count samples
            captured += 1
        if captured >= samples:
            break
    if not encs and FACE_LIB == 'face_recognition':
        print('[WARN] No face encodings captured')
        return False
    # append to known lists
    if FACE_LIB == 'face_recognition':
        for e in encs:
            known_face_encodings.append(e)
            known_face_names.append(name)
    else:
        # fallback: store filenames as placeholder names
        for f in person_dir.iterdir():
            known_face_names.append(name)
            known_face_encodings.append(None)
    save_known_faces()
    return True


def recognize_face(frame, tolerance=0.5):
    if FACE_LIB != 'face_recognition' or not known_face_encodings:
        return None
    try:
        rgb = frame[:, :, ::-1]
        locs = face_recognition.face_locations(rgb)
        if not locs:
            return None
        encs = face_recognition.face_encodings(rgb, known_face_locations=locs)
        for enc in encs:
            matches = face_recognition.compare_faces(known_face_encodings, enc, tolerance=tolerance)
            if True in matches:
                idx = matches.index(True)
                return known_face_names[idx]
    except Exception as e:
        print(f"[WARN] recognize_face error: {e}")
    return None

# HTTP endpoints for enroll and face-login
@app.route('/enroll')
@sifreli_erisilir
def enroll_route():
    name = request.args.get('name')
    if not name:
        return {'ok': False, 'error': 'name query parameter required'}, 400
    ok = enroll_face(name)
    if ok:
        return {'ok': True, 'name': name}
    return {'ok': False, 'error': 'enroll failed'}, 500

@app.route('/face_login')
@sifreli_erisilir
def face_login():
    # capture a single frame and attempt recognition
    camera = get_camera()
    if camera is None:
        return redirect(url_for('giris'))
    ret, frame = camera.read()
    if not ret:
        return redirect(url_for('giris'))
    name = recognize_face(frame)
    if name:
        session['giris_basarili'] = True
        session['user'] = name
        return redirect(url_for('anasayfa'))
    else:
        return redirect(url_for('giris'))

# load known faces on start
load_known_faces()
def basla_ngrok():
    global ngrok_url
    auth_token = os.environ.get("NGROK_AUTHTOKEN")
    if not SIFRE or not auth_token or ngrok is None:
        print("ERROR: Kamera yayını için pyngrok, KAMERA_SIFRE ve NGROK_AUTHTOKEN gerekir.")
        return
    try:
        ngrok.set_auth_token(auth_token)
        public_url = ngrok.connect(5000, auth=f"user:{SIFRE}")
        ngrok_url = str(public_url)
        url_parts = ngrok_url.split('"')
        if len(url_parts) > 1:
            ngrok_url = url_parts[1]
        print(f"OK ngrok basarili: {ngrok_url}")
        with open('ngrok_url.json', 'w', encoding='utf-8') as f:
            json.dump({'url': ngrok_url, 'kamera': f'{ngrok_url}/kamera'}, f, indent=2)
        with open('ngrok_url.txt', 'w', encoding='utf-8') as f:
            f.write(f"Kamera Server URL: {ngrok_url}\n")
            f.write(f"Kamera Feed: {ngrok_url}/kamera\n")
        print(f"OK URL kaydedildi: ngrok_url.json")
    except Exception as e:
        print(f"ERROR: {e}")


if __name__ == '__main__':
    ngrok_thread = threading.Thread(target=basla_ngrok, daemon=True)
    ngrok_thread.start()
    time.sleep(2)
    app.run(host='0.0.0.0', port=5000, threaded=True, debug=False)
