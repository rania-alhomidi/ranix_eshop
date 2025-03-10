from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
import os
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# إعداد مسار رفع الصور
# تحديد مسار حفظ الصور
UPLOAD_FOLDER = 'static/uploads'
app = Flask(__name__)
app.secret_key = 'f2d9e8a0b7c6d1e6f3a8c4b8d9e2f6a4'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# التأكد من أن المجلد موجود
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['SECRET_KEY'] = 'your_secret_key'  # مفتاح سري لحماية الجلسات


# دالة الاتصال بقاعدة البيانات
def get_db_connection():
    conn = sqlite3.connect('database/Eshop.db')
    conn.row_factory = sqlite3.Row  # لجلب النتائج كمصفوفات تشبه القواميس
    return conn

@app.route('/admin')
def home():
    return render_template('admin/index.html')

# إضافة قسم جديد
@app.route('/cate', methods=['GET', 'POST'])
def add_category():
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        name = request.form['name']
        parent_id = request.form.get('parent', None)
        image = request.files.get('image')

        cursor.execute('SELECT * FROM category WHERE name = ?', (name,))
        if cursor.fetchone():
            flash('عذرًا، هذه الفئة موجودة بالفعل.', 'danger')
            return redirect(url_for('add_category'))

        # حفظ الصورة إذا تم تحميلها
        image_path = None
        if image and image.filename:
            filename = secure_filename(image.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image.save(filepath)  # حفظ الصورة على السيرفر
            image_path = f'static/uploads/{filename}'  # حفظ المسار النسبي في قاعدة البيانات

        # إدراج الفئة في قاعدة البيانات
        cursor.execute(
            'INSERT INTO category (name, parent_id, image) VALUES (?, ?, ?)',
            (name, parent_id if parent_id else None, image_path)
        )
        conn.commit()
        conn.close()

        flash('تمت إضافة الفئة بنجاح!', 'success')
        return redirect(url_for('categories'))

    cursor.execute('SELECT * FROM category')
    categories = cursor.fetchall()
    conn.close()

    return render_template('admin/cate.html', categories=categories)

# عرض الأقسام
@app.route('/showcate')
def categories():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM category")
    categories = cursor.fetchall()
    conn.close()
    return render_template('admin/showcate.html', categories=categories)

@app.route('/edit_category/<int:category_id>', methods=['GET', 'POST'])
def edit_category(category_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    # جلب بيانات الفئة الحالية
    cursor.execute("SELECT * FROM category WHERE id = ?", (category_id,))
    category = cursor.fetchone()

    if not category:
        flash("القسم غير موجود!", "danger")
        return redirect(url_for('categories'))

    if request.method == 'POST':
        name = request.form['name']
        parent_id = request.form.get('parent', None)
        image = request.files.get('image')

        # تحديد مسار الصورة الجديد
        image_path = category['image']  # الاحتفاظ بالصورة القديمة في حال لم يتم رفع صورة جديدة

        if image and image.filename:  # إذا تم رفع صورة جديدة
            filename = secure_filename(image.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image.save(image_path)  # حفظ الصورة في المجلد
        
        # تحديث البيانات في قاعدة البيانات
        cursor.execute("""
            UPDATE category 
            SET name = ?, parent_id = ?, image = ? 
            WHERE id = ?
        """, (name, parent_id, image_path, category_id))

        conn.commit()
        conn.close()
        flash("تم تعديل القسم بنجاح!", "success")
        return redirect(url_for('categories'))

    # جلب جميع الفئات الأخرى لاختيار الفئة الرئيسية
    cursor.execute("SELECT * FROM category WHERE id != ?", (category_id,))
    categories = cursor.fetchall()

    conn.close()
    return render_template('admin/edit_category.html', category=category, categories=categories)


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
    categories = conn.execute('SELECT id, name FROM category').fetchall()
    sellers = conn.execute('SELECT seller_id, name FROM sellers').fetchall()
    addresses = conn.execute('SELECT address_id, street FROM addresses').fetchall()
    conn.close()
    
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        original_price = request.form['original_price']  # السعر الأصلي الذي يدخله المستخدم
        profit_price = request.form['profit_price']  # السعر بعد إضافة الربح الذي يدخله المستخدم
        quantity = request.form['quantity']
        category_id = request.form['category']
        seller_id = request.form['seller']
        address_id = request.form['address']
        image = request.files.get('image')

        # حفظ الصورة
        image_path = 'static/uploads/default_seller.jpg'
        if image and image.filename:
            filename = secure_filename(image.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image.save(filepath)
            image_path = f'static/uploads/{filename}'

        conn = get_db_connection()
        # إدخال المنتج
        conn.execute('''INSERT INTO product (name, description, quantity, category_id, seller_id, address_id, image) 
                        VALUES (?, ?, ?, ?, ?, ?, ?)''',
                     (name, description, quantity, category_id, seller_id, address_id, image_path))
        conn.commit()

        # الحصول على الـ product_id
        product_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]

        # إدخال الأسعار في جدول prices
        conn.execute('''INSERT INTO prices (product_id, original_price, profit_price) 
                        VALUES (?, ?, ?)''', 
                     (product_id, original_price, profit_price))
        conn.commit()
        conn.close()
        
        flash("تمت إضافة المنتج بنجاح!", "success")
        return redirect('/add_product')
    
    return render_template('admin/add_product.html', categories=categories, sellers=sellers, addresses=addresses)

# @app.route('/add_seller', methods=['GET', 'POST'])
# def add_seller():
#     conn = get_db_connection()
#     addresses = conn.execute('SELECT address_id, street FROM addresses').fetchall()
#     conn.close()
    
#     if request.method == 'POST':
#         name = request.form['name']
#         phone = request.form['phone']
#         email = request.form['email']
#         address_id = request.form['address']
#         image = request.files.get('image')

#         # حفظ الصورة
#         image_path = 'static/uploads/default_seller.jpg'
#         if image and image.filename:
#             filename = secure_filename(image.filename)
#             filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
#             image.save(filepath)
#             image_path = f'static/uploads/{filename}'

#         conn = get_db_connection()
#         conn.execute('INSERT INTO sellers (name, phone, email, address_id, image) VALUES (?, ?, ?, ?, ?)',
#                      (name, phone, email, address_id, image_path))
#         conn.commit()
#         conn.close()
        
#         flash("تمت إضافة البائع بنجاح!", "success")
#         return redirect('/show_seller')
    
#     return render_template('add_seller.html', addresses=addresses)

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
@app.route('/show_product', methods=['GET'])
def show_product():
    conn = get_db_connection()
    # الاستعلام للحصول على المنتجات مع البيانات المرتبطة مثل السعر والفئة والبائع والعنوان
    products = conn.execute('''
        SELECT p.id, p.name, p.description, pr.original_price, pr.profit_price, p.quantity, 
               c.name AS category, s.name AS seller, a.address AS address
        FROM product p
        JOIN prices pr ON p.id = pr.product_id
        JOIN category c ON p.category_id = c.id
        JOIN sellers s ON p.seller_id = s.seller_id
        JOIN user_addresses a ON p.address_id = a.id
    ''').fetchall()
    
    conn.close()  # إغلاق الاتصال بعد الحصول على البيانات
    
    # إرسال البيانات إلى القالب
    return render_template('admin/show_product.html', products=products)

@app.route('/delete_product/<int:product_id>')
def delete_product(product_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM product WHERE id = ?", (product_id,))
    products = cursor.fetchone()
    
    if not products:
        flash("المنتج غير موجود!", "danger")
        return redirect(url_for('show_product'))

    # حذف القسم من قاعدة البيانات
    cursor.execute("DELETE FROM product WHERE id = ?", (product_id,))
    conn.commit()
    conn.close()

    flash("تم حذف القسم بنجاح!", "danger")
    return redirect(url_for('show_product'))


# تشغيل التطبيق
@app.route('/edit_product/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    conn = get_db_connection()
    categories = conn.execute('SELECT id, name FROM category').fetchall()
    sellers = conn.execute('SELECT seller_id, name FROM sellers').fetchall()
    addresses = conn.execute('SELECT address_id, street FROM addresses').fetchall()
    
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        price = request.form['price']
        quantity = request.form['quantity']
        category_id = request.form['category']
        seller_id = request.form['seller']
        address_id = request.form['address']
        
        conn.execute('''UPDATE product 
                        SET name = ?, description = ?, price = ?, quantity = ?, category_id = ?, seller_id = ?, address_id = ? 
                        WHERE id = ?''', 
                     (name, description, price, quantity, category_id, seller_id, address_id, product_id))
        conn.commit()
        conn.close()
        
        return redirect('/show_product')
    
    product = conn.execute('SELECT * FROM product WHERE id = ?', (product_id,)).fetchone()
    conn.close()
    
    return render_template('admin/edit_product.html', product=product, categories=categories, sellers=sellers, addresses=addresses)

@app.route('/toggle_featured/<int:product_id>/<int:featured>', methods=['GET'])
def toggle_featured(product_id, featured):
    conn = get_db_connection()
    conn.execute('UPDATE product SET featured = ? WHERE id = ?', (featured, product_id))
    conn.commit()
    conn.close()
    
    return redirect('/show_product')

# @app.route('/show_seller')
# def show_seller():
#     conn = get_db_connection()
#     sellers = conn.execute('''
#         SELECT s.seller_id, s.name, s.phone, s.email, s.image, a.street
#         FROM sellers s
#         LEFT JOIN addresses a ON s.address_id = a.address_id
#     ''').fetchall()
#     conn.close()
    
#     return render_template('show_seller.html', sellers=sellers)

@app.route('/seller', methods=['GET', 'POST'])
def add_seller():
    if request.method == 'POST':
        try:
            # استقبال البيانات النصية
            name = request.form['name']
            store_name = request.form['store_name']
            address = request.form['address']
            phone_number = request.form['phone_number']
            password = request.form['password']
            email = request.form['email']
            commercial_record = request.form['commercial_record']
            product_type = request.form['product_type']

            # استقبال الملفات
            store_image = request.files.get('store_image')
            id_image = request.files.get('id_image')
            documents = request.files.get('documents')

            # دالة لحفظ الملفات وإرجاع المسار
            def save_file(file):
                if file and file.filename:
                    filepath = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
                    file.save(filepath)
                    return filepath  # إرجاع المسار
                return ""  # إرجاع قيمة فارغة في حال لم يتم تحميل ملف

            store_image_path = save_file(store_image)
            id_image_path = save_file(id_image)
            documents_path = save_file(documents)

            # الاتصال بقاعدة البيانات
            conn = sqlite3.connect("database/Eshop.db")
            cursor = conn.cursor()

            # إدخال البيانات في الجدول
            cursor.execute("""
                INSERT INTO sellers 
                (name, store_name, store_image, address, phone_number, password, email, commercial_record, id_image, documents, product_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (name, store_name, store_image_path, address, phone_number, password, email, commercial_record, id_image_path, documents_path, product_type))

            conn.commit()
            conn.close()

            flash("تمت إضافة البائع بنجاح!", "success")
            return redirect('/seller')

        except Exception as e:
            flash(f"حدث خطأ: {str(e)}", "danger")

    return render_template('admin/seller.html')

@app.route('/show_seller')
def show_seller():
    conn = sqlite3.connect("database/Eshop.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT seller_id, name, store_name, store_image, address, phone_number, password, email, 
               commercial_record, id_image, documents, product_type, created_at 
        FROM sellers
    """)
    sellers = cursor.fetchall()
    conn.close()
    
    return render_template("admin/show_seller.html", sellers=sellers)


@app.route('/edit_seller/<int:seller_id>', methods=['GET', 'POST'])
def edit_seller(seller_id):
    conn = sqlite3.connect("database/Eshop.db")
    cursor = conn.cursor()

    # جلب بيانات البائع الحالي
    cursor.execute('''SELECT * FROM sellers WHERE seller_id = ?''', (seller_id,))
    seller = cursor.fetchone()

    if request.method == 'POST':
        try:
            # استقبال البيانات النصية
            name = request.form['name']
            store_name = request.form['store_name']
            address = request.form['address']
            phone_number = request.form['phone_number']
            password = request.form['password']
            email = request.form['email']
            commercial_record = request.form['commercial_record']
            product_type = request.form['product_type']

            # استقبال الملفات (إذا تم رفع ملفات جديدة)
            store_image = request.files.get('store_image')
            id_image = request.files.get('id_image')
            documents = request.files.get('documents')

            # دالة لحفظ الملفات وإرجاع المسار
            def save_file(file):
                if file and file.filename:
                    filepath = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
                    file.save(filepath)
                    return filepath  # إرجاع المسار
                return ""  # إرجاع قيمة فارغة في حال لم يتم تحميل ملف

            store_image_path = save_file(store_image) or seller[2]  # استخدم الصورة الحالية إذا لم يتم رفع جديدة
            id_image_path = save_file(id_image) or seller[8]  # استخدم الصورة الحالية إذا لم يتم رفع جديدة
            documents_path = save_file(documents) or seller[9]  # استخدم الملف الحالي إذا لم يتم رفع جديد

            # تحديث البيانات في قاعدة البيانات
            cursor.execute("""
                UPDATE sellers SET
                    name = ?,
                    store_name = ?,
                    store_image = ?,
                    address = ?,
                    phone_number = ?,
                    password = ?,
                    email = ?,
                    commercial_record = ?,
                    id_image = ?,
                    documents = ?,
                    product_type = ?
                WHERE seller_id = ?
            """, (name, store_name, store_image_path, address, phone_number, password, email, commercial_record, id_image_path, documents_path, product_type, seller_id))

            conn.commit()
            conn.close()

            flash("تم تعديل بيانات البائع بنجاح!", "success")
            return redirect('/show_seller')

        except Exception as e:
            flash(f"حدث خطأ: {str(e)}", "danger")

    return render_template('admin/edit_seller.html', seller=seller)

# interface
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/shop-details/<int:product_id>')
def product_details(product_id):
    conn = get_db_connection()
    product = conn.execute('''SELECT p.name, p.description, p.price, p.quantity, p.image, 
                                     c.name as category, s.name as seller, a.street as address 
                              FROM product p
                              JOIN category c ON p.category_id = c.id
                              JOIN sellers s ON p.seller_id = s.seller_id
                              JOIN addresses a ON p.address_id = a.address_id
                              WHERE p.id = ?''', (product_id,)).fetchone()
    conn.close()

    if not product:
        flash("هذا المنتج غير موجود!", "danger")
        return redirect('/')

    return render_template('shop-details.html', product=product)

@app.route('/blog-details')
def blogdetails():
    return render_template('blog-details.html')

@app.route('/blog')
def blog():
    return render_template('blog.html')

@app.route('/checkout')
def checkout():
    return render_template('checkout.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

# @app.route('/shop-details')
# def details():
#     return render_template('shop-details.html')

@app.route('/shop-grid')
def grid():
    return render_template('shop-grid.html')

@app.route('/shoping-cart')
def cart():
    return render_template('shoping-cart.html')



# تشغيل التطبيق
if __name__ == '__main__':
    app.run(debug=True)
