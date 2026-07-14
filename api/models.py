from django.db import models
from django.contrib.auth.models import AbstractUser

class UserProfile(AbstractUser):
    ROLE_CHOICES = (
        ('buyer', 'Buyer'),
        ('seller', 'Seller'),
        ('admin', 'Admin'),
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='buyer')
    phone = models.CharField(max_length=15, blank=True, null=True)
    location = models.CharField(max_length=100, default='Ahmedabad')

    def __str__(self):
        return f"{self.username} ({self.role})"

class Car(models.Model):
    STATUS_CHOICES = (
        ('available', 'Available'),
        ('pending', 'Pending'),
        ('sold', 'Sold'),
    )
    
    name = models.CharField(max_length=200)
    brand = models.CharField(max_length=100, blank=True, null=True)
    model = models.CharField(max_length=100, blank=True, null=True)
    year = models.IntegerField()
    km = models.IntegerField()
    fuel_type = models.CharField(max_length=50)
    transmission = models.CharField(max_length=50)
    owners = models.CharField(max_length=50)
    color = models.CharField(max_length=50)
    engine_capacity = models.IntegerField(blank=True, null=True)
    mileage = models.FloatField(blank=True, null=True)
    seating_capacity = models.IntegerField(default=5)
    
    price = models.FloatField()  # In Lakhs
    predicted_price = models.FloatField(blank=True, null=True)  # Valuation from ML model
    image = models.CharField(max_length=1000, blank=True, null=True)  # URL or path
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='available')
    seller = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='cars', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.year} - Rs. {self.price}L"

class Inquiry(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('contacted', 'Contacted'),
        ('closed', 'Closed'),
    )
    car = models.ForeignKey(Car, on_delete=models.CASCADE, related_name='inquiries')
    buyer = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='sent_inquiries')
    message = models.TextField()
    phone = models.CharField(max_length=15)
    email = models.EmailField()
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Inquiry on {self.car.name} by {self.buyer.username}"

class Order(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('completed', 'Completed'),
    )
    car = models.ForeignKey(Car, on_delete=models.CASCADE, related_name='orders')
    buyer = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='orders')
    price = models.FloatField()
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='completed')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order for {self.car.name} by {self.buyer.username} (Rs. {self.price}L)"
