import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'carverse.settings')
django.setup()

from django.contrib.auth import authenticate, get_user_model

User = get_user_model()

print("Listing all users in database:")
for user in User.objects.all():
    print(f"Username: {user.username}, Role: {user.role}, Password hashed: {user.password[:20]}...")

print("\nTesting authentication:")
test_cases = [
    ('ahmedabad_seller', 'seller123'),
    ('ahmedabad_buyer', 'buyer123'),
    ('carverse_admin', 'admin123')
]

for username, password in test_cases:
    user = authenticate(username=username, password=password)
    if user:
        print(f"✅ Success: Authenticated {username}")
    else:
        print(f"❌ Failed: Could not authenticate {username}")
