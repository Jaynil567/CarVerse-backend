import os
import django
import pandas as pd

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'carverse.settings')
django.setup()

from django.contrib.auth import get_user_model
from api.models import Car

User = get_user_model()

def seed():
    csv_path = "./public/car_details.csv"
    if not os.path.exists(csv_path):
        print(f"Error: {csv_path} not found.")
        return
        
    print(f"Loading data from {csv_path} into Django Database...")
    df = pd.read_csv(csv_path)
    
    # Create default admin
    admin_user, created = User.objects.get_or_create(
        username='carverse_admin',
        email='admin@carverse.com',
        defaults={
            'role': 'admin',
            'phone': '9998887776',
            'location': 'Ahmedabad'
        }
    )
    if created:
        admin_user.set_password('admin123')
        admin_user.save()
        print("Created default admin user: carverse_admin / admin123")
    else:
        print("Default admin user already exists.")

    # Create default seller
    seller_user, created = User.objects.get_or_create(
        username='ahmedabad_seller',
        email='seller@carverse.com',
        defaults={
            'role': 'seller',
            'phone': '9876543210',
            'location': 'Ahmedabad'
        }
    )
    if created:
        seller_user.set_password('seller123')
        seller_user.save()
        print("Created default seller user: ahmedabad_seller / seller123")
    else:
        print("Default seller user already exists.")
        
    # Create default buyer
    buyer_user, created = User.objects.get_or_create(
        username='ahmedabad_buyer',
        email='buyer@carverse.com',
        defaults={
            'role': 'buyer',
            'phone': '9998887776',
            'location': 'Ahmedabad'
        }
    )
    if created:
        buyer_user.set_password('buyer123')
        buyer_user.save()
        print("Created default buyer user: ahmedabad_buyer / buyer123")
    else:
        print("Default buyer user already exists.")

    cars_seeded = 0
    for idx, row in df.iterrows():
        name = row['Name']
        year = int(row['Manufacturing Year'])
        price = float(row['Old Car Price (Lakh)'])
        
        # Check if already exists
        if Car.objects.filter(name=name, year=year, price=price).exists():
            continue
            
        brand = name.split(' ')[0]
        words = name.split(' ')
        model = " ".join(words[1:]) if len(words) > 1 else name
        
        Car.objects.create(
            name=name,
            brand=brand,
            model=model,
            year=year,
            km=int(row['KM']),
            fuel_type=row['Fuel Type'],
            transmission=row['Transmission'],
            owners=row['No of Owners'],
            color=row['Color'],
            engine_capacity=int(row['Engine Capacity (cc)']) if not pd.isna(row['Engine Capacity (cc)']) else 1197,
            mileage=float(row['Mileage (kmpl)']) if not pd.isna(row['Mileage (kmpl)']) else 18.2,
            seating_capacity=int(row['Seating Capacity']) if not pd.isna(row['Seating Capacity']) else 5,
            price=price,
            predicted_price=price,
            image=row['IMG'] if not pd.isna(row['IMG']) else "https://images.unsplash.com/photo-1549399542-7e3f8b79c341?auto=format&fit=crop&w=800&q=80",
            status='available',
            seller=seller_user
        )
        cars_seeded += 1
        
    print(f"Database seed complete. Added {cars_seeded} cars. Total cars in DB: {Car.objects.count()}")

if __name__ == "__main__":
    seed()
