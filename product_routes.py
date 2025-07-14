from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session, make_response
import sqlite3

product_bp = Blueprint('product', __name__) # لا بادئة هنا، مسارات المنتج في الجذر

def get_db_connection():
    conn = sqlite3.connect('database/Eshop.db')
    conn.row_factory = sqlite3.Row
    return conn

@product_bp.route('/')
def index():
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row # التأكد من أن row_factory مضبوط لسهولة الوصول للبيانات بالأسماء

    # جلب التصنيفات الرئيسية النشطة فقط (is_active = 1)
    main_categories = conn.execute("""
        SELECT * FROM category
        WHERE parent_id IS NULL AND is_active = 1
        ORDER BY name
    """).fetchall()

    # جلب المنتجات (تأكد أنك بحاجة لجلب كل المنتجات هنا إذا كانت الصفحة الرئيسية بها عرض للمنتجات)
    products = conn.execute("SELECT * FROM product").fetchall()

    # جلب معرف المستخدم
    user_id = request.cookies.get('user_auth')
    user_name = request.cookies.get('user_name')

    # جلب المنتجات التي أعجب بها المستخدم
    if user_id:
        liked_rows = conn.execute("SELECT product_id FROM likes WHERE user_id = ?", (user_id,)).fetchall()
        liked_products = [row['product_id'] for row in liked_rows]
    else:
        liked_products = []

    # 📊 جلب عدد العملاء الكلي من جدول 'user' 🆕
    cursor = conn.cursor() # يمكنك استخدام نفس الـ conn لكن قد تحتاج لمؤشر جديد أحياناً أو تكتفي بـ conn.execute مباشرة
    cursor.execute("SELECT COUNT(id) AS total_customers FROM user")
    total_customers_data = cursor.fetchone()
    total_customers = total_customers_data['total_customers'] if total_customers_data else 0

    # 📦 جلب عدد المنتجات الكلي من جدول 'product' 🆕
    cursor.execute("SELECT COUNT(id) AS total_products FROM product")
    total_products_data = cursor.fetchone()
    total_products = total_products_data['total_products'] if total_products_data else 0

    conn.close()

    return render_template(
        'index.html',
        main_categories=main_categories,
        products=products,
        liked_products=liked_products,
        user_name=user_name,
        total_customers=total_customers, # 🆕 تمرير عدد العملاء
        total_products=total_products    # 🆕 تمرير عدد المنتجات
    )


@product_bp.route('/subcategories/<int:category_id>')
def show_subcategories(category_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    main_category = cursor.execute("SELECT id, name FROM category WHERE id = ?", (category_id,)).fetchone()
    subcategories = cursor.execute("SELECT id, name, image FROM category WHERE parent_id = ?", (category_id,)).fetchall()
    categories = cursor.execute("SELECT * FROM category WHERE parent_id IS NULL").fetchall()

    # معالجة الصور مع التحقق من وجودها
    processed_subcategories = []
    for id, name, image in subcategories:
        if image:  # إذا كانت الصورة موجودة
            image_path = url_for('static', filename=f"uploads/category_img/{image.split('/')[-1]}")
        else:  # إذا كانت الصورة غير موجودة (NULL)
            image_path = url_for('static', filename='images/default_category.png')  # صورة افتراضية

        processed_subcategories.append((id, name, image_path))

    conn.close()
    return render_template('subcategories.html',
                         main_category=main_category,
                         subcategories=processed_subcategories,
                         categories=categories)



@product_bp.route('/category/<int:category_id>')
def show_products_by_category(category_id):
    conn = get_db_connection()
# في الدالة التي تجلب المنتجات (مثلاً show_products_by_category)
    products = conn.execute('''
        SELECT 
            p.id,
            p.name,
            COALESCE(p.image, 'static/uploads/products/default_product.jpg') AS image,
            p.description,
            pr.profit_price,
            p.featured
        FROM product p
        LEFT JOIN prices pr ON p.price_id = pr.id
        WHERE p.category_id = ?
    ''', (category_id,)).fetchall()

    conn.close()
    return render_template('shop_users.html', products=products)


@product_bp.route('/product/<int:product_id>', methods=['GET'])
def product_details(product_id):
    conn = get_db_connection()
    
    # جلب بيانات المنتج الأساسية مع ضمان وجود مسار صورة افتراضي
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

    # جلب جميع صور المنتج
    product_images = conn.execute('''
        SELECT * FROM product_image WHERE product_id = ? ORDER BY is_main DESC
    ''', (product_id,)).fetchall()

    # جلب المنتجات ذات الصلة
    related_products = conn.execute('''
        SELECT p.id, p.name, COALESCE(p.image, 'static/uploads/products/default_product.jpg') AS image, pr.profit_price
        FROM product p
        LEFT JOIN prices pr ON p.price_id = pr.id
        WHERE p.category_id = (SELECT category_id FROM product WHERE id = ?) AND p.id != ?
        LIMIT 4
    ''', (product_id, product_id)).fetchall()

    conn.close()

    return render_template(
        'shop-details.html',
        product=product,
        product_images=product_images,
        related_products=list(related_products),
        quantity=product['quantity']
    )



@product_bp.route('/show_product1', methods=['GET'])
def show_product1():
    user_id = session.get('user_id')

    conn = get_db_connection()

    # جلب المنتجات المميزة
    products = conn.execute('''
        SELECT
            p.id,
            p.name,
            p.image,
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

    # جلب المنتجات المعجبة إذا كان المستخدم مسجل الدخول
    liked_products = []
    if user_id:
        liked_products = conn.execute('''
            SELECT product_id FROM likes WHERE user_id = ?
        ''', (user_id,)).fetchall()
        liked_products = [p['product_id'] for p in liked_products]

    conn.close()

    return render_template('shop_user.html',
                         products=products,
                         liked_products=liked_products)