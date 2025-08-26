from django.db import models
from django.db.models import F, Sum
from django.utils import timezone
from decimal import Decimal

# Helper function to get the first RawMaterial ID
def get_first_raw_material_pk():
    try:
        return RawMaterial.objects.first().pk
    except RawMaterial.DoesNotExist:
        return None

# Helper function to get the first FinishedProduct ID
def get_first_finished_product_pk():
    try:
        return FinishedProduct.objects.first().pk
    except FinishedProduct.DoesNotExist:
        return None

class RawMaterial(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Raw Material Name")
    current_stock_kg = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name="Current Stock (Kg)"
    )

    def __str__(self):
        return f"{self.name} ({self.current_stock_kg} kg)"

    class Meta:
        verbose_name = "Raw Material"
        verbose_name_plural = "Raw Materials"

class WheatPurchase(models.Model):
    PAYMENT_MODES = [
        ('Cash', 'Cash'),
        ('Credit', 'Credit'),
    ]
    raw_material = models.ForeignKey(
        RawMaterial, on_delete=models.CASCADE, default=get_first_raw_material_pk, verbose_name="Raw Material"
    )
    quantity_kg = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Quantity (Kg)")
    price_per_unit = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Price Per Kg")
    other_expenses = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name="Other Expenses"
    )
    payment_mode = models.CharField(max_length=6, choices=PAYMENT_MODES, verbose_name="Payment Mode")
    purchase_date = models.DateTimeField(auto_now_add=True, verbose_name="Purchase Date")
    is_paid = models.BooleanField(default=False, verbose_name="Payment Status")

    @property
    def total_price(self):
        return self.quantity_kg * self.price_per_unit

    def __str__(self):
        return f"Purchase of {self.quantity_kg} kg on {self.purchase_date.date()}"

    class Meta:
        verbose_name = "Wheat Purchase"
        verbose_name_plural = "Wheat Purchases"
        ordering = ['-purchase_date']

class FinishedProduct(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Product Name")
    current_stock_kg = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name="Current Stock (Kg)"
    )
    cost_per_kg = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name="Cost Per Kg"
    )
    mrp_per_kg = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name="MRP Per Kg"
    )
    selling_price_per_kg = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name="Selling Price Per Kg"
    )
    raw_material_ratio = models.DecimalField(
        max_digits=5, decimal_places=2, default=1, verbose_name="Raw Material Used (Per Kg)"
    )

    def __str__(self):
        return f"{self.name} ({self.current_stock_kg} kg)"

    class Meta:
        verbose_name = "Finished Product"
        verbose_name_plural = "Finished Products"

class Production(models.Model):
    production_date = models.DateTimeField(default=timezone.now, verbose_name="Production Date")
    raw_material = models.ForeignKey(
        RawMaterial, on_delete=models.CASCADE, default=get_first_raw_material_pk, verbose_name="Raw Material"
    )
    finished_product = models.ForeignKey(
        FinishedProduct, on_delete=models.CASCADE, default=get_first_finished_product_pk, verbose_name="Finished Product"
    )
    quantity_kg = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Quantity Produced (Kg)")

    def __str__(self):
        return f"Produced {self.quantity_kg} kg of {self.finished_product.name}"

    class Meta:
        verbose_name = "Production Entry"
        verbose_name_plural = "Production Entries"
        ordering = ['-production_date']

class Customer(models.Model):
    name = models.CharField(max_length=200, verbose_name="Customer Name")
    address = models.TextField(blank=True, null=True, verbose_name="Address")
    phone_number = models.CharField(max_length=15, unique=True, verbose_name="Phone Number")
    email = models.EmailField(blank=True, null=True, verbose_name="Email")
    
    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Customer"
        verbose_name_plural = "Customers"

class Bill(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, verbose_name="Customer")
    bill_date = models.DateTimeField(auto_now_add=True, verbose_name="Bill Date")
    is_paid = models.BooleanField(default=False, verbose_name="Payment Status")
    other_expenses = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Other Expenses")
    has_gst = models.BooleanField(default=True, verbose_name="Include GST")

    def get_subtotal(self):
        subtotal = self.items.aggregate(total=Sum(F('quantity_kg') * F('price_per_unit'))).get('total')
        if subtotal is None:
            return Decimal('0.00')
        return subtotal

    def get_gst_amount(self):
        if self.has_gst:
            return self.get_subtotal() * Decimal('0.18')
        return Decimal('0.00')

    def get_grand_total(self):
        return self.get_subtotal() + self.get_gst_amount() + self.other_expenses

    def __str__(self):
        return f"Bill for {self.customer.name if self.customer else 'N/A'} on {self.bill_date.date()}"

    class Meta:
        verbose_name = "Sales Bill"
        verbose_name_plural = "Sales Bills"
        ordering = ['-bill_date']

class BillItem(models.Model):
    bill = models.ForeignKey(Bill, on_delete=models.CASCADE, related_name='items', verbose_name="Sales Bill")
    product = models.ForeignKey(
        FinishedProduct, on_delete=models.CASCADE, default=get_first_finished_product_pk, verbose_name="Product"
    )
    quantity_kg = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Quantity (Kg)")
    price_per_unit = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Price Per Unit")
    has_stock_deducted = models.BooleanField(default=False)

    @property
    def total_price(self):
        return self.quantity_kg * self.price_per_unit
        
    def __str__(self):
        return f"{self.quantity_kg} kg of {self.product.name}"

    class Meta:
        verbose_name = "Bill Item"
        verbose_name_plural = "Bill Items"

class Expense(models.Model):
    description = models.CharField(max_length=255, verbose_name="Description")
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Amount")
    date = models.DateTimeField(auto_now_add=True, verbose_name="Date")
    
    def __str__(self):
        return f"{self.description} - {self.amount}"
    
    class Meta:
        verbose_name = "Other Expense"
        verbose_name_plural = "Other Expenses"
        ordering = ['-date']