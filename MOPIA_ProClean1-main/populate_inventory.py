#!/usr/bin/env python
"""
Script to populate initial inventory data for MOPIA ProClean
"""
import os
import sys
import django

# Add the project directory to the Python path
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_dir)

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mopia.settings')
django.setup()

from core.models import InventoryCategory, InventoryItem

def create_categories():
    """Create inventory categories"""
    categories = [
        ('cleaning_agents', 'Cleaning Agents'),
        ('tools', 'Tools'),
        ('equipment', 'Equipment'),
    ]
    
    for category_name, display_name in categories:
        category, created = InventoryCategory.objects.get_or_create(
            name=category_name,
            defaults={'description': f'{display_name} used for cleaning services'}
        )
        if created:
            print(f"Created category: {display_name}")
        else:
            print(f"Category already exists: {display_name}")

def create_inventory_items():
    """Create initial inventory items"""
    
    # Get categories
    cleaning_agents = InventoryCategory.objects.get(name='cleaning_agents')
    tools = InventoryCategory.objects.get(name='tools')
    equipment = InventoryCategory.objects.get(name='equipment')
    
    # Cleaning Agents (Disposable)
    cleaning_items = [
        ('All-Purpose Cleaner', 'Multi-surface cleaning solution', 'liters', 50, 5, 25.00),
        ('Glass Cleaner', 'For windows and mirrors', 'liters', 20, 3, 30.00),
        ('Disinfectant', 'Antibacterial surface cleaner', 'liters', 30, 5, 45.00),
        ('Floor Cleaner', 'For mopping floors', 'liters', 40, 5, 35.00),
        ('Toilet Bowl Cleaner', 'Specialized toilet cleaner', 'liters', 15, 2, 40.00),
        ('Degreaser', 'Heavy-duty grease remover', 'liters', 10, 2, 50.00),
        ('Carpet Shampoo', 'For carpet cleaning', 'liters', 8, 1, 60.00),
        ('Wood Polish', 'For furniture care', 'liters', 5, 1, 55.00),
    ]
    
    for name, description, unit, stock, min_stock, cost in cleaning_items:
        item, created = InventoryItem.objects.get_or_create(
            category=cleaning_agents,
            name=name,
            defaults={
                'description': description,
                'unit': unit,
                'current_stock': stock,
                'minimum_stock': min_stock,
                'unit_cost': cost,
                'is_disposable': True
            }
        )
        if created:
            print(f"Created cleaning agent: {name}")
    
    # Tools (Non-disposable)
    tool_items = [
        ('Microfiber Cloths', 'Reusable cleaning cloths', 'pieces', 100, 20, 15.00),
        ('Sponges', 'Cleaning sponges', 'pieces', 50, 10, 5.00),
        ('Rubber Gloves', 'Protective gloves', 'pairs', 30, 5, 25.00),
        ('Scrub Brushes', 'Various cleaning brushes', 'pieces', 20, 5, 35.00),
        ('Squeegees', 'Window cleaning tools', 'pieces', 10, 2, 150.00),
        ('Mops', 'Floor cleaning mops', 'pieces', 15, 3, 200.00),
        ('Buckets', 'Cleaning buckets', 'pieces', 12, 3, 120.00),
        ('Spray Bottles', 'For cleaning solutions', 'pieces', 25, 5, 45.00),
        ('Dustpans', 'For collecting debris', 'pieces', 8, 2, 80.00),
        ('Toilet Brushes', 'Toilet cleaning brushes', 'pieces', 10, 2, 60.00),
    ]
    
    for name, description, unit, stock, min_stock, cost in tool_items:
        item, created = InventoryItem.objects.get_or_create(
            category=tools,
            name=name,
            defaults={
                'description': description,
                'unit': unit,
                'current_stock': stock,
                'minimum_stock': min_stock,
                'unit_cost': cost,
                'is_disposable': False
            }
        )
        if created:
            print(f"Created tool: {name}")
    
    # Equipment (Non-disposable)
    equipment_items = [
        ('Vacuum Cleaner', 'High-power vacuum cleaner', 'units', 5, 1, 15000.00),
        ('Carpet Cleaning Machine', 'Professional carpet cleaner', 'units', 2, 1, 25000.00),
        ('Floor Polisher', 'Electric floor polishing machine', 'units', 2, 1, 18000.00),
        ('Pressure Washer', 'High-pressure cleaning equipment', 'units', 1, 1, 30000.00),
        ('Steam Cleaner', 'Steam cleaning equipment', 'units', 3, 1, 12000.00),
        ('Extension Cords', 'Power extension cords', 'pieces', 8, 2, 500.00),
        ('Step Ladders', 'For high cleaning areas', 'pieces', 4, 1, 2500.00),
        ('Cleaning Carts', 'Mobile cleaning supply cart', 'pieces', 3, 1, 3500.00),
    ]
    
    for name, description, unit, stock, min_stock, cost in equipment_items:
        item, created = InventoryItem.objects.get_or_create(
            category=equipment,
            name=name,
            defaults={
                'description': description,
                'unit': unit,
                'current_stock': stock,
                'minimum_stock': min_stock,
                'unit_cost': cost,
                'is_disposable': False
            }
        )
        if created:
            print(f"Created equipment: {name}")

def main():
    print("Populating MOPIA ProClean inventory...")
    print("=" * 50)
    
    # Create categories first
    create_categories()
    print()
    
    # Create inventory items
    create_inventory_items()
    print()
    
    # Summary
    total_items = InventoryItem.objects.count()
    total_value = sum(item.stock_value for item in InventoryItem.objects.all())
    
    print("=" * 50)
    print("INVENTORY SUMMARY")
    print("=" * 50)
    print(f"Total Items: {total_items}")
    print(f"Total Inventory Value: ₱{total_value:,.2f}")
    
    print("\nInventory by Category:")
    for category in InventoryCategory.objects.all():
        items_count = category.items.count()
        category_value = sum(item.stock_value for item in category.items.all())
        print(f"  {category.get_name_display()}: {items_count} items (₱{category_value:,.2f})")
    
    print("\nInventory setup completed successfully!")

if __name__ == '__main__':
    main()
