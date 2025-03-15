from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import sqlite3
import os
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

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

# @app.route('/add_product', methods=['GET', 'POST'])
# def add_product():
#     conn = get_db_connection()
#     categories = conn.execute('SELECT id, name FROM category').fetchall()
#     sellers = conn.execute('SELECT id, name FROM sellers').fetchall()
#     addresses = conn.execute('SELECT address_id, street FROM addresses').fetchall()
#     conn.close()
    
#     if request.method == 'POST':
#         name = request.form['name']
#         description = request.form['description']
#         original_price = request.form['original_price']
#         profit_price = request.form['profit_price']
#         quantity = request.form['quantity']
#         category_id = request.form['category']
#         seller_id = request.form['seller']
#         address_id = request.form['address']
#         image = request.files.get('image')

#         # حفظ الصورة
#         image_path = 'static/uploads/default_seller.jpg'
#         if image and image.filename:
#             filename = secure_filename(image.filename)
#             filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
#             image.save(filepath)
#             image_path = f'static/uploads/{filename}'

#         # فتح الاتصال بقاعدة البيانات
#         conn = get_db_connection()
#         cursor = conn.cursor()

#         # التحقق مما إذا كان المنتج موجودًا بالفعل باستخدام name
#         cursor.execute('SELECT id FROM product WHERE name = ?', (name,))
#         existing_product = cursor.fetchone()

#         if existing_product:
#             flash("المنتج موجود بالفعل!", "danger")
#             conn.close()  # إغلاق الاتصال إذا كان المنتج موجودًا
#             return redirect('/add_product')

#         # إدخال المنتج في جدول product
#         cursor.execute('''INSERT INTO product (name, description, category_id, seller_id, address_id, image) 
#                           VALUES (?, ?, ?, ?, ?, ?)''',
#                        (name, description, category_id, seller_id, address_id, image_path))
#         conn.commit()

#         # الحصول على الـ product_id
#         product_id = cursor.lastrowid

#         # إدخال الأسعار في جدول prices
#         cursor.execute('''INSERT INTO prices (product_id, original_price, profit_price) 
#                           VALUES (?, ?, ?)''', 
#                        (product_id, original_price, profit_price))
#         conn.commit()
        
#         # إدخال الكمية في جدول stock
#         cursor.execute('''INSERT INTO stock (product_id, quantity) 
#                           VALUES (?, ?)''',
#                        (product_id, quantity))
#         conn.commit()
        
#         conn.close()  # إغلاق الاتصال بعد إتمام العملية
        
#         flash("تمت إضافة المنتج بنجاح!", "success")
#         return redirect('/add_product')
    
#     return render_template('admin/add_product.html', categories=categories, sellers=sellers, addresses=addresses)


@app.route('/add_product', methods=['GET', 'POST'])
def add_product():
    conn = get_db_connection()
    categories = conn.execute('SELECT id, name FROM category').fetchall()
    sellers = conn.execute('SELECT id, name FROM sellers').fetchall()
    addresses = conn.execute('SELECT address_id, street FROM addresses').fetchall()
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

        # حفظ الصورة
        image_path = 'static/uploads/default_seller.jpg'
        if image and image.filename:
            filename = secure_filename(image.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image.save(filepath)
            image_path = f'static/uploads/{filename}'

        # فتح الاتصال بقاعدة البيانات
        conn = get_db_connection()
        cursor = conn.cursor()

        # التحقق مما إذا كان المنتج موجودًا بالفعل باستخدام name
        cursor.execute('SELECT id FROM product WHERE name = ?', (name,))
        existing_product = cursor.fetchone()

        if existing_product:
            flash("المنتج موجود بالفعل!", "danger")
            conn.close()  # إغلاق الاتصال إذا كان المنتج موجودًا
            return redirect('/add_product')

        # إدخال المنتج في جدول product
        cursor.execute('''INSERT INTO product (name, description, category_id, seller_id, address_id, image) 
                          VALUES (?, ?, ?, ?, ?, ?)''',
                       (name, description, category_id, seller_id, address_id, image_path))
        conn.commit()

        # الحصول على الـ product_id
        product_id = cursor.lastrowid

        # إدخال الأسعار في جدول prices
        cursor.execute('''INSERT INTO prices (product_id, original_price, profit_price) 
                          VALUES (?, ?, ?)''', 
                       (product_id, original_price, profit_price))
        conn.commit()
        
        # إدخال الكمية في جدول stock
        cursor.execute('''INSERT INTO stock (product_id, quantity) 
                          VALUES (?, ?)''',
                       (product_id, quantity))
        conn.commit()
        
        conn.close()  # إغلاق الاتصال بعد إتمام العملية
        
        flash("تمت إضافة المنتج بنجاح!", "success")
        return redirect('/add_product')
    
    return render_template('admin/add_product.html', categories=categories, sellers=sellers, addresses=addresses)


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
    # الاستعلام للحصول على المنتجات مع البيانات المرتبطة مثل السعر والفئة والبائع والعنوان والكمية
    products = conn.execute('''
        SELECT p.id, p.name, p.description, pr.original_price, pr.profit_price, 
               COALESCE(s.quantity, 0) AS quantity,  -- التأكد من عدم إرجاع None
               c.name AS category, sllr.name AS sellers, a.address AS seller_address
        FROM product p
        JOIN prices pr ON p.id = pr.product_id
        LEFT JOIN stock s ON p.id = s.product_id  -- الانضمام إلى جدول المخزون
        JOIN category c ON p.category_id = c.id
        JOIN sellers sllr ON p.seller_id = sllr.id
        JOIN seller_address a ON p.address_id = a.id
    ''').fetchall()
    
    conn.close()  # إغلاق الاتصال بعد الحصول على البيانات
    
    # إرسال البيانات إلى القالب
    return render_template('admin/show_product.html', products=products)


# تعديل منتج في الادمن 
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

# اضافة عنوان
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


@app.route('/seller', methods=['GET', 'POST'])
def add_seller():
    if request.method == 'GET':
        return render_template('admin/seller.html') 

    if request.method == 'POST':
        try:
            # --- Get form data ---
            name = request.form['name']
            store_name = request.form['store_name']
            #address = request.form['address']  
            phone_number = request.form['phone_number']
            password = generate_password_hash(request.form['password'])
            email = request.form['email']
            commercial_record = request.form['commercial_record']
            product_type = request.form['product_type']
            latitude = request.form['latitude']      
            longitude = request.form['longitude']   
            street_address = request.form['addressDisplay']

            # --- File handling ---
            store_image = request.files['store_image']
            id_image = request.files['id_image']
            documents = request.files['documents']

            store_image_path = ""
            id_image_path = ""
            documents_path = ""

            if store_image and allowed_file(store_image.filename):
                store_image_filename = secure_filename(store_image.filename)
                store_image_path = os.path.join(app.config['UPLOAD_FOLDER'], store_image_filename)
                store_image.save(store_image_path)
               
               
            if id_image and allowed_file(id_image.filename):
                id_image_filename = secure_filename(id_image.filename)
                id_image_path = os.path.join(app.config['UPLOAD_FOLDER'], id_image_filename)
                id_image.save(id_image_path)
                
                
            if documents and allowed_file(documents.filename):
                documents_filename = secure_filename(documents.filename)
                documents_path = os.path.join(app.config['UPLOAD_FOLDER'], documents_filename)
                documents.save(documents_path)

            # --- Database interaction ---
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute("INSERT INTO seller_address (latitude, longitude, address) VALUES (?, ?, ?)",
                           (latitude, longitude, street_address))  # Use street_address
            address_id = cursor.lastrowid

            cursor.execute('''
                INSERT INTO sellers
                (name, store_name, store_image, address, phone_number, password, email, commercial_record, id_image, documents, product_type, SAddress_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (name, store_name, store_image_path, street_address, phone_number, password, email, commercial_record, id_image_path, documents_path, product_type, address_id))

            conn.commit()
            conn.close()

            flash("تمت إضافة البائع وعنوانه بنجاح!", "success")
            return redirect(url_for('add_seller'))

        except Exception as e:
            flash(f"حدث خطأ: {str(e)}", "danger")
            return redirect(url_for('add_seller'))


from datetime import datetime

@app.template_filter('datetimeformat')
def datetimeformat(value, format='%d %B %Y - %H:%M'):
    return datetime.strptime(value, '%Y-%m-%d %H:%M:%S').strftime(format)

        
@app.route('/show_seller', methods=['POST', 'GET'])
def show_seller():
    # الاتصال بقاعدة البيانات
    conn = sqlite3.connect("database/Eshop.db")
    cursor = conn.cursor()

    # استرجاع جميع بيانات البائعين
    sellers = cursor.execute("""
        SELECT sellers.id, sellers.name, sellers.store_name, sellers.store_image, sellers.address, sellers.phone_number, 
               sellers.email, sellers.commercial_record, sellers.product_type,sellers.created_at, seller_address.latitude, seller_address.longitude, 
               seller_address.address AS street_address
        FROM sellers
        JOIN seller_address ON sellers.SAddress_id = seller_address.id
    """).fetchall()

    conn.close()

    # تمرير البيانات إلى الصفحة
    return render_template('admin/show_seller.html', sellers=sellers)

@app.route('/edit_seller/<int:seller_id>', methods=['GET', 'POST'])
def edit_seller(seller_id):
    conn = sqlite3.connect("database/Eshop.db")
    cursor = conn.cursor()

    # جلب بيانات البائع الحالي
    cursor.execute('''SELECT * FROM sellers WHERE id = ?''', (seller_id,))
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
                WHERE id = ?
            """, (name, store_name, store_image_path, address, phone_number, password, email, commercial_record, id_image_path, documents_path, product_type, seller_id))

            conn.commit()
            conn.close()

            flash("تم تعديل بيانات البائع بنجاح!", "success")
            return redirect('/show_seller')

        except Exception as e:
            flash(f"حدث خطأ: {str(e)}", "danger")

    return render_template('admin/edit_seller.html', seller=seller)
# حذف قسم
@app.route('/delete_seller/<int:seller_id>')
def delete_seller(seller_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    # التأكد من أن القسم موجود
    cursor.execute("SELECT * FROM sellers WHERE id = ?", (seller_id,))
    category = cursor.fetchone()
    
    if not category:
        flash("صاحب المتجر غير موجود!", "danger")
        return redirect(url_for('sllers'))

    # حذف القسم من قاعدة البيانات
    cursor.execute("DELETE FROM sellers WHERE id = ?", (seller_id,))
    conn.commit()
    conn.close()

    flash("تم حذف صاحب المتجر بنجاح!", "danger")
    return redirect(url_for('sellers'))

# الصفحه الرئسية لواجهه المستخدم
@app.route('/')
def index():
    return render_template('index.html')

# عرض تفاصيل المنتجات في واجهه المستخدم
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


@app.route('/shop-grid')
def grid():
    return render_template('shop-grid.html')

@app.route('/shoping-cart')
def cart():
    return render_template('shoping-cart.html')



# تشغيل التطبيق
if __name__ == '__main__':
    app.run()