import requests
import sys
import os

BASE_URL = "http://localhost:8400/api/v1/pos/communications"
AUTH_URL = "http://localhost:8400/api/auth/jwt/login"

session = requests.Session()

def login():
    print(f"Logging in to {AUTH_URL}...")
    # Credenciales por defecto del seed
    resp = session.post(AUTH_URL, data={"username": "admin@blackshot.pos", "password": "admin1234"})
    if resp.status_code not in [200, 204]:
        print(f"FAILED Login: {resp.status_code} {resp.text}")
        return False
    print("Login OK")
    return True

def test_voice_upload():
    print("Testing Voice Upload...")
    # Crear un archivo de audio falso
    audio_content = b"fake opus audio data"
    files = {'audio': ('test.webm', audio_content, 'audio/webm')}
    data = {'is_global': 'true', 'area_ids': '1'}
    
    resp = session.post(f"{BASE_URL}/voice", files=files, data=data)
    if resp.status_code != 200:
        print(f"FAILED Upload: {resp.status_code} {resp.text}")
        return False
    
    msg = resp.json()
    print(f"Upload OK: ID={msg['id']}, Path={msg['audio_path']}")
    return msg['id'], msg['audio_path']

def test_history():
    print("Testing History...")
    resp = session.get(f"{BASE_URL}/history")
    if resp.status_code != 200:
        print(f"FAILED History: {resp.status_code} {resp.text}")
        return False
    
    history = resp.json()
    if len(history) > 0:
        print(f"History OK: Found {len(history)} messages")
        return True
    else:
        print("FAILED History: Empty")
        return False

def test_audio_download(filename):
    print(f"Testing Audio Download: {filename}...")
    resp = session.get(f"{BASE_URL}/audio/{filename}")
    if resp.status_code != 200:
        print(f"FAILED Download: {resp.status_code} {resp.text}")
        return False
    
    print("Download OK")
    return True

if __name__ == "__main__":
    if not login():
        sys.exit(1)
    
    msg_id, audio_path = test_voice_upload()
    if not msg_id:
        sys.exit(1)
        
    if not test_history():
        sys.exit(1)
        
    if not test_audio_download(audio_path):
        sys.exit(1)
        
    print("\nALL INTERCOM BACKEND TESTS PASSED")
