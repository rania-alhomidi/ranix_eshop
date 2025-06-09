# cart_routes.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, make_response
import sqlite3
import json
from datetime import datetime, timedelta

cart_bp = Blueprint('cart', __name__)

def get_db_connection():
    conn = sqlite3.connect('database/Eshop.db')
    conn.row_factory = sqlite3.Row
    return conn

# --- مسارات (Routes) لعربة التسوق ---

@cart_bp.route('/view_cart')
def view_cart():
    cart_cookie = request.cookies.get('cart')
    cart_items = json.loads(cart_cookie) if cart_cookie else []

    # إذا أردت جلب بيانات أكثر تفصيلاً للمنتجات من قاعدة البيانات، يمكنك القيام بذلك هنا
    # For now, we'll assume the cart cookie contains enough info to display.

    total_price = sum(item.get('price', 0) * item.get('quantity', 0) for item in cart_items)

    return render_template('cart.html', cart=cart_items, total_price=total_price)

@cart_bp.route('/add_to_cart/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    try:
        # التأكد من تحويل price و quantity إلى أرقام مباشرة هنا
        name = request.form.get('name')
        # استخدم get() مع قيمة افتراضية للتأكد من أنها لا تسبب خطأ إذا كان المفتاح مفقودًا
        price_str = request.form.get('price', '0.0')
        quantity_str = request.form.get('quantity', '1')

        price = float(price_str)
        quantity = int(quantity_str)

        if quantity <= 0:
            flash("الكمية يجب أن تكون موجبة.", "warning")
            return redirect(url_for('product.index')) # أو أي صفحة مناسبة

        image = request.form.get('image', 'default_product.jpg')
        description = request.form.get('description')
        seller = request.form.get('seller')

    except (ValueError, TypeError) as e:
        flash(f"بيانات المنتج غير صالحة. خطأ: {e}", "error")
        print(f"Error converting price/quantity for product_id {product_id}: {e}")
        return redirect(url_for('product.index'))

    product_item = {
        'product_id': product_id,
        'name': name,
        'price': price,     # الآن float
        'quantity': quantity, # الآن int
        'image': image,
        'description': description,
        'seller': seller
    }

    # قراءة الكوكيز وتحويلها من JSON
    cart_cookie = request.cookies.get('cart')
    cart = json.loads(cart_cookie) if cart_cookie else []

    found = False
    for item in cart:
        # تأكد من أن product_id هو نفس النوع (int) عند المقارنة
        if item.get('product_id') == product_id:
            item['quantity'] = item.get('quantity', 0) + quantity # ضمان أن الكمية رقم
            found = True
            break
    if not found:
        cart.append(product_item)

    # إنشاء الاستجابة وحفظ الكوكيز
    response = make_response(redirect(url_for('cart.view_cart')))
    expires = datetime.now() + timedelta(days=7)
    response.set_cookie('cart', json.dumps(cart), expires=expires, httponly=True, secure=True, samesite='Lax') # إعدادات أمان الكوكيز
    flash(f"تم إضافة {quantity} من {name} إلى سلة التسوق.", "success")
    return response

@cart_bp.route('/update_cart/<int:product_id>', methods=['POST'])
def update_cart(product_id):
    cart = request.cookies.get('cart')
    if not cart:
        flash("عربة التسوق فارغة", "warning")
        return redirect(url_for('cart.view_cart'))

    cart = json.loads(cart)
    action = request.form.get('action')

    new_cart = []
    item_found = False
    for item in cart:
        if item['product_id'] == product_id:
            item_found = True
            if action == 'remove':
                continue
            elif action == 'increase':
                item['quantity'] += 1
            elif action == 'decrease' and item['quantity'] > 1:
                item['quantity'] -= 1
        new_cart.append(item)

    if not item_found and action != 'remove':
        flash("المنتج غير موجود في سلة التسوق.", "danger")
        return redirect(url_for('cart.view_cart'))

    response = make_response(redirect(url_for('cart.view_cart')))
    expires = datetime.now() + timedelta(days=7)
    response.set_cookie('cart', json.dumps(new_cart), expires=expires, httponly=True, secure=True, samesite='Lax')
    return response

@cart_bp.route('/clear_cart', methods=['POST'])
def clear_cart():
    response = make_response(redirect(url_for('cart.view_cart')))
    response.set_cookie('cart', '', expires=0, httponly=True, secure=True, samesite='Lax')
    flash("تم تفريغ عربة التسوق.", "info")
    return response

# ملاحظة: دالة confirm_order_page، checkout، و order_summary
# يجب أن تكون في order_routes.py وليس هنا.
# قم بإزالتها من هنا.