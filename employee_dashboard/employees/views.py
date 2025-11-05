from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta
from .models import UserTime
from .forms import UserTimeForm
from django.contrib import messages
from django.contrib.auth.models import User  # 👈 REQUIRED IMPORT for user registration


# =======================
# 🔹 LOGIN VIEW
# =======================
def user_login(request):
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('dashboard')
        else:
            return render(request, 'login.html', {'error': 'Invalid username or password'})

    return render(request, 'login.html')


# =======================
# 🔹 DASHBOARD VIEW
# =======================
@login_required(login_url='login')
def usertime_dashboard(request):
    today = timezone.now().date()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    records = UserTime.objects.filter(user=request.user, date__range=[week_start, week_end])
    total_hours = sum([r.total_hours() for r in records])
    avg_hours = round(total_hours / records.count(), 2) if records else 0

    context = {
        'records': records,
        'total_hours': total_hours,
        'avg_hours': avg_hours,
        'week_start': week_start,
        'week_end': week_end,
    }
    return render(request, 'dashboard.html', context)


# =======================
# 🔹 ADD WORK ENTRY
# =======================
@login_required(login_url='login')
def add_usertime(request):
    """
    Handles adding a new working hours entry for the logged-in user.
    Includes backend validation and user feedback messages.
    """
    if request.method == 'POST':
        form = UserTimeForm(request.POST)

        if form.is_valid():
            entry = form.save(commit=False)
            entry.user = request.user

            # Validate start and finish times
            if entry.start_time >= entry.finish_time:
                messages.error(request, "⚠️ Start time must be earlier than End time.")
                return render(request, 'usertime_form.html', {'form': form})

            entry.day_of_week = entry.date.strftime("%A")
            entry.save()

            messages.success(request, '✅ Entry added successfully!')
            return redirect('dashboard')

        else:
            messages.error(request, "Please correct the highlighted errors and try again.")

    else:
        form = UserTimeForm()

    return render(request, 'usertime_form.html', {'form': form})
# =======================
# 🔹 LOGOUT
# =======================
def user_logout(request):
    logout(request)
    return redirect('login')


# =======================
# 🔹 REGISTER VIEW
# =======================
def user_register(request):
    if request.method == "POST":
        username = request.POST.get('username')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')

        if password1 != password2:
            messages.error(request, "❌ Passwords do not match.")
        elif User.objects.filter(username=username).exists():
            messages.error(request, "⚠️ Username already exists.")
        else:
            user = User.objects.create_user(username=username, email=email, password=password1)
            user.save()
            messages.success(request, "✅ Account created successfully! Please log in.")
            return redirect('login')

    return render(request, 'register.html')

