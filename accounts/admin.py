from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("Business Access", {
            "fields": ("role", "supplier_company")
        }),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Business Access", {
            "fields": ("role", "supplier_company")
        }),
    )

    list_display = (
        "username",
        "role",
        "supplier_company",
        "is_staff"
    )
