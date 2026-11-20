from django.db import models


class SupplierCompany(models.Model):
    
    name = models.CharField(max_length=200, unique=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name
    
    
class Product(models.Model):
    
    supplier = models.ForeignKey(SupplierCompany, on_delete=models.PROTECT,
                                 related_name="products")
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50)
    category = models.CharField(max_length=100, blank=True)
    
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['supplier', 'code'],
                name="unique_supplier_product_code"
            )
        ]
        
    def __str__(self):
        return f"{self.name} ({self.supplier.name})"