from django.contrib import admin
from .models import SupplierCompany, Product


@admin.register(SupplierCompany)
class SupplierCompanyAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "created_at")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "code", "supplier")
    list_filter = ("supplier",)
    search_fields = ("name", "code")
