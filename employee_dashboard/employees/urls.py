from django.urls import path
from django.shortcuts import redirect
from . import views

urlpatterns = [
    # Redirect root (/) → login page
    path('', lambda request: redirect('login')),  # 👈 FIXES the 404

    path('login/', views.user_login, name='login'),
    path('register/', views.user_register, name='register'),
    path('dashboard/', views.usertime_dashboard, name='dashboard'),
    path('dashboard/add/', views.add_usertime, name='add_usertime'),
    path('logout/', views.user_logout, name='logout'),
]
