from flask import Flask, render_template, request, redirect, url_for, flash, jsonify,session,make_response
import sqlite3
import os
import json
from datetime import datetime, timedelta
import random
import redis

from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
redis_client = redis.StrictRedis(host='localhost', port=6379, db=0, decode_responses=True)

# إعداد مسار رفع الصور
UPLOAD_FOLDER = 'static/uploads'
app.secret_key = 'f2d9e8a0b7c6d1e6f3a8c4b8d9e2f6a4'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['SECRET_KEY'] = 'your_secret_key'

def get_db_connection():
    conn = sqlite3.connect('database/Eshop.db')
    conn.row_factory = sqlite3.Row
    return conn










# الصفحه الرئسية للادمن
@app.route('/admin')
def home():
   return render_template('admin/index.html')
    #return render_template('/storage/emulated/0/Documents/Pydroid3/git_eshop-main/templates/admin/index.html')


@app.route('/cate', methods=['GET', 'POST'])
def add_category():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        if request.method == 'POST':
            name = request.form.get('name')
            if not name:
                flash('اسم القسم مطلوب', 'danger')
                return redirect(url_for('add_category'))

            parent_id = request.form.get('parent', None)
            image = request.files.get('image')
            is_active = 1 if request.form.get('is_active') == '1' else 0

            # التحقق من وجود الفئة
            cursor.execute('SELECT id FROM category WHERE name = ?', (name,))
            if cursor.fetchone():
                flash('هذا القسم موجود بالفعل!', 'danger')
                return redirect(url_for('add_category'))

            # معالجة parent_id
            parent_id = int(parent_id) if parent_id and parent_id.isdigit() else None

            # تعيين مسار الصورة إذا تم تحميلها
            image_path = None
            if image and image.filename:
                upload_folder = os.path.join(app.config['UPLOAD_FOLDER'], 'category_img')
                if not os.path.exists(upload_folder):
                    os.makedirs(upload_folder)

                # حفظ الصورة
                filename = secure_filename(image.filename)
                filepath = os.path.join(upload_folder, filename)
                image.save(filepath)  # حفظ الصورة على الخادم
                image_path = f'static/uploads/category_img/{filename}'  # حفظ المسار النسبي في قاعدة البيانات

            # إدراج الفئة
            cursor.execute(
                'INSERT INTO category (name, parent_id, image, is_active) VALUES (?, ?, ?, ?)',
                (name, parent_id, image_path, is_active)
            )
            conn.commit()
            flash('تم إضافة القسم بنجاح!', 'success')
            return redirect(url_for('categories'))

        # جلب الفئات للقائمة المنسدلة
        categories = conn.execute('SELECT id, name FROM category').fetchall()
        return render_template('admin/cate.html', categories=categories)

    except Exception as e:
        flash(f'حدث خطأ: {str(e)}', 'danger')
        return redirect(url_for('add_category'))
    finally:
        if 'conn' in locals():
            conn.close()

@app.route('/toggle_category/<int:category_id>/<int:status>')
def toggle_category(category_id, status):
    try:
        conn = get_db_connection()
        conn.execute('UPDATE category SET is_active = ? WHERE id = ?', (status, category_id))
        conn.commit()
        flash("تم تغيير حالة القسم", "success")
    except Exception as e:
        flash(f"خطأ في تحديث الحالة: {str(e)}", "danger")
    finally:
        conn.close()
    return redirect(url_for('categories'))

@app.route('/showcate')
def categories():
    filter_type = request.args.get('filter', 'all')
    try:
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        
        query = """
            SELECT c1.*, c2.name as parent_name 
            FROM category c1
            LEFT JOIN category c2 ON c1.parent_id = c2.id
        """
        
        if filter_type == 'active':
            query += " WHERE c1.is_active = 1"
        elif filter_type == 'inactive':
            query += " WHERE c1.is_active = 0"
            
        query += " ORDER BY c1.is_active DESC, c1.name"
        
        categories = conn.execute(query).fetchall()
        return render_template('admin/show_cate.html', categories=categories)
        
    except Exception as e:
        flash(f"خطأ في جلب البيانات: {str(e)}", "danger")
        return redirect(url_for('index'))
    finally:
        if 'conn' in locals():
            conn.close()

            
@app.route('/')
def index():
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row

    # جلب التصنيفات الرئيسية النشطة فقط (is_active = 1)
    main_categories = conn.execute("""
        SELECT * FROM category 
        WHERE parent_id IS NULL AND is_active = 1
        ORDER BY name
    """).fetchall()

    # جلب المنتجات
    products = conn.execute("SELECT * FROM product").fetchall()

    # جلب معرف المستخدم
    user_id = request.cookies.get('user_auth')

    # جلب المنتجات التي أعجب بها المستخدم
    if user_id:
        liked_rows = conn.execute("SELECT product_id FROM likes WHERE user_id = ?", (user_id,)).fetchall()
        liked_products = [row['product_id'] for row in liked_rows]
    else:
        liked_products = []

    conn.close()

    return render_template(
        'index.html',
        main_categories=main_categories,  # تم تغيير الاسم من categories إلى main_categories
        products=products,
        liked_products=liked_products
    )

@app.context_processor
def inject_categories():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # جلب الأقسام الرئيسية فقط (التي ليس لها parent_id)
        cursor.execute("""
            SELECT id, name, parent_id, image 
            FROM category 
            WHERE parent_id IS NULL 
            ORDER BY name
        """)
        main_categories = cursor.fetchall()
        
        # جلب جميع الأقسام لاستخدامها في أماكن أخرى
        cursor.execute("SELECT id, name, parent_id, image FROM category ORDER BY name")
        all_categories = cursor.fetchall()
        
        return {
            'main_categories': main_categories,
            'all_categories': all_categories
        }
    finally:
        conn.close()
@app.route('/subcategories/<int:category_id>')
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

@app.route('/edit_category/<int:category_id>', methods=['GET', 'POST'])
def edit_category(category_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Fetch the current category data
    cursor.execute("SELECT * FROM category WHERE id = ?", (category_id,))
    category = cursor.fetchone()

    if not category:
        flash("القسم غير موجود!", "danger")
        return redirect(url_for('categories'))

    if request.method == 'POST':
        name = request.form['name']
        parent_id = request.form.get('parent', None) or None  # Ensure NULL if empty
        image = request.files.get('image')

        # Determine the new image path
        image_path = category['image']  # Keep the old image if no new image is uploaded

        if image and image.filename:  # If a new image is uploaded
            # Ensure the upload folder exists
            upload_folder = os.path.join(app.config['UPLOAD_FOLDER'], 'category_img')
            if not os.path.exists(upload_folder):
                os.makedirs(upload_folder)

            # Save the new image
            filename = secure_filename(image.filename)
            filepath = os.path.join(upload_folder, filename)
            image.save(filepath)  # Save the image to the server
            image_path = f'static/uploads/category_img/{filename}'  # Save the relative path in the database

        # Update category in database
        cursor.execute("""
            UPDATE category 
            SET name = ?, parent_id = ?, image = ?
            WHERE id = ?
        """, (name, parent_id, image_path, category_id))
        
        conn.commit()
        conn.close()
        
        flash("تم تعديل القسم بنجاح!", "success")
        return redirect(url_for('categories'))  # تأكد أن هذه هي الصفحة الصحيحة للعودة إليها

    # Fetch all categories except current one for parent selection
    cursor.execute("SELECT * FROM category WHERE id != ?", (category_id,))
    categories = cursor.fetchall()
    
    conn.close()
    return render_template('admin/edit_category.html', 
                         category=category, 
                         categories=categories)
# حذف قسم
@app.route('/delete_category/<int:category_id>')
def delete_category(category_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    # التأكد من أن القسم موجود
    cursor.execute("SELECT * FROM category WHERE id = ?", (category_id,))
    category = cursor.fetchone()
    
    if not category:
        flash("القسم غير موجود!", "danger")
        return redirect(url_for('categories'))

    # حذف القسم من قاعدة البيانات
    cursor.execute("DELETE FROM category WHERE id = ?", (category_id,))
    conn.commit()
    conn.close()

    flash("تم حذف القسم بنجاح!", "danger")
    return redirect(url_for('categories'))


@app.route('/add_product', methods=['GET', 'POST'])
def add_product():
    conn = get_db_connection()
    categories = conn.execute('SELECT id, name, parent_id FROM category').fetchall()
    sellers = conn.execute('SELECT id, name FROM sellers').fetchall()
    addresses = conn.execute('SELECT id, address FROM seller_address').fetchall()
    conn.close()
    
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        original_price = request.form['original_price']
        profit_price = request.form['profit_price']
        quantity = request.form['quantity']
        category_id = request.form['category']
        seller_id = request.form['seller']
        address_id = request.form['address']
        image = request.files.get('image')

        # تأكد من وجود مجلد uploads
        UPLOAD_FOLDER = os.path.join(app.config['UPLOAD_FOLDER'], 'products')
        if not os.path.exists(UPLOAD_FOLDER):
            os.makedirs(UPLOAD_FOLDER)

        # حفظ الصورة
        image_path = 'static/uploads/products/default_seller.jpg'
        if image and image.filename:
            filename = secure_filename(image.filename)
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            image.save(filepath)
            image_path = f'static/uploads/products/{filename}'

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            # التحقق من وجود المنتج
            cursor.execute('SELECT id FROM product WHERE name = ?', (name,))
            if cursor.fetchone():
                flash("المنتج موجود بالفعل!", "danger")
                return redirect('/add_product')

            # إدراج المنتج مع جميع الحقول المطلوبة
            cursor.execute('''
                INSERT INTO product (
                    name, description, category_id, 
                    seller_id, address_id, image, 
                    featured, price_id, stock_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                name, description, category_id,
                seller_id, address_id, image_path,
                0, None, None  # featured=1, price_id و stock_id سيتم تحديثها لاحقاً
            ))
            product_id = cursor.lastrowid

            # إدراج السعر
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

            # تحديث المنتج بروابط السعر والمخزون
            cursor.execute('''
                UPDATE product 
                SET price_id = ?, stock_id = ?
                WHERE id = ?
            ''', (price_id, stock_id, product_id))

            conn.commit()
            flash("تمت إضافة المنتج بنجاح!", "success")

        except Exception as e:
            conn.rollback()
            flash(f"حدث خطأ: {str(e)}", "danger")
            print(f"Error: {str(e)}")  # طباعة الخطأ للتdebug

        finally:
            conn.close()

        return redirect('/add_product')
    
    return render_template('admin/add_product.html', 
                         categories=categories, 
                         sellers=sellers, 
                         addresses=addresses)

@app.route('/get_address/<int:seller_id>', methods=['GET'])
def get_address(seller_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT seller_address.id, seller_address.address
        FROM sellers
        JOIN seller_address ON sellers.SAddress_id = seller_address.id
        WHERE sellers.id = ?
    ''', (seller_id,))

    address = cursor.fetchone()
    conn.close()

    if address:
        return jsonify({'address_id': address[0], 'address': address[1]})
    else:
        return jsonify({'address_id': None, 'address': ''})
    

@app.route('/show_product', methods=['GET'])
def show_product():
    conn = get_db_connection()
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
            sllr.name AS seller,
            sa.address AS address,
            p.featured
        FROM product p
        LEFT JOIN prices pr ON p.price_id = pr.id
        LEFT JOIN stock s ON p.stock_id = s.id
        LEFT JOIN category c ON p.category_id = c.id
        LEFT JOIN sellers sllr ON p.seller_id = sllr.id
        LEFT JOIN seller_address sa ON sllr.SAddress_id = sa.id
        ORDER BY p.id DESC
    ''').fetchall()
    
    conn.close()
    return render_template('admin/show_product.html', products=products)

@app.route('/show_product1', methods=['GET'])
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


@app.route('/toggle_featured/<int:product_id>/<int:status>')
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
    
    return redirect(url_for('show_product'))

@app.route('/product/<int:product_id>', methods=['GET'])
def product_details(product_id):
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

    related_products = conn.execute('''
        SELECT p.id, p.name, p.image, pr.profit_price
        FROM product p
        LEFT JOIN prices pr ON p.price_id = pr.id
        WHERE p.category_id = (SELECT category_id FROM product WHERE id = ?) AND p.id != ?
        LIMIT 4
    ''', (product_id, product_id)).fetchall()

    conn.close()

    return render_template(
        'shop-details.html',
        product=product,
        related_products=list(related_products),
        quantity=product['quantity']  # تمرير الكمية إلى القالب
    )




@app.route('/delete_product/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # التحقق من وجود المنتج
        cursor.execute('SELECT image FROM product WHERE id = ?', (product_id,))
        product = cursor.fetchone()
        if not product:
            flash("المنتج غير موجود!", "danger")
            return redirect('/show_product')
        
        # حذف الصورة المرتبطة إذا لم تكن الصورة الافتراضية
        image_path = product['image']
        if image_path != 'static/uploads/products/default_seller.jpg':
            image_full_path = os.path.join(app.root_path, image_path)
            if os.path.exists(image_full_path):
                os.remove(image_full_path)
        
        # حذف البيانات المرتبطة من الجداول الأخرى
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
    
    return redirect('/show_product')




# ربط منتج ب قسم 

@app.route('/category/<int:category_id>')
def show_products_by_category(category_id):
    conn = get_db_connection()
    # استعلام لجلب المنتجات التابعة للقسم المحدد
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
            sllr.name AS seller,
            sa.address AS address,
            p.featured
        FROM product p
        LEFT JOIN prices pr ON p.price_id = pr.id
        LEFT JOIN stock s ON p.stock_id = s.id
        LEFT JOIN category c ON p.category_id = c.id
        LEFT JOIN sellers sllr ON p.seller_id = sllr.id
        LEFT JOIN seller_address sa ON sllr.SAddress_id = sa.id
        WHERE p.category_id = ?
    ''', (category_id,)).fetchall()
    
    conn.close()
    return render_template('shop_users.html', products=products)

@app.route('/edit_product/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    conn = get_db_connection()
    
    # جلب بيانات المنتج
    product = conn.execute('''
        SELECT 
            p.id, 
            p.name, 
            p.description, 
            p.image, 
            p.category_id, 
            p.seller_id, 
            p.address_id, 
            pr.original_price, 
            pr.profit_price, 
            s.quantity, 
            sa.address
        FROM product p
        LEFT JOIN prices pr ON p.price_id = pr.id
        LEFT JOIN stock s ON p.stock_id = s.id
        LEFT JOIN sellers sllr ON p.seller_id = sllr.id
        LEFT JOIN seller_address sa ON sllr.SAddress_id = sa.id  -- الربط مع seller_address عبر sellers
    WHERE p.id = ?
    ''', (product_id,)).fetchone()
    
    categories = conn.execute('SELECT id, name FROM category').fetchall()
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
        address = request.form['address']
        image = request.files.get('image')

        # تحديث الصورة إذا تم تحميل صورة جديدة
        image_path = product['image']  # الصورة الحالية
        if image and image.filename:
            filename = secure_filename(image.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image.save(filepath)
            image_path = f'static/uploads/{filename}'

        conn = get_db_connection()
        cursor = conn.cursor()

        # تحديث جدول المنتجات
        cursor.execute('''
            UPDATE product 
            SET name = ?, description = ?, category_id = ?, 
                seller_id = ?, address_id = ?, image = ?
            WHERE id = ?
        ''', (name, description, category_id, seller_id, address, image_path, product_id))
        
        # تحديث جدول الأسعار
        cursor.execute('''
            UPDATE prices 
            SET original_price = ?, profit_price = ? 
            WHERE product_id = ?
        ''', (original_price, profit_price, product_id))
        
        # تحديث جدول المخزون
        cursor.execute('''
            UPDATE stock 
            SET quantity = ? 
            WHERE product_id = ?
        ''', (quantity, product_id))
        
        conn.commit()
        conn.close()
        
        flash("تم تحديث المنتج بنجاح!", "success")
        return redirect('/show_product')
    
    return render_template('admin/edit_product.html', product=product, categories=categories, sellers=sellers)


@app.route('/add_address', methods=['GET', 'POST'])
def add_address():
    if request.method == 'POST':
        street = request.form['street']
        
        conn = get_db_connection()
        conn.execute('INSERT INTO addresses (street) VALUES (?)', (street,))
        conn.commit()
        conn.close()
        
        return redirect('/add_address')
    
    return render_template('admin/add_address.html')
# اضافة بايع في الادمن
# دالة للتحقق من نوع الملف المسموح به
def allowed_file(filename):
    # تحقق من وجود النقطة في الاسم لتحديد الامتداد
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

from datetime import datetime

@app.template_filter('datetimeformat')
def datetimeformat(value, format='%d %B %Y - %H:%M'):
    return datetime.strptime(value, '%Y-%m-%d %H:%M:%S').strftime(format)





@app.route('/seller', methods=['GET', 'POST'])
def add_seller():
    if request.method == 'GET':
        return render_template('admin/seller.html')

    if request.method == 'POST':
        try:
            # --- الحصول على البيانات من النموذج ---
            name = request.form.get('name')
            store_name = request.form.get('store_name')
            commercial_record = request.form.get('commercial_record')
            latitude = request.form.get('latitude')
            longitude = request.form.get('longitude')
            street_address = request.form.get('addressDisplay')
            number1 = request.form.get('number1')
            number2 = request.form.get('number2')
            
            print(f"📥 بيانات مستلمة: {request.form}")
            
            # --- معالجة الملفات ---
            store_image = request.files.get('store_image')
            id_image = request.files.get('id_image')
            documents = request.files.get('documents')

            # تحديد المسارات
            upload_base_folder = app.config['UPLOAD_FOLDER']
            store_image_folder = os.path.join(upload_base_folder, "store_images")
            id_image_folder = os.path.join(upload_base_folder, "id_images")
            documents_folder = os.path.join(upload_base_folder, "documents")

            os.makedirs(store_image_folder, exist_ok=True)
            os.makedirs(id_image_folder, exist_ok=True)
            os.makedirs(documents_folder, exist_ok=True)

            store_image_path = id_image_path = documents_path = ""

            if store_image and allowed_file(store_image.filename):
                store_image_filename = secure_filename(store_image.filename)
                store_image_path = os.path.join(store_image_folder, store_image_filename)
                store_image.save(store_image_path)

            if id_image and allowed_file(id_image.filename):
                id_image_filename = secure_filename(id_image.filename)
                id_image_path = os.path.join(id_image_folder, id_image_filename)
                id_image.save(id_image_path)

            if documents and allowed_file(documents.filename):
                documents_filename = secure_filename(documents.filename)
                documents_path = os.path.join(documents_folder, documents_filename)
                documents.save(documents_path)

            # --- الاتصال بقاعدة البيانات ---
            conn = get_db_connection()
            cursor = conn.cursor()

            # إدخال العنوان
            cursor.execute(
                "INSERT INTO seller_address (latitude, longitude, address) VALUES (?, ?, ?)",
                (latitude, longitude, street_address)
            )
            address_id = cursor.lastrowid
            print(f"✅ إدخال العنوان: {address_id}")

            # إدخال الأرقام
            cursor.execute(
                "INSERT INTO numbers (number1, number2) VALUES (?, ?)",
                (number1, number2)
            )
            num_id = cursor.lastrowid
            print(f"✅ إدخال الأرقام: {num_id}")

            # إدخال البائع
            cursor.execute('''
                INSERT INTO sellers
                (name, store_name, store_image, address, commercial_record, id_image, documents, SAddress_id, num_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                name, store_name, store_image_path, street_address, commercial_record, id_image_path, documents_path, address_id, num_id
            ))

            conn.commit()
            print("✅ إدخال البائع ناجح!")
            conn.close()

            flash("تمت إضافة البائع بنجاح!", "success")
            return redirect(url_for('add_seller'))

        except Exception as e:
            print(f"❌ خطأ: {str(e)}")
            flash(f"حدث خطأ: {str(e)}", "danger")
            return redirect(url_for('add_seller'))

        
@app.route('/show_seller', methods=['POST', 'GET'])
def show_seller():
    # الاتصال بقاعدة البيانات
    conn = sqlite3.connect("database/Eshop.db")
    cursor = conn.cursor()

    # استرجاع جميع بيانات البائعين
    sellers = cursor.execute("""
        SELECT 
            s.id, s.name, s.store_name, s.store_image, 
            s.commercial_record, s.id_image, s.documents,
            s.created_at,
            sa.address, sa.latitude, sa.longitude,
            n.number1, n.number2
        FROM sellers s
        JOIN seller_address sa ON s.SAddress_id = sa.id
        JOIN numbers n ON s.num_id = n.id
        ORDER BY s.created_at DESC """).fetchall()

    conn.close()

    # تمرير البيانات إلى الصفحة
    return render_template('admin/show_seller.html', sellers=sellers)


# يعرض اصحاب المنتجات في الheader


@app.route('/seller/<int:seller_id>/products')
def seller_products(seller_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    # جلب معلومات البائع أولاً
    seller = cursor.execute('SELECT id, store_name FROM sellers WHERE id = ?', (seller_id,)).fetchone()
    
    if not seller:
        abort(404)  # إذا لم يتم العثور على البائع
    
    products = cursor.execute('''
        SELECT 
            p.id, p.name, p.image, p.description,
            pr.original_price, pr.profit_price,
            s.quantity, c.name AS category,
            sllr.name AS seller, sa.address AS address,
            p.featured, p.seller_id
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
    return render_template('seller_product.html', products=products, seller=seller)

@app.context_processor
def inject_sellers():
    conn = get_db_connection()
    sellers = conn.execute('SELECT id, store_name FROM sellers').fetchall()
    conn.close()
    return dict(sellers=sellers)


@app.route('/edit_seller/<int:seller_id>', methods=['GET', 'POST'])
def edit_seller(seller_id):
    try:
        conn = sqlite3.connect("database/Eshop.db")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # جلب بيانات البائع مع معلومات العنوان والأرقام
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
            return redirect('/show_seller')

        if request.method == 'POST':
            # استقبال البيانات الأساسية
            name = request.form['name']
            store_name = request.form['store_name']
            commercial_record = request.form['commercial_record']
            
            # بيانات العنوان
            latitude = request.form.get('latitude')
            longitude = request.form.get('longitude')
            street_address = request.form.get('addressDisplay')
            
            # أرقام الهاتف
            number1 = request.form.get('number1')
            number2 = request.form.get('number2')

            # معالجة الملفات
            store_image = seller['store_image']
            id_image = seller['id_image']
            documents = seller['documents']

            if 'store_image' in request.files:
                file = request.files['store_image']
                if file.filename != '':
                    filename = secure_filename(file.filename)
                    path = os.path.join(app.config['UPLOAD_FOLDER'], 'store_images', filename)
                    os.makedirs(os.path.dirname(path), exist_ok=True)
                    file.save(path)
                    store_image = path

            if 'id_image' in request.files:
                file = request.files['id_image']
                if file.filename != '':
                    filename = secure_filename(file.filename)
                    path = os.path.join(app.config['UPLOAD_FOLDER'], 'id_images', filename)
                    os.makedirs(os.path.dirname(path), exist_ok=True)
                    file.save(path)
                    id_image = path

            if 'documents' in request.files:
                file = request.files['documents']
                if file.filename != '':
                    filename = secure_filename(file.filename)
                    path = os.path.join(app.config['UPLOAD_FOLDER'], 'documents', filename)
                    os.makedirs(os.path.dirname(path), exist_ok=True)
                    file.save(path)
                    documents = path

            # تحديث البيانات في قاعدة البيانات
            cursor.execute("""
                UPDATE sellers SET
                    name = ?,
                    store_name = ?,
                    commercial_record = ?,
                    store_image = ?,
                    id_image = ?,
                    documents = ?
                WHERE id = ?
            """, (name, store_name, commercial_record, store_image, id_image, documents, seller_id))

            # تحديث العنوان
            cursor.execute("""
                UPDATE seller_address SET
                    latitude = ?,
                    longitude = ?,
                    address = ?
                WHERE id = ?
            """, (latitude, longitude, street_address, seller['SAddress_id']))

            # تحديث الأرقام
            cursor.execute("""
                UPDATE numbers SET
                    number1 = ?,
                    number2 = ?
                WHERE id = ?
            """, (number1, number2, seller['num_id']))

            conn.commit()
            flash("تم تعديل بيانات البائع بنجاح!", "success")
            return redirect('/show_seller')

        # تحويل كائن sqlite3.Row إلى dict لسهولة الاستخدام في القالب
        seller_dict = dict(seller)
        seller_dict['has_location'] = bool(seller['latitude'] and seller['longitude'])
        
        return render_template('admin/edit_seller.html', seller=seller_dict)

    except Exception as e:
        flash(f"حدث خطأ: {str(e)}", "danger")
        return redirect('/show_seller')
    finally:
        conn.close()
# حذف قسم
@app.route('/delete_seller/<int:seller_id>')
def delete_seller(seller_id):
    try:
        conn = sqlite3.connect("database/Eshop.db")
        cursor = conn.cursor()

        # التأكد من أن البائع موجود
        cursor.execute("SELECT * FROM sellers WHERE id = ?", (seller_id,))
        seller = cursor.fetchone()
        
        if not seller:
            flash("صاحب المتجر غير موجود!", "danger")
            return redirect('/show_seller')

        # حذف البائع من قاعدة البيانات
        cursor.execute("DELETE FROM sellers WHERE id = ?", (seller_id,))
        conn.commit()
        conn.close()

        flash("تم حذف صاحب المتجر بنجاح!", "success")
        return redirect('/show_seller')
    
    except Exception as e:
        flash(f"حدث خطأ أثناء الحذف: {str(e)}", "danger")
        return redirect('/show_seller')


@app.route('/blog-details')
def blogdetails():
    return render_template('blog-details.html')

@app.route('/blog')
def blog():
    return render_template('blog.html')







@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    name = request.form.get('name')
    price = float(request.form.get('price'))
    quantity = int(request.form.get('quantity', 1))
    image = request.form.get('image')  
    description = request.form.get('description')
    seller = request.form.get('seller')

    product_item = {
        'product_id': product_id,
        'name': name,
        'price': price,
        'quantity': quantity,
        'image': image,
        'description': description,
        'seller': seller
    }

    cart = request.cookies.get('cart')
    cart = json.loads(cart) if cart else []

    for item in cart:
        if item.get('product_id') == product_id:
            item['quantity'] += quantity
            break
    else:
        cart.append(product_item)

    response = make_response(redirect(url_for('view_cart')))
    expires = datetime.now() + timedelta(days=7)
    response.set_cookie('cart', json.dumps(cart), expires=expires)
    return response
    
@app.route('/view_cart')
def view_cart():
    cart = request.cookies.get('cart')
    cart = json.loads(cart) if cart else []
    
    # تحقق من البيانات وتأكد من وجود image_url
    for item in cart:
        if 'image_url' not in item:
            item['image_url'] = 'default_product.jpg'  # صورة افتراضية
        # تأكد من أن المسار صحيح (إزالة أي مسارات مطلقة إذا كانت موجودة)
        item['image_url'] = item['image_url'].split('/')[-1]  # يأخذ اسم الملف فقط
    
    return render_template('cart.html', cart=cart)

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if request.method == 'POST':
        cart = request.cookies.get('cart')
        if not cart:
            return "عربة التسوق فارغة", 400
        
        cart = json.loads(cart)
        total_amount = sum(item['price'] * item['quantity'] for item in cart)
        user_id = 1  # يجب جلبه من الجلسة عند دعم المستخدمين المسجلين
        created_at = datetime.now()
        
        db = get_db_connection()
        cursor = db.cursor()
        try:
            cursor.execute('''
                INSERT INTO orders1 (user_id, total_price, status, created_at)
                VALUES (?, ?, ?, ?)
            ''', (user_id, total_amount, 'pending', created_at))
            order_id = cursor.lastrowid
            
            for item in cart:
                cursor.execute('''
                    INSERT INTO Order_Items (order_id, product_id, quantity, price)
                    VALUES (?, ?, ?, ?)
                ''', (order_id, item['product_id'], item['quantity'], item['price']))
            
            db.commit()
        except sqlite3.IntegrityError as e:
            db.rollback()
            return f"خطأ في إدخال البيانات: {e}", 400
        except Exception as e:
            db.rollback()
            return f"حدث خطأ غير متوقع: {e}", 500
        finally:
            db.close()
        
        response = make_response(redirect(url_for('order_summary', order_id=order_id)))
        response.set_cookie('cart', '', expires=0)
        return response
    
    return render_template('checkout1html')

@app.route('/order_summary/<int:order_id>')
def order_summary(order_id):
    db = get_db_connection()
    cursor = db.cursor()
    cursor.execute('''
        SELECT * FROM orders1 WHERE id = ?
    ''', (order_id,))
    order = cursor.fetchone()
    
    cursor.execute('''
        SELECT oi.quantity, oi.price, p.name FROM Order_Items oi
        JOIN product p ON oi.product_id = p.id
        WHERE oi.order_id = ?
    ''', (order_id,))
    items = cursor.fetchall()
    db.close()
    
    if not order:
        return "الطلب غير موجود", 404
    
    return render_template('order_summary.html', order=order, items=items)

@app.route('/cart')
def cart():
    return "هذه صفحة العربة"

@app.route('/update_cart/<int:product_id>', methods=['POST'])
def update_cart(product_id):
    cart = request.cookies.get('cart')
    if not cart:
        return "عربة التسوق فارغة", 400

    cart = json.loads(cart)
    action = request.form.get('action')

    if action == 'remove':
        cart = [item for item in cart if item['product_id'] != product_id]
    else:
        for item in cart:
            if item['product_id'] == product_id:
                if action == 'increase':
                    item['quantity'] += 1
                elif action == 'decrease' and item['quantity'] > 1:
                    item['quantity'] -= 1
                break

    response = make_response(redirect(url_for('view_cart')))
    expires = datetime.now() + timedelta(days=7)
    response.set_cookie('cart', json.dumps(cart), expires=expires)
    return response

@app.route('/clear_cart', methods=['POST'])
def clear_cart():
    response = make_response(redirect(url_for('view_cart')))
    response.set_cookie('cart', '', expires=0)
    return response















@app.route('/contact')
def contact():
    return render_template('contact.html')



# @app.route('/shoping-cart')
# def cart():
#     return render_template('shoping-cart.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'GET':
        return render_template('signup.html')

    if request.method == 'POST':
        try:
            name = request.form['name']
            phone = request.form['phone_number']
            password = generate_password_hash(request.form['password'])
            email = request.form['email']
            latitude = request.form['latitude']
            longitude = request.form['longitude']
            address = request.form['addressDisplay']

            conn = get_db_connection()
            cursor = conn.cursor()

            # إضافة العنوان
            cursor.execute("INSERT INTO user_addresses (latitude, longitude, address) VALUES (?, ?, ?)",
                          (latitude, longitude, address))
            address_id = cursor.lastrowid

            # إضافة المستخدم
            cursor.execute("INSERT INTO user (name, num, pass, email, ud_ia) VALUES (?, ?, ?, ?, ?)",
                          (name, phone, password, email, address_id))
            user_id = cursor.lastrowid
            conn.commit()

            # تسجيل الدخول تلقائيًا باستخدام الكوكيز
            response = make_response(redirect(url_for('index')))
            response.set_cookie(
                'user_auth',
                value=str(user_id),
                max_age=60*60*24*30,
                secure=True,
                httponly=True,
                samesite='Lax'
            )
            response.set_cookie(
                'user_name',
                value=name,
                max_age=60*60*24*7,
                secure=True,
                httponly=False
            )

            flash('تم إنشاء الحساب وتسجيل الدخول بنجاح!', 'success')
            return response

        except sqlite3.IntegrityError as e:
            flash('البريد الإلكتروني أو رقم الهاتف مسجل مسبقًا.', 'danger')
            return redirect(url_for('signup'))

        except Exception as e:
            flash('حدث خطأ أثناء إنشاء الحساب. الرجاء المحاولة مرة أخرى.', 'danger')
            return redirect(url_for('signup'))

        finally:
            if 'conn' in locals():
                conn.close()



@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('signin.html')

    if request.method == 'POST':
        name = request.form['name']
        password = request.form['password']

        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM user WHERE name = ?", (name,))
        user = cursor.fetchone()
        conn.close()

        if user is None:
            flash('اسم المستخدم غير موجود.', 'danger')
            return redirect(url_for('login'))

        stored_password = user['pass']
        if check_password_hash(stored_password, password):
            response = make_response(redirect(url_for('index')))
            response.set_cookie(
                'user_auth',
                value=str(user['id']),
                max_age=60*60*24*7,
                secure=True,
                httponly=True,
                samesite='Lax'
            )
            response.set_cookie(
                'user_name',
                value=user['name'],
                max_age=60*60*24*7,
                secure=True,
                httponly=False
            )

            flash('تم تسجيل الدخول بنجاح.', 'success')
            return response
        else:
            flash('كلمة المرور غير صحيحة.', 'danger')
            return redirect(url_for('login'))

# 🟢 تسجيل الخروج
@app.route('/logout')
def logout():
    response = make_response(redirect(url_for('index')))
    response.delete_cookie('user_auth')
    response.delete_cookie('user_name')
    flash('تم تسجيل الخروج بنجاح.', 'success')
    return response

from functools import wraps

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = request.cookies.get('user_auth')
        
        if not user_id:
            flash('يجب تسجيل الدخول للوصول إلى هذه الصفحة', 'warning')
            return redirect(url_for('login', next=request.url))
            
        # تحقق من وجود المستخدم في DB
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM user WHERE id = ?", (user_id,))
        if not cursor.fetchone():
            response = make_response(redirect(url_for('login')))
            response.delete_cookie('user_auth')
            response.delete_cookie('user_name')
            flash('جلسة العمل منتهية، يرجى تسجيل الدخول مرة أخرى', 'warning')
            return response
            
        return f(*args, **kwargs)
    return decorated_function



@app.route('/profile')
@login_required
def profile():
    try:
        user_id = request.cookies.get('user_auth')
        print(f"قيمة الكوكي user_auth: {user_id}")  # للتأكد من وجود الكوكي
        
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # استعلام أكثر تفصيلاً للتحقق من المشكلة
        cursor.execute("""
            SELECT 
                u.id, u.name, u.num, u.email, u.ud_ia,
                a.address, a.latitude, a.longitude
            FROM user u
            LEFT JOIN user_addresses a ON u.ud_ia = a.id
            WHERE u.id = ?
        """, (user_id,))
        
        user_data = cursor.fetchone()
        conn.close()

        if not user_data:
            print("لم يتم العثور على مستخدم بهذا المعرف")
            return render_template('profile.html', error="المستخدم غير موجود")
        
        print("بيانات المستخدم المسترجعة:", dict(user_data))

        # تحويل None إلى قيم افتراضية
        user = {
            'id': user_data['id'],
            'name': user_data['name'] or 'غير محدد',
            'num': user_data['num'] or 'غير محدد',
            'email': user_data['email'] or 'غير محدد',
            'address': user_data['address'] or 'لم يتم إضافة عنوان',
            'latitude': user_data['latitude'],
            'longitude': user_data['longitude']
        }

        return render_template('profile.html', user=user)

    except Exception as e:
        print(f"خطأ مفاجئ: {str(e)}")
        return render_template('profile.html', error="حدث خطأ في جلب البيانات")
    

# show_users
@app.route('/users')
@login_required
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



# delete user
@app.route('/delete_user/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # حذف المستخدم
        cursor.execute("DELETE FROM user WHERE id = ?", (user_id,))
        conn.commit()
        conn.close()

        return redirect(url_for('users', message="تم حذف المستخدم بنجاح."))

    except Exception as e:
        print(f"خطأ أثناء الحذف: {e}")
        return redirect(url_for('users', error="حدث خطأ أثناء حذف المستخدم."))

@app.route('/toggle_like/<int:product_id>', methods=['POST'])
def toggle_like(product_id):
    if 'user_id' not in session:
        return jsonify({
            'success': False, 
            'message': 'يجب تسجيل الدخول أولاً',
            'is_authenticated': False
        }), 401

    user_id = session['user_id']
    
    conn = get_db_connection()
    try:
        like = conn.execute('SELECT * FROM likes WHERE user_id=? AND product_id=?', 
                          (user_id, product_id)).fetchone()
        
        if like:
            conn.execute('DELETE FROM likes WHERE user_id=? AND product_id=?', 
                        (user_id, product_id))
            action = 'unliked'
        else:
            conn.execute('INSERT INTO likes (user_id, product_id) VALUES (?, ?)', 
                        (user_id, product_id))
            action = 'liked'
        
        conn.commit()
        return jsonify({
            'success': True, 
            'action': action,
            'is_authenticated': True
        })
    except Exception as e:
        return jsonify({
            'success': False, 
            'message': str(e),
            'is_authenticated': True
        }), 500
    finally:
        conn.close()

@app.route('/wishlist')
def wishlist():
    if 'user_id' not in session:
        flash('يجب تسجيل الدخول لعرض المفضلة', 'warning')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    liked_products = conn.execute('''
        SELECT product.* FROM product
        JOIN likes ON product.id = likes.product_id
        WHERE likes.user_id = ?
    ''', (session['user_id'],)).fetchall()
    
    conn.close()
    
    return render_template('wishlist.html', products=liked_products)

if __name__ == '__main__':
    app.run()