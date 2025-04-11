from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session, make_response
import sqlite3
import json
from datetime import datetime, timedelta

cart_bp = Blueprint('cart', __name__) # لا بادئة هنا، مسارات العربة في الجذر

def get_db_connection():
    conn = sqlite3.connect('database/Eshop.db')
    conn.row_factory = sqlite3.Row
    return conn


@cart_bp.route('/add_to_cart/<int:product_id>', methods=['POST'])
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

    response = make_response(redirect(url_for('cart.view_cart')))
    expires = datetime.now() + timedelta(days=7)
    response.set_cookie('cart', json.dumps(cart), expires=expires)
    return response

@cart_bp.route('/view_cart')
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

@cart_bp.route('/checkout', methods=['GET', 'POST'])
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

        response = make_response(redirect(url_for('cart.order_summary', order_id=order_id)))
        response.set_cookie('cart', '', expires=0)
        return response

    return render_template('checkout1.html') # تأكد من اسم القالب الصحيح

@cart_bp.route('/order_summary/<int:order_id>')
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

@cart_bp.route('/cart')
def cart_page(): # تجنب تكرار اسم الدالة مع اسم الـ Blueprint
    return "هذه صفحة العربة"

@cart_bp.route('/update_cart/<int:product_id>', methods=['POST'])
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

    response = make_response(redirect(url_for('cart.view_cart')))
    expires = datetime.now() + timedelta(days=7)
    response.set_cookie('cart', json.dumps(cart), expires=expires)
    return response

@cart_bp.route('/clear_cart', methods=['POST'])
def clear_cart():
    response = make_response(redirect(url_for('cart.view_cart')))
    response.set_cookie('cart', '', expires=0)
    return response