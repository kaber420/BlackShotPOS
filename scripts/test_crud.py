import requests
import sys

BASE_URL = "http://localhost:8000/api/v1/pos"
# Simulating the token if needed, but for local tests we might have disabled it or use a default
HEADERS = {"X-Omni-Token": "test-token-admin"} # Adjust if necessary

def test_categories():
    print("Testing Categories CRUD...")
    # Create
    resp = requests.post(f"{BASE_URL}/categories", params={"name": "Test Cat", "description": "Desc"}, headers=HEADERS)
    if resp.status_code != 200:
        print(f"FAILED Create Category: {resp.text}")
        return False
    cat_id = resp.json()["id"]
    
    # Update
    resp = requests.put(f"{BASE_URL}/categories/{cat_id}", params={"name": "Updated Cat"}, headers=HEADERS)
    if resp.status_code != 200:
        print(f"FAILED Update Category: {resp.text}")
        return False
    
    # Delete
    resp = requests.delete(f"{BASE_URL}/categories/{cat_id}", headers=HEADERS)
    if resp.status_code != 200:
        print(f"FAILED Delete Category: {resp.text}")
        return False
    print("Categories CRUD OK")
    return True

def test_ingredients():
    print("Testing Ingredients CRUD...")
    # Create
    data = {"name": "Test Ing", "unit": "g", "current_stock": 100, "minimum_stock": 10}
    resp = requests.post(f"{BASE_URL}/ingredients", json=data, headers=HEADERS)
    if resp.status_code != 200:
        print(f"FAILED Create Ingredient: {resp.text}")
        return False
    ing_id = resp.json()["id"]
    
    # Update
    data["current_stock"] = 150
    resp = requests.put(f"{BASE_URL}/ingredients/{ing_id}", json=data, headers=HEADERS)
    if resp.status_code != 200:
        print(f"FAILED Update Ingredient: {resp.text}")
        return False
    
    # Delete
    resp = requests.delete(f"{BASE_URL}/ingredients/{ing_id}", headers=HEADERS)
    if resp.status_code != 200:
        print(f"FAILED Delete Ingredient: {resp.text}")
        return False
    print("Ingredients CRUD OK")
    return True

if __name__ == "__main__":
    # Note: Backend must be running for this to work
    print("Ensure the backend is running at http://localhost:8000")
    try:
        c_ok = test_categories()
        i_ok = test_ingredients()
        if c_ok and i_ok:
            print("\nALL BACKEND CRUD TESTS PASSED")
        else:
            sys.exit(1)
    except Exception as e:
        print(f"Error connecting to backend: {e}")
        sys.exit(1)
