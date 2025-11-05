from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('dashboard/', views.usertime_dashboard, name='dashboard'),
    path('dashboard/add/', views.add_usertime, name='add_usertime'),

    # Admin Panel
    path('admin-dashboard/', views.admin_user_list, name='admin_user_list'),
    path('admin-dashboard/<int:user_id>/', views.admin_user_timesheet, name='admin_user_timesheet'),

    # ✅ Two paths for exporting
    path('admin-dashboard/<int:user_id>/export/', views.export_employee_timesheet, name='export_employee_timesheet'),
    path('dashboard/export/', views.export_employee_timesheet, name='export_self_timesheet'),

    # ✅ Delete feature
    path('admin-dashboard/delete-timesheet/', views.delete_user_timesheet, name='delete_user_timesheet'),

    # Access Request
    path('request-access/', views.request_access, name='request_access'),
]
