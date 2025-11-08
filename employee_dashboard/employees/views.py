from django.contrib.auth.decorators import user_passes_test, login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from datetime import datetime, timedelta
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth.models import User
from django.http import HttpResponse, JsonResponse
from .models import UserTime, AccessRequest
from .forms import UserTimeForm
from django.db import IntegrityError
import csv


# ---------------------------
# Helper: Date range generator
# ---------------------------
def daterange(start_date, end_date):
    cur = start_date
    while cur <= end_date:
        yield cur
        cur += timedelta(days=1)


# ---------------------------
# LOGIN / LOGOUT
# ---------------------------
def user_login(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            if user.is_superuser:
                return redirect("admin_user_list")
            return redirect("dashboard")
        else:
            return render(request, "login.html", {"error": "Invalid username or password"})

    return render(request, "login.html")


def user_logout(request):
    logout(request)
    return redirect("login")


# ---------------------------
# USER DASHBOARD (Weekly editable)
# ---------------------------
@login_required(login_url='login')
def dashboard(request):
    """
    Editable weekly dashboard.
    Auto-refreshes for new week (Mon-Sun).
    Allows AJAX saving of daily productive hours.
    Works correctly with date filter.
    """
    today = timezone.now().date()

    # --- GET filter parameters ---
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')

    # Default: current week (Mon–Sun)
    if not start_date_str or not end_date_str:
        start_date = today - timedelta(days=today.weekday())  # Monday
        end_date = start_date + timedelta(days=6)              # Sunday
        filter_active = False
    else:
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
            filter_active = True
        except ValueError:
            messages.error(request, "⚠️ Invalid date format.")
            return redirect("dashboard")

    # --- POST: Save entries ---
    if request.method == "POST":
        changed, errors = 0, []
        for d in daterange(start_date, end_date):
            val = request.POST.get(f"hours_{d.isoformat()}")
            if not val:
                continue
            try:
                hours = float(val)
            except ValueError:
                continue

            ut, created = UserTime.objects.get_or_create(
                user=request.user,
                date=d,
                defaults={
                    "day_of_week": d.strftime("%A"),
                    "productive_hours": hours,
                    "start_time": timezone.now().time(),
                    "finish_time": timezone.now().time(),
                    "target_hours": 8,
                    "comment": "",
                },
            )
            if not created:
                ut.productive_hours = hours
                ut.day_of_week = d.strftime("%A")
                ut.save()
            changed += 1

        # AJAX response
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"success": True, "message": f"✅ Saved {changed} entries!"})

        messages.success(request, f"✅ Saved {changed} entries successfully!")
        return redirect(
            f"/dashboard/?start_date={start_date.isoformat()}&end_date={end_date.isoformat()}"
        )

    # --- GET: Display records ---
    records_qs = UserTime.objects.filter(
        user=request.user, date__range=[start_date, end_date]
    ).order_by("date")

    records = {ut.date: float(ut.productive_hours or 0) for ut in records_qs}
    date_list = [
        start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1)
    ]
    total_hours = round(sum(records.get(d, 0) for d in date_list), 2)

    context = {
        "records": records,
        "date_list": date_list,
        "start_date": start_date,
        "end_date": end_date,
        "filter_active": filter_active,
        "total_hours": total_hours,
        "admin_view": False,
    }
    return render(request, "dashboard.html", context)


# ---------------------------
# ADMIN - List employees
# ---------------------------
@user_passes_test(lambda u: u.is_superuser)
def admin_user_list(request):
    employees = User.objects.filter(is_superuser=False).order_by("username")

    context = {
        "admin_view": True,
        "employees": employees,
        "start_date": timezone.now().date(),
        "end_date": timezone.now().date(),
        "filter_active": False,
        "records": {},
        "date_list": [],
        "total_hours": 0,
    }
    return render(request, "dashboard.html", context)


# ---------------------------
# ADMIN - Employee's timesheet
# ---------------------------
@user_passes_test(lambda u: u.is_superuser)
def admin_user_timesheet(request, user_id):
    employee = get_object_or_404(User, id=user_id)
    today = timezone.now().date()

    start_date_str = request.GET.get("start_date")
    end_date_str = request.GET.get("end_date")

    if not start_date_str or not end_date_str:
        start_date = today - timedelta(days=today.weekday())
        end_date = start_date + timedelta(days=6)
        filter_active = False
    else:
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
            filter_active = True
        except ValueError:
            messages.error(request, "Invalid date format.")
            return redirect("admin_user_timesheet", user_id=user_id)

    records_qs = UserTime.objects.filter(user=employee, date__range=[start_date, end_date])
    records = {ut.date: float(ut.productive_hours or 0) for ut in records_qs}

    date_list = [start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1)]
    total_hours = round(sum(records.get(d, 0) for d in date_list), 2)

    context = {
        "employee": employee,
        "records": records,
        "date_list": date_list,
        "start_date": start_date,
        "end_date": end_date,
        "filter_active": filter_active,
        "total_hours": total_hours,
        "admin_view": False,
    }
    return render(request, "dashboard.html", context)


# ---------------------------
# EXPORT CSV (user + admin)
# ---------------------------
@user_passes_test(lambda u: u.is_authenticated)
def export_employee_timesheet(request, user_id=None):
    """Exports filtered timesheet for user or employee (admin)."""
    if user_id:
        employee = get_object_or_404(User, id=user_id)
        if not request.user.is_superuser and employee != request.user:
            return HttpResponse("Unauthorized", status=403)
    else:
        employee = request.user

    start_date_str = request.GET.get("start_date")
    end_date_str = request.GET.get("end_date")

    try:
        if start_date_str and end_date_str:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
            qs = UserTime.objects.filter(user=employee, date__range=[start_date, end_date]).order_by("date")
            filename_range = f"{start_date.isoformat()}_to_{end_date.isoformat()}"
        else:
            qs = UserTime.objects.filter(user=employee).order_by("date")
            filename_range = "all"
    except ValueError:
        return HttpResponse("Invalid date format", status=400)

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = (
        f'attachment; filename="{employee.username}_timesheet_{filename_range}.csv"'
    )

    writer = csv.writer(response)
    writer.writerow(["Date", "Day", "Productive Hours", "Target Hours", "Comment"])
    for r in qs:
        writer.writerow([r.date.isoformat(), r.day_of_week, r.productive_hours, r.target_hours, r.comment or ""])

    return response


# ---------------------------
# ADMIN - Delete user timesheet
# ---------------------------
@user_passes_test(lambda u: u.is_superuser)
def delete_user_timesheet(request):
    users = User.objects.filter(is_superuser=False)
    if request.method == "POST":
        user_id = request.POST.get("user_id")
        password = request.POST.get("password")

        if not request.user.check_password(password):
            messages.error(request, "❌ Incorrect admin password.")
            return redirect("delete_user_timesheet")

        employee = get_object_or_404(User, id=user_id)
        deleted_count, _ = UserTime.objects.filter(user=employee).delete()
        messages.success(request, f"✅ Deleted {deleted_count} timesheet entries for {employee.username}.")
        return redirect("admin_user_list")

    return render(request, "delete_timesheet.html", {"users": users})


# ---------------------------
# ACCESS REQUEST (Register page)
# ---------------------------
def request_access(request):
    if request.method == "POST":
        name = request.POST.get("name")
        email = request.POST.get("email")
        message = request.POST.get("message", "")

        if AccessRequest.objects.filter(email=email).exists():
            messages.warning(request, "⚠️ You’ve already submitted a request.")
        else:
            AccessRequest.objects.create(name=name, email=email, message=message)
            messages.success(request, "✅ Your request has been submitted! The admin will contact you soon.")
            return redirect("login")

    return render(request, "register.html")
