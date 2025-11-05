from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta
from .models import UserTime
from .forms import UserTimeForm

from django.contrib.auth import logout
from django.shortcuts import redirect

def user_login(request):
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('dashboard')  # keep as 'dashboard'
        else:
            return render(request, 'login.html', {'error': 'Invalid credentials'})
    return render(request, 'login.html')


@login_required
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


@login_required
def add_usertime(request):
    if request.method == 'POST':
        form = UserTimeForm(request.POST)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.user = request.user
            entry.day_of_week = entry.date.strftime("%A")
            entry.save()
            return redirect('dashboard')  # changed from usertime_dashboard
    else:
        form = UserTimeForm()
    return render(request, 'usertime_form.html', {'form': form})


def user_logout(request):
    logout(request)
    return redirect('login')