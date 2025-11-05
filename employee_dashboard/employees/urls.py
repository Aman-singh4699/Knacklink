from django.urls import path
from . import views

urlpatterns = [
    path('', views.user_login, name='login'),
    path('dashboard/', views.usertime_dashboard, name='dashboard'),
    path('dashboard/add/', views.add_usertime, name='add_usertime'),
    path('logout/', views.user_logout, name='logout'),
]
