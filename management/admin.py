from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.db.models import F, Sum

from .models import (
    Customer, FinishedProduct, RawMaterial,
    Expense, WheatPurchase, Production, Bill, BillItem
)

# Inline for BillItem to be shown on the Bill admin page
class BillItemInline(admin.TabularInline):
    model = BillItem
    extra = 1

# Admin class for Bill with a print bill link and robust stock management
@admin.register(Bill)
class BillAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'customer', 'bill_date', 'is_paid',
        'get_subtotal_display', 'get_gst_amount_display',
        'get_grand_total_display', 'print_bill_link'
    )
    list_display_links = ('id', 'customer')
    list_filter = ('bill_date', 'is_paid')
    search_fields = ('customer__name', 'id')
    inlines = [BillItemInline]
    actions = ['mark_as_paid']

    # Method to create the HTML for the print button
    def print_bill_link(self, obj):
        url = reverse('bill_print', args=[obj.id])
        return format_html('<a class="button" href="{}" target="_blank" style="background-color:#4CAF50; color:white; padding:5px 10px; text-decoration:none; border-radius:3px;">Print Bill</a>', url)
    print_bill_link.short_description = "Print"

    # Action to mark selected bills as paid
    def mark_as_paid(self, request, queryset):
        queryset.update(is_paid=True)
    mark_as_paid.short_description = "Mark selected bills as paid"

    # Methods to display calculated fields
    def get_subtotal_display(self, obj):
        return f"₹{obj.get_subtotal()}"
    get_subtotal_display.short_description = "Subtotal"

    def get_gst_amount_display(self, obj):
        return f"₹{obj.get_gst_amount()}"
    get_gst_amount_display.short_description = "GST"

    def get_grand_total_display(self, obj):
        return f"₹{obj.get_grand_total()}"
    get_grand_total_display.short_description = "Grand Total"
    
    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        
        # We need to handle both new items and changes to existing ones.
        for formset in formsets:
            # Handle stock deduction for added or changed items
            for form in formset.save_existing_objects():
                item = form.instance
                # Deduct finished product stock
                item.product.current_stock_kg = F('current_stock_kg') - item.quantity_kg
                item.product.save()

            # Handle stock increase for deleted items
            for form in formset.deleted_forms:
                item = form.instance
                # Re-add finished product stock
                item.product.current_stock_kg = F('current_stock_kg') + item.quantity_kg
                item.product.save()

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone_number', 'email')
    search_fields = ('name', 'phone_number', 'email')

@admin.register(FinishedProduct)
class FinishedProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'current_stock_kg', 'cost_per_kg', 'mrp_per_kg', 'selling_price_per_kg')
    readonly_fields = ('current_stock_kg',)

@admin.register(RawMaterial)
class RawMaterialAdmin(admin.ModelAdmin):
    list_display = ('name', 'current_stock_kg')
    readonly_fields = ('current_stock_kg',)
    
@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('description', 'amount', 'date')
    list_filter = ('date',)
    search_fields = ('description',)

@admin.register(WheatPurchase)
class WheatPurchaseAdmin(admin.ModelAdmin):
    list_display = ('quantity_kg', 'price_per_unit', 'total_price', 'payment_mode', 'is_paid', 'purchase_date')
    list_filter = ('purchase_date', 'payment_mode', 'is_paid')
    search_fields = ('purchase_date',)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        
        # Update stock on both creation and changes
        if not change:
            # Handle new purchase
            raw_material = obj.raw_material
            raw_material.current_stock_kg = F('current_stock_kg') + obj.quantity_kg
            raw_material.save()
        else:
            # Logic for handling changes would go here if needed
            pass

@admin.register(Production)
class ProductionAdmin(admin.ModelAdmin):
    list_display = ('raw_material', 'finished_product', 'quantity_kg', 'production_date')
    list_filter = ('production_date',)
    search_fields = ('raw_material__name', 'finished_product__name')

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        
        # Update stock on both creation and changes
        if not change:
            raw_material = obj.raw_material
            finished_product = obj.finished_product
            
            raw_material.current_stock_kg = F('current_stock_kg') - (obj.quantity_kg * obj.finished_product.raw_material_ratio)
            raw_material.save()

            finished_product.current_stock_kg = F('current_stock_kg') + obj.quantity_kg
            finished_product.save()
        else:
            # Logic for handling changes would go here if needed
            pass