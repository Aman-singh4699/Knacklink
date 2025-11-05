from django.contrib.auth.decorators import user_passes_test, login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from datetime import datetime, timedelta
from django.utils import timezone
from datetime import timedelta
from django.contrib import messages
from django.contrib.auth.models import User
from django.http import HttpResponse
from .models import UserTime, AccessRequest
from .forms import UserTimeForm
import csv


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
            # Redirect admins to admin dashboard
            if user.is_superuser:
                return redirect('admin_user_list')
            else:
                return redirect('dashboard')
        else:
            return render(request, 'login.html', {'error': 'Invalid username or password'})

    return render(request, 'login.html')


# =======================
# 🔹 LOGOUT
# =======================
def user_logout(request):
    logout(request)
    return redirect('login')


# =======================
# 🔹 NORMAL USER DASHBOARD
# =======================
@login_required(login_url='login')
def usertime_dashboard(request):
    """
    Dashboard for logged-in user.
    Supports date filtering and validation for future/invalid ranges.
    """

    today = timezone.now().date()
    filter_active = False

    # Default to current week
    start_date = today - timedelta(days=today.weekday())
    end_date = start_date + timedelta(days=6)

    # Capture filter inputs
    start_date_str = request.GET.get("start_date")
    end_date_str = request.GET.get("end_date")

    # ✅ If filter form submitted
    if start_date_str and end_date_str:
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
            filter_active = True

            # Validation checks
            if start_date > end_date:
                messages.warning(request, "⚠️ Start date cannot be after end date.")
                return redirect("dashboard")

            if start_date > today and end_date > today:
                messages.warning(request, "⚠️ Selected range is in the future — no data available yet.")
                return redirect("dashboard")

        except ValueError:
            messages.error(request, "⚠️ Invalid date format.")
            return redirect("dashboard")

    # ✅ Query user data within range
    records = UserTime.objects.filter(
        user=request.user,
        date__range=[start_date, end_date]
    ).order_by("date")

    if filter_active and not records.exists():
        messages.info(request, "ℹ️ No entries found for the selected date range.")

    # Stats
    total_hours = sum([r.total_hours() for r in records])
    avg_hours = round(total_hours / records.count(), 2) if records else 0

    context = {
        "records": records,
        "total_hours": total_hours,
        "avg_hours": avg_hours,
        "week_start": start_date,
        "week_end": end_date,
        "filter_active": filter_active,
        "admin_view": False,   # Important for correct template section
    }

    return render(request, "dashboard.html", context)

# =======================
# 🔹 ADD WORK ENTRY
# =======================
@login_required(login_url='login')
def add_usertime(request):
    if request.method == 'POST':
        form = UserTimeForm(request.POST)

        if form.is_valid():
            entry = form.save(commit=False)
            entry.user = request.user

            # Validation
            if entry.start_time >= entry.finish_time:
                messages.error(request, "⚠️ Start time must be earlier than End time.")
                return render(request, 'usertime_form.html', {'form': form})

            entry.day_of_week = entry.date.strftime("%A")
            entry.save()
            messages.success(request, '✅ Entry added successfully!')
            return redirect('dashboard')
        else:
            messages.error(request, "Please correct the highlighted errors.")
    else:
        form = UserTimeForm()

    return render(request, 'usertime_form.html', {'form': form})


# =======================
# 🔹 ADMIN: LIST ALL EMPLOYEES
# =======================
@user_passes_test(lambda u: u.is_superuser)
def admin_user_list(request):
    employees = User.objects.filter(is_superuser=False)
    return render(request, 'dashboard.html', {'employees': employees, 'admin_view': True})


# =======================
# 🔹 ADMIN: VIEW SPECIFIC EMPLOYEE TIMESHEET
# =======================
@user_passes_test(lambda u: u.is_superuser)
def admin_user_timesheet(request, user_id):
    """
    Admin view to see a specific employee's timesheet
    with working date filters and validation.
    """
    employee = get_object_or_404(User, id=user_id)
    today = timezone.now().date()
    filter_active = False

    # Default to current week
    start_date = today - timedelta(days=today.weekday())
    end_date = start_date + timedelta(days=6)

    # Get filter inputs
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')

    if start_date_str and end_date_str:
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
            filter_active = True

            # Validation
            if start_date > end_date:
                messages.warning(request, "⚠️ Start date cannot be after end date.")
                return redirect('admin_user_timesheet', user_id=user_id)

            if start_date > today and end_date > today:
                messages.warning(request, "⚠️ Future dates selected — no data available.")
                return redirect('admin_user_timesheet', user_id=user_id)

        except ValueError:
            messages.error(request, "Invalid date format.")
            return redirect('admin_user_timesheet', user_id=user_id)

    # 🔹 Apply filter range
    records = UserTime.objects.filter(
        user=employee,
        date__range=[start_date, end_date]
    ).order_by('-date')

    if filter_active and not records.exists():
        messages.info(request, "ℹ️ No entries found for this range.")

    # 🔹 Stats
    total_hours = sum([r.total_hours() for r in records])
    avg_hours = round(total_hours / records.count(), 2) if records else 0

    context = {
        'records': records,
        'total_hours': total_hours,
        'avg_hours': avg_hours,
        'employee': employee,
        'week_start': start_date,
        'week_end': end_date,
        'filter_active': filter_active,
        'admin_view': False,  # Keeps consistent layout
    }

    return render(request, 'dashboard.html', context)

# =======================
# 🔹 ADMIN: EXPORT EMPLOYEE TIMESHEET
# =======================
@user_passes_test(lambda u: u.is_authenticated)  # ✅ Allow both admin and user
def export_employee_timesheet(request, user_id=None):
    """
    Exports a user's timesheet data.
    - Admins can export anyone’s
    - Normal users can only export their own
    """
    # Determine which user's data to export
    if user_id:
        employee = get_object_or_404(User, id=user_id)
        if not request.user.is_superuser and employee != request.user:
            return HttpResponse("Unauthorized", status=403)
    else:
        employee = request.user  # ✅ Superuser or user exporting their own data

    records = UserTime.objects.filter(user=employee)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{employee.username}_timesheet.csv"'

    writer = csv.writer(response)
    writer.writerow(['Date', 'Day', 'Start Time', 'Finish Time', 'Productive Hours', 'Target Hours', 'Comment'])

    for record in records:
        writer.writerow([
            record.date,
            record.day_of_week,
            record.start_time,
            record.finish_time,
            record.productive_hours,
            record.target_hours,
            record.comment or ''
        ])

    return response

@user_passes_test(lambda u: u.is_superuser)
def delete_user_timesheet(request):
    """
    Allows admin to delete all timesheet entries for a selected user
    after confirming their password.
    """
    users = User.objects.filter(is_superuser=False)
    if request.method == "POST":
        user_id = request.POST.get("user_id")
        password = request.POST.get("password")

        # ✅ Validate admin password
        if not request.user.check_password(password):
            messages.error(request, "❌ Incorrect admin password.")
            return redirect("delete_user_timesheet")

        # ✅ Validate user selection
        employee = get_object_or_404(User, id=user_id)
        deleted_count, _ = UserTime.objects.filter(user=employee).delete()

        if deleted_count > 0:
            messages.success(request, f"✅ Deleted {deleted_count} timesheet entries for {employee.username}.")
        else:
            messages.info(request, f"ℹ️ No timesheet entries found for {employee.username}.")

        return redirect("admin_user_list")

    return render(request, "delete_timesheet.html", {"users": users})

# =======================
# 🔹 USER ACCESS REQUEST
# =======================
def request_access(request):
    if request.method == "POST":
        name = request.POST.get('name')
        email = request.POST.get('email')
        message = request.POST.get('message', '')

        if AccessRequest.objects.filter(email=email).exists():
            messages.warning(request, "⚠️ You’ve already submitted a request. Please wait for admin approval.")
        else:
            AccessRequest.objects.create(name=name, email=email, message=message)
            messages.success(request, "✅ Your request has been submitted! The admin will contact you soon.")
            return redirect('login')

    return render(request, 'register.html')
