import requests
import sys

BASE_URL = "http://localhost:8400/api/v1/pos"
AUTH_URL = "http://localhost:8400/api/auth/jwt/login"

# Use a session to persist cookies
session = requests.Session()

def login():
    print(f"Logging in to {AUTH_URL}...")
    resp = session.post(AUTH_URL, data={"username": "admin@blackshot.pos", "password": "admin_password"})
    if resp.status_code not in [200, 204]:
        print(f"FAILED Login: {resp.status_code} {resp.text}")
        return False
    print("Login OK")
    return True

def test_categories():
    import uuid
    cat_name = f"Test Cat {uuid.uuid4().hex[:6]}"
    print(f"Testing Categories CRUD with name: {cat_name}...")
    # Create
    resp = session.post(f"{BASE_URL}/categories", json={"name": cat_name, "description": "Desc"})
    if resp.status_code != 200:
        print(f"FAILED Create Category: {resp.status_code} {resp.text}")
        return False
    cat_id = resp.json()["id"]
    
    # Update
    resp = session.put(f"{BASE_URL}/categories/{cat_id}", json={"name": f"Updated {cat_name}"})
    if resp.status_code != 200:
        print(f"FAILED Update Category: {resp.status_code} {resp.text}")
        return False
    
    # Delete
    resp = session.delete(f"{BASE_URL}/categories/{cat_id}")
    if resp.status_code != 200:
        print(f"FAILED Delete Category: {resp.status_code} {resp.text}")
        return False
    print("Categories CRUD OK")
    return True

def test_ingredients():
    print("Testing Ingredients CRUD...")
    # Create
    data = {"name": "Test Ing", "unit": "g", "current_stock": 100, "minimum_stock": 10}
    resp = session.post(f"{BASE_URL}/ingredients", json=data)
    if resp.status_code != 200:
        print(f"FAILED Create Ingredient: {resp.status_code} {resp.text}")
        return False
    ing_id = resp.json()["id"]
    
    # Update
    data["current_stock"] = 150
    resp = session.put(f"{BASE_URL}/ingredients/{ing_id}", json=data)
    if resp.status_code != 200:
        print(f"FAILED Update Ingredient: {resp.status_code} {resp.text}")
        return False
    
    # Delete
    resp = session.delete(f"{BASE_URL}/ingredients/{ing_id}")
    if resp.status_code != 200:
        print(f"FAILED Delete Ingredient: {resp.status_code} {resp.text}")
        return False
    print("Ingredients CRUD OK")
    return True

if __name__ == "__main__":
    print("Ensure the backend is running at http://localhost:8400")
    try:
        if not login():
            sys.exit(1)
        c_ok = test_categories()
        i_ok = test_ingredients()
        if c_ok and i_ok:
            print("\nALL BACKEND CRUD TESTS PASSED")
        else:
            sys.exit(1)
    except Exception as e:
        print(f"Error connecting to backend: {e}")
        sys.exit(1)
