from fastapi import FastAPI, APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
import jwt
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
import hashlib
import json
from decimal import Decimal
import asyncio

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Security
security = HTTPBearer()
JWT_SECRET = os.environ.get('JWT_SECRET', 'your-secret-key-change-in-production')

# Create the main app without a prefix
app = FastAPI(title="POS System API", version="1.0.0")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Pydantic Models
class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    username: str
    pin: str
    role: str  # 'admin' or 'employee'
    full_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    is_approved: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class UserCreate(BaseModel):
    username: str
    pin: str
    full_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    role: str = "employee"

class UserLogin(BaseModel):
    username: str
    pin: str

class Product(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None
    price: int  # Price in cents
    category: str
    sku: str
    barcode: Optional[str] = None
    stock_quantity: int = 0
    min_stock_level: int = 5
    cost_price: Optional[int] = None  # Cost in cents
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ProductCreate(BaseModel):
    name: str
    description: Optional[str] = None
    price: int
    category: str
    sku: str
    barcode: Optional[str] = None
    stock_quantity: int = 0
    min_stock_level: int = 5
    cost_price: Optional[int] = None

class Customer(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    loyalty_points: int = 0
    total_spent: int = 0  # Total in cents
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class CustomerCreate(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None

class OrderItem(BaseModel):
    product_id: str
    product_name: str
    quantity: int
    unit_price: int  # Price in cents
    total_price: int  # Total in cents

class Order(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    order_number: str
    customer_id: Optional[str] = None
    customer_name: Optional[str] = None
    items: List[OrderItem]
    subtotal: int  # Subtotal in cents
    tax_amount: int  # Tax in cents
    discount_amount: int = 0  # Discount in cents
    total_amount: int  # Total in cents
    payment_method: str  # 'cash', 'card', 'digital_wallet'
    payment_status: str = 'pending'  # 'pending', 'completed', 'failed', 'refunded'
    square_payment_id: Optional[str] = None
    cashier_id: str
    cashier_name: str
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class OrderCreate(BaseModel):
    customer_id: Optional[str] = None
    items: List[OrderItem]
    payment_method: str
    discount_amount: int = 0
    notes: Optional[str] = None

class PaymentRequest(BaseModel):
    order_id: str
    payment_method: str  # 'cash', 'card', 'digital_wallet'
    amount: int  # Amount in cents
    cash_received: Optional[int] = None  # For cash payments
    payment_token: Optional[str] = None  # For card/digital wallet

class InventoryMovement(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    product_id: str
    movement_type: str  # 'sale', 'purchase', 'adjustment', 'return'
    quantity: int  # Positive for additions, negative for reductions
    reference_id: Optional[str] = None  # Order ID, purchase ID, etc.
    notes: Optional[str] = None
    user_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class SalesReport(BaseModel):
    period: str
    total_sales: int  # Total in cents
    total_orders: int
    total_customers: int
    avg_order_value: int  # Average in cents
    top_products: List[Dict[str, Any]]
    payment_methods: Dict[str, int]
    sales_by_hour: Dict[str, int]

# Authentication helpers
def hash_pin(pin: str) -> str:
    """Hash PIN for secure storage"""
    return hashlib.sha256(pin.encode()).hexdigest()

def verify_pin(pin: str, hashed_pin: str) -> bool:
    """Verify PIN against hashed version"""
    return hash_pin(pin) == hashed_pin

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(hours=24)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm="HS256")
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current authenticated user"""
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=["HS256"])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials"
            )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )
    
    user = await db.users.find_one({"id": user_id})
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    return User(**user)

def generate_order_number():
    """Generate unique order number"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    random_suffix = str(uuid.uuid4())[:8].upper()
    return f"ORD-{timestamp}-{random_suffix}"

# Authentication endpoints
@api_router.post("/auth/register")
async def register_user(user_data: UserCreate):
    """Register new user (employee registration with admin approval)"""
    # Check if username already exists
    existing_user = await db.users.find_one({"username": user_data.username})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # Hash PIN
    hashed_pin = hash_pin(user_data.pin)
    
    # Create user
    user = User(
        username=user_data.username,
        pin=hashed_pin,
        full_name=user_data.full_name,
        email=user_data.email,
        phone=user_data.phone,
        role=user_data.role,
        is_approved=user_data.role == "admin"  # Auto-approve admins
    )
    
    # Insert to database
    await db.users.insert_one(user.dict())
    
    return {"message": "User registered successfully", "requires_approval": user_data.role == "employee"}

@api_router.post("/auth/login")
async def login_user(login_data: UserLogin):
    """Login user with username and PIN"""
    user = await db.users.find_one({"username": login_data.username})
    if not user or not verify_pin(login_data.pin, user["pin"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or PIN"
        )
    
    if not user["is_approved"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account not approved by admin"
        )
    
    # Create access token
    access_token = create_access_token(data={"sub": user["id"], "role": user["role"]})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "username": user["username"],
            "full_name": user["full_name"],
            "role": user["role"]
        }
    }

@api_router.get("/auth/me")
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return current_user

# User management endpoints (Admin only)
@api_router.get("/users/pending", response_model=List[User])
async def get_pending_users(current_user: User = Depends(get_current_user)):
    """Get users pending approval (Admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    users = await db.users.find({"is_approved": False}).to_list(length=None)
    return [User(**user) for user in users]

@api_router.put("/users/{user_id}/approve")
async def approve_user(user_id: str, current_user: User = Depends(get_current_user)):
    """Approve user (Admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await db.users.update_one(
        {"id": user_id},
        {"$set": {"is_approved": True, "updated_at": datetime.now(timezone.utc)}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"message": "User approved successfully"}

@api_router.get("/users", response_model=List[User])
async def get_all_users(current_user: User = Depends(get_current_user)):
    """Get all users (Admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    users = await db.users.find().to_list(length=None)
    return [User(**user) for user in users]

# Product management endpoints
@api_router.post("/products", response_model=Product)
async def create_product(product_data: ProductCreate, current_user: User = Depends(get_current_user)):
    """Create new product"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Check if SKU already exists
    existing_product = await db.products.find_one({"sku": product_data.sku})
    if existing_product:
        raise HTTPException(status_code=400, detail="SKU already exists")
    
    product = Product(**product_data.dict())
    await db.products.insert_one(product.dict())
    
    return product

@api_router.get("/products", response_model=List[Product])
async def get_products(
    category: Optional[str] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get all products with optional filtering"""
    query = {"is_active": True}
    
    if category:
        query["category"] = category
    
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"sku": {"$regex": search, "$options": "i"}},
            {"barcode": {"$regex": search, "$options": "i"}}
        ]
    
    products = await db.products.find(query).to_list(length=None)
    return [Product(**product) for product in products]

@api_router.get("/products/categories")
async def get_product_categories(current_user: User = Depends(get_current_user)):
    """Get all product categories"""
    categories = await db.products.distinct("category", {"is_active": True})
    return {"categories": categories}

@api_router.put("/products/{product_id}", response_model=Product)
async def update_product(
    product_id: str,
    product_data: ProductCreate,
    current_user: User = Depends(get_current_user)
):
    """Update product"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    update_data = product_data.dict()
    update_data["updated_at"] = datetime.now(timezone.utc)
    
    result = await db.products.update_one(
        {"id": product_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Product not found")
    
    updated_product = await db.products.find_one({"id": product_id})
    return Product(**updated_product)

@api_router.get("/products/low-stock")
async def get_low_stock_products(current_user: User = Depends(get_current_user)):
    """Get products with low stock"""
    products = await db.products.aggregate([
        {"$match": {"is_active": True}},
        {"$addFields": {"is_low_stock": {"$lte": ["$stock_quantity", "$min_stock_level"]}}},
        {"$match": {"is_low_stock": True}}
    ]).to_list(length=None)
    
    return [Product(**product) for product in products]

# Customer management endpoints
@api_router.post("/customers", response_model=Customer)
async def create_customer(customer_data: CustomerCreate, current_user: User = Depends(get_current_user)):
    """Create new customer"""
    customer = Customer(**customer_data.dict())
    await db.customers.insert_one(customer.dict())
    return customer

@api_router.get("/customers", response_model=List[Customer])
async def get_customers(
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get all customers with optional search"""
    query = {}
    
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}},
            {"phone": {"$regex": search, "$options": "i"}}
        ]
    
    customers = await db.customers.find(query).to_list(length=None)
    return [Customer(**customer) for customer in customers]

# Order management endpoints
@api_router.post("/orders", response_model=Order)
async def create_order(order_data: OrderCreate, current_user: User = Depends(get_current_user)):
    """Create new order"""
    # Calculate totals
    subtotal = sum(item.total_price for item in order_data.items)
    tax_rate = 0.08  # 8% tax rate
    tax_amount = int(subtotal * tax_rate)
    total_amount = subtotal + tax_amount - order_data.discount_amount
    
    # Get customer name if customer_id provided
    customer_name = None
    if order_data.customer_id:
        customer = await db.customers.find_one({"id": order_data.customer_id})
        if customer:
            customer_name = customer["name"]
    
    order = Order(
        order_number=generate_order_number(),
        customer_id=order_data.customer_id,
        customer_name=customer_name,
        items=order_data.items,
        subtotal=subtotal,
        tax_amount=tax_amount,
        discount_amount=order_data.discount_amount,
        total_amount=total_amount,
        payment_method=order_data.payment_method,
        cashier_id=current_user.id,
        cashier_name=current_user.full_name,
        notes=order_data.notes
    )
    
    await db.orders.insert_one(order.dict())
    
    # Update inventory for each item
    for item in order_data.items:
        await db.products.update_one(
            {"id": item.product_id},
            {"$inc": {"stock_quantity": -item.quantity}}
        )
        
        # Record inventory movement
        movement = InventoryMovement(
            product_id=item.product_id,
            movement_type="sale",
            quantity=-item.quantity,
            reference_id=order.id,
            user_id=current_user.id
        )
        await db.inventory_movements.insert_one(movement.dict())
    
    return order

@api_router.get("/orders", response_model=List[Order])
async def get_orders(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get orders with optional date filtering"""
    query = {}
    
    if date_from and date_to:
        try:
            from_date = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
            to_date = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
            query["created_at"] = {"$gte": from_date, "$lte": to_date}
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format")
    
    orders = await db.orders.find(query).sort("created_at", -1).to_list(length=100)
    return [Order(**order) for order in orders]

@api_router.get("/orders/{order_id}", response_model=Order)
async def get_order(order_id: str, current_user: User = Depends(get_current_user)):
    """Get specific order"""
    order = await db.orders.find_one({"id": order_id})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    return Order(**order)

# Payment processing endpoints (simplified for sandbox)
@api_router.post("/payments/process")
async def process_payment(payment_data: PaymentRequest, current_user: User = Depends(get_current_user)):
    """Process payment (simplified sandbox implementation)"""
    order = await db.orders.find_one({"id": payment_data.order_id})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if order["payment_status"] == "completed":
        raise HTTPException(status_code=400, detail="Order already paid")
    
    payment_status = "completed"
    payment_id = f"pay_{str(uuid.uuid4())[:8]}"
    
    # For demonstration, we'll simulate different payment scenarios
    if payment_data.payment_method == "cash":
        if payment_data.cash_received and payment_data.cash_received >= payment_data.amount:
            change_due = payment_data.cash_received - payment_data.amount
            payment_status = "completed"
        else:
            raise HTTPException(status_code=400, detail="Insufficient cash received")
    
    # Update order payment status
    await db.orders.update_one(
        {"id": payment_data.order_id},
        {
            "$set": {
                "payment_status": payment_status,
                "square_payment_id": payment_id,
                "updated_at": datetime.now(timezone.utc)
            }
        }
    )
    
    # Update customer total spent if customer exists
    if order.get("customer_id"):
        await db.customers.update_one(
            {"id": order["customer_id"]},
            {
                "$inc": {
                    "total_spent": payment_data.amount,
                    "loyalty_points": payment_data.amount // 100  # 1 point per dollar
                }
            }
        )
    
    response_data = {
        "payment_id": payment_id,
        "status": payment_status,
        "amount": payment_data.amount,
        "order_id": payment_data.order_id
    }
    
    if payment_data.payment_method == "cash" and payment_data.cash_received:
        response_data["change_due"] = payment_data.cash_received - payment_data.amount
    
    return response_data

# Analytics and reporting endpoints
@api_router.get("/analytics/sales-summary")
async def get_sales_summary(
    period: str = "today",  # today, week, month, year
    current_user: User = Depends(get_current_user)
):
    """Get sales summary for specified period"""
    now = datetime.now(timezone.utc)
    
    if period == "today":
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "week":
        start_date = now - timedelta(days=7)
    elif period == "month":
        start_date = now - timedelta(days=30)
    elif period == "year":
        start_date = now - timedelta(days=365)
    else:
        raise HTTPException(status_code=400, detail="Invalid period")
    
    # Aggregate sales data
    pipeline = [
        {
            "$match": {
                "created_at": {"$gte": start_date},
                "payment_status": "completed"
            }
        },
        {
            "$group": {
                "_id": None,
                "total_sales": {"$sum": "$total_amount"},
                "total_orders": {"$sum": 1},
                "avg_order_value": {"$avg": "$total_amount"}
            }
        }
    ]
    
    sales_data = await db.orders.aggregate(pipeline).to_list(length=1)
    
    if not sales_data:
        sales_data = [{
            "total_sales": 0,
            "total_orders": 0,
            "avg_order_value": 0
        }]
    
    # Get top products
    top_products_pipeline = [
        {"$match": {"created_at": {"$gte": start_date}, "payment_status": "completed"}},
        {"$unwind": "$items"},
        {
            "$group": {
                "_id": "$items.product_id",
                "product_name": {"$first": "$items.product_name"},
                "total_quantity": {"$sum": "$items.quantity"},
                "total_revenue": {"$sum": "$items.total_price"}
            }
        },
        {"$sort": {"total_quantity": -1}},
        {"$limit": 5}
    ]
    
    top_products = await db.orders.aggregate(top_products_pipeline).to_list(length=5)
    
    return {
        "period": period,
        "total_sales": sales_data[0]["total_sales"],
        "total_orders": sales_data[0]["total_orders"],
        "avg_order_value": int(sales_data[0]["avg_order_value"]) if sales_data[0]["avg_order_value"] else 0,
        "top_products": top_products
    }

# Basic endpoints
@api_router.get("/")
async def root():
    return {"message": "POS System API", "version": "1.0.0"}

@api_router.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc)}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()