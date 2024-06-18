from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from address.models import ShopAddress
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone

User = get_user_model()

def product_upload_path(instance, filename):
    return f"product/{instance.product.category}/{instance.product.created}/{filename}"

class Shop(models.Model):   
    name = models.CharField(max_length=100)
    description = models.TextField()
    rate = models.DecimalField(max_digits=3, decimal_places=2, default=None, null=True, 
                               validators=[MinValueValidator(0), MaxValueValidator(5)])
    address = models.OneToOneField(ShopAddress, related_name="shop", on_delete=models.CASCADE)
    
    def __str__(self):
        return f"{self.name}"
    
class Category(models.Model):
    name = models.CharField(max_length=250)
    parent = models.ForeignKey("self", null=True, blank=True,
                               on_delete=models.CASCADE, related_name="subcategories")
    
    def __str__(self):
        return f"{self.name}"
    
class Product(models.Model):
    class Status(models.TextChoices):
        OUT_OF_STOCK = "OUT OF STOCK", "Out of stock"
        IN_STOCK = "IN STOCK", "In stock"
    
    shop = models.ManyToManyField(Shop, related_name="products")
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="products")
    name = models.CharField(max_length=100)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount = models.DecimalField(max_digits=3, decimal_places=2, default=0.0,
                                   validators=[MinValueValidator(0), MaxValueValidator(1)])
    rate = models.DecimalField(max_digits=3, decimal_places=2, default=None, null=True, 
                               validators=[MinValueValidator(0), MaxValueValidator(5)])
    status = models.CharField(max_length=50, choices=Status.choices, default=Status.OUT_OF_STOCK)
    quantity = models.PositiveIntegerField(default=0)
    updated = models.DateTimeField(auto_now=True)
    created = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name}"

    
class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="photo")
    image = models.ImageField(upload_to=product_upload_path)
    
    def __str__(self):
        return f"{self.product.name}/{self.image}"

    
class OrderProduct(models.Model):
    class Status(models.TextChoices):
        SHIPPED = "SHIPPED", "Shipped"
        PROCESSING = "PROCESSING", "Processing"
        DELIVERED = "DELIVERED", "Delivered"
        CANCELED = "CANCELED", "Canceled"
        
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="order_products")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="order_items")
    price = models.DecimalField(max_digits=7, decimal_places=2, blank=True)
    courier = models.ForeignKey(User, related_name="couriers", on_delete=models.SET_NULL,
                                null=True, limit_choices_to={"role": "COURIER"})
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.SHIPPED)
    created = models.DateTimeField(auto_now_add=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        # price с учётом скидки
        self.price = self.product.price * (1 - self.product.discount)
        # вызов ошибки, если пользователь courier не является курьером
        self.clean()
        # установка времени доставки
        if self.status == "DELIVERED" and self.delivered_at is None:
            self.delivered_at = timezone.now()
            
        super().save(*args, **kwargs)
        
    def clean(self) -> None:
        if self.courier and self.courier.role != "COURIER":
            raise ValidationError("The assigned courier must have the role 'COURIER'.")
        
    def __str__(self):
        return f"Customer: {self.customer} | Courier: {self.courier} | Product: {self.product}"