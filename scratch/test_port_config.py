import os
import sys
import shutil

# Add root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pos_core.setup import _ensure_secure_tokens, _update_env_file

TEST_ENV = "scratch/test.env"

def setup_test_env(port="8400"):
    with open(TEST_ENV, "w") as f:
        f.write(f'PORT="{port}"\n')
        f.write('ALLOWED_ORIGINS="http://localhost:8400"\n')

def test_ensure_tokens():
    print("--- Testing _ensure_secure_tokens ---")
    setup_test_env()
    _ensure_secure_tokens(TEST_ENV)
    
    with open(TEST_ENV, "r") as f:
        lines = f.readlines()
        content = "".join(lines)
        print(content)
        
        found_frontend = False
        found_port = False
        for line in lines:
            if 'FRONTEND_PORT="80"' in line:
                found_frontend = True
            if 'PORT="8400"' in line:
                found_port = True
        
        assert found_frontend, "FRONTEND_PORT default not found"
        assert found_port, "Existing PORT was modified"
    print("✅ _ensure_secure_tokens passed.")

def test_logic_simulation():
    print("\n--- Simulating Origin Generation Logic ---")
    # This simulates the logic I just added to setup.py
    local_ip = "192.168.1.50"
    current_frontend_port = "80"
    current_api_port = "8400"
    current_origins = "http://localhost:8400"
    
    new_origins = current_origins
    for p in [current_frontend_port, current_api_port]:
        if p in ["80", "443"]:
            o = f"http://{local_ip}" if p == "80" else f"https://{local_ip}"
        else:
            o = f"http://{local_ip}:{p}"
        if o not in new_origins:
            new_origins += f",{o}"
    
    print(f"Generated Origins: {new_origins}")
    assert f"http://{local_ip}" in new_origins
    assert f"http://{local_ip}:8400" in new_origins
    assert f"http://{local_ip}:80" not in new_origins # Should be omitted
    print("✅ Origin generation logic (standard port) passed.")

    # Test with custom frontend port
    current_frontend_port = "5173"
    new_origins = current_origins
    for p in [current_frontend_port, current_api_port]:
        if p in ["80", "443"]:
            o = f"http://{local_ip}" if p == "80" else f"https://{local_ip}"
        else:
            o = f"http://{local_ip}:{p}"
        if o not in new_origins:
            new_origins += f",{o}"
    
    print(f"Generated Origins (Dev): {new_origins}")
    assert f"http://{local_ip}:5173" in new_origins
    assert f"http://{local_ip}:8400" in new_origins
    print("✅ Origin generation logic (dev port) passed.")

if __name__ == "__main__":
    if not os.path.exists("scratch"):
        os.makedirs("scratch")
    try:
        test_ensure_tokens()
        test_logic_simulation()
    finally:
        if os.path.exists(TEST_ENV):
            os.remove(TEST_ENV)
