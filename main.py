from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any
import sqlite3
from datetime import datetime

app = FastAPI(title="Kopitiam API", version="2.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_FILE = "kopitiam.db"

# ==========================================
# SAFE DATABASE CONNECTION MANAGER
# ==========================================
def get_db():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False, timeout=15.0)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

# ==========================================
# DATABASE SETUP (Run on Startup)
# ==========================================
@app.on_event("startup")
def setup_database():
    db = sqlite3.connect(DB_FILE, check_same_thread=False, timeout=15.0)
    cursor = db.cursor()
    cursor.executescript('''
        CREATE TABLE IF NOT EXISTS Inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            unit TEXT NOT NULL,
            current_stock REAL NOT NULL,
            safety_stock REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS Menu (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT,
            price REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS Recipes (
            menu_id INTEGER,
            inventory_id INTEGER,
            amount_needed REAL NOT NULL,
            FOREIGN KEY(menu_id) REFERENCES Menu(id) ON DELETE CASCADE,
            FOREIGN KEY(inventory_id) REFERENCES Inventory(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS SalesLog (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            menu_id INTEGER,
            qty INTEGER NOT NULL,
            total_price REAL NOT NULL,
            FOREIGN KEY(menu_id) REFERENCES Menu(id) ON DELETE CASCADE
        );
    ''')
    
    cursor.execute("SELECT COUNT(*) FROM Inventory")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("INSERT INTO Inventory (name, unit, current_stock, safety_stock) VALUES (?, ?, ?, ?)", [
            ('Coffee Powder', 'kg', 10.0, 2.5),
            ('Tea Bags', 'pcs', 150.0, 30.0), # Updated to track by individual bags
            ('Sugar', 'kg', 10.0, 3.0),
            ('Evaporated Milk', 'tin', 48.0, 12.0)
        ])
    db.commit()
    db.close()

# ==========================================
# PYDANTIC MODELS
# ==========================================
class SaleRequest(BaseModel):
    menu_id: int
    qty: int

class BatchSaleRequest(BaseModel):
    date: str
    items: List[SaleRequest]

class InventoryItem(BaseModel):
    name: str; unit: str; current_stock: float; safety_stock: float
class MenuItem(BaseModel):
    name: str; category: str; price: float
class RecipeItem(BaseModel):
    inventory_id: int; amount_needed: float
class RecipeUpdate(BaseModel):
    recipe: List[RecipeItem]

# ==========================================
# CORE APIs 
# ==========================================
@app.get("/api/inventory")
def get_inventory(db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM Inventory")
    items = [dict(row) for row in cursor.fetchall()]
    for item in items: item['is_low_stock'] = item['current_stock'] <= item['safety_stock']
    return items

@app.post("/api/inventory")
def add_inventory(item: InventoryItem, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("INSERT INTO Inventory (name, unit, current_stock, safety_stock) VALUES (?, ?, ?, ?)",
                   (item.name, item.unit, item.current_stock, item.safety_stock))
    db.commit()
    return {"status": "success"}

@app.put("/api/inventory/{inv_id}")
def update_inventory(inv_id: int, item: InventoryItem, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("UPDATE Inventory SET name=?, unit=?, current_stock=?, safety_stock=? WHERE id=?",
                   (item.name, item.unit, item.current_stock, item.safety_stock, inv_id))
    db.commit()
    return {"status": "success"}

@app.get("/api/menu")
def get_menu(db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM Menu")
    return [dict(row) for row in cursor.fetchall()]

@app.post("/api/menu")
def add_menu(item: MenuItem, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("INSERT INTO Menu (name, category, price) VALUES (?, ?, ?)", (item.name, item.category, item.price))
    db.commit()
    return {"status": "success", "id": cursor.lastrowid}

@app.delete("/api/menu/{menu_id}")
def delete_menu(menu_id: int, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("DELETE FROM Menu WHERE id = ?", (menu_id,))
    db.commit()
    return {"status": "success"}

@app.get("/api/menu/{menu_id}/recipe")
def get_recipe(menu_id: int, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("""SELECT r.inventory_id, i.name, i.unit, r.amount_needed FROM Recipes r JOIN Inventory i ON r.inventory_id = i.id WHERE r.menu_id = ?""", (menu_id,))
    return [dict(row) for row in cursor.fetchall()]

@app.post("/api/menu/{menu_id}/recipe")
def update_recipe(menu_id: int, req: RecipeUpdate, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("DELETE FROM Recipes WHERE menu_id = ?", (menu_id,))
    for item in req.recipe:
        cursor.execute("INSERT INTO Recipes (menu_id, inventory_id, amount_needed) VALUES (?, ?, ?)", (menu_id, item.inventory_id, item.amount_needed))
    db.commit()
    return {"status": "success"}

@app.post("/api/import-menu")
def import_legacy_menu(data: Dict[str, Any], db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT id, name FROM Inventory")
    inv_map = {row['name'].lower(): row['id'] for row in cursor.fetchall()}
    
    # Map to the new Tea Bags ingredient
    coffee_id, tea_id = inv_map.get('coffee powder'), inv_map.get('tea bags')
    
    added_count = 0
    for drink_name, drink_data in data.items():
        for t_data in drink_data.get("temperature", []):
            dtype = t_data.get("type", "")
            cursor.execute("INSERT INTO Menu (name, category, price) VALUES (?, ?, ?)", (f"{drink_name} ({dtype})", "Drink", t_data.get("price", 0.0)))
            m_id = cursor.lastrowid
            added_count += 1
            
            # Map standard size BOM
            if "Kopi" in drink_name and coffee_id: 
                cursor.execute("INSERT INTO Recipes (menu_id, inventory_id, amount_needed) VALUES (?, ?, ?)", (m_id, coffee_id, 0.01 if dtype == "Hot" else 0.02))
            elif "Teh" in drink_name and tea_id: 
                # 1 bag for Hot, 2 bags for Cold
                cursor.execute("INSERT INTO Recipes (menu_id, inventory_id, amount_needed) VALUES (?, ?, ?)", (m_id, tea_id, 1.0 if dtype == "Hot" else 2.0))
            
            # Map Big size BOM
            if "price_big" in t_data:
                cursor.execute("INSERT INTO Menu (name, category, price) VALUES (?, ?, ?)", (f"{drink_name} ({dtype} - Big)", "Drink", t_data["price_big"]))
                m_id_big = cursor.lastrowid
                added_count += 1
                if "Kopi" in drink_name and coffee_id: 
                    cursor.execute("INSERT INTO Recipes (menu_id, inventory_id, amount_needed) VALUES (?, ?, ?)", (m_id_big, coffee_id, 0.02))
                elif "Teh" in drink_name and tea_id: 
                    # 2 bags for Big
                    cursor.execute("INSERT INTO Recipes (menu_id, inventory_id, amount_needed) VALUES (?, ?, ?)", (m_id_big, tea_id, 2.0))
    db.commit()
    return {"status": "success", "imported": added_count}

# ==========================================
# DAILY BATCH SALES & COMPARISON ANALYTICS
# ==========================================
@app.post("/api/sell/batch")
def process_batch_sale(req: BatchSaleRequest, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    
    for sale in req.items:
        cursor.execute("SELECT price FROM Menu WHERE id = ?", (sale.menu_id,))
        menu_item = cursor.fetchone()
        if not menu_item: continue
        
        cursor.execute("SELECT inventory_id, amount_needed FROM Recipes WHERE menu_id = ?", (sale.menu_id,))
        recipe = cursor.fetchall()
        
        for ingredient in recipe:
            cursor.execute("UPDATE Inventory SET current_stock = current_stock - ? WHERE id = ?",
                           (ingredient['amount_needed'] * sale.qty, ingredient['inventory_id']))
            
        total_price = menu_item['price'] * sale.qty
        cursor.execute("INSERT INTO SalesLog (date, menu_id, qty, total_price) VALUES (?, ?, ?, ?)",
                       (req.date, sale.menu_id, sale.qty, total_price))
                       
    db.commit()
    return {"status": "success", "message": f"Saved {len(req.items)} records for {req.date}."}

@app.get("/api/analytics/compare")
def compare_analytics(d1: str, d2: str, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    
    def get_day_stats(query_date):
        cursor.execute("SELECT SUM(total_price) as rev, SUM(qty) as cups FROM SalesLog WHERE date = ?", (query_date,))
        totals = cursor.fetchone()
        
        cursor.execute("""
            SELECT i.name, SUM(r.amount_needed * s.qty) as expected_used, i.unit
            FROM SalesLog s
            JOIN Recipes r ON s.menu_id = r.menu_id
            JOIN Inventory i ON r.inventory_id = i.id
            WHERE s.date = ?
            GROUP BY i.id
        """, (query_date,))
        usage = [dict(row) for row in cursor.fetchall()]
        
        return {
            "revenue": totals['rev'] or 0.0,
            "cups": totals['cups'] or 0,
            "usage": usage
        }

    return {
        "date1": get_day_stats(d1),
        "date2": get_day_stats(d2)
    }

@app.get("/api/analytics")
def get_analytics(db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT COUNT(DISTINCT date) FROM SalesLog")
    days_active = cursor.fetchone()[0] or 1
    
    cursor.execute("SELECT SUM(total_price) as rev, SUM(qty) as cups FROM SalesLog")
    totals = cursor.fetchone()
    total_rev = totals['rev'] or 0.0
    total_qty = totals['cups'] or 0
    
    cursor.execute("""
        SELECT m.name, SUM(s.qty) as total_qty, SUM(s.total_price) as total_rev 
        FROM SalesLog s JOIN Menu m ON s.menu_id = m.id 
        GROUP BY m.id ORDER BY total_qty DESC LIMIT 5
    """)
    top_items = [dict(row) for row in cursor.fetchall()]
    
    cursor.execute("""
        SELECT date as day, SUM(total_price) as daily_rev 
        FROM SalesLog GROUP BY day ORDER BY day DESC LIMIT 7
    """)
    trend = [dict(row) for row in cursor.fetchall()]
    
    return {
        "revenue": total_rev,
        "items_sold": total_qty,
        "avg_daily_rev": total_rev / days_active,
        "avg_daily_qty": total_qty / days_active,
        "top_items": top_items,
        "trend": trend
    }