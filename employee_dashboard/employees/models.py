from django.db import models
from django.contrib.auth.models import User

class UserTime(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField()
    day_of_week = models.CharField(max_length=10)
    start_time = models.TimeField(blank=True, null=True)
    finish_time = models.TimeField(blank=True, null=True)
    productive_hours = models.DecimalField(max_digits=4, decimal_places=2)
    target_hours = models.DecimalField(max_digits=4, decimal_places=2, default=8.00)
    comment = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-date']
        unique_together = ('user', 'date')
        indexes = [
            models.Index(fields=['user', 'date']),
        ]

    def total_hours(self):
        from datetime import datetime
        if self.start_time and self.finish_time:
            start = datetime.combine(self.date, self.start_time)
            end = datetime.combine(self.date, self.finish_time)
            return round((end - start).total_seconds() / 3600, 2)
        return None

    def __str__(self):
        return f"{self.user.username} - {self.date}"


class AccessRequest(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_reviewed = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.email})"
