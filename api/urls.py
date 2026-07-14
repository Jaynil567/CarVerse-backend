from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    RegisterView, LoginView, UserProfileView,
    CarViewSet, PredictPriceView, InquiryViewSet,
    OrderViewSet, FilterOptionsView, DatabaseSeederView,
    UserProfileViewSet, StartScrapeView, StartTrainView,
    ReadLogsView, ProcessStatusView
)

router = DefaultRouter()
router.register(r'cars', CarViewSet, basename='car')
router.register(r'inquiries', InquiryViewSet, basename='inquiry')
router.register(r'orders', OrderViewSet, basename='order')
router.register(r'users', UserProfileViewSet, basename='user')

urlpatterns = [
    # Auth endpoints
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/user/', UserProfileView.as_view(), name='user-profile'),
    
    # ML Estimation
    path('cars/predict-price/', PredictPriceView.as_view(), name='predict-price'),
    
    # Dropdowns & Filters
    path('options/', FilterOptionsView.as_view(), name='filter-options'),
    
    # Database Seed Utility
    path('seed/', DatabaseSeederView.as_view(), name='db-seed'),
    
    # Background scraping and training triggers for Admin Panel
    path('admin/start-scrape/', StartScrapeView.as_view(), name='start-scrape'),
    path('admin/start-train/', StartTrainView.as_view(), name='start-train'),
    path('admin/logs/', ReadLogsView.as_view(), name='admin-logs'),
    path('admin/status/', ProcessStatusView.as_view(), name='admin-status'),
    
    # Router ViewSets
    path('', include(router.urls)),
]

