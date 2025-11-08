from django.contrib import admin
from django.contrib.auth.models import User, Group
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import ReadOnlyPasswordHashField, AdminPasswordChangeForm
from django import forms
from .models import UserTime, AccessRequest


# 🚫 Hide Groups model completely from admin
try:
    admin.site.unregister(Group)
except admin.sites.NotRegistered:
    pass


# ========================
# Custom simplified User forms
# ========================
class CustomUserCreationForm(forms.ModelForm):
    password1 = forms.CharField(label='Password', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Confirm Password', widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ['username', 'email', 'is_staff', 'is_superuser', 'is_active']

    def clean_password2(self):
        pw1 = self.cleaned_data.get("password1")
        pw2 = self.cleaned_data.get("password2")
        if pw1 and pw2 and pw1 != pw2:
            raise forms.ValidationError("Passwords don't match")
        return pw2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class CustomUserChangeForm(forms.ModelForm):
    """Minimal edit form with proper password field (shows link)."""
    password = ReadOnlyPasswordHashField(
        label="Password",
        help_text=(
            "Raw passwords are not stored, so there is no way to see this user's password, "
            "but you can change the password using "
            "<a href=\"../password/\">this form</a>."
        ),
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'is_active', 'is_staff', 'is_superuser']


# ========================
# Clean User Admin (no extra perms, works perfectly)
# ========================
class CustomUserAdmin(BaseUserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    change_password_form = AdminPasswordChangeForm  # ✅ Correct built-in password change form

    list_display = ['username', 'email', 'is_staff', 'is_superuser', 'is_active']
    search_fields = ['username', 'email']
    list_filter = ['is_staff', 'is_superuser', 'is_active']
    ordering = ['username']

    fieldsets = (
        (None, {'fields': ('username', 'email', 'password')}),
        ('Account Status', {'fields': ('is_active', 'is_staff', 'is_superuser')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'username', 'email', 'password1', 'password2',
                'is_active', 'is_staff', 'is_superuser'
            ),
        }),
    )

    # ✅ Remove permission fields dynamically
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        for field in ['groups', 'user_permissions']:
            if field in form.base_fields:
                form.base_fields.pop(field)
        return form


# ✅ Unregister default User and re-register
try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass

admin.site.register(User, CustomUserAdmin)


# ========================
# Access Request Admin
# ========================
@admin.register(AccessRequest)
class AccessRequestAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'message')
    search_fields = ('name', 'email')
    ordering = ('-id',)
    list_per_page = 20


# ========================
# User Time Admin
# ========================
@admin.register(UserTime)
class UserTimeAdmin(admin.ModelAdmin):
    list_display = ('user', 'date', 'day_of_week', 'productive_hours', 'target_hours')
    list_filter = ('user', 'date')
    search_fields = ('user__username',)
    ordering = ('-date',)
    list_per_page = 25
