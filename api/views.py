import os
import joblib
import pandas as pd
import numpy as np
from rest_framework import status, views, viewsets, permissions, authentication
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate, get_user_model
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.utils.text import slugify

from .models import Car, Inquiry, Order
from .serializers import (
    UserProfileSerializer, CarSerializer, InquirySerializer, OrderSerializer
)

User = get_user_model()

# =====================================================================
# AUTHENTICATION VIEWS
# =====================================================================

class RegisterView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = UserProfileSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            token, created = Token.objects.get_or_create(user=user)
            return Response({
                'token': token.key,
                'user': UserProfileSerializer(user).data
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        
        if not username or not password:
            return Response({'error': 'Please provide both username and password'}, status=status.HTTP_400_BAD_REQUEST)
            
        user = authenticate(username=username, password=password)
        if user:
            token, created = Token.objects.get_or_create(user=user)
            return Response({
                'token': token.key,
                'user': UserProfileSerializer(user).data
            })
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

class UserProfileView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)

# =====================================================================
# CAR MANAGEMENT VIEWSET
# =====================================================================

class CarViewSet(viewsets.ModelViewSet):
    queryset = Car.objects.all().order_by('-created_at')
    serializer_class = CarSerializer
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        queryset = Car.objects.all().order_by('-created_at')
        
        # Admin gets full access to all cars
        if self.request.user.is_authenticated and self.request.user.role == 'admin':
            seller_id = self.request.query_params.get('seller_id', None)
            if seller_id:
                queryset = queryset.filter(seller_id=seller_id)
        else:
            # If logged in as seller and accessing my cars
            my_listings = self.request.query_params.get('my_listings', None)
            if my_listings == 'true' and self.request.user.is_authenticated:
                return queryset.filter(seller=self.request.user)
                
            # Standard browse filtering (only available cars for normal views)
            if my_listings != 'true':
                queryset = queryset.filter(status='available')


        # Filters
        brand = self.request.query_params.get('brand', None)
        fuel_type = self.request.query_params.get('fuel_type', None)
        transmission = self.request.query_params.get('transmission', None)
        min_price = self.request.query_params.get('min_price', None)
        max_price = self.request.query_params.get('max_price', None)
        min_year = self.request.query_params.get('min_year', None)
        max_year = self.request.query_params.get('max_year', None)
        owners = self.request.query_params.get('owners', None)
        search = self.request.query_params.get('search', None)

        if brand:
            queryset = queryset.filter(brand__iexact=brand)
        if fuel_type:
            queryset = queryset.filter(fuel_type__iexact=fuel_type)
        if transmission:
            queryset = queryset.filter(transmission__iexact=transmission)
        if min_price:
            queryset = queryset.filter(price__gte=float(min_price))
        if max_price:
            queryset = queryset.filter(price__lte=float(max_price))
        if min_year:
            queryset = queryset.filter(year__gte=int(min_year))
        if max_year:
            queryset = queryset.filter(year__lte=int(max_year))
        if owners:
            queryset = queryset.filter(owners__iexact=owners)
        if search:
            queryset = queryset.filter(name__icontains=search)

        return queryset

    def perform_create(self, serializer):
        # Determine image URL: check if uploaded file exists
        img_url = "https://images.unsplash.com/photo-1549399542-7e3f8b79c341?auto=format&fit=crop&w=800&q=80"
        
        # Check if an image is sent as a file
        if 'image_file' in self.request.FILES:
            image_file = self.request.FILES['image_file']
            
            if settings.CLOUDINARY_CONFIGURED:
                import cloudinary.uploader
                try:
                    upload_result = cloudinary.uploader.upload(image_file)
                    img_url = upload_result.get('secure_url')
                    print(f"Uploaded to Cloudinary: {img_url}")
                except Exception as e:
                    print(f"Cloudinary upload error: {e}, falling back to local storage")
                    img_url = self._save_local_file(image_file)
            else:
                img_url = self._save_local_file(image_file)
        elif 'image' in self.request.data and self.request.data['image']:
            img_url = self.request.data['image']

        # Determine brand and model from Name if not directly provided
        name = self.request.data.get('name', '')
        brand = self.request.data.get('brand', '')
        model = self.request.data.get('model', '')
        if not brand and name:
            brand = name.split(' ')[0]
        if not model and name:
            words = name.split(' ')
            model = " ".join(words[1:]) if len(words) > 1 else name

        serializer.save(
            seller=self.request.user, 
            image=img_url,
            brand=brand,
            model=model
        )

    def _save_local_file(self, file_obj):
        # Clean file name and save to local media root
        filename = slugify(file_obj.name.split('.')[0]) + '.' + file_obj.name.split('.')[-1]
        path = default_storage.save(f'car_images/{filename}', ContentFile(file_obj.read()))
        # Build local URL (relative to root domain)
        request = self.request
        return f"{request.scheme}://{request.get_host()}/media/{path}"

# =====================================================================
# MACHINE LEARNING PRICE PREDICTION
# =====================================================================

class PredictPriceView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        try:
            km = float(request.data.get('KM', 45000))
            fuel_type = request.data.get('Fuel Type', 'Petrol')
            year = int(request.data.get('Manufacturing Year', 2018))
            owners = request.data.get('No of Owners', 'First')
            transmission = request.data.get('Transmission', 'Manual')
            engine_capacity = float(request.data.get('Engine Capacity (cc)', 1197))
            mileage = float(request.data.get('Mileage (kmpl)', 18.2))
            seating = int(request.data.get('Seating Capacity', 5))
            
            # Predict path
            model_path = os.path.join(settings.BASE_DIR, 'pricing_model.joblib')
            
            if os.path.exists(model_path):
                # Predict using ML pipeline
                pipeline = joblib.load(model_path)
                
                input_df = pd.DataFrame([{
                    'KM': km,
                    'Fuel Type': fuel_type,
                    'Manufacturing Year': year,
                    'No of Owners': owners,
                    'Transmission': transmission,
                    'Engine Capacity (cc)': engine_capacity,
                    'Mileage (kmpl)': mileage,
                    'Seating Capacity': seating
                }])
                
                predicted_price = float(pipeline.predict(input_df)[0])
                print(f"ML Predicted price: {predicted_price:.2f} Lakhs")
            else:
                # Math-based depreciation fallback logic if ML model joblib is not generated yet
                print("ML Model file not found. Calculating using fallback depreciation formula.")
                base_price = 10.0  # base lakh
                
                # Capacity booster
                if engine_capacity > 2000:
                    base_price += 15.0
                elif engine_capacity > 1500:
                    base_price += 6.0
                
                # Transmission booster
                if transmission.lower() == 'automatic':
                    base_price += 1.5
                    
                # Depreciation by year (assume current year is 2026)
                age = max(0, 2026 - year)
                depreciation_rate = 0.08  # 8% per year
                depreciated = base_price * ((1 - depreciation_rate) ** age)
                
                # KM depreciation (-0.1 lakh per 15k kms)
                km_penalty = (km / 15000) * 0.15
                depreciated = max(1.0, depreciated - km_penalty)
                
                # Owners penalty
                if owners.lower() == 'second':
                    depreciated *= 0.85
                elif owners.lower() in ['third', 'more than 2']:
                    depreciated *= 0.70
                    
                # Fuel type bonus
                if fuel_type.lower() == 'diesel':
                    depreciated += 0.8
                elif fuel_type.lower() == 'cng':
                    depreciated -= 0.5
                    
                predicted_price = float(round(depreciated, 2))
                print(f"Fallback Predicted price: {predicted_price:.2f} Lakhs")

                
            return Response({
                'predicted_price': round(predicted_price, 2),
                'currency': 'Lakh INR'
            })
            
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

# =====================================================================
# INQUIRIES & ORDERS VIEWS
# =====================================================================

class InquiryViewSet(viewsets.ModelViewSet):
    queryset = Inquiry.objects.all().order_by('-created_at')
    serializer_class = InquirySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'seller':
            # Seller sees inquiries on their own cars
            return Inquiry.objects.filter(car__seller=user).order_by('-created_at')
        # Buyers see inquiries they've sent
        return Inquiry.objects.filter(buyer=user).order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(buyer=self.request.user)

class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all().order_by('-created_at')
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'seller':
            # Seller sees orders on their own cars
            return Order.objects.filter(car__seller=user).order_by('-created_at')
        # Buyers see orders they placed
        return Order.objects.filter(buyer=user).order_by('-created_at')

    def perform_create(self, serializer):
        car_id = self.request.data.get('car')
        car = Car.objects.get(id=car_id)
        
        # Place the order
        order = serializer.save(buyer=self.request.user, price=car.price)
        
        # Mark car as sold
        car.status = 'sold'
        car.save()

# =====================================================================
# OPTIONS & DB SEEDER VIEWS
# =====================================================================

class FilterOptionsView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        # Fetch distinct options from DB
        brands = list(Car.objects.filter(status='available').values_list('brand', flat=True).distinct())
        # Clean nulls
        brands = sorted([b for b in brands if b])
        
        fuel_types = ['Petrol', 'Diesel', 'CNG', 'Electric', 'Hybrid']
        transmissions = ['Manual', 'Automatic']
        owners = ['First', 'Second', 'Third']
        colors = ['White', 'Black', 'Silver', 'Grey', 'Red', 'Blue', 'Brown']
        
        return Response({
            'brands': brands if brands else ['Maruti', 'Hyundai', 'Honda', 'Toyota', 'Tata', 'Mahindra', 'BMW', 'Mercedes'],
            'fuel_types': fuel_types,
            'transmissions': transmissions,
            'owners': owners,
            'colors': colors
        })

class DatabaseSeederView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        csv_path = os.path.join(settings.BASE_DIR, 'public', 'car_details.csv')
        if not os.path.exists(csv_path):
            return Response({'error': 'car_details.csv file not found'}, status=status.HTTP_404_NOT_FOUND)
            
        try:
            df = pd.read_csv(csv_path)
            
            # Create a default seller user if not exists
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

            cars_seeded = 0
            for idx, row in df.iterrows():
                # Check if car already exists
                name = row['Name']
                year = int(row['Manufacturing Year'])
                price = float(row['Old Car Price (Lakh)'])
                
                if Car.objects.filter(name=name, year=year, price=price).exists():
                    continue
                    
                brand = name.split(' ')[0]
                words = name.split(' ')
                model = " ".join(words[1:]) if len(words) > 1 else name
                
                car = Car.objects.create(
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
                
            return Response({
                'status': 'success',
                'message': f'Successfully seeded database. Added {cars_seeded} cars.',
                'total_cars': Car.objects.count()
            })
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# =====================================================================
# USER PROFILES VIEWSET FOR ADMIN MANAGEMENT
# =====================================================================

class UserProfileViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Only admin role can query users
        if self.request.user.role != 'admin':
            return User.objects.none()
        return User.objects.all().order_by('-date_joined')

    def destroy(self, request, *args, **kwargs):
        if request.user.role != 'admin':
            return Response({'error': 'Only admins can manage user accounts.'}, status=status.HTTP_403_FORBIDDEN)
        
        instance = self.get_object()
        
        # Don't let admin delete their active login profile
        if instance == request.user:
            return Response({'error': 'You cannot delete your own admin account.'}, status=status.HTTP_400_BAD_REQUEST)
            
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

# =====================================================================
# BACKGROUND SCRAPING & ML TRAINING HANDLERS FOR ADMIN
# =====================================================================

import sys
import subprocess

active_processes = {
    'scrape': None,
    'train': None
}

class StartScrapeView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if request.user.role != 'admin':
            return Response({'error': 'Unauthorized access'}, status=status.HTTP_403_FORBIDDEN)

        global active_processes
        if active_processes['scrape'] and active_processes['scrape'].poll() is None:
            return Response({'status': 'running', 'message': 'Scraper is already running.'})

        log_path = os.path.join(settings.BASE_DIR, 'public', 'scraping_log.txt')
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write("Starting live Selenium scraping crawler...\n")

        script_path = os.path.join(settings.BASE_DIR, 'scraper.py')
        log_file = open(log_path, 'a', encoding='utf-8')

        try:
            proc = subprocess.Popen(
                [sys.executable, script_path],
                stdout=log_file,
                stderr=log_file,
                text=True,
                cwd=settings.BASE_DIR
            )
            active_processes['scrape'] = proc
            return Response({'status': 'started', 'message': 'Scraping started in background.'})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class StartTrainView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if request.user.role != 'admin':
            return Response({'error': 'Unauthorized access'}, status=status.HTTP_403_FORBIDDEN)

        global active_processes
        if active_processes['train'] and active_processes['train'].poll() is None:
            return Response({'status': 'running', 'message': 'ML model training is already running.'})

        log_path = os.path.join(settings.BASE_DIR, 'public', 'training_log.txt')
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write("Starting Random Forest Model Training...\n")

        script_path = os.path.join(settings.BASE_DIR, 'train_model.py')
        log_file = open(log_path, 'a', encoding='utf-8')

        try:
            proc = subprocess.Popen(
                [sys.executable, script_path],
                stdout=log_file,
                stderr=log_file,
                text=True,
                cwd=settings.BASE_DIR
            )
            active_processes['train'] = proc
            return Response({'status': 'started', 'message': 'Training started in background.'})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ReadLogsView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if request.user.role != 'admin':
            return Response({'error': 'Unauthorized access'}, status=status.HTTP_403_FORBIDDEN)

        log_type = request.query_params.get('type', 'scrape')
        filename = 'scraping_log.txt' if log_type == 'scrape' else 'training_log.txt'
        log_path = os.path.join(settings.BASE_DIR, 'public', filename)

        if not os.path.exists(log_path):
            return Response({'logs': 'No execution logs recorded yet.'})

        try:
            with open(log_path, 'r', encoding='utf-8') as f:
                logs = f.read()
            return Response({'logs': logs})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ProcessStatusView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if request.user.role != 'admin':
            return Response({'error': 'Unauthorized access'}, status=status.HTTP_403_FORBIDDEN)

        global active_processes
        
        scrape_running = active_processes['scrape'] is not None and active_processes['scrape'].poll() is None
        train_running = active_processes['train'] is not None and active_processes['train'].poll() is None

        return Response({
            'scraping': scrape_running,
            'training': train_running
        })


