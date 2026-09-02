from django.apps import apps
from django.db import connection, DatabaseError
from django.utils.timezone import now, timedelta
from smart_campus.users.models import User
from .models import Activity

def is_model_available(app_label, model_name):
    try:
        if not apps.is_installed(app_label):
            return None
        model = apps.get_model(app_label, model_name)
        table_name = model._meta.db_table
        if table_name in connection.introspection.table_names():
            return model
    except (LookupError, ValueError, DatabaseError):
        pass
    return None

def get_modules_info():
    return {
        "assets": {
            "name": "Assets Management",
            "available": is_model_available("assets", "Asset") is not None,
            "app_label": "assets",
            "model_name": "Asset",
        },
        "inventory": {
            "name": "Inventory Management",
            "available": is_model_available("inventory", "InventoryItem") is not None,
            "app_label": "inventory",
            "model_name": "InventoryItem",
        },
        "complaints": {
            "name": "Complaints & Maintenance",
            "available": is_model_available("complaints", "Complaint") is not None,
            "app_label": "complaints",
            "model_name": "Complaint",
        },
    }

def log_activity(user, activity_type, title, description, status="", user_name="", timestamp=None):
    """
    Utility function to log an activity in the central dashboard Activity table.
    """
    if timestamp is None:
        timestamp = now()
    
    name = user_name
    if user:
        name = user.name or user.username
        
    return Activity.objects.create(
        user=user,
        user_name=name,
        activity_type=activity_type,
        title=title,
        description=description,
        status=status,
        timestamp=timestamp
    )

def seed_mock_activities():
    """
    Populates the database with some realistic activities for demonstration/testing.
    """
    # Check if activities already exist
    if Activity.objects.exists():
        return
        
    # Get or create a default student
    student, _ = User.objects.get_or_create(
        username="student1",
        defaults={
            "email": "student1@campus.edu",
            "name": "John Student"
        }
    )
    if not student.has_usable_password():
        student.set_password("securepassword123")
        student.save()

    # Get or create a default admin/staff
    admin, _ = User.objects.get_or_create(
        username="admin1",
        defaults={
            "email": "admin1@campus.edu",
            "name": "Alice Admin",
            "is_staff": True,
            "is_superuser": True
        }
    )
    if not admin.has_usable_password():
        admin.set_password("securepassword123")
        admin.save()
        
    base_time = now()
    
    # 1. Student complaints
    log_activity(
        student, "COMPLAINT", 
        "Water leakage in Hostel Block C restroom", 
        "Water is dripping constantly from the flush tank in the second-floor restroom.",
        "Pending", timestamp=base_time - timedelta(hours=2)
    )
    log_activity(
        student, "COMPLAINT", 
        "Library Wi-Fi connection issues", 
        "Connection frequently drops in the reading hall section.",
        "Resolved", timestamp=base_time - timedelta(days=2)
    )
    log_activity(
        student, "COMPLAINT", 
        "Smart board in Lecture Hall 204 not turning on", 
        "Unable to start the board, power indicator is flashing red.",
        "In Progress", timestamp=base_time - timedelta(days=1)
    )
    
    # 2. General campus complaints (other students)
    log_activity(
        None, "COMPLAINT",
        "Cafeteria air conditioner servicing",
        "The central AC unit in dining hall A is blowing hot air.",
        "Resolved", user_name="Robert Smith", timestamp=base_time - timedelta(days=5)
    )
    log_activity(
        None, "COMPLAINT",
        "Gym treadmill console display broken",
        "Treadmill #3 display does not power up.",
        "Pending", user_name="Emma Watson", timestamp=base_time - timedelta(hours=12)
    )
    
    # 3. Assets
    log_activity(
        admin, "ASSET",
        "Registered 15 new HP EliteDesk desktops",
        "Added to the new Computer Lab 3 in Block A.",
        "Active", timestamp=base_time - timedelta(days=4)
    )
    log_activity(
        admin, "ASSET",
        "Asset marked for maintenance: Projector Block B-10",
        "Sent projector from Room 102 to repair for bulb replacement.",
        "Maintenance", timestamp=base_time - timedelta(days=3)
    )
    log_activity(
        admin, "ASSET",
        "Registered new Canon Laser Printer",
        "Installed in the Administration building room 12.",
        "Active", timestamp=base_time - timedelta(days=8)
    )
    
    # 4. Inventory
    log_activity(
        admin, "INVENTORY",
        "Low stock warning: Dry erase markers (Blue/Black)",
        "Stock level dropped below reorder level (12 units remaining).",
        "Low Stock", timestamp=base_time - timedelta(hours=4)
    )
    log_activity(
        admin, "INVENTORY",
        "Stock updated: A4 Xerox Paper reorder received",
        "Added 50 boxes of 80gsm paper to central store.",
        "Active", timestamp=base_time - timedelta(days=1)
    )
    log_activity(
        admin, "INVENTORY",
        "Low stock warning: LED Bulbs 15W",
        "Only 5 bulbs remaining in inventory.",
        "Low Stock", timestamp=base_time - timedelta(days=3)
    )
    
    # 5. Maintenance / System
    log_activity(
        admin, "MAINTENANCE",
        "Routine fire extinguisher check complete",
        "Inspected all 45 fire extinguishers across Hostel Block A and B.",
        "Resolved", timestamp=base_time - timedelta(days=2)
    )
    log_activity(
        admin, "MAINTENANCE",
        "Weekly generator inspection scheduled",
        "Review backup fuel levels and engine spark plugs.",
        "Pending", timestamp=base_time - timedelta(days=1)
    )
    log_activity(
        admin, "SYSTEM",
        "Database automatic backup succeeded",
        "Nightly database snapshot exported to secure S3 storage.",
        "Active", timestamp=base_time - timedelta(hours=8)
    )

def get_assets_metrics(filters=None):
    # Total, Active, Maintenance based on Activity model
    assets_qs = Activity.objects.filter(activity_type='ASSET')
    
    if filters and filters.get("start_date"):
        assets_qs = assets_qs.filter(timestamp__gte=filters["start_date"])
        
    total = assets_qs.count()
    active = assets_qs.filter(status='Active').count()
    maintenance = assets_qs.filter(status='Maintenance').count()
    
    return {
        "total": total,
        "active": active,
        "maintenance": maintenance
    }

def get_inventory_metrics(filters=None):
    inv_qs = Activity.objects.filter(activity_type='INVENTORY')
    
    if filters and filters.get("start_date"):
        inv_qs = inv_qs.filter(timestamp__gte=filters["start_date"])
        
    total = inv_qs.count()
    low_stock = inv_qs.filter(status='Low Stock').count()
    
    return {
        "total": total,
        "low_stock": low_stock
    }

def get_complaints_metrics(user=None, filters=None):
    complaint_qs = Activity.objects.filter(activity_type__in=['COMPLAINT', 'MAINTENANCE'])
    
    if user:
        complaint_qs = complaint_qs.filter(user=user)
        
    if filters:
        if filters.get("start_date"):
            complaint_qs = complaint_qs.filter(timestamp__gte=filters["start_date"])
        if filters.get("status") and filters.get("status") != "all":
            # Map frontend statuses
            status_map = {
                "pending": "Pending",
                "in_progress": "In Progress",
                "resolved": "Resolved"
            }
            mapped_status = status_map.get(filters["status"].lower(), filters["status"])
            complaint_qs = complaint_qs.filter(status__iexact=mapped_status)
            
    total = complaint_qs.count()
    pending = complaint_qs.filter(status__iexact='Pending').count()
    in_progress = complaint_qs.filter(status__iexact='In Progress').count()
    resolved = complaint_qs.filter(status__iexact='Resolved').count()
    
    return {
        "total": total,
        "pending": pending,
        "in_progress": in_progress,
        "resolved": resolved
    }
