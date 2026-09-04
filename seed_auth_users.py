"""
Seed / Provision Supabase Auth Users and RBAC roles.

This script creates standard test users in Supabase Auth (if they do not already exist)
and synchronizes their roles in the PostgreSQL `public.users` table.

Accounts provisioned:
1. Admin:
   - admin@univ.ac.lk / password123
   - admin@university.ac.lk / adminpass123
2. Lecturer:
   - arthur.vance@university.ac.lk / password123
   - pasan@cse.mrt.ac.lk / password123
3. Student:
   - sandaru@gmail.com / sandaru123

Usage:
    python seed_auth_users.py
"""

import os
import requests
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://ywxuyhdvcvfqayckertu.supabase.co")
SUPABASE_SERVICE_ROLE_KEY = os.getenv(
    "SUPABASE_SERVICE_ROLE_KEY",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inl3eHV5aGR2Y3ZmcWF5Y2tlcnR1Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4NDE3OTY3OCwiZXhwIjoyMDk5NzU1Njc4fQ.ODNtjbvjNqCgpGH7L7bWz5Zt4WAgwFVf-ucKbNVC8L8"
)

TEST_USERS = [
    {
        "email": "admin@univ.ac.lk",
        "password": "password123",
        "role": "admin",
        "username": "admin",
    },
    {
        "email": "admin@university.ac.lk",
        "password": "adminpass123",
        "role": "admin",
        "username": "admin_uoc",
    },
    {
        "email": "arthur.vance@university.ac.lk",
        "password": "password123",
        "role": "lecturer",
        "username": "arthur.vance",
    },
    {
        "email": "pasan@cse.mrt.ac.lk",
        "password": "password123",
        "role": "lecturer",
        "username": "pasan",
    },
    {
        "email": "sandaruvidushan@gmail.com",
        "password": "password123",
        "role": "student",
        "username": "sandaruvidushan",
    },
    {
        "email": "sandaru@gmail.com",
        "password": "sandaru123",
        "role": "student",
        "username": "sandaru",
    },
    {
        "email": "test1@gmail.com",
        "password": "password123",
        "role": "student",
        "username": "test1",
    },
]


def seed_users():
    headers = {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
    }

    print(f"Connecting to Supabase at: {SUPABASE_URL}")
    print("--- Provisioning Auth Users ---")

    # Fetch existing auth users list
    existing_users_res = requests.get(
        f"{SUPABASE_URL}/auth/v1/admin/users",
        headers=headers,
    )
    existing_users_by_email = {}
    if existing_users_res.status_code == 200:
        for u in existing_users_res.json().get("users", []):
            if u.get("email"):
                existing_users_by_email[u["email"].lower()] = u["id"]

    for user in TEST_USERS:
        email = user["email"].lower()
        if email in existing_users_by_email:
            user_id = existing_users_by_email[email]
            update_payload = {
                "password": user["password"],
                "email_confirm": True,
                "user_metadata": {
                    "role": user["role"],
                    "username": user["username"],
                },
            }
            res = requests.put(
                f"{SUPABASE_URL}/auth/v1/admin/users/{user_id}",
                headers=headers,
                json=update_payload,
            )
            if res.status_code == 200:
                print(f" [UPDATED PASSWORD] {user['email']} (role: {user['role']})")
            else:
                print(f" [UPDATE FAILED] {user['email']}: {res.text}")
        else:
            payload = {
                "email": user["email"],
                "password": user["password"],
                "email_confirm": True,
                "user_metadata": {
                    "role": user["role"],
                    "username": user["username"],
                },
            }

            res = requests.post(
                f"{SUPABASE_URL}/auth/v1/admin/users",
                headers=headers,
                json=payload,
            )

            if res.status_code in (200, 201):
                print(f" [CREATED] {user['email']} (role: {user['role']})")
            else:
                data = res.json()
                msg = data.get("message", "") or data.get("msg", "")
                print(f" [INFO] {user['email']}: {msg or res.status_code}")

        # Update role and status in public.users table directly to ensure DB sync
        patch_res = requests.patch(
            f"{SUPABASE_URL}/rest/v1/users?username=eq.{user['username']}",
            headers=headers,
            json={"role": user["role"], "status": "active", "is_active": True},
        )
        if patch_res.status_code in (200, 204):
            print(f"   |-- synced DB public.users role => {user['role']}, status => active")

    print("\n--- Current Users in Database ---")
    list_res = requests.get(
        f"{SUPABASE_URL}/rest/v1/users?select=username,role,status",
        headers=headers,
    )
    if list_res.status_code == 200:
        for row in list_res.json():
            print(f" - {row.get('username')}: {row.get('role')} ({row.get('status')})")

    print("\nAuth seeding complete.")


if __name__ == "__main__":
    seed_users()
