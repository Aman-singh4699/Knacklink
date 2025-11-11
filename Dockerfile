# Use official Python image
FROM python:3.12-slim

# Set work directory
WORKDIR /app

# Copy dependencies
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy all project files
COPY . /app/

# Set working directory to where manage.py lives
WORKDIR /app/employee_dashboard

# Collect static files
RUN python manage.py collectstatic --noinput

# Expose port for Railway
EXPOSE 8000

# Start Django using Gunicorn
CMD ["gunicorn", "employee_dashboard.wsgi:application", "--bind", "0.0.0.0:8000"]
