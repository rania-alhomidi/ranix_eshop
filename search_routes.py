from flask import Flask,Blueprint, render_template, request, redirect, url_for, flash, jsonify, session, make_response
import sqlite3
import os
import json
from datetime import datetime, timedelta

search_bp = Blueprint('search_bp', __name__)

def get_db_connection():
    conn = sqlite3.connect('database/Eshop.db')
    conn.row_factory = sqlite3.Row
    return conn

@search_bp.route('/search', methods=['GET'])
def search_products():
    # جلب معايير البحث
    query = request.args.get('q', '').strip()
    category_id = request.args.get('category_id', type=int)
    brand = request.args.get('brand', '').strip()
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    sort_by = request.args.get('sort_by', 'name_asc')

    conn = get_db_connection()
    
    # بناء الاستعلام (من الكود الأصلي مع تعديلات)
    sql_query = """
    SELECT 
        p.id, 
        p.name, 
        p.description, 
        p.featured,
        pr.profit_price AS price,
        c.name AS category_name,
        s.store_name AS seller_name,
        COALESCE(
            (SELECT pi.image_path FROM product_image pi WHERE pi.product_id = p.id LIMIT 1),
            'default_images/product_default.jpg'
        ) AS image,
        st.quantity AS stock_quantity
    FROM product p
    JOIN prices pr ON p.price_id = pr.id
    JOIN category c ON p.category_id = c.id
    JOIN sellers s ON p.seller_id = s.id
    JOIN stock st ON p.stock_id = st.id
    WHERE st.quantity > 0
    """
    
    params = []
    
    # إضافة شروط البحث (من الكود الأصلي)
    if query:
        sql_query += " AND (p.name LIKE ? OR p.description LIKE ? OR c.name LIKE ? OR s.store_name LIKE ?)"
        params.extend([f'%{query}%', f'%{query}%', f'%{query}%', f'%{query}%'])
    
    if category_id:
        sql_query += " AND c.id = ?"
        params.append(category_id)
        
    if brand:
        sql_query += " AND s.store_name LIKE ?"
        params.append(f'%{brand}%')
        
    if min_price is not None:
        sql_query += " AND pr.profit_price >= ?"
        params.append(min_price)
    
    if max_price is not None:
        sql_query += " AND pr.profit_price <= ?"
        params.append(max_price)

    # إضافة الترتيب (من الكود الأصلي)
    if sort_by == 'price_asc':
        sql_query += " ORDER BY pr.profit_price ASC"
    elif sort_by == 'price_desc':
        sql_query += " ORDER BY pr.profit_price DESC"
    elif sort_by == 'newest':
        sql_query += " ORDER BY p.created_at DESC"
    elif sort_by == 'featured':
        sql_query += " ORDER BY p.featured DESC, p.name ASC"
    else:
        sql_query += " ORDER BY p.name ASC"

    try:
        products = conn.execute(sql_query, tuple(params)).fetchall()
        
        # AJAX/API Request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            products_list = [dict(product) for product in products]
            return jsonify({
                "success": True,
                "products": products_list,
                "count": len(products_list)
            })
        
        # Normal HTML Request
        return render_template('search_results.html',
                            products=products,
                            search_query=query,
                            category_id=category_id,
                            brand=brand,
                            min_price=min_price,
                            max_price=max_price,
                            sort_by=sort_by)
            
    except sqlite3.Error as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                "success": False,
                "error": str(e),
                "message": "حدث خطأ في جلب المنتجات"
            }), 500
        else:
            flash("حدث خطأ أثناء البحث. يرجى المحاولة مرة أخرى.", "error")
            return redirect(url_for('product.index'))
            
    finally:
        conn.close()


        
# نقطة نهاية لجلب الفئات لملء الفلاتر
@search_bp.route('/get_categories', methods=['GET'])
def get_categories():
    conn = get_db_connection()
    try:
        cursor = conn.execute("SELECT id, name FROM category WHERE is_active = 1 ORDER BY name ASC")
        categories = [{"id": row['id'], "name": row['name']} for row in cursor.fetchall()]
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return jsonify({"error": "Failed to retrieve categories"}), 500
    finally:
        conn.close()
    return jsonify(categories)

# نقطة نهاية لجلب الماركات/البائعين لملء الفلاتر
@search_bp.route('/get_brands', methods=['GET'])
def get_brands():
    conn = get_db_connection()
    try:
        cursor = conn.execute("SELECT DISTINCT store_name FROM sellers ORDER BY store_name ASC")
        brands = [row['store_name'] for row in cursor.fetchall()]
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return jsonify({"error": "Failed to retrieve brands"}), 500
    finally:
        conn.close()
    return jsonify(brands)

# نقطة نهاية لاقتراحات البحث التلقائية
@search_bp.route('/suggestions', methods=['GET'])
def get_suggestions():
    term = request.args.get('term', '').strip()
    conn = get_db_connection()
    suggestions = []
    if term:
        try:
            # البحث عن أسماء المنتجات والفئات التي تبدأ بالكلمة المدخلة
            cursor_products = conn.execute("SELECT DISTINCT name FROM product WHERE name LIKE ? LIMIT 5", (f'{term}%',))
            suggestions.extend([row['name'] for row in cursor_products.fetchall()])
            
            cursor_categories = conn.execute("SELECT DISTINCT name FROM category WHERE name LIKE ? LIMIT 5", (f'{term}%',))
            suggestions.extend([row['name'] for row in cursor_categories.fetchall()])
            
            # إزالة التكرارات والحفاظ على عدد محدود
            suggestions = list(set(suggestions))[:7] # يمكن ضبط العدد
            suggestions.sort() # ترتيب أبجدي للاقتراحات
            
        except sqlite3.Error as e:
            print(f"Database error: {e}")
        finally:
            conn.close()
    return jsonify(suggestions)

