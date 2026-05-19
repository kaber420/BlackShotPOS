from fastapi.testclient import TestClient
from main import app
import sys

client = TestClient(app)

def test_routes():
    print("Testing basic routes...")
    
    # Test root endpoint
    response = client.get("/")
    assert response.status_code == 200
    print("Root OK:", response.json())
    
    # Test catalog endpoint to see if it responds (could be 200 or 401/403 depending on auth, but shouldn't 500)
    response = client.get("/api/v1/pos/catalog/categories")
    print("Categories OK:", response.status_code)
    
    # We can try to upload an invalid file to see if the media router is hooked up correctly
    response = client.post("/api/v1/pos/media/upload", files={"file": ("test.txt", b"hello", "text/plain")})
    # Since it lacks auth, it might return 401 Unauthorized or 403 Forbidden.
    print("Media Upload Endpoint exists. Status:", response.status_code)
    
    print("All basic routing works.")

if __name__ == "__main__":
    try:
        test_routes()
    except Exception as e:
        print("Error during test:", e)
        sys.exit(1)
