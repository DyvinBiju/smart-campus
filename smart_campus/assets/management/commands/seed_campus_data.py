import datetime
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from smart_campus.assets.models import Asset, Location
from smart_campus.inventory.models import InventoryCategory, InventoryItem, StockTransaction, StorageLocation

User = get_user_model()


class Command(BaseCommand):
    help = "Seeds realistic demo/sample data for Assets, Locations, and Inventory modules."

    def add_arguments(self, parser):
        parser.add_argument(
            "--clean",
            action="store_true",
            help="Delete seeded demo records before recreating them (Use with caution).",
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("=== Starting Campus Data Seeding Process ==="))

        with transaction.atomic():
            admin_user = self.get_or_create_admin_user()

            location_stats = self.seed_locations()
            asset_stats = self.seed_assets(location_stats["map"])
            category_stats = self.seed_inventory_categories()
            storage_stats = self.seed_storage_locations()
            inventory_stats = self.seed_inventory_items_and_transactions(admin_user, storage_stats["map"])

        self.stdout.write(self.style.SUCCESS("\n=== Data Seeding Completed Successfully ==="))
        self.stdout.write(f"Locations Created: {location_stats['created']}")
        self.stdout.write(f"Locations Already Existed: {location_stats['existed']}")
        self.stdout.write(f"Assets Created: {asset_stats['created']}")
        self.stdout.write(f"Assets Already Existed: {asset_stats['existed']}")
        self.stdout.write(f"Inventory Categories Created: {category_stats['created']}")
        self.stdout.write(f"Inventory Categories Already Existed: {category_stats['existed']}")
        self.stdout.write(f"Storage Locations Created: {storage_stats['created']}")
        self.stdout.write(f"Storage Locations Already Existed: {storage_stats['existed']}")
        self.stdout.write(f"Inventory Items Created: {inventory_stats['items_created']}")
        self.stdout.write(f"Inventory Items Already Existed: {inventory_stats['items_existed']}")
        self.stdout.write(f"Stock Transactions Created: {inventory_stats['tx_created']}")
        self.stdout.write(f"Stock Transactions Already Existed: {inventory_stats['tx_existed']}")

    def get_or_create_admin_user(self):
        """Finds an existing Admin or superuser, or creates a demo admin user if none exists."""
        admin_user = (
            User.objects.filter(role=User.Role.ADMIN).first()
            or User.objects.filter(is_superuser=True).first()
            or User.objects.filter(is_staff=True).first()
        )
        if not admin_user:
            admin_user, created = User.objects.get_or_create(
                username="admin_demo",
                defaults={
                    "email": "admin_demo@campus.edu",
                    "name": "Demo Administrator",
                    "role": User.Role.ADMIN,
                    "is_staff": True,
                    "is_superuser": True,
                },
            )
            if created:
                admin_user.set_password("demo12345")
                admin_user.save()
                self.stdout.write(self.style.SUCCESS("Created demo admin user 'admin_demo'"))
        return admin_user

    def seed_locations(self):
        """Seeds hierarchical campus locations into Location model."""
        locations_tree = [
            {"name": "Main Campus", "type": "CAMPUS", "parent": None, "desc": "Main University Campus Grounds"},
            {"name": "Main Academic Block", "type": "BLOCK", "parent": "Main Campus", "desc": "Primary academic block containing lecture halls and main computer labs"},
            {"name": "Computer Science Block", "type": "BLOCK", "parent": "Main Campus", "desc": "Department of Computer Science building"},
            {"name": "Science Block", "type": "BLOCK", "parent": "Main Campus", "desc": "Science faculty laboratories and testing facilities"},
            {"name": "Administration Block", "type": "BLOCK", "parent": "Main Campus", "desc": "Principal office, administrative services, and conference rooms"},
            {"name": "Library Block", "type": "BLOCK", "parent": "Main Campus", "desc": "Central library and digital reading rooms"},
            {"name": "Engineering Block", "type": "BLOCK", "parent": "Main Campus", "desc": "Engineering faculty, server rooms, and maintenance workshops"},
            {"name": "Computer Lab 1", "type": "COMPUTER_LAB", "parent": "Main Academic Block", "desc": "High performance computing lab (Room 101)"},
            {"name": "Computer Lab 2", "type": "COMPUTER_LAB", "parent": "Main Academic Block", "desc": "Programming & AI research lab (Room 102)"},
            {"name": "Seminar Hall", "type": "HALL", "parent": "Main Academic Block", "desc": "250-seater multimedia auditorium"},
            {"name": "Main Entrance", "type": "OTHER", "parent": "Main Academic Block", "desc": "Main entrance security desk"},
            {"name": "Faculty Room", "type": "STAFF_ROOM", "parent": "Computer Science Block", "desc": "CS Faculty workstations"},
            {"name": "Principal Office", "type": "OFFICE", "parent": "Administration Block", "desc": "Principal executive office suite"},
            {"name": "Conference Room", "type": "HALL", "parent": "Administration Block", "desc": "Administrative 12-seater conference room"},
            {"name": "Electronics Lab", "type": "LABORATORY", "parent": "Science Block", "desc": "Electronics testing and measurement lab"},
            {"name": "Library Office", "type": "OFFICE", "parent": "Library Block", "desc": "Librarian administration desk"},
            {"name": "Server Room", "type": "SERVER_ROOM", "parent": "Engineering Block", "desc": "Central network server and IT infrastructure room"},
            {"name": "Maintenance Room", "type": "MAINTENANCE_ROOM", "parent": "Engineering Block", "desc": "Central maintenance workshop and spare storage"},
        ]

        created_count = 0
        existed_count = 0
        loc_map = {}

        for data in locations_tree:
            parent_obj = loc_map.get(data["parent"]) if data["parent"] else None
            loc_obj, created = Location.objects.get_or_create(
                name=data["name"],
                defaults={
                    "location_type": data["type"],
                    "parent": parent_obj,
                    "description": data["desc"],
                    "is_active": True,
                },
            )
            loc_map[data["name"]] = loc_obj
            if created:
                created_count += 1
            else:
                existed_count += 1

        return {"created": created_count, "existed": existed_count, "map": loc_map}

    def seed_assets(self, loc_map):
        """Seeds realistic campus assets into Asset model with Location bindings."""
        assets_data = [
            {
                "asset_code": "AST-0001",
                "name": "Dell OptiPlex 7090 Desktop PC",
                "category": "IT & Computers",
                "location_name": "Computer Lab 1",
                "building": "Main Academic Block",
                "room": "Computer Lab 1",
                "status": "ACTIVE",
                "purchase_date": datetime.date(2023, 1, 15),
                "description": "Intel Core i7, 16GB RAM, 512GB SSD desktop workstation",
            },
            {
                "asset_code": "AST-0002",
                "name": "Dell OptiPlex 7090 Desktop PC",
                "category": "IT & Computers",
                "location_name": "Computer Lab 2",
                "building": "Main Academic Block",
                "room": "Computer Lab 2",
                "status": "ACTIVE",
                "purchase_date": datetime.date(2023, 1, 15),
                "description": "Intel Core i7, 16GB RAM, 512GB SSD desktop workstation",
            },
            {
                "asset_code": "AST-0003",
                "name": "Lenovo ThinkPad L14 Laptop",
                "category": "IT & Computers",
                "location_name": "Principal Office",
                "building": "Administration Block",
                "room": "Principal Office",
                "status": "ACTIVE",
                "purchase_date": datetime.date(2023, 3, 20),
                "description": "Core i5 11th Gen, 16GB RAM, Admin workstation",
            },
            {
                "asset_code": "AST-0004",
                "name": "HP ProBook 450 Laptop",
                "category": "IT & Computers",
                "location_name": "Faculty Room",
                "building": "Computer Science Block",
                "room": "Faculty Room",
                "status": "IN_STOCK",
                "purchase_date": datetime.date(2023, 5, 10),
                "description": "Faculty spare workstation laptop",
            },
            {
                "asset_code": "AST-0005",
                "name": "Epson EB-X06 3LCD Projector",
                "category": "Audio / Visual",
                "location_name": "Seminar Hall",
                "building": "Main Academic Block",
                "room": "Seminar Hall",
                "status": "ACTIVE",
                "purchase_date": datetime.date(2022, 8, 12),
                "description": "3600 Lumens HDMI Projector",
            },
            {
                "asset_code": "AST-0006",
                "name": "BenQ MX560 XGA Projector",
                "category": "Audio / Visual",
                "location_name": "Computer Lab 1",
                "building": "Main Academic Block",
                "room": "Computer Lab 1",
                "status": "UNDER_MAINTENANCE",
                "purchase_date": datetime.date(2022, 9, 1),
                "description": "Sent for bulb replacement and optical cleaning",
            },
            {
                "asset_code": "AST-0007",
                "name": "HP LaserJet Pro MFP Printer",
                "category": "IT & Computers",
                "location_name": "Principal Office",
                "building": "Administration Block",
                "room": "Principal Office",
                "status": "ACTIVE",
                "purchase_date": datetime.date(2021, 11, 5),
                "description": "High-speed monochrome network laser printer",
            },
            {
                "asset_code": "AST-0008",
                "name": "Cisco Catalyst 2960 Switch 24-Port",
                "category": "Electrical & Utilities",
                "location_name": "Server Room",
                "building": "Engineering Block",
                "room": "Server Room",
                "status": "ACTIVE",
                "purchase_date": datetime.date(2020, 4, 18),
                "description": "Managed Gigabit Ethernet Switch",
            },
            {
                "asset_code": "AST-0009",
                "name": "Aruba AP-505 Wi-Fi Access Point",
                "category": "Electrical & Utilities",
                "location_name": "Seminar Hall",
                "building": "Main Academic Block",
                "room": "Seminar Hall",
                "status": "ACTIVE",
                "purchase_date": datetime.date(2022, 2, 14),
                "description": "Dual-band Wi-Fi 6 enterprise access point",
            },
            {
                "asset_code": "AST-0010",
                "name": "APC Smart-UPS 3000VA",
                "category": "Electrical & Utilities",
                "location_name": "Server Room",
                "building": "Engineering Block",
                "room": "Server Room",
                "status": "ACTIVE",
                "purchase_date": datetime.date(2021, 6, 30),
                "description": "Rackmount Uninterruptible Power Supply",
            },
            {
                "asset_code": "AST-0011",
                "name": "Daikin 2 Ton Inverter Air Conditioner",
                "category": "Electrical & Utilities",
                "location_name": "Computer Lab 1",
                "building": "Main Academic Block",
                "room": "Computer Lab 1",
                "status": "ACTIVE",
                "purchase_date": datetime.date(2022, 4, 5),
                "description": "Split AC unit with stabilizer",
            },
            {
                "asset_code": "AST-0012",
                "name": "Voltas 1.5 Ton Split Air Conditioner",
                "category": "Electrical & Utilities",
                "location_name": "Library Office",
                "building": "Library Block",
                "room": "Library Office",
                "status": "UNDER_MAINTENANCE",
                "purchase_date": datetime.date(2021, 5, 20),
                "description": "Compressor inspection and gas recharge",
            },
            {
                "asset_code": "AST-0013",
                "name": "ViewSonic 75-inch Interactive Smart Board",
                "category": "Audio / Visual",
                "location_name": "Seminar Hall",
                "building": "Main Academic Block",
                "room": "Seminar Hall",
                "status": "ACTIVE",
                "purchase_date": datetime.date(2023, 7, 1),
                "description": "4K Touchscreen display with digital pen",
            },
            {
                "asset_code": "AST-0014",
                "name": "Hikvision 4MP Dome CCTV Camera",
                "category": "Electrical & Utilities",
                "location_name": "Main Entrance",
                "building": "Main Academic Block",
                "room": "Main Entrance",
                "status": "ACTIVE",
                "purchase_date": datetime.date(2022, 10, 15),
                "description": "Outdoor night vision security camera",
            },
            {
                "asset_code": "AST-0015",
                "name": "Fujitsu Fi-7160 Document Scanner",
                "category": "IT & Computers",
                "location_name": "Conference Room",
                "building": "Administration Block",
                "room": "Conference Room",
                "status": "IN_STOCK",
                "purchase_date": datetime.date(2022, 1, 10),
                "description": "Duplex high-speed document scanner",
            },
            {
                "asset_code": "AST-0016",
                "name": "Tektronix Digital Oscilloscope 100MHz",
                "category": "Lab Equipment",
                "location_name": "Electronics Lab",
                "building": "Science Block",
                "room": "Electronics Lab",
                "status": "ACTIVE",
                "purchase_date": datetime.date(2020, 12, 1),
                "description": "Dual channel digital storage oscilloscope",
            },
            {
                "asset_code": "AST-0017",
                "name": "Fluke 177 True-RMS Digital Multimeter",
                "category": "Lab Equipment",
                "location_name": "Electronics Lab",
                "building": "Science Block",
                "room": "Electronics Lab",
                "status": "ACTIVE",
                "purchase_date": datetime.date(2021, 3, 15),
                "description": "Precision electronic testing meter",
            },
            {
                "asset_code": "AST-0018",
                "name": "Ergonomic Executive Office Desk Set",
                "category": "Classroom & Furniture",
                "location_name": "Principal Office",
                "building": "Administration Block",
                "room": "Principal Office",
                "status": "ACTIVE",
                "purchase_date": datetime.date(2019, 8, 20),
                "description": "Teak wood desk with side drawer unit",
            },
            {
                "asset_code": "AST-0019",
                "name": "Modular 12-Seater Conference Table",
                "category": "Classroom & Furniture",
                "location_name": "Conference Room",
                "building": "Administration Block",
                "room": "Conference Room",
                "status": "ACTIVE",
                "purchase_date": datetime.date(2019, 8, 20),
                "description": "Conference table with integrated power sockets",
            },
            {
                "asset_code": "AST-0020",
                "name": "Blue Star Water Cooler & Dispenser",
                "category": "Electrical & Utilities",
                "location_name": "Maintenance Room",
                "building": "Engineering Block",
                "room": "Maintenance Room",
                "status": "DAMAGED",
                "purchase_date": datetime.date(2018, 5, 11),
                "description": "Cooling coil malfunction, pending repair decision",
            },
            {
                "asset_code": "AST-0021",
                "name": "Epson LX-310 Dot Matrix Printer",
                "category": "Other",
                "location_name": "Library Office",
                "building": "Library Block",
                "room": "Library Office",
                "status": "RETIRED",
                "purchase_date": datetime.date(2015, 2, 10),
                "description": "Decommissioned printer replaced by laser printer",
            },
        ]

        created_count = 0
        existed_count = 0

        for item in assets_data:
            code = item["asset_code"]
            loc_obj = loc_map.get(item["location_name"])
            
            obj, created = Asset.objects.get_or_create(
                asset_code=code,
                defaults={
                    "name": item["name"],
                    "category": item["category"],
                    "location": loc_obj,
                    "building": item["building"],
                    "room": item["room"],
                    "status": item["status"],
                    "purchase_date": item["purchase_date"],
                    "description": item["description"],
                },
            )
            if not created and loc_obj and not obj.location:
                obj.location = loc_obj
                obj.save()

            if created:
                created_count += 1
            else:
                existed_count += 1

        return {"created": created_count, "existed": existed_count}

    def seed_inventory_categories(self):
        """Seeds Inventory Categories into InventoryCategory model."""
        categories_data = [
            {"name": "Stationery", "description": "Office and classroom stationery supplies"},
            {"name": "Printing Supplies", "description": "Paper, toner cartridges, and ink supplies"},
            {"name": "IT & Networking Supplies", "description": "Cables, connectors, peripheral accessories, and networking consumables"},
            {"name": "Electrical Supplies", "description": "Bulbs, switches, fuses, tapes, and wiring components"},
            {"name": "Cleaning Supplies", "description": "Disinfectants, detergents, and sanitation tools"},
            {"name": "Maintenance Supplies", "description": "Lubricants, fasteners, hardware tools, and repair materials"},
            {"name": "Laboratory Supplies", "description": "Electronic components, chemicals, glassware, and testing items"},
            {"name": "Safety Supplies", "description": "Personal protective equipment, masks, gloves, and safety gear"},
            {"name": "Plumbing Supplies", "description": "Pipes, fittings, valves, and plumbing consumables"},
            {"name": "Spare Parts", "description": "Screws, nuts, bolts, washers, and replacement hardware"},
        ]

        created_count = 0
        existed_count = 0

        for item in categories_data:
            name = item["name"]
            obj, created = InventoryCategory.objects.get_or_create(
                name=name,
                defaults={"description": item["description"]},
            )
            if created:
                created_count += 1
            else:
                existed_count += 1

        return {"created": created_count, "existed": existed_count}

    def seed_storage_locations(self):
        """Seeds predefined inventory storage locations into StorageLocation model."""
        locations_data = [
            {
                "name": "Central Store",
                "code": "CS-001",
                "description": "Main campus central store room for general consumables",
                "is_active": True,
            },
            {
                "name": "Server Room Store",
                "code": "SR-001",
                "description": "Adjacent IT server room for networking and IT supplies",
                "is_active": True,
            },
            {
                "name": "Maintenance Room",
                "code": "MR-001",
                "description": "Maintenance workshop storage for tools and electrical supplies",
                "is_active": True,
            },
            {
                "name": "Electronics Lab Store",
                "code": "EL-001",
                "description": "Laboratory equipment and component storage for ECE/EEE department",
                "is_active": True,
            },
            {
                "name": "Housekeeping Store",
                "code": "HK-001",
                "description": "Cleaning materials and sanitation supply store",
                "is_active": True,
            },
            {
                "name": "Admin Block Store",
                "code": "AB-001",
                "description": "Stationery and printing supply store for administration block",
                "is_active": True,
            },
            {
                "name": "Plumbing Store",
                "code": "PL-001",
                "description": "Plumbing and water supply materials store",
                "is_active": True,
            },
            {
                "name": "Safety Equipment Store",
                "code": "SE-001",
                "description": "PPE, safety gear, and first-aid supplies store",
                "is_active": True,
            },
        ]

        created_count = 0
        existed_count = 0
        location_map = {}

        for loc_data in locations_data:
            code = loc_data["code"]
            obj, created = StorageLocation.objects.get_or_create(
                code=code,
                defaults={
                    "name": loc_data["name"],
                    "description": loc_data["description"],
                    "is_active": loc_data["is_active"],
                },
            )
            location_map[loc_data["name"]] = obj
            # Also map legacy string keys used in items_spec
            if created:
                created_count += 1
            else:
                existed_count += 1

        # Convenience aliases for legacy storage_location string values in items_spec
        location_map["Server Room"] = location_map.get("Server Room Store")
        location_map["Electronics Lab"] = location_map.get("Electronics Lab Store")

        self.stdout.write(self.style.SUCCESS(
            f"  [+] Storage Locations: {created_count} created, {existed_count} already existed."
        ))
        return {"created": created_count, "existed": existed_count, "map": location_map}

    def seed_inventory_items_and_transactions(self, admin_user, storage_location_map=None):
        """
        Seeds Inventory Items and initial Stock Transactions cleanly.
        Items start at initial quantity = 0, then RECEIVE/ISSUE transactions populate
        the mathematical quantity and audit logs idempotently.
        """
        items_spec = [
            {
                "name": "A4 Printer Paper 80GSM",
                "category": "Printing Supplies",
                "minimum_quantity": 10,
                "unit": "reams",
                "storage_location": "Central Store",
                "description": "White 80gsm A4 printing paper ream (500 sheets)",
                "receive_qty": 40,
                "issue_qty": 0,
                "asset_code": None,
            },
            {
                "name": "HDMI Cable 2m",
                "category": "IT & Networking Supplies",
                "minimum_quantity": 5,
                "unit": "pieces",
                "storage_location": "Server Room",
                "description": "High-speed HDMI 2.0 cable",
                "receive_qty": 15,
                "issue_qty": 3,
                "asset_code": "AST-0005",
            },
            {
                "name": "Cat6 Ethernet Cable (300m Roll)",
                "category": "IT & Networking Supplies",
                "minimum_quantity": 20,
                "unit": "meters",
                "storage_location": "Server Room",
                "description": "UTP solid copper networking cable",
                "receive_qty": 100,
                "issue_qty": 20,
                "asset_code": "AST-0008",
            },
            {
                "name": "3M Electrical Insulation Tape",
                "category": "Electrical Supplies",
                "minimum_quantity": 5,
                "unit": "rolls",
                "storage_location": "Maintenance Room",
                "description": "Black PVC electrical tape",
                "receive_qty": 20,
                "issue_qty": 2,
                "asset_code": None,
            },
            {
                "name": "Philips 15W LED Bulb (Cool Day)",
                "category": "Electrical Supplies",
                "minimum_quantity": 10,
                "unit": "pieces",
                "storage_location": "Maintenance Room",
                "description": "B22 cap 15W cool white LED bulb",
                "receive_qty": 30,
                "issue_qty": 5,
                "asset_code": None,
            },
            {
                "name": "Nylon Cable Ties (Pack of 100)",
                "category": "IT & Networking Supplies",
                "minimum_quantity": 50,
                "unit": "pieces",
                "storage_location": "Server Room",
                "description": "Self-locking 200mm cable ties",
                "receive_qty": 200,
                "issue_qty": 50,
                "asset_code": None,
            },
            {
                "name": "Nitrile Disposable Gloves (Box of 50)",
                "category": "Safety Supplies",
                "minimum_quantity": 25,
                "unit": "pairs",
                "storage_location": "Central Store",
                "description": "Powder-free blue nitrile examination gloves",
                "receive_qty": 120,
                "issue_qty": 20,
                "asset_code": None,
            },
            {
                "name": "M4 Stainless Steel Screw Set",
                "category": "Spare Parts",
                "minimum_quantity": 100,
                "unit": "pieces",
                "storage_location": "Maintenance Room",
                "description": "Assorted M4 pan head machine screws",
                "receive_qty": 600,
                "issue_qty": 100,
                "asset_code": None,
            },
            {
                "name": "WD-40 Multi-Use Lubricant Spray",
                "category": "Maintenance Supplies",
                "minimum_quantity": 3,
                "unit": "liters",
                "storage_location": "Maintenance Room",
                "description": "Anti-rust and penetrating oil spray",
                "receive_qty": 6,
                "issue_qty": 2,
                "asset_code": None,
            },
            {
                "name": "Dell USB Wired Keyboard",
                "category": "IT & Networking Supplies",
                "minimum_quantity": 3,
                "unit": "pieces",
                "storage_location": "Server Room",
                "description": "Standard QWERTY USB keyboard",
                "receive_qty": 8,
                "issue_qty": 2,
                "asset_code": "AST-0001",
            },
            {
                "name": "RJ45 Modular Plug Connectors",
                "category": "IT & Networking Supplies",
                "minimum_quantity": 20,
                "unit": "pieces",
                "storage_location": "Server Room",
                "description": "Cat6 8P8C crimp connectors",
                "receive_qty": 100,
                "issue_qty": 40,
                "asset_code": None,
            },
            {
                "name": "6-Socket Surge Protector Extension Board",
                "category": "Electrical Supplies",
                "minimum_quantity": 3,
                "unit": "pieces",
                "storage_location": "Maintenance Room",
                "description": "Heavy-duty extension board with switch",
                "receive_qty": 10,
                "issue_qty": 3,
                "asset_code": None,
            },
            {
                "name": "3M N95 Safety Dust Mask",
                "category": "Safety Supplies",
                "minimum_quantity": 20,
                "unit": "pieces",
                "storage_location": "Central Store",
                "description": "Particulate respirator safety mask",
                "receive_qty": 100,
                "issue_qty": 25,
                "asset_code": None,
            },
            {
                "name": "1-Inch Heavy Duty PVC Pipe (3m)",
                "category": "Plumbing Supplies",
                "minimum_quantity": 10,
                "unit": "meters",
                "storage_location": "Maintenance Room",
                "description": "Schedule 40 rigid PVC plumbing pipe",
                "receive_qty": 30,
                "issue_qty": 10,
                "asset_code": None,
            },
            {
                "name": "Duracell AA Alkaline Battery",
                "category": "Electrical Supplies",
                "minimum_quantity": 10,
                "unit": "pieces",
                "storage_location": "Central Store",
                "description": "1.5V long-lasting AA batteries",
                "receive_qty": 50,
                "issue_qty": 20,
                "asset_code": None,
            },
            {
                "name": "HP 12A Black Toner Cartridge",
                "category": "Printing Supplies",
                "minimum_quantity": 5,
                "unit": "cartridges",
                "storage_location": "Central Store",
                "description": "Monochrome LaserJet toner cartridge",
                "receive_qty": 8,
                "issue_qty": 5,
                "asset_code": "AST-0007",
            },
            {
                "name": "Disinfectant Floor Cleaning Liquid",
                "category": "Cleaning Supplies",
                "minimum_quantity": 5,
                "unit": "bottles",
                "storage_location": "Central Store",
                "description": "Concentrated pine floor disinfectant 5L",
                "receive_qty": 10,
                "issue_qty": 8,
                "asset_code": None,
            },
            {
                "name": "Dell Optical USB Mouse",
                "category": "IT & Networking Supplies",
                "minimum_quantity": 5,
                "unit": "pieces",
                "storage_location": "Server Room",
                "description": "Red LED optical USB mouse",
                "receive_qty": 10,
                "issue_qty": 8,
                "asset_code": "AST-0002",
            },
            {
                "name": "Dry Erase Whiteboard Markers (Pack of 10)",
                "category": "Stationery",
                "minimum_quantity": 5,
                "unit": "boxes",
                "storage_location": "Central Store",
                "description": "Assorted color whiteboard markers",
                "receive_qty": 6,
                "issue_qty": 5,
                "asset_code": None,
            },
            {
                "name": "Glass Tube Fuse 10A",
                "category": "Electrical Supplies",
                "minimum_quantity": 10,
                "unit": "pieces",
                "storage_location": "Maintenance Room",
                "description": "Fast-acting 5x20mm glass fuse",
                "receive_qty": 10,
                "issue_qty": 10,
                "asset_code": None,
            },
            {
                "name": "100uF 50V Electrolytic Capacitor",
                "category": "Laboratory Supplies",
                "minimum_quantity": 5,
                "unit": "pieces",
                "storage_location": "Electronics Lab",
                "description": "Radial lead aluminum electrolytic capacitor",
                "receive_qty": 15,
                "issue_qty": 15,
                "asset_code": None,
            },
        ]

        items_created = 0
        items_existed = 0
        tx_created = 0
        tx_existed = 0

        category_map = {c.name: c for c in InventoryCategory.objects.all()}
        if storage_location_map is None:
            storage_location_map = {}

        for spec in items_spec:
            category = category_map.get(spec["category"])
            if not category:
                category, _ = InventoryCategory.objects.get_or_create(name=spec["category"])

            item_obj = InventoryItem.objects.filter(name=spec["name"], category=category).first()

            # Resolve the StorageLocation FK from map; fall back gracefully
            storage_loc_obj = storage_location_map.get(spec.get("storage_location", ""))

            if not item_obj:
                item_obj = InventoryItem.objects.create(
                    name=spec["name"],
                    category=category,
                    quantity=0,
                    minimum_quantity=spec["minimum_quantity"],
                    unit=spec["unit"],
                    storage_location=spec["storage_location"],
                    location=storage_loc_obj,
                    description=spec["description"],
                )
                items_created += 1
            else:
                # Backfill location FK for previously seeded items without it
                if storage_loc_obj and item_obj.location_id != storage_loc_obj.pk:
                    item_obj.location = storage_loc_obj
                    item_obj.save(update_fields=["location"])
                items_existed += 1

            rec_note = f"Initial stock receipt of {spec['receive_qty']} {spec['unit']} for {spec['name']}"
            existing_rec_tx = StockTransaction.objects.filter(
                item=item_obj,
                transaction_type="RECEIVE",
                notes=rec_note,
            ).first()

            if not existing_rec_tx:
                StockTransaction.objects.create(
                    item=item_obj,
                    transaction_type="RECEIVE",
                    quantity=spec["receive_qty"],
                    notes=rec_note,
                    created_by=admin_user,
                )
                tx_created += 1
            else:
                tx_existed += 1

            if spec["issue_qty"] > 0:
                asset_obj = None
                if spec.get("asset_code"):
                    asset_obj = Asset.objects.filter(asset_code=spec["asset_code"]).first()

                iss_note = f"Issued {spec['issue_qty']} {spec['unit']} for maintenance/setup work"
                existing_iss_tx = StockTransaction.objects.filter(
                    item=item_obj,
                    transaction_type="ISSUE",
                    notes=iss_note,
                ).first()

                if not existing_iss_tx:
                    StockTransaction.objects.create(
                        item=item_obj,
                        transaction_type="ISSUE",
                        quantity=spec["issue_qty"],
                        asset=asset_obj,
                        notes=iss_note,
                        created_by=admin_user,
                    )
                    tx_created += 1
                else:
                    tx_existed += 1

        return {
            "items_created": items_created,
            "items_existed": items_existed,
            "tx_created": tx_created,
            "tx_existed": tx_existed,
        }
