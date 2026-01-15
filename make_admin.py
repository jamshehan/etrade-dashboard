#!/usr/bin/env python
"""
Script to create or update a user to admin role.
"""
from database_pg import TransactionDatabase

db = TransactionDatabase()

# Step 1: Get your Clerk user ID
print("To find your Clerk user ID:")
print("1. Open the browser dev tools (F12)")
print("2. Go to Application/Storage > Local Storage")
print("3. Look for a Clerk-related key, or...")
print("4. Go to Network tab, make an API request, and inspect the JWT token")
print()

auth_id = input("Enter your Clerk user ID (e.g., user_2abc123xyz): ").strip()
email = input("Enter your email address: ").strip()

if not auth_id or not email:
    print("Error: Both fields are required")
    exit(1)

# Check if user already exists
existing_user = db.get_user_by_auth_id(auth_id)

if existing_user:
    print(f"\nUser found: {existing_user['email']} (role: {existing_user['role']})")
    update = input("Update to admin role? (y/n): ").strip().lower()

    if update == 'y':
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE users SET role = 'admin' WHERE auth_provider_id = %s",
                    (auth_id,)
                )
                conn.commit()
        print("✓ User updated to admin role!")
else:
    # Create new user
    user = db.create_user(
        auth_provider_id=auth_id,
        email=email,
        full_name=email.split('@')[0].replace('.', ' ').title(),
        role='admin'
    )
    print(f"✓ Created admin user: {user['email']}")

print("\nRefresh your browser to see the changes!")
