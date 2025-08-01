from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session, make_response
import sqlite3
from datetime import datetime, timedelta

product_bp = Blueprint('product', __name__)

def get_db_connection():
    conn = sqlite3.connect('database/Eshop.db')
    conn.row_factory = sqlite3.Row
    return conn

# دالة جديدة لجلب الأقسام الرئيسية خصيصًا للشريط العلوي
# هذه الدالة يمكن استدعاؤها في أي route تريد أن يظهر فيه الشريط
def get_main_categories_for_navbar():
    conn = get_db_connection()
    # جلب الأقسام الرئيسية كقائمة dictionaries بدلاً من Row objects
    categories = conn.execute("""
        SELECT id, name FROM category
        WHERE parent_id IS NULL AND is_active = 1
        ORDER BY name
    """).fetchall()
    
    # تحويل كل Row إلى dictionary قابل للتعديل
    categories_dicts = []
    for category in categories:
        category_dict = dict(category)  # تحويل Row إلى dictionary
        subcategories = conn.execute("""
            SELECT id, name FROM category
            WHERE parent_id = ? AND is_active = 1
            ORDER BY name
        """, (category_dict['id'],)).fetchall()
        
        # تحويل subcategories إلى قائمة dictionaries
        category_dict['subcategories'] = [dict(sub) for sub in subcategories]
        categories_dicts.append(category_dict)
    
    conn.close()
    return categories_dicts

@product_bp.route('/')
def index():
    conn = get_db_connection()

    # هنا يمكنك جلب main_categories إذا كنت تحتاجها لعرض خاص بالصفحة الرئيسية
    # ولكن لن نمررها للشريط العلوي (header)
    main_categories = conn.execute("""
        SELECT * FROM category
        WHERE parent_id IS NULL AND is_active = 1
        ORDER BY name
    """).fetchall()
    
    products = conn.execute("SELECT * FROM product WHERE featured = 1 LIMIT 8").fetchall()

    user_id = request.cookies.get('user_auth')
    user_name = request.cookies.get('user_name')

    if user_id:
        liked_rows = conn.execute("SELECT product_id FROM likes WHERE user_id = ?", (user_id,)).fetchall()
        liked_products = [row['product_id'] for row in liked_rows]
    else:
        liked_products = []

    total_customers_data = conn.execute("SELECT COUNT(id) AS total_customers FROM user").fetchone()
    total_customers = total_customers_data['total_customers'] if total_customers_data else 0

    total_products_data = conn.execute("SELECT COUNT(id) AS total_products FROM product").fetchone()
    total_products = total_products_data['total_products'] if total_products_data else 0

    most_visited_categories = conn.execute('''
        SELECT id, name, image, view_count
        FROM category
        WHERE is_active = 1 AND parent_id IS NOT NULL
        ORDER BY view_count DESC
        LIMIT 5
    ''').fetchall()

    today = datetime.now().strftime('%Y-%m-%d')
    ads = conn.execute('''
        SELECT
            a.id,
            a.title,
            a.description,
            a.content_type,
            a.content_path,
            a.link_url,
            COALESCE(s.store_name, 'إعلان عام') AS store_name
        FROM ads a
        LEFT JOIN sellers s ON a.seller_id = s.id
        WHERE a.is_active = 1
        AND a.start_date <= ?
        AND a.end_date >= ?
        ORDER BY RANDOM()
        LIMIT 5
    ''', (today, today)).fetchall()

    for ad in ads:
        conn.execute('UPDATE ads SET impression_count = impression_count + 1 WHERE id = ?', (ad['id'],))
    conn.commit()

    conn.close()

    return render_template(
        'index.html',
        # لا تمرر main_categories للشريط هنا
        main_categories_page=main_categories, # يمكنك إعادة تسميته ليكون أوضح أنه مخصص للصفحة نفسها
        products=products,
        liked_products=liked_products,
        user_name=user_name,
        total_customers=total_customers,
        total_products=total_products,
        ads=ads,
        most_visited_categories=most_visited_categories
    )

@product_bp.route('/subcategories/<int:category_id>')
def show_subcategories(category_id):
    conn = get_db_connection()
    
    # جلب البيانات كـ dictionary
    main_category = conn.execute("""
        SELECT id, name, image 
        FROM category 
        WHERE id = ? AND is_active = 1
    """, (category_id,)).fetchone()
    
    if not main_category:
        flash("القسم الرئيسي غير موجود!", "danger")
        return redirect(url_for('product.index'))
    
    main_category = dict(main_category)  # تحويل إلى dictionary

    conn.execute('UPDATE category SET view_count = view_count + 1 WHERE id = ?', (category_id,))
    conn.commit()

    subcategories = conn.execute("""
        SELECT id, name, image 
        FROM category 
        WHERE parent_id = ? AND is_active = 1
        ORDER BY name
    """, (category_id,)).fetchall()
    
    # تحويل subcategories إلى قائمة dictionaries
    subcategories = [dict(sub) for sub in subcategories]

    products_in_main_category = conn.execute('''
        SELECT p.*, pr.profit_price, pr.original_price
        FROM product p
        LEFT JOIN prices pr ON p.price_id = pr.id
        WHERE p.category_id = ?
        ORDER BY p.id DESC
    ''', (category_id,)).fetchall()

    main_categories_for_navbar = get_main_categories_for_navbar()
    
    conn.close()

    return render_template('subcategories.html',
                         main_category=main_category,
                         subcategories=subcategories,
                         products=products_in_main_category,
                         main_categories=main_categories_for_navbar)


@product_bp.route('/category/<int:category_id>')
def show_products_by_category(category_id):
    conn = get_db_connection()
    products = []
    category_info = None
    liked_products = []

    try:
        category_info = conn.execute('SELECT id, name, view_count FROM category WHERE id = ? AND is_active = 1', (category_id,)).fetchone()

        if not category_info:
            flash("القسم غير موجود أو غير نشط!", "danger")
            return redirect(url_for('product.index'))

        conn.execute('UPDATE category SET view_count = view_count + 1 WHERE id = ?', (category_id,))
        conn.commit()

        products = conn.execute('''
            SELECT
                p.id,
                p.name,
                COALESCE(p.image, 'static/uploads/products/default_product.jpg') AS image,
                p.description,
                pr.profit_price,
                pr.original_price,
                p.featured
            FROM product p
            LEFT JOIN prices pr ON p.price_id = pr.id
            WHERE p.category_id = ?
            ORDER BY p.id DESC
        ''', (category_id,)).fetchall()

        user_id = request.cookies.get('user_auth')
        if user_id:
            liked_rows = conn.execute("SELECT product_id FROM likes WHERE user_id = ?", (user_id,)).fetchall()
            liked_products = [row['product_id'] for row in liked_rows]
            
        # *** هنا نمرر الأقسام الرئيسية للشريط ***
        main_categories_for_navbar = get_main_categories_for_navbar()

    except Exception as e:
        flash(f"حدث خطأ أثناء جلب المنتجات: {str(e)}", "danger")
        print(f"Error in show_products_by_category: {e}")
        return redirect(url_for('product.index'))
    finally:
        conn.close()

    return render_template('shop_users.html',
                            products=products,
                            liked_products=liked_products,
                            category_name=category_info['name'] if category_info else "كل المنتجات",
                            main_categories=main_categories_for_navbar # <--- تم إضافة هذا
                            )


@product_bp.route('/product/<int:product_id>', methods=['GET'])
def product_details(product_id):
    conn = get_db_connection()

    product = conn.execute('''
        SELECT
            p.id,
            p.name,
            COALESCE(p.image, 'static/uploads/products/default_product.jpg') AS image,
            p.description,
            pr.original_price,
            pr.profit_price,
            COALESCE(s.quantity, 0) AS quantity,
            c.name AS category,
            sllr.name AS seller,
            sllr.id AS seller_id,
            sa.address AS address
        FROM product p
        LEFT JOIN prices pr ON p.price_id = pr.id
        LEFT JOIN stock s ON p.stock_id = s.id
        LEFT JOIN category c ON p.category_id = c.id
        LEFT JOIN sellers sllr ON p.seller_id = sllr.id
        LEFT JOIN seller_address sa ON sllr.SAddress_id = sa.id
        WHERE p.id = ?
    ''', (product_id,)).fetchone()

    if product is None:
        return "المنتج غير موجود", 404

    product_images = conn.execute('''
        SELECT * FROM product_image WHERE product_id = ? ORDER BY is_main DESC
    ''', (product_id,)).fetchall()

    related_products = conn.execute('''
        SELECT p.id, p.name, COALESCE(p.image, 'static/uploads/products/default_product.jpg') AS image, pr.profit_price
        FROM product p
        LEFT JOIN prices pr ON p.price_id = pr.id
        WHERE p.category_id = (SELECT category_id FROM product WHERE id = ?) AND p.id != ?
        LIMIT 4
    ''', (product_id, product_id)).fetchall()
    
    # *** هنا نمرر الأقسام الرئيسية للشريط ***
    main_categories_for_navbar = get_main_categories_for_navbar()

    conn.close()

    return render_template(
        'shop-details.html',
        product=product,
        product_images=product_images,
        related_products=list(related_products),
        quantity=product['quantity'],
        main_categories=main_categories_for_navbar # <--- تم إضافة هذا
    )

@product_bp.route('/show_product1', methods=['GET'])
def show_product1(): # هذه هي دالة عرض المنتجات المميزة (ربما "الكل" أو "منتجات مميزة")
    user_id = request.cookies.get('user_auth')
    conn = get_db_connection()

    products = conn.execute('''
        SELECT
            p.id,
            p.name,
            COALESCE(p.image, 'static/uploads/products/default_product.jpg') AS image,
            p.description,
            pr.original_price,
            pr.profit_price,
            s.quantity,
            c.name AS category,
            p.featured
        FROM product p
        LEFT JOIN prices pr ON p.price_id = pr.id
        LEFT JOIN stock s ON p.stock_id = s.id
        LEFT JOIN category c ON p.category_id = c.id
        WHERE p.featured = 1
        ORDER BY p.id DESC
    ''').fetchall()

    liked_products = []
    if user_id:
        liked_products = conn.execute('''
            SELECT product_id FROM likes WHERE user_id = ?
        ''', (user_id,)).fetchall()
        liked_products = [p['product_id'] for p in liked_products]
    
    # *** هنا نمرر الأقسام الرئيسية للشريط ***
    main_categories_for_navbar = get_main_categories_for_navbar()

    conn.close()

    return render_template('shop_user.html', # ربما يجب تغيير اسم القالب إلى shop_products.html ليكون أوضح
                            products=products,
                            liked_products=liked_products,
                            main_categories=main_categories_for_navbar # <--- تم إضافة هذا
                            )