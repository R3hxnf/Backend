#!/usr/bin/env python3
"""
Seed script to populate the POS system with sample data
"""
import asyncio
import os
import sys
from pathlib import Path
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import hashlib
from datetime import datetime, timezone
import uuid

# Load environment variables
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

def hash_pin(pin: str) -> str:
    """Hash PIN for secure storage"""
    return hashlib.sha256(pin.encode()).hexdigest()

async def seed_users():
    """Create sample users"""
    print("Creating sample users...")
    
    # Admin user
    admin_user = {
        "id": str(uuid.uuid4()),
        "username": "admin",
        "pin": hash_pin("1234"),
        "role": "admin",
        "full_name": "System Administrator",
        "email": "admin@posystem.com",
        "phone": "+1-555-0001",
        "is_approved": True,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    
    # Employee user
    employee_user = {
        "id": str(uuid.uuid4()),
        "username": "cashier1",
        "pin": hash_pin("5678"),
        "role": "employee",
        "full_name": "John Cashier",
        "email": "john@posystem.com",
        "phone": "+1-555-0002",
        "is_approved": True,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    
    # Check if users already exist
    existing_admin = await db.users.find_one({"username": "admin"})
    if not existing_admin:
        await db.users.insert_one(admin_user)
        print("✓ Admin user created (username: admin, pin: 1234)")
    
    existing_employee = await db.users.find_one({"username": "cashier1"})
    if not existing_employee:
        await db.users.insert_one(employee_user)
        print("✓ Employee user created (username: cashier1, pin: 5678)")

async def seed_products():
    """Create sample products"""
    print("Creating sample products...")
    
    products = [
        {
            "id": str(uuid.uuid4()),
            "name": "Coffee - Medium",
            "description": "Premium medium roast coffee",
            "price": 350,  # $3.50
            "category": "Beverages",
            "sku": "COFFEE-MED-001",
            "barcode": "123456789012",
            "stock_quantity": 100,
            "min_stock_level": 10,
            "cost_price": 200,
            "is_active": True,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Croissant",
            "description": "Fresh butter croissant",
            "price": 450,  # $4.50
            "category": "Bakery",
            "sku": "CROIS-001",
            "barcode": "123456789013",
            "stock_quantity": 50,
            "min_stock_level": 5,
            "cost_price": 250,
            "is_active": True,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Orange Juice",
            "description": "Fresh squeezed orange juice",
            "price": 400,  # $4.00
            "category": "Beverages",
            "sku": "OJ-FRESH-001",
            "barcode": "123456789014",
            "stock_quantity": 30,
            "min_stock_level": 5,
            "cost_price": 200,
            "is_active": True,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Sandwich - Turkey",
            "description": "Turkey and cheese sandwich",
            "price": 850,  # $8.50
            "category": "Food",
            "sku": "SAND-TURK-001",
            "barcode": "123456789015",
            "stock_quantity": 25,
            "min_stock_level": 3,
            "cost_price": 500,
            "is_active": True,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Muffin - Blueberry",
            "description": "Fresh blueberry muffin",
            "price": 320,  # $3.20
            "category": "Bakery",
            "sku": "MUFF-BLUE-001",
            "barcode": "123456789016",
            "stock_quantity": 40,
            "min_stock_level": 8,
            "cost_price": 180,
            "is_active": True,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Water Bottle",
            "description": "500ml purified water",
            "price": 150,  # $1.50
            "category": "Beverages",
            "sku": "WATER-500-001",
            "barcode": "123456789017",
            "stock_quantity": 200,
            "min_stock_level": 20,
            "cost_price": 75,
            "is_active": True,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
    ]
    
    # Clear existing products
    await db.products.delete_many({})
    
    # Insert new products
    await db.products.insert_many(products)
    print(f"✓ Created {len(products)} sample products")

async def seed_customers():
    """Create sample customers"""
    print("Creating sample customers...")
    
    customers = [
        {
            "id": str(uuid.uuid4()),
            "name": "Alice Johnson",
            "email": "alice@example.com",
            "phone": "+1-555-0101",
            "address": "123 Main St, Anytown, ST 12345",
            "loyalty_points": 150,
            "total_spent": 5000,  # $50.00
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Bob Smith",
            "email": "bob@example.com",
            "phone": "+1-555-0102",
            "address": "456 Oak Ave, Somewhere, ST 12346",
            "loyalty_points": 200,
            "total_spent": 7500,  # $75.00
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Carol Wilson",
            "email": "carol@example.com",
            "phone": "+1-555-0103",
            "address": "789 Pine St, Elsewhere, ST 12347",
            "loyalty_points": 75,
            "total_spent": 2500,  # $25.00
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
    ]
    
    # Clear existing customers
    await db.customers.delete_many({})
    
    # Insert new customers
    await db.customers.insert_many(customers)
    print(f"✓ Created {len(customers)} sample customers")

async def main():
    """Main seeding function"""
    print("🌱 Seeding POS System Database...")
    print("=" * 40)
    
    try:
        await seed_users()
        await seed_products()
        await seed_customers()
        
        print("=" * 40)
        print("✅ Database seeding completed successfully!")
        print()
        print("Login credentials:")
        print("Admin: username=admin, pin=1234")
        print("Employee: username=cashier1, pin=5678")
        
    except Exception as e:
        print(f"❌ Error seeding database: {e}")
        sys.exit(1)
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(main())