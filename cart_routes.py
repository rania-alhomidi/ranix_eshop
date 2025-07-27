# cart_routes.py

from flask import Blueprint, render_template, request, redirect, url_for, flash, make_response, jsonify
import sqlite3
import json
from datetime import datetime, timedelta
import os # تأكد من استيراد os للتعامل مع المسارات

# إنشاء Blueprint لسلة التسوق
cart_bp = Blueprint('cart', __name__)

# دالة للاتصال بقاعدة البيانات
def get_db_connection():
    conn = sqlite3.connect('database/Eshop.db')
    conn.row_factory = sqlite3.Row  # لتسهيل الوصول إلى الأعمدة بالاسم
    return conn

# دالة مساعدة لربط سلة التسوق بالمستخدم الحالي
def get_current_user_key():
    user_id = request.cookies.get('user_auth')
    if user_id:
        return str(user_id)
    return 'guest_cart'

# --- مسارات (Routes) عربة التسوق ---

@cart_bp.route('/view_cart')
def view_cart():
    user_key = get_current_user_key()
    all_carts_cookie = request.cookies.get('all_user_carts')
    all_user_carts = json.loads(all_carts_cookie) if all_carts_cookie else {}
    cart_items = all_user_carts.get(user_key, [])

    print(f"DEBUG (view_cart): User Key: {user_key}")
    print(f"DEBUG (view_cart): Raw cart_items from cookie: {cart_items}")

    total_price = 0.0
    total_items_count = 0

    updated_cart_items = []

    conn = get_db_connection()
    for item in cart_items:
        product_id = item['product_id']
        quantity = item.get('quantity', 0)

        print(f"DEBUG (view_cart): Processing product_id: {product_id}, quantity: {quantity}")

        # *** التعديل الرئيسي هنا: ضم جدول product_image لجلب مسار الصورة ***
        updated_product = conn.execute("""
            SELECT
                p.name,
                pr.profit_price as price,
                pi.image_path as image -- جلب image_path وتسميته 'image'
            FROM
                product p
            JOIN
                prices pr ON p.price_id = pr.id
            LEFT JOIN
                product_image pi ON p.id = pi.product_id AND pi.is_main = TRUE -- ضم الصورة الرئيسية
            WHERE
                p.id = ?
        """, (product_id,)).fetchone()

        if updated_product:
            # التحقق من أن المسار image_path ليس NULL أو فارغًا
            image_path = updated_product['image']
            if image_path is None or image_path == '':
                # إذا كانت الصورة فارغة، استخدم الصورة الافتراضية
                # يجب أن تكون هذه الصورة موجودة في 'static/uploads/products/default_product.jpg'
                image_path = 'uploads/products/default_product.jpg'
                print(f"DEBUG (view_cart): Product {product_id} has no main image or image path is empty. Using default.")

            updated_item = {
                'product_id': product_id,
                'name': updated_product['name'],
                'price': float(updated_product['price']),
                'quantity': quantity,
                'image': image_path # استخدام المسار الصحيح أو الافتراضي
            }

            total_price += updated_item['price'] * quantity
            total_items_count += quantity

            updated_cart_items.append(updated_item)
            print(f"DEBUG (view_cart): Added to updated_cart_items: {updated_item}")
        else:
            print(f"DEBUG (view_cart): Product ID {product_id} not found in DB or has no valid price/main image. Skipping.")
            # يمكنك إضافة رسالة فلاش هنا إذا أردت إبلاغ المستخدم
            # flash(f"تمت إزالة المنتج (ID: {product_id}) من سلة التسوق لأنه لم يعد متاحًا.", "warning")

    conn.close()

    print(f"DEBUG (view_cart): Final updated_cart_items: {updated_cart_items}")
    print(f"DEBUG (view_cart): Total price: {total_price}, Total items: {total_items_count}")

    # تأكد من أن قالب cart.html يستخدم مسار الصورة بشكل صحيح:
    # <img src="{{ url_for('static', filename=item.image) }}" alt="{{ item.name }}" class="product-image">
    # (لاحظ أنه لا يوجد 'uploads/' إضافية هنا، لأن 'item.image' ستكون
    # إما 'uploads/products/اسم_الصورة.jpg' أو 'uploads/products/default_product.jpg')

    return render_template('cart.html',
                           cart=updated_cart_items,
                           total_price=total_price,
                           total_items_count=total_items_count)

# ... (بقية دوال cart_routes.py مثل add_to_cart، update_cart، clear_cart) ...
# تذكر أن تطبق نفس التعديل على استعلام SQL في دالة add_to_cart أيضًا!
# الكود أدناه يوضح تعديل add_to_cart:

@cart_bp.route('/add_to_cart/<int:product_id>', methods=['POST','GET'])
def add_to_cart(product_id):
    user_key = get_current_user_key()

    try:
        conn = get_db_connection()
        product_db_info = conn.execute(
            """
            SELECT
                p.name,
                pr.profit_price as price,
                pi.image_path as image -- *** التعديل هنا أيضاً ***
            FROM
                product p
            JOIN
                prices pr ON p.price_id = pr.id
            LEFT JOIN
                product_image pi ON p.id = pi.product_id AND pi.is_main = TRUE
            WHERE
                p.id = ?
            """,
            (product_id,)
        ).fetchone()
        conn.close()

        if not product_db_info:
            return jsonify({'success': False, 'message': "المنتج غير موجود أو سعره غير محدد."}), 404

        name = product_db_info['name']
        price = float(product_db_info['price'])
        # التعامل مع حالة عدم وجود مسار صورة رئيسية للمنتج عند الإضافة
        image = product_db_info['image'] if product_db_info['image'] else 'uploads/products/default_product.jpg'

        quantity_str = request.form.get('quantity', '1')
        quantity = int(quantity_str)

        if quantity <= 0:
            return jsonify({'success': False, 'message': "الكمية يجب أن تكون موجبة."}), 400

    except (ValueError, TypeError, Exception) as e: # أضف Exception لالتقاط أخطاء DB
        print(f"Error converting price/quantity or DB query for product_id {product_id}: {e}")
        return jsonify({'success': False, 'message': f"بيانات المنتج غير صالحة. خطأ: {e}"}), 400

    product_item = {
        'product_id': product_id,
        'name': name,
        'price': price,
        'quantity': quantity,
        'image': image # استخدام المسار الصحيح أو الافتراضي
    }

    all_carts_cookie = request.cookies.get('all_user_carts')
    all_user_carts = json.loads(all_carts_cookie) if all_carts_cookie else {}

    current_user_cart = all_user_carts.get(user_key, [])

    found = False
    for item in current_user_cart:
        if item.get('product_id') == product_id:
            item['quantity'] = item.get('quantity', 0) + quantity
            # تحديث معلومات المنتج في السلة حتى لو كان موجودًا (للتأكد من أحدث سعر وصورة)
            item['name'] = name
            item['price'] = price
            item['image'] = image
            found = True
            break
    if not found:
        current_user_cart.append(product_item)

    all_user_carts[user_key] = current_user_cart

    response = make_response(jsonify({
        'success': True,
        'message': f"تم إضافة {quantity} من {name} إلى سلة التسوق.",
        'total_items_count': sum(item['quantity'] for item in current_user_cart)
    }))

    expires = datetime.now() + timedelta(days=7)
    # تأكد من أن secure=True فقط إذا كنت تستخدم HTTPS في الإنتاج
    response.set_cookie('all_user_carts', json.dumps(all_user_carts), expires=expires, httponly=True, samesite='Lax')

    return response

# ... (بقية الكود لدالتي update_cart و clear_cart) ...

@cart_bp.route('/update_cart/<int:product_id>', methods=['POST'])
def update_cart(product_id):
    user_key = get_current_user_key()

    all_carts_cookie = request.cookies.get('all_user_carts')
    all_user_carts = json.loads(all_carts_cookie) if all_carts_cookie else {}

    current_user_cart = all_user_carts.get(user_key, [])

    if not current_user_cart:
        flash("عربة التسوق فارغة", "warning")
        return redirect(url_for('cart.view_cart'))

    action = request.form.get('action')

    new_user_cart = []
    item_found = False
    for item in current_user_cart:
        if item['product_id'] == product_id:
            item_found = True
            if action == 'remove':
                flash(f"تمت إزالة {item.get('name', 'المنتج')} من سلة التسوق.", "info")
                continue
            elif action == 'increase':
                item['quantity'] += 1
                flash(f"تمت زيادة كمية {item.get('name', 'المنتج')} إلى {item['quantity']}.", "info")
            elif action == 'decrease' and item['quantity'] > 1:
                item['quantity'] -= 1
                flash(f"تمت تقليل كمية {item.get('name', 'المنتج')} إلى {item['quantity']}.", "info")
            elif action == 'decrease' and item['quantity'] == 1:
                flash(f"تمت إزالة {item.get('name', 'المنتج')} من سلة التسوق.", "info")
                continue
        new_user_cart.append(item)

    if not item_found:
        flash("المنتج غير موجود في سلة التسوق.", "danger")
    
    all_user_carts[user_key] = new_user_cart

    response = make_response(redirect(url_for('cart.view_cart')))
    expires = datetime.now() + timedelta(days=7)
    response.set_cookie('all_user_carts', json.dumps(all_user_carts), expires=expires, httponly=True, secure=True, samesite='Lax')
    return response


@cart_bp.route('/clear_cart', methods=['POST'])
def clear_cart():
    user_key = get_current_user_key()

    all_carts_cookie = request.cookies.get('all_user_carts')
    all_user_carts = json.loads(all_carts_cookie) if all_carts_cookie else {}

    if user_key in all_user_carts:
        del all_user_carts[user_key] 

    response = make_response(redirect(url_for('cart.view_cart')))
    expires = datetime.now() + timedelta(days=7)
    response.set_cookie('all_user_carts', json.dumps(all_user_carts), expires=expires, httponly=True, secure=True, samesite='Lax')
    
    flash("تم تفريغ عربة التسوق.", "info")
    return response