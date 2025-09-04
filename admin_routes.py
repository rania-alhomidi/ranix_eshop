from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session, make_response
import sqlite3
import os
import traceback
import uuid  # أضف هذا السطر مع باقي الاستيرادات
from werkzeug.utils import secure_filename

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}

def get_db_connection():
    conn = sqlite3.connect('database/Eshop.db')
    conn.row_factory = sqlite3.Row
    return conn


# 🆕 دالة جديدة لجلب المنتجات الأكثر مبيعاً
def get_top_selling_products():
    conn = get_db_connection()
    try:
        query = """
        SELECT
            p.name AS product_name,
            p.image AS image,
            SUM(oi.price * oi.quantity) AS total_price,
            SUM(oi.quantity) AS total_sales
        FROM Order_Items oi
        JOIN product p ON oi.product_id = p.id
        GROUP BY p.id
        ORDER BY total_sales DESC
        LIMIT 5;
        """
        top_products = conn.execute(query).fetchall()
        return [dict(row) for row in top_products]
    except sqlite3.Error as e:
        print(f"Database error getting top selling products: {e}")
        return []
    finally:
        conn.close()

# Add this new function to get the latest activity from the database
def get_latest_activity():
    conn = get_db_connection()
    try:
        # This is a complex query to demonstrate fetching various types of activities.
        # It's a UNION of different queries for different event types.
        query = """
        SELECT
            'order_status' AS event_type,
            o.id AS item_id,
            'تم تعديل حالة الطلب #' || o.id || ' إلى "' || o.status || '"' AS description,
            o.order_date AS timestamp,
            'bi-arrow-repeat text-primary' AS icon_class
        FROM orders o
        ORDER BY o.order_date DESC
        LIMIT 2
        
        UNION ALL
        
        SELECT
            'product_creation' AS event_type,
            p.id AS item_id,
            'تمت إضافة منتج جديد: ' || p.name AS description,
            p.created_at AS timestamp,
            'bi-plus-circle-fill text-success' AS icon_class
        FROM product p
        ORDER BY p.created_at DESC
        LIMIT 2
        
        UNION ALL
        
        SELECT
            'seller_creation' AS event_type,
            s.id AS item_id,
            'تم إنشاء حساب جديد لبائع ' || s.name AS description,
            s.created_at AS timestamp,
            'bi-shop text-info' AS icon_class
        FROM sellers s
        ORDER BY s.created_at DESC
        LIMIT 2
        
        ORDER BY timestamp DESC
        LIMIT 5;
        """
        # Note: The UNION ALL is a simplified example. A real-world scenario
        # might require a dedicated 'activity_log' table for efficiency.

        latest_activities = conn.execute(query).fetchall()
        return [dict(row) for row in latest_activities]
    except sqlite3.Error as e:
        print(f"Database error getting latest activity: {e}")
        return []
    finally:
        conn.close()


@admin_bp.route('/')
def home():
    conn = get_db_connection()
    cursor = conn.cursor()

    # جلب عدد العملاء الكلي
    cursor.execute("SELECT COUNT(id) AS total_customers FROM user")
    total_customers_data = cursor.fetchone()
    total_customers = total_customers_data['total_customers'] if total_customers_data else 0

    # جلب عدد المنتجات الكلي
    cursor.execute("SELECT COUNT(id) AS total_products FROM product")
    total_products_data = cursor.fetchone()
    total_products = total_products_data['total_products'] if total_products_data else 0

    # 📁🆕 جلب عدد الأقسام الفرعية فقط (التي لها parent_id)
    cursor.execute("SELECT COUNT(id) AS total_subcategories FROM category WHERE parent_id IS NOT NULL")
    total_subcategories_data = cursor.fetchone()
    total_subcategories = total_subcategories_data['total_subcategories'] if total_subcategories_data else 0

# 📁🆕 جلب عدد الأقسام الرئيسية فقط (التي ليس لها parent_id)
    cursor.execute("SELECT COUNT(id) AS total_main_categories FROM category WHERE parent_id IS NULL")
    total_main_categories_data = cursor.fetchone()
    total_main_categories = total_main_categories_data['total_main_categories'] if total_main_categories_data else 0


    # 🆕 جلب عدد البائعين الكلي
    cursor.execute("SELECT COUNT(id) AS total_sellers FROM sellers") # بافتراض أن جدول البائعين اسمه 'sellers'
    total_sellers_data = cursor.fetchone()
    total_sellers = total_sellers_data['total_sellers'] if total_sellers_data else 0


 # 🆕 استعلامات المقاييس الجديدة
    total_orders = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    pending_orders = conn.execute("SELECT COUNT(*) FROM orders WHERE status = 'قيد الانتظار'").fetchone()[0]
    total_purchases = conn.execute("SELECT SUM(total_price) FROM orders").fetchone()[0] or 0.0

     # 🆕 استدعاء الدالة الجديدة
    top_selling_products = get_top_selling_products()

# جلب النشاط الأخير (New)
    latest_activities = get_latest_activity()

    conn.close()

    # تمرير جميع الإحصائيات إلى القالب
    return render_template('admin/index.html',
                           total_customers=total_customers,
                           total_products=total_products,
                           total_subcategories=total_subcategories, # 🆕 تمرير عدد الأقسام الفرعية
                           total_main_categories=total_main_categories, # 🆕 تمرير عدد الأقسام الرئيسية
                           total_sellers=total_sellers,
                           total_orders=total_orders,
                           pending_orders=pending_orders,
                           total_purchases=total_purchases,
                           top_selling_products=top_selling_products, # 🆕 تمرير قائمة المنتجات الأكثر مبيعاً للقالب
                           latest_activities=latest_activities # Pass the new data to the template

                          )


@admin_bp.route('/profile')
def profile():
    return render_template('admin/profile.html')

@admin_bp.route('/cate', methods=['GET', 'POST'])
def add_category():
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        name = request.form['name']
        parent_id = request.form.get('parent')
        image = request.files.get('image')
        is_active = 1 if request.form.get('is_active') == '1' else 0

        cursor.execute('SELECT id FROM category WHERE name = ?', (name,))
        if cursor.fetchone():
            flash('هذا القسم موجود بالفعل!', 'danger')
            return redirect(url_for('admin.add_category'))

        parent_id = int(parent_id) if parent_id and parent_id.isdigit() else None

        image_path = None
        if image and image.filename:
            upload_folder = os.path.join(UPLOAD_FOLDER, 'category_img')
            os.makedirs(upload_folder, exist_ok=True)
            filename = secure_filename(image.filename)
            filepath = os.path.join(upload_folder, filename)
            image.save(filepath)
            image_path = f'static/uploads/category_img/{filename}'

        cursor.execute(
            'INSERT INTO category (name, parent_id, image, is_active) VALUES (?, ?, ?, ?)',
            (name, parent_id, image_path, is_active)
        )
        conn.commit()
        conn.close()
        flash('تم إضافة القسم بنجاح!', 'success')
        return redirect(url_for('admin.categories'))

    categories = conn.execute('SELECT id, name FROM category').fetchall()
    conn.close()
    return render_template('admin/cate.html', categories=categories)

@admin_bp.route('/toggle_category/<int:category_id>/<int:status>')
def toggle_category(category_id, status):
    conn = get_db_connection()
    try:
        conn.execute('UPDATE category SET is_active = ? WHERE id = ?', (status, category_id))
        conn.commit()
        flash("تم تغيير حالة القسم", "success")
    except Exception as e:
        flash(f"خطأ في تحديث الحالة: {str(e)}", "danger")
    finally:
        conn.close()
    return redirect(url_for('admin.categories'))

# ... (بقية الاستيرادات والدوال) ...

@admin_bp.route('/showcate') # تأكد أن هذا هو المسار لصفحة عرض الأقسام
def categories():
    filter_type = request.args.get('filter', 'all')
    try:
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row

        query = """
            SELECT c1.*, c2.name as parent_name,
                   (SELECT COUNT(p.id) FROM product p WHERE p.category_id = c1.id) as product_count
            FROM category c1
            LEFT JOIN category c2 ON c1.parent_id = c2.id
        """
        params = []

        if filter_type == 'active':
            query += " WHERE c1.is_active = 1"
        elif filter_type == 'inactive':
            query += " WHERE c1.is_active = 0"
        elif filter_type == 'main': # 🆕 فلترة الأقسام الرئيسية
            query += " WHERE c1.parent_id IS NULL"
        elif filter_type == 'sub':  # 🆕 فلترة الأقسام الفرعية
            query += " WHERE c1.parent_id IS NOT NULL"

        query += " ORDER BY c1.is_active DESC, c1.name"

        categories = conn.execute(query, params).fetchall() # تمرير params حتى لو كانت فارغة
        return render_template('admin/show_cate.html', categories=categories)

    except Exception as e:
        flash(f"خطأ في جلب البيانات: {str(e)}", "danger")
        return redirect(url_for('admin.categories'))
    finally:
        conn.close()

# ... (بقية الدوال) ...
@admin_bp.route('/edit_category/<int:category_id>', methods=['GET', 'POST'])
def edit_category(category_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM category WHERE id = ?", (category_id,))
    category = cursor.fetchone()

    if not category:
        flash("القسم غير موجود!", "danger")
        return redirect(url_for('admin.categories'))

    if request.method == 'POST':
        name = request.form['name']
        parent_id = request.form.get('parent', None) or None
        image = request.files.get('image')

        image_path = category['image']

        if image and image.filename:
            upload_folder = os.path.join(UPLOAD_FOLDER, 'category_img')
            os.makedirs(upload_folder, exist_ok=True)
            filename = secure_filename(image.filename)
            filepath = os.path.join(upload_folder, filename)
            image.save(filepath)
            image_path = f'static/uploads/category_img/{filename}'

        cursor.execute("""
            UPDATE category
            SET name = ?, parent_id = ?, image = ?
            WHERE id = ?
        """, (name, parent_id, image_path, category_id))

        conn.commit()
        conn.close()
        flash("تم تعديل القسم بنجاح!", "success")
        return redirect(url_for('admin.categories'))

    cursor.execute("SELECT * FROM category WHERE id != ?", (category_id,))
    categories = cursor.fetchall()
    conn.close()
    return render_template('admin/edit_category.html',
                         category=category,
                         categories=categories)
                         
                                     


@admin_bp.route('/category_details_admin/<int:category_id>')
def category_details_admin(category_id):
    conn = get_db_connection()
    category = conn.execute('''
        SELECT c1.*, c2.name as parent_name,
               (SELECT COUNT(p.id) FROM product p WHERE p.category_id = c1.id) as product_count
        FROM category c1
        LEFT JOIN category c2 ON c1.parent_id = c2.id
        WHERE c1.id = ?
    ''', (category_id,)).fetchone()
    conn.close()

    if not category:
        flash("القسم غير موجود!", "danger")
        return redirect(url_for('admin.categories'))

    return render_template('admin/category_details_admin.html', category=category)

                         
                         
                         

@admin_bp.route('/add_product', methods=['GET', 'POST'])
def add_product():
    conn = get_db_connection()
    categories = conn.execute('SELECT id, name, parent_id FROM category WHERE parent_id IS NOT NULL').fetchall()
    sellers = conn.execute('SELECT id, name FROM sellers').fetchall()
    conn.close()

    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        original_price = request.form['original_price']
        profit_price = request.form['profit_price']
        quantity = request.form['quantity']
        category_id = request.form['category']
        seller_id = request.form['seller']
        images = request.files.getlist('images')

        upload_folder = os.path.join(UPLOAD_FOLDER, 'products')
        os.makedirs(upload_folder, exist_ok=True)
        main_image_path = 'static/uploads/products/default_product.jpg'

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            # التحقق من عدم تكرار اسم المنتج
            cursor.execute('SELECT id FROM product WHERE name = ?', (name,))
            if cursor.fetchone():
                flash("المنتج موجود بالفعل!", "danger")
                return redirect(url_for('admin.add_product'))

            # إدراج المنتج الأساسي
            cursor.execute('''
                INSERT INTO product (
                    name, description, category_id,
                    seller_id, image,
                    featured, price_id, stock_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                name, description, category_id,
                seller_id, main_image_path,
                0, None, None
            ))
            product_id = cursor.lastrowid

            # إدراج الأسعار
            cursor.execute('''
                INSERT INTO prices (product_id, original_price, profit_price)
                VALUES (?, ?, ?)
            ''', (product_id, original_price, profit_price))
            price_id = cursor.lastrowid

            # إدراج المخزون
            cursor.execute('''
                INSERT INTO stock (product_id, quantity)
                VALUES (?, ?)
            ''', (product_id, quantity))
            stock_id = cursor.lastrowid

            # تحديث المنتج بمعرفات الأسعار والمخزون
            cursor.execute('''
                UPDATE product
                SET price_id = ?, stock_id = ?
                WHERE id = ?
            ''', (price_id, stock_id, product_id))

            # معالجة الصور المرفوعة
            if images and images[0].filename:
                for idx, image in enumerate(images):
                    if image and image.filename:
                        filename = secure_filename(image.filename)
                        unique_filename = f"{uuid.uuid4().hex}_{filename}"
                        filepath = os.path.join(upload_folder, unique_filename)
                        image.save(filepath)
                        image_path = f'static/uploads/products/{unique_filename}'

                        is_main = (idx == 0)
                        cursor.execute('''
                            INSERT INTO product_image (product_id, image_path, is_main)
                            VALUES (?, ?, ?)
                        ''', (product_id, image_path, is_main))

                        if is_main:
                            cursor.execute('''
                                UPDATE product SET image = ? WHERE id = ?
                            ''', (image_path, product_id))
            else:
                # إدراج الصورة الافتراضية إذا لم يتم رفع أي صور
                cursor.execute('''
                    INSERT INTO product_image (product_id, image_path, is_main)
                    VALUES (?, ?, ?)
                ''', (product_id, main_image_path, True))

            conn.commit()
            flash("تمت إضافة المنتج بنجاح!", "success")

        except Exception as e:
            conn.rollback()
            flash(f"حدث خطأ أثناء إضافة المنتج: {str(e)}", "danger")
            print(f"Error: {str(e)}")
            return redirect(url_for('admin.add_product'))

        finally:
            conn.close()

        return redirect(url_for('admin.add_product'))

    return render_template('admin/add_product.html',
                         categories=categories,
                         sellers=sellers)

@admin_bp.route('/product_details_admin/<int:product_id>')
def product_details_admin(product_id):
    conn = get_db_connection()
    product = conn.execute('''
        SELECT
            p.id,
            p.name,
            p.image,
            p.description,
            pr.original_price,
            pr.profit_price,
            COALESCE(s.quantity, 0) AS quantity,
            c.name AS category,
            c.id AS category_id,
            sllr.name AS seller,
            sllr.id AS seller_id,
            sa.address AS address,
            p.featured
        FROM product p
        LEFT JOIN prices pr ON p.price_id = pr.id
        LEFT JOIN stock s ON p.stock_id = s.id
        LEFT JOIN category c ON p.category_id = c.id
        LEFT JOIN sellers sllr ON p.seller_id = sllr.id
        LEFT JOIN seller_address sa ON sllr.SAddress_id = sa.id
        WHERE p.id = ?
    ''', (product_id,)).fetchone()
    conn.close()

    if product is None:
        flash("المنتج غير موجود", "danger")
        return redirect(url_for('admin.show_product'))

    return render_template('admin/product_details_admin.html', product=product)






@admin_bp.route('/show_product', methods=['GET'])
def show_product():
    # الحصول على معلمة الفلترة من الرابط، القيمة الافتراضية هي 'all'
    filter_type = request.args.get('filter', 'all')
    
    conn = get_db_connection()
    query = '''
        SELECT
            p.id,
            p.name,
            p.image,
            p.description,
            pr.original_price,
            pr.profit_price,
            s.quantity,
            c.name AS category,
            c.id AS category_id,
            sllr.name AS seller,
            sllr.id AS seller_id,
            sa.address AS address,
            p.featured
        FROM product p
        LEFT JOIN prices pr ON p.price_id = pr.id
        LEFT JOIN stock s ON p.stock_id = s.id
        LEFT JOIN category c ON p.category_id = c.id
        LEFT JOIN sellers sllr ON p.seller_id = sllr.id
        LEFT JOIN seller_address sa ON sllr.SAddress_id = sa.id
    '''
    
    # إضافة شرط الفلترة إلى الاستعلام
    if filter_type == 'featured':
        query += ' WHERE p.featured = 1'
    elif filter_type == 'hidden':
        query += ' WHERE p.featured = 0'
        
    query += ' ORDER BY p.id DESC'
    
    products = conn.execute(query).fetchall()
    conn.close()
    
    # تمرير معلمة الفلترة إلى القالب
    return render_template('admin/show_product.html', products=products, filter_type=filter_type)

@admin_bp.route('/toggle_featured/<int:product_id>/<int:status>')
def toggle_featured(product_id, status):
    conn = get_db_connection()
    try:
        conn.execute('UPDATE product SET featured = ? WHERE id = ?', (status, product_id))
        conn.commit()
        flash("تم تحديث حالة العرض بنجاح", "success")
    except Exception as e:
        conn.rollback()
        flash(f"حدث خطأ: {str(e)}", "danger")
    finally:
        conn.close()

    return redirect(url_for('admin.show_product'))

@admin_bp.route('/delete_product/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('SELECT image FROM product WHERE id = ?', (product_id,))
        product = cursor.fetchone()
        if not product:
            flash("المنتج غير موجود!", "danger")
            return redirect(url_for('admin.show_product'))

        image_path = product['image']
        if image_path != 'static/uploads/products/default_seller.jpg':
            image_full_path = os.path.join(os.path.dirname(__file__), image_path)
            if os.path.exists(image_full_path):
                os.remove(image_full_path)

        cursor.execute('DELETE FROM prices WHERE product_id = ?', (product_id,))
        cursor.execute('DELETE FROM stock WHERE product_id = ?', (product_id,))
        cursor.execute('DELETE FROM product WHERE id = ?', (product_id,))
        conn.commit()

        flash("تم حذف المنتج بنجاح!", "success")
    except Exception as e:
        conn.rollback()
        flash(f"حدث خطأ أثناء الحذف: {str(e)}", "danger")
    finally:
        conn.close()

    return redirect(url_for('admin.show_product'))

@admin_bp.route('/edit_product/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    # جلب تفاصيل المنتج الأساسية
    product = conn.execute('''
        SELECT
            p.id,
            p.name,
            p.description,
            p.category_id,
            p.seller_id,
            sllr.SAddress_id, -- نحتاج address_id من جدول البائع للوصول إلى العنوان
            pr.original_price,
            pr.profit_price,
            s.quantity
        FROM product p
        LEFT JOIN prices pr ON p.price_id = pr.id
        LEFT JOIN stock s ON p.stock_id = s.id
        LEFT JOIN sellers sllr ON p.seller_id = sllr.id
        WHERE p.id = ?
    ''', (product_id,)).fetchone()

    if not product:
        conn.close()
        flash("المنتج غير موجود!", "danger")
        return redirect(url_for('admin.show_product'))

    # جلب عنوان البائع
    seller_address = conn.execute('SELECT address FROM seller_address WHERE id = ?', (product['SAddress_id'],)).fetchone()
    if seller_address:
        product = dict(product) # تحويل Row إلى dict لتعديله
        product['address'] = seller_address['address']
    else:
        product = dict(product)
        product['address'] = None


    # جلب صور المنتج الحالية
    current_images = conn.execute('SELECT id, image_path, is_main FROM product_image WHERE product_id = ? ORDER BY is_main DESC, id ASC', (product_id,)).fetchall()

    categories = conn.execute('SELECT id, name FROM category WHERE parent_id IS NOT NULL').fetchall() # Only subcategories
    sellers = conn.execute('SELECT id, name FROM sellers').fetchall()
    
    conn.close() # أغلق الاتصال هنا بعد جلب البيانات لـ GET

    if request.method == 'POST':
        conn = get_db_connection() # أعد فتح الاتصال للتعامل مع POST
        cursor = conn.cursor()

        name = request.form['name']
        description = request.form['description']
        original_price = request.form['original_price']
        profit_price = request.form['profit_price']
        quantity = request.form['quantity']
        category_id = request.form['category']
        seller_id = request.form['seller']
        address = request.form['address']
        new_images = request.files.getlist('images') # الصور الجديدة المرفوعة
        existing_image_ids_to_keep = request.form.getlist('existing_images') # IDs للصور الموجودة التي يجب الاحتفاظ بها

        try:
            # 1. تحديث بيانات المنتج الأساسية
            # البحث عن SAddress_id للبائع الحالي
            cursor.execute("SELECT SAddress_id FROM sellers WHERE id = ?", (seller_id,))
            current_seller_address_id = cursor.fetchone()
            if current_seller_address_id:
                current_seller_address_id = current_seller_address_id['SAddress_id']
            else:
                current_seller_address_id = None # أو التعامل مع حالة البائع بدون عنوان

            # تحديث عنوان البائع المرتبط بالمنتج (إذا كان هناك تغيير)
            # بما أن العنوان مرتبط بالبائع، يجب تحديث جدول seller_address باستخدام SAddress_id للبائع
            # أو إذا كان لكل منتج عنوانه الخاص، يجب أن يكون هناك عمود address_id في جدول product
            # بناءً على الكود الذي قدمته، العنوان موجود في seller_address ويرتبط بالبائع.
            # لذا سنقوم بتحديث العنوان المرتبط بالبائع.
            if current_seller_address_id:
                cursor.execute('UPDATE seller_address SET address = ? WHERE id = ?', (address, current_seller_address_id))

            cursor.execute('''
                UPDATE product
                SET name = ?, description = ?, category_id = ?, seller_id = ?
                WHERE id = ?
            ''', (name, description, category_id, seller_id, product_id))

            # 2. تحديث الأسعار
            cursor.execute('''
                UPDATE prices
                SET original_price = ?, profit_price = ?
                WHERE product_id = ?
            ''', (original_price, profit_price, product_id))

            # 3. تحديث المخزون
            cursor.execute('''
                UPDATE stock
                SET quantity = ?
                WHERE product_id = ?
            ''', (quantity, product_id))

            # 4. تحديث الصور المتعددة
            uploaded_product_folder = os.path.join(UPLOAD_FOLDER, 'products')
            os.makedirs(uploaded_product_folder, exist_ok=True)

            # حذف الصور القديمة التي لم يتم الاحتفاظ بها
            for img in current_images:
                if str(img['id']) not in existing_image_ids_to_keep:
                    # احذف الملف من الخادم
                    if img['image_path'] and os.path.exists(os.path.join(uploaded_product_folder, os.path.basename(img['image_path']))):
                        os.remove(os.path.join(uploaded_product_folder, os.path.basename(img['image_path'])))
                    # احذف السجل من قاعدة البيانات
                    cursor.execute('DELETE FROM product_image WHERE id = ?', (img['id'],))

            # إضافة الصور الجديدة
            if new_images and new_images[0].filename:
                for idx, image_file in enumerate(new_images):
                    if image_file and allowed_file(image_file.filename):
                        filename = secure_filename(image_file.filename)
                        unique_filename = f"{uuid.uuid4().hex}_{filename}"
                        filepath = os.path.join(uploaded_product_folder, unique_filename)
                        image_file.save(filepath)
                        image_path_db = f'static/uploads/products/{unique_filename}'

                        # إضافة الصورة الجديدة إلى جدول product_image
                        cursor.execute('''
                            INSERT INTO product_image (product_id, image_path, is_main)
                            VALUES (?, ?, ?)
                        ''', (product_id, image_path_db, (idx == 0 and not existing_image_ids_to_keep)))
                        # إذا لم تكن هناك صور قديمة تم الاحتفاظ بها وكانت هذه أول صورة جديدة، اجعلها رئيسية.

            # تحديث الصورة الرئيسية في جدول product
            # إذا لم تعد هناك صور، أو إذا تم حذف الصورة الرئيسية القديمة، عين أول صورة متبقية كصورة رئيسية
            # أو استخدم صورة افتراضية.
            updated_main_image = 'static/uploads/products/default_product.jpg' # الصورة الافتراضية
            # جلب أول صورة (التي قد تكون رئيسية) بعد التحديثات
            first_image_record = cursor.execute('SELECT image_path FROM product_image WHERE product_id = ? ORDER BY is_main DESC, id ASC LIMIT 1', (product_id,)).fetchone()
            if first_image_record:
                updated_main_image = first_image_record['image_path']

            cursor.execute('UPDATE product SET image = ? WHERE id = ?', (updated_main_image, product_id))

            conn.commit()
            flash("تم تحديث المنتج بنجاح!", "success")
            return redirect(url_for('admin.show_product'))

        except Exception as e:
            conn.rollback()
            flash(f"حدث خطأ أثناء تحديث المنتج: {str(e)}", "danger")
            print(f"Error updating product: {str(e)}") # لغرض التصحيح
            return redirect(url_for('admin.edit_product', product_id=product_id))
        finally:
            conn.close()

    return render_template('admin/edit_product.html',
                           product=product,
                           categories=categories,
                           sellers=sellers,
                           current_images=current_images) # تمرير الصور الحالية للقالب

@admin_bp.route('/add_address', methods=['GET', 'POST'])
def add_address():
    if request.method == 'POST':
        street = request.form['street']

        conn = get_db_connection()
        conn.execute('INSERT INTO addresses (street) VALUES (?)', (street,))
        conn.commit()
        conn.close()

        return redirect(url_for('admin.add_address'))

    return render_template('admin/add_address.html')


@admin_bp.route('/seller', methods=['GET', 'POST'])
def add_seller():
    if request.method == 'GET':
        return render_template('admin/seller.html')

    if request.method == 'POST':
        try:
            name = request.form.get('name')
            store_name = request.form.get('store_name')
            commercial_record = request.form.get('commercial_record')
            latitude = request.form.get('latitude')
            longitude = request.form.get('longitude')
            street_address = request.form.get('addressDisplay')
            number1 = request.form.get('number1')
            number2 = request.form.get('number2')

            store_image = request.files.get('store_image')
            id_image = request.files.get('id_image')
            documents = request.files.get('documents')

            upload_base_folder = UPLOAD_FOLDER # C:\Users\PC\Desktop\project\static\uploads
            store_image_folder = os.path.join(upload_base_folder, "store_images") # C:\Users\PC\Desktop\project\static\uploads\store_images
            id_image_folder = os.path.join(upload_base_folder, "id_images")     # C:\Users\PC\Desktop\project\static\uploads\id_images
            documents_folder = os.path.join(upload_base_folder, "documents")       # C:\Users\PC\Desktop\project\static\uploads\documents

            os.makedirs(store_image_folder, exist_ok=True)
            os.makedirs(id_image_folder, exist_ok=True)
            os.makedirs(documents_folder, exist_ok=True)

            store_image_db_path = ""
            id_image_db_path = ""
            documents_db_path = ""

            # معالجة وحفظ صورة المتجر
            if store_image and allowed_file(store_image.filename):
                store_image_filename = secure_filename(store_image.filename)
                store_image_full_fs_path = os.path.join(store_image_folder, store_image_filename)
                store_image.save(store_image_full_fs_path)
                # المسار الذي سيُحفظ في قاعدة البيانات: static/uploads/store_images/filename.ext
                store_image_db_path = os.path.join("static", "uploads", "store_images", store_image_filename).replace('\\', '/')

            # معالجة وحفظ صورة الهوية
            if id_image and allowed_file(id_image.filename):
                id_image_filename = secure_filename(id_image.filename)
                id_image_full_fs_path = os.path.join(id_image_folder, id_image_filename)
                id_image.save(id_image_full_fs_path)
                # المسار الذي سيُحفظ في قاعدة البيانات: static/uploads/id_images/filename.ext
                id_image_db_path = os.path.join("static", "uploads", "id_images", id_image_filename).replace('\\', '/')

            # معالجة وحفظ المستندات
            if documents and allowed_file(documents.filename):
                documents_filename = secure_filename(documents.filename)
                documents_full_fs_path = os.path.join(documents_folder, documents_filename)
                documents.save(documents_full_fs_path)
                # المسار الذي سيُحفظ في قاعدة البيانات: static/uploads/documents/filename.ext
                documents_db_path = os.path.join("static", "uploads", "documents", documents_filename).replace('\\', '/')


            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute(
                "INSERT INTO seller_address (latitude, longitude, address) VALUES (?, ?, ?)",
                (latitude, longitude, street_address)
            )
            address_id = cursor.lastrowid

            cursor.execute(
                "INSERT INTO numbers (number1, number2) VALUES (?, ?)",
                (number1, number2)
            )
            num_id = cursor.lastrowid

            # التأكد من ترتيب الأعمدة وقيمها عند الإدخال
            # تأكد أن 'address' هو العمود الرابع (seller[4])
            # وأن 'id_image' هو العمود السادس (seller[6])
            # وأن 'documents' هو العمود السابع (seller[7])
            cursor.execute('''
                INSERT INTO sellers
                (name, store_name, store_image, address, commercial_record, id_image, documents, SAddress_id, num_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                name,
                store_name,
                store_image_db_path,   # القيمة لـ seller[3]
                street_address,        # القيمة لـ seller[4]
                commercial_record,     # القيمة لـ seller[5]
                id_image_db_path,      # القيمة لـ seller[6]
                documents_db_path,     # القيمة لـ seller[7]
                address_id,
                num_id
            ))

            conn.commit()
            conn.close()

            flash("تمت إضافة البائع بنجاح!", "success")
            return redirect(url_for('admin.add_seller'))

        except Exception as e:
            print(f"حدث خطأ: {e}")
            traceback.print_exc()
            flash(f"حدث خطأ: {str(e)}", "danger")
            return redirect(url_for('admin.add_seller'))

@admin_bp.route('/show_seller', methods=['POST', 'GET'])
def show_seller():
    conn = sqlite3.connect("database/Eshop.db")
    cursor = conn.cursor()

    sellers = cursor.execute("""
        SELECT
            s.id, s.name, s.store_name, s.store_image,
            s.commercial_record, s.id_image, s.documents,
            s.created_at,
            sa.address, sa.latitude, sa.longitude,
            n.number1, n.number2,
            (SELECT COUNT(p.id) FROM product p WHERE p.seller_id = s.id) as product_count
        FROM sellers s
        JOIN seller_address sa ON s.SAddress_id = sa.id
        JOIN numbers n ON s.num_id = n.id
        ORDER BY s.created_at DESC """).fetchall()

    conn.close()
    return render_template('admin/show_seller.html', sellers=sellers)




@admin_bp.route('/edit_seller/<int:seller_id>', methods=['GET', 'POST'])
def edit_seller(seller_id):
    conn = None # تعريف conn خارج try ليكون متاحاً في finally
    try:
        conn = sqlite3.connect("database/Eshop.db")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('''
            SELECT s.*, sa.latitude, sa.longitude, sa.address as full_address,
                   n.number1, n.number2
            FROM sellers s
            LEFT JOIN seller_address sa ON s.SAddress_id = sa.id
            LEFT JOIN numbers n ON s.num_id = n.id
            WHERE s.id = ?
        ''', (seller_id,))
        seller = cursor.fetchone()

        if not seller:
            flash("صاحب المتجر غير موجود!", "danger")
            return redirect(url_for('admin.show_seller'))

        # استخراج المعرفات لتحديث الجداول المرتبطة
        s_address_id = seller['SAddress_id']
        num_id = seller['num_id']

        if request.method == 'POST':
            name = request.form['name']
            store_name = request.form['store_name']
            commercial_record = request.form['commercial_record']

            latitude = request.form.get('latitude')
            longitude = request.form.get('longitude')
            street_address = request.form.get('addressDisplay') # اسم الحقل في الفورم

            number1 = request.form.get('number1')
            number2 = request.form.get('number2')

            # احتفظ بالمسارات القديمة كافتراض، هذه هي المسارات المخزنة في قاعدة البيانات
            store_image_db_path = seller['store_image']
            id_image_db_path = seller['id_image']
            documents_db_path = seller['documents']

            # مجلدات التحميل الفعلية على نظام الملفات (يجب أن تكون UPLOAD_FOLDER معرفة)
            store_image_folder = os.path.join(UPLOAD_FOLDER, 'store_images')
            id_image_folder = os.path.join(UPLOAD_FOLDER, 'id_images')
            documents_folder = os.path.join(UPLOAD_FOLDER, 'documents')

            # تأكد من إنشاء المجلدات إذا لم تكن موجودة
            os.makedirs(store_image_folder, exist_ok=True)
            os.makedirs(id_image_folder, exist_ok=True)
            os.makedirs(documents_folder, exist_ok=True)

            # معالجة رفع صورة المتجر الجديدة
            if 'store_image' in request.files:
                file = request.files['store_image']
                if file.filename != '' and allowed_file(file.filename): # أضف allowed_file للتحقق من النوع
                    filename = secure_filename(file.filename)
                    full_fs_path = os.path.join(store_image_folder, filename)
                    file.save(full_fs_path)
                    # هذا هو التعديل الأساسي: تحويل المسار للتخزين في قاعدة البيانات
                    # يجب أن يبدأ المسار بـ 'static/' لكي يعمل url_for('static', filename=...)
                    store_image_db_path = os.path.join("static", "uploads", "store_images", filename).replace('\\', '/')

            # معالجة رفع صورة الهوية الجديدة
            if 'id_image' in request.files:
                file = request.files['id_image']
                if file.filename != '' and allowed_file(file.filename): # أضف allowed_file
                    filename = secure_filename(file.filename)
                    full_fs_path = os.path.join(id_image_folder, filename)
                    file.save(full_fs_path)
                    id_image_db_path = os.path.join("static", "uploads", "id_images", filename).replace('\\', '/')

            # معالجة رفع المستندات الجديدة
            if 'documents' in request.files:
                file = request.files['documents']
                if file.filename != '' and allowed_file(file.filename): # أضف allowed_file
                    filename = secure_filename(file.filename)
                    full_fs_path = os.path.join(documents_folder, filename)
                    file.save(full_fs_path)
                    documents_db_path = os.path.join("static", "uploads", "documents", filename).replace('\\', '/')

            # تحديث جدول sellers
            cursor.execute("""
                UPDATE sellers SET
                    name = ?,
                    store_name = ?,
                    commercial_record = ?,
                    store_image = ?,
                    id_image = ?,
                    documents = ?
                WHERE id = ?
            """, (name, store_name, commercial_record, store_image_db_path, id_image_db_path, documents_db_path, seller_id))

            # تحديث جدول seller_address
            cursor.execute("""
                UPDATE seller_address SET
                    latitude = ?,
                    longitude = ?,
                    address = ?
                WHERE id = ?
            """, (latitude, longitude, street_address, s_address_id))

            # تحديث جدول numbers
            cursor.execute("""
                UPDATE numbers SET
                    number1 = ?,
                    number2 = ?
                WHERE id = ?
            """, (number1, number2, num_id))

            conn.commit()
            flash("تم تعديل بيانات البائع بنجاح!", "success")
            return redirect(url_for('admin.show_seller'))

        # إذا كانت طريقة الطلب GET (لأول مرة يتم عرض النموذج)
        seller_dict = dict(seller) # تحويل Row إلى Dict للوصول السهل للمفاتيح
        seller_dict['has_location'] = bool(seller['latitude'] and seller['longitude'])

        # تهيئة القيم للحقول في القالب (خاصة حقول الخريطة)
        seller_dict['addressDisplay'] = seller['full_address'] if seller['full_address'] else ''
        seller_dict['latitude'] = seller['latitude'] if seller['latitude'] else ''
        seller_dict['longitude'] = seller['longitude'] if seller['longitude'] else ''

        # تمرير المسارات الحالية لكي يعرضها القالب بجانب حقول الرفع
        seller_dict['current_store_image'] = seller['store_image']
        seller_dict['current_id_image'] = seller['id_image']
        seller_dict['current_documents'] = seller['documents']


        return render_template('admin/edit_seller.html', seller=seller_dict)

    except Exception as e:
        print(f"حدث خطأ في edit_seller: {e}") # طباعة الخطأ في الكونسول لتتبع أفضل
        traceback.print_exc() # طباعة تتبع الخطأ الكامل
        flash(f"حدث خطأ: {str(e)}", "danger")
        return redirect(url_for('admin.show_seller'))
    finally:
        if conn: # أغلق الاتصال فقط إذا كان مفتوحاً
            conn.close()

@admin_bp.route('/delete_category/<int:category_id>')
def delete_category(category_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM category WHERE id = ?", (category_id,))
    category = cursor.fetchone()

    if not category:
        flash("القسم غير موجود!", "danger")
        return redirect(url_for('admin.categories'))

    cursor.execute("DELETE FROM category WHERE id = ?", (category_id,))
    conn.commit()
    conn.close()

    flash("تم حذف القسم بنجاح!", "danger")
    return redirect(url_for('admin.categories'))

@admin_bp.route('/delete_seller/<int:seller_id>')
def delete_seller(seller_id):
    conn = sqlite3.connect("database/Eshop.db")
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM sellers WHERE id = ?", (seller_id,))
    seller = cursor.fetchone()

    if not seller:
        flash("صاحب المتجر غير موجود!", "danger")
        return redirect(url_for('admin.show_seller'))

    cursor.execute("DELETE FROM sellers WHERE id = ?", (seller_id,))
    conn.commit()
    conn.close()

    flash("تم حذف صاحب المتجر بنجاح!", "success")
    return redirect(url_for('admin.show_seller'))


@admin_bp.route('/users')
def users():
    try:
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                u.id, u.name, u.num, u.email, u.ud_ia,
                a.address, a.latitude, a.longitude
            FROM user u
            LEFT JOIN user_addresses a ON u.ud_ia = a.id
        """)

        users_data = cursor.fetchall()
        conn.close()

        users = []
        for user in users_data:
            users.append({
                'id': user['id'],
                'name': user['name'] or 'غير محدد',
                'num': user['num'] or 'غير محدد',
                'email': user['email'] or 'غير محدد',
                'address': user['address'] or 'لم يتم إضافة عنوان',
                'latitude': user['latitude'],
                'longitude': user['longitude']
            })

        return render_template('admin/show_users.html', users=users)

    except Exception as e:
        print(f"خطأ مفاجئ: {str(e)}")
        return render_template('admin/show_users.html', error="حدث خطأ أثناء جلب المستخدمين")


@admin_bp.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM user WHERE id = ?", (user_id,))
        conn.commit()
        conn.close()

        return redirect(url_for('admin.users', message="تم حذف المستخدم بنجاح."))

    except Exception as e:
        print(f"خطأ أثناء الحذف: {e}")
        return redirect(url_for('admin.users', error="حدث خطأ أثناء حذف المستخدم."))


@admin_bp.route('/seller_products_admin/<int:seller_id>')
def seller_products_admin(seller_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    seller = cursor.execute('SELECT id, store_name FROM sellers WHERE id = ?', (seller_id,)).fetchone()
    if not seller:
        flash("البائع غير موجود!", "danger")
        return redirect(url_for('admin.show_seller'))

    products = cursor.execute('''
        SELECT
            p.id, p.name, p.image, p.description,
            pr.original_price, pr.profit_price,
            s.quantity, c.name AS category,
            c.id AS category_id,
            sllr.name AS seller,
            sllr.id AS seller_id,
            sa.address AS address,
            p.featured
        FROM product p
        LEFT JOIN prices pr ON p.price_id = pr.id
        LEFT JOIN stock s ON p.stock_id = s.id
        LEFT JOIN category c ON p.category_id = c.id
        LEFT JOIN sellers sllr ON p.seller_id = sllr.id
        LEFT JOIN seller_address sa ON sllr.SAddress_id = sa.id
        WHERE p.seller_id = ?
        ORDER BY p.id DESC
    ''', (seller_id,)).fetchall()

    conn.close()
    return render_template('admin/seller_products_admin.html', products=products, seller=seller)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


