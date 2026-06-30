from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction
from .models import PurchaseOrder, PurchaseOrderItem
from inventory.models import InventoryItem, StockRecord

@receiver(post_save, sender=PurchaseOrder)
def update_inventory_on_po_completion(sender, instance, created, **kwargs):
    """
    Signal receiver that updates inventory when a Purchase Order is marked as 'completed'.
    """
    # We only care about when the status becomes 'completed'.
    # 'created' is False on update. We also check if the status was changed.
    if not created and instance.status == 'completed':
        # To prevent this from running multiple times if the order is saved again
        # while already 'completed', we check if stock records for this PO already exist.
        if StockRecord.objects.filter(purchase_order=instance).exists():
            return # Stock has already been updated for this PO.

        try:
            with transaction.atomic():
                # Loop through each item in the completed purchase order
                for item in instance.items.all():
                    # Find or create the corresponding inventory item for the specific resort
                    inventory_item, created_item = InventoryItem.objects.get_or_create(
                        resort=instance.resort,
                        product_code=item.product_code,
                        defaults={'name': item.product_name, 'current_stock': 0}
                    )

                    # Update the stock level
                    inventory_item.current_stock += item.quantity
                    inventory_item.save()

                    # Create a stock record to log this transaction
                    StockRecord.objects.create(
                        item=inventory_item,
                        change=item.quantity,
                        reason='purchase',
                        purchase_order=instance,
                        notes=f"Aggiunto da buono d'ordine #{instance.id}"
                    )
        except Exception as e:
            # In a real-world scenario, you'd want more robust error handling,
            # like logging the error and maybe notifying an admin.
            print(f"Error updating inventory for PO #{instance.id}: {e}")
