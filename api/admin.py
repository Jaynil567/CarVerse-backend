from django.contrib import admin
from .models import (
    Car,
    Inquiry,
    Order,
    UserProfile,
)

admin.site.register(Car)
admin.site.register(Inquiry)
admin.site.register(Order)
admin.site.register(UserProfile)


