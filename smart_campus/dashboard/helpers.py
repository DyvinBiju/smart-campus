from django.apps import apps
from django.db import connection, DatabaseError
from django.utils.timezone import now, timedelta
from smart_campus.users.models import User
from .models import Activity

def is_model_available(app_label, model_name):
    try:
        clean_label = app_label.split(".")[-1]
        model = apps.get_model(clean_label, model_name)
        if model:
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
    AssetModel = is_model_available("assets", "Asset")
    if AssetModel and AssetModel.objects.exists():
        try:
            total = AssetModel.objects.count()
            active = AssetModel.objects.filter(status__iexact="ACTIVE").count()
            maintenance = AssetModel.objects.filter(status__in=["UNDER_MAINTENANCE", "DAMAGED"]).count()
            return {
                "total": total,
                "active": active,
                "maintenance": maintenance
            }
        except DatabaseError:
            pass

    # Fallback to Activity model based metrics
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
    InventoryItemModel = is_model_available("inventory", "InventoryItem")
    if InventoryItemModel and InventoryItemModel.objects.exists():
        try:
            total = InventoryItemModel.objects.count()
            # Low stock items where quantity <= minimum_quantity
            from django.db.models import F
            low_stock = InventoryItemModel.objects.filter(quantity__lte=F("minimum_quantity")).count()
            return {
                "total": total,
                "low_stock": low_stock
            }
        except DatabaseError:
            pass

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
    ComplaintModel = is_model_available("complaints", "Complaint")
    if ComplaintModel and ComplaintModel.objects.exists():
        try:
            qs = ComplaintModel.objects.all()
            if user and not (user.is_superuser or user.role == User.Role.ADMIN or user.is_staff):
                qs = qs.filter(user=user)

            if filters and filters.get("start_date"):
                qs = qs.filter(created_at__gte=filters["start_date"])

            total = qs.count()
            pending = qs.filter(status__in=["Submitted", "Under Review", "Action Required"]).count()
            in_progress = qs.filter(status__in=["Assigned", "Under Inspection", "In Progress"]).count()
            resolved = qs.filter(status__in=["Resolved", "Closed"]).count()
            unassigned = qs.filter(assigned_to__isnull=True).count()

            # Pending requests count if MaintenanceRequest model available
            MaintReqModel = is_model_available("complaints", "MaintenanceRequest")
            pending_requests = MaintReqModel.objects.filter(status="PENDING").count() if MaintReqModel else 0

            return {
                "total": total,
                "pending": pending,
                "in_progress": in_progress,
                "resolved": resolved,
                "unassigned": unassigned,
                "pending_requests": pending_requests,
                "requires_action": unassigned + pending_requests,
            }
        except DatabaseError:
            pass

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
        "resolved": resolved,
        "unassigned": pending,
        "pending_requests": 0,
        "requires_action": pending,
    }


def get_maintenance_staff_metrics(user):
    """
    Calculates operational metrics specific to the logged-in Maintenance Staff member.
    """
    ComplaintModel = is_model_available("complaints", "Complaint")
    if ComplaintModel and user and user.is_authenticated:
        try:
            user_complaints = ComplaintModel.objects.filter(assigned_to=user)
            assigned_total = user_complaints.count()
            pending_inspection = user_complaints.filter(status__in=["Submitted", "Under Review", "Assigned"]).count()
            in_progress = user_complaints.filter(status__in=["Under Inspection", "In Progress", "Action Required"]).count()
            high_priority = user_complaints.filter(priority="High").count()

            MaintReqModel = is_model_available("complaints", "MaintenanceRequest")
            my_requests_count = MaintReqModel.objects.filter(requested_by=user).count() if MaintReqModel else 0

            return {
                "assigned_total": assigned_total,
                "pending_inspection": pending_inspection,
                "in_progress": in_progress,
                "high_priority": high_priority,
                "my_requests_count": my_requests_count,
            }
        except DatabaseError:
            pass

    return {
        "assigned_total": 0,
        "pending_inspection": 0,
        "in_progress": 0,
        "high_priority": 0,
        "my_requests_count": 0,
    }


def get_realtime_audit_activities(start_date=None, category_filter="all", status_filter="all", limit=12):
    """
    Aggregates real-time audit logs across Complaints, ComplaintHistory,
    StockTransactions, Assets, and central Activity models into a unified audit feed.
    """
    activities = []

    # 1. Complaint History Audit Logs
    HistoryModel = is_model_available("complaints", "ComplaintHistory")
    if HistoryModel and category_filter in ["all", "COMPLAINT", "MAINTENANCE"]:
        try:
            h_qs = HistoryModel.objects.select_related("complaint", "changed_by").all()
            if start_date:
                h_qs = h_qs.filter(timestamp__gte=start_date)
            for h in h_qs.order_by("-timestamp")[:limit]:
                user_str = (h.changed_by.name or h.changed_by.username) if h.changed_by else "System"
                activities.append({
                    "activity_type": "COMPLAINT",
                    "get_activity_type_display": "Complaint Activity",
                    "timestamp": h.timestamp,
                    "title": f"{h.complaint.complaint_id}: {h.complaint.title}",
                    "description": h.comment or f"Status changed to {h.status}",
                    "user_name": user_str,
                    "status": h.status,
                })
        except Exception:
            pass

    # 2. Stock Transactions Audit Logs
    StockTxModel = is_model_available("inventory", "StockTransaction")
    if StockTxModel and category_filter in ["all", "INVENTORY"]:
        try:
            st_qs = StockTxModel.objects.select_related("item", "created_by").all()
            if start_date:
                st_qs = st_qs.filter(created_at__gte=start_date)
            for st in st_qs.order_by("-created_at")[:limit]:
                user_str = (st.created_by.name or st.created_by.username) if st.created_by else "Inventory System"
                activities.append({
                    "activity_type": "INVENTORY",
                    "get_activity_type_display": "Inventory Update",
                    "timestamp": st.created_at,
                    "title": f"{st.get_transaction_type_display()}: {st.item.name}",
                    "description": f"{st.quantity} {st.item.unit} - {st.notes or 'Stock transaction recorded'}",
                    "user_name": user_str,
                    "status": st.item.stock_status,
                })
        except Exception:
            pass

    # 3. Asset Creation & Status Updates
    AssetModel = is_model_available("assets", "Asset")
    if AssetModel and category_filter in ["all", "ASSET"]:
        try:
            a_qs = AssetModel.objects.all()
            if start_date:
                a_qs = a_qs.filter(created_at__gte=start_date)
            for ast in a_qs.order_by("-created_at")[:limit]:
                activities.append({
                    "activity_type": "ASSET",
                    "get_activity_type_display": "Asset Update",
                    "timestamp": ast.created_at,
                    "title": f"Asset Logged: {ast.name} ({ast.asset_code})",
                    "description": f"Location: {ast.building} {ast.room or ''} | Category: {ast.category}",
                    "user_name": "Admin Staff",
                    "status": ast.get_status_display(),
                })
        except Exception:
            pass

    # 4. Central Activity Model Logs
    try:
        act_qs = Activity.objects.all()
        if start_date:
            act_qs = act_qs.filter(timestamp__gte=start_date)
        if category_filter != "all":
            act_qs = act_qs.filter(activity_type__iexact=category_filter)
        if status_filter != "all":
            act_qs = act_qs.filter(status__iexact=status_filter)
        for act in act_qs.order_by("-timestamp")[:limit]:
            activities.append({
                "activity_type": act.activity_type,
                "get_activity_type_display": act.get_activity_type_display(),
                "timestamp": act.timestamp,
                "title": act.title,
                "description": act.description,
                "user_name": act.user_name or "System",
                "status": act.status,
            })
    except Exception:
        pass

    # Sort all aggregated activities by timestamp descending
    activities.sort(key=lambda x: x["timestamp"], reverse=True)

    # Filter by status_filter if specified and not 'all'
    if status_filter and status_filter != "all":
        status_lower = status_filter.lower()
        activities = [
            a for a in activities
            if status_lower in (a.get("status") or "").lower()
        ]

    return activities[:limit]



