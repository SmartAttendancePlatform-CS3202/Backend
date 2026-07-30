import os
import requests
from dotenv import load_dotenv

load_dotenv(os.path.join("services", "attendance-service", ".env"))

SUPABASE_URL = os.getenv("SUPABASE_URL")
# For testing we can use the service role key to hit the auth endpoints
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") 
API_URL = "http://localhost:8000"

def run_test():
    print("1. Logging in user...")
    auth_response = requests.post(
        f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
        headers={"apikey": SUPABASE_KEY, "Content-Type": "application/json"},
        json={
            "email": "sandaru@gmail.com",
            "password": "sandaru123",
        }
    )

    data = auth_response.json()
    access_token = data.get("access_token")

    if not access_token:
        print(f"Failed to get access token. Error: {data}")
        return

    print("2. Got Access Token successfully!")
    
    print("3. Testing Secure API endpoint (/me)...")
    api_response = requests.get(
        f"{API_URL}/me",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    
    print(f"Status Code: {api_response.status_code}")
    print(f"Response: {api_response.text}")

if __name__ == "__main__":
    run_test()
