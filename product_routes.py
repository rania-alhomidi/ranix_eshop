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

    # --- بداية التعديل: جلب المنتجات الأكثر شراءً ---
    # هذا الاستعلام يحسب مجموع الكميات المباعة لكل منتج ويرتبها تنازلياً.
    most_bought_products = conn.execute('''
        SELECT
            p.id,
            p.name,
            -- استخدم COALESCE لجلب مسار الصورة الرئيسية أو صورة افتراضية
            COALESCE(pi.image_path, 'uploads/products/default_product.jpg') AS image,
            pr.profit_price,
            SUM(oi.quantity) AS total_sold
        FROM order_items oi
        JOIN product p ON oi.product_id = p.id
        LEFT JOIN prices pr ON p.price_id = pr.id
        LEFT JOIN product_image pi ON p.id = pi.product_id AND pi.is_main = 1
        GROUP BY p.id
        ORDER BY total_sold DESC
        LIMIT 8  -- عرض أفضل 8 منتجات فقط
    ''').fetchall()
    # --- نهاية التعديل ---

    # ... (بقية الكود الخاص بجلب المنتجات المميزة والبيانات الأخرى)
    main_categories = conn.execute("""
        SELECT * FROM category
        WHERE parent_id IS NULL AND is_active = 1
        ORDER BY name
    """).fetchall()
    
    products = conn.execute("SELECT * FROM product WHERE featured = 1 LIMIT 8").fetchall()

    user_id = request.cookies.get('user_auth')
    user_name = request.cookies.get('user_name')

   
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
        main_categories_page=main_categories,
        products=products, # هذه المنتجات المميزة (featured products)
        # liked_products=liked_products,
        user_name=user_name,
        total_customers=total_customers,
        total_products=total_products,
        ads=ads,
        most_visited_categories=most_visited_categories,
        most_bought_products=most_bought_products  # <--- تمرير المنتجات الأكثر مبيعاً إلى القالب
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
# في دالة show_products_by_category
        products = conn.execute('''
            SELECT
                p.id,
                p.name,
                COALESCE(p.image, 'static/uploads/products/default_product.jpg') AS image,
                p.description,
                pr.profit_price,
                pr.original_price,
                p.featured,
                -- ✅ إضافة حقل متوسط التقييم ✅
                (SELECT AVG(rating) FROM product_ratings WHERE product_id = p.id) AS avg_rating
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


# ... (الكود السابق) ...

@product_bp.route('/product/<int:product_id>', methods=['GET'])
def product_details(product_id):
    conn = get_db_connection()

    # جلب تفاصيل المنتج (الكود الحالي لديك)
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

    # جلب جميع التقييمات لهذا المنتج
    ratings = conn.execute('''
        SELECT 
            r.rating,
            r.review_text,
            r.created_at,
            u.name AS user_name
        FROM product_ratings r
        JOIN user u ON r.user_id = u.id
        WHERE r.product_id = ?
        ORDER BY r.created_at DESC
    ''', (product_id,)).fetchall()

    # حساب متوسط التقييم وعدد التقييمات الإجمالي
    avg_rating_row = conn.execute(
        'SELECT AVG(rating) AS avg_rating, COUNT(id) AS total_ratings FROM product_ratings WHERE product_id = ?',
        (product_id,)
    ).fetchone()
    
    avg_rating = round(avg_rating_row['avg_rating'], 1) if avg_rating_row['avg_rating'] else 0
    total_ratings = avg_rating_row['total_ratings']

    product_images = conn.execute('''
        SELECT * FROM product_image WHERE product_id = ? ORDER BY is_main DESC
    ''', (product_id,)).fetchall()

    related_products = conn.execute('''
        SELECT 
            p.id, 
            p.name, 
            COALESCE(p.image, 'static/uploads/products/default_product.jpg') AS image,
            pr.profit_price,
            (SELECT AVG(rating) FROM product_ratings WHERE product_id = p.id) AS avg_rating
        FROM product p
        LEFT JOIN prices pr ON p.price_id = pr.id
        WHERE 
            p.id != ? AND 
            p.category_id = (SELECT category_id FROM product WHERE id = ?)
        LIMIT 4
    ''', (product_id, product_id)).fetchall()
    
    main_categories_for_navbar = get_main_categories_for_navbar()
    conn.close()

    # تمرير البيانات الجديدة إلى القالب
    return render_template(
        'shop-details.html',
        product=product,
        product_images=product_images,
        related_products=related_products, # ✅ تم تعديل هذا ✅
        quantity=product['quantity'],
        main_categories=main_categories_for_navbar,
        ratings=ratings,
        avg_rating=avg_rating,
        total_ratings=total_ratings
    )


@product_bp.route('/show_product1', methods=['GET'])
def show_product1(): # هذه هي دالة عرض المنتجات المميزة (ربما "الكل" أو "منتجات مميزة")
    user_id = request.cookies.get('user_auth')
    conn = get_db_connection()

    # في دالة show_product1
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
            p.featured,
            -- ✅ إضافة حقل متوسط التقييم ✅
            (SELECT AVG(rating) FROM product_ratings WHERE product_id = p.id) AS avg_rating
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


# تقييمات المستخدم

@product_bp.route('/product/<int:product_id>/rate', methods=['POST'])
def add_rating(product_id):
    # التأكد من أن المستخدم مسجل الدخول
    user_id = request.cookies.get('user_auth')
    if not user_id:
        return jsonify({'success': False, 'message': 'يجب تسجيل الدخول لإضافة تقييم.'}), 401

    data = request.get_json()
    rating = data.get('rating')
    review_text = data.get('review_text', '')

    if not rating:
        return jsonify({'success': False, 'message': 'التقييم مطلوب.'}), 400

    conn = get_db_connection()
    try:
        # التحقق مما إذا كان المستخدم قد قام بالتقييم من قبل
        existing_rating = conn.execute(
            'SELECT 1 FROM product_ratings WHERE product_id = ? AND user_id = ?',
            (product_id, user_id)
        ).fetchone()

        if existing_rating:
            # يمكن أن تسمح بتحديث التقييم بدلاً من منعه
            conn.execute(
                'UPDATE product_ratings SET rating = ?, review_text = ?, created_at = CURRENT_TIMESTAMP WHERE product_id = ? AND user_id = ?',
                (rating, review_text, product_id, user_id)
            )
            message = 'تم تحديث تقييمك بنجاح!'
        else:
            conn.execute(
                'INSERT INTO product_ratings (product_id, user_id, rating, review_text) VALUES (?, ?, ?, ?)',
                (product_id, user_id, rating, review_text)
            )
            message = 'تم إضافة تقييمك بنجاح!'
        
        conn.commit()
        
        # إعادة حساب متوسط التقييمات وعددها
        avg_rating_row = conn.execute(
            'SELECT AVG(rating) AS avg_rating, COUNT(id) AS total_ratings FROM product_ratings WHERE product_id = ?',
            (product_id,)
        ).fetchone()
        
        avg_rating = round(avg_rating_row['avg_rating'], 1) if avg_rating_row['avg_rating'] else 0
        total_ratings = avg_rating_row['total_ratings']
        
    except sqlite3.Error as e:
        conn.rollback()
        return jsonify({'success': False, 'message': f'خطأ في قاعدة البيانات: {str(e)}'}), 500
    finally:
        conn.close()

    return jsonify({
        'success': True,
        'message': message,
        'avg_rating': avg_rating,
        'total_ratings': total_ratings
    })