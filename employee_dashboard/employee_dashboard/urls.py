from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect

def home_redirect(request):
    # ✅ Logged-in users go where they belong
    if request.user.is_authenticated:
        if request.user.is_superuser:
            # Superuser → goes to Admin Dashboard first
            return redirect('admin_user_list')
        else:
            # Normal user → goes to their timesheet dashboard
            return redirect('dashboard')
    return redirect('login')  # Not logged in → login page

urlpatterns = [
    path('', home_redirect),
    path('admin/', admin.site.urls),
    path('', include('employees.urls')),
]
