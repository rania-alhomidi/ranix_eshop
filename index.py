from flask import Flask, render_template, request, redirect, url_for,flash
import sqlite3
import os
from werkzeug.utils import secure_filename
app = Flask(__name__)

def get_db_connection():
    conn = sqlite3.connect('database/Eshop.db')
    conn.row_factory = sqlite3.Row
    return conn


UPLOAD_FOLDER = 'uploads'  # تحديد المجلد الذي سيتم حفظ الصور فيه
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)  # إذا لم يكن المجلد موجودًا، سيتم إنشاؤه


@app.route('/add', methods=['POST', 'GET'])
def add_address():
    user_id = request.form.get('user_id')
    latitude = request.form.get('latitude')
    longitude = request.form.get('longitude')
    address = request.form.get('address')

    if not all([user_id, latitude, longitude, address]):
        return "جميع الحقول مطلوبة!", 400

    conn = sqlite3.connect("database/Eshop.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO user_addresses (user_id, latitude, longitude, address)
        VALUES (?, ?, ?, ?)
    """, (user_id, latitude, longitude, address))
    conn.commit()
    conn.close()

    return redirect('/admin/address1')

@app.route('/admin/address1')
def address():
    conn = sqlite3.connect("database/Eshop.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, user_id, latitude, longitude, address FROM user_addresses")
    addresses = cursor.fetchall()
    conn.close()
    return render_template("admin/address1.html", addresses=addresses)
@app.route('/add_price', methods=['GET', 'POST'])
def add_price():
    if request.method == 'POST':
        product_id = request.form['product_id']
        original_price = request.form['original_price']
        profit_price = request.form['profit_price']
        
        # حفظ البيانات في قاعدة البيانات
        conn = get_db_connection()
        conn.execute('INSERT INTO prices (product_id, original_price, profit_price) VALUES (?, ?, ?)',
                     (product_id, original_price, profit_price))
        conn.commit()
        conn.close()
        
        return redirect(url_for('add_price'))  # العودة لنفس الصفحة بعد الحفظ

    return render_template('admin/add_price.html')

# صفحة عرض الأسعار
@app.route('/show_prices')
def show_prices():
    conn = get_db_connection()
    prices = conn.execute('SELECT * FROM prices').fetchall()
    conn.close()
    
    return render_template('admin/show_price.html', prices=prices)









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
        address = request.form['address']
        image = request.files.get('image')

        # حفظ الصورة
        image_path = 'static/uploads/default_product.jpg'
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
        cursor.execute('''INSERT INTO product (name, description, category_id, seller_id, address, image) 
                          VALUES (?, ?, ?, ?, ?, ?)''',
                       (name, description, category_id, seller_id, address, image_path))
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
    
    return render_template('admin/add_product.html', categories=categories, sellers=sellers)












if __name__ == '__main__':
    app.run(debug=True)
