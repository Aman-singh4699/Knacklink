# Use official Python image
FROM python:3.12-slim

# Set work directory
WORKDIR /app

# Copy dependencies
COPY ../requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY .. /app/

# Move into Django project directory
WORKDIR /app/employee_dashboard

# Collect static files safely
RUN python manage.py collectstatic --noinput || true

# Expose port
EXPOSE 8000

# ✅ Start Django using Gunicorn
CMD ["gunicorn", "employee_dashboard.wsgi:application", "--bind", "0.0.0.0:8000"]
