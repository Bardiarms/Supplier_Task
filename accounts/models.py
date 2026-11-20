from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError


class User(AbstractUser):
    
    class Role(models.TextChoices):
        ORGANIZATION_MANAGER = "organization_manager", "Organization Manager"
        SUPPLIER_MANAGER = "supplier_manager", "Supplier Manager"
        
    role = models.CharField(
        max_length=24,
        choices=Role.choices,
        blank=True
    )
    
    supplier_company = models.ForeignKey(
        "suppliers.SupplierCompany",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="users"
    )
    
    def clean(self):
        super().clean()

        supplier_roles = [
            self.Role.SUPPLIER_MANAGER,
        ]

        if self.role in supplier_roles and not self.supplier_company_id:
            raise ValidationError({
                "supplier_company": "Supplier users must belong to a company."
            })

        if self.role == self.Role.ORGANIZATION_MANAGER and self.supplier_company_id:
            raise ValidationError({
                "supplier_company": "Organization managers cannot belong to a supplier."
            })