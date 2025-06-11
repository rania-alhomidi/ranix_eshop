# cart_routes.py

from flask import Blueprint, render_template, request, redirect, url_for, flash, make_response, jsonify # أضف jsonify
import sqlite3
import json
from datetime import datetime, timedelta

# إنشاء Blueprint لسلة التسوق
cart_bp = Blueprint('cart', __name__)

# دالة للاتصال بقاعدة البيانات
def get_db_connection():
    conn = sqlite3.connect('database/Eshop.db')
    conn.row_factory = sqlite3.Row  # لتسهيل الوصول إلى الأعمدة بالاسم
    return conn

# --- دالة مساعدة لربط سلة التسوق بالمستخدم الحالي ---
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

    total_price = 0.0
    total_items_count = 0 

    for item in cart_items:
        item_price = float(item.get('price', 0))
        item_quantity = int(item.get('quantity', 0))
        
        total_price += item_price * item_quantity
        total_items_count += item_quantity 

    return render_template('cart.html', 
                           cart=cart_items, 
                           total_price=total_price,
                           total_items_count=total_items_count)

@cart_bp.route('/add_to_cart/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    user_key = get_current_user_key() 

    try:
        conn = get_db_connection()
        product_db_info = conn.execute(
            """
            SELECT 
                p.name, 
                pr.original_price as price, 
                p.image 
            FROM 
                product p
            JOIN 
                prices pr ON p.price_id = pr.id
            WHERE 
                p.id = ?
            """, 
            (product_id,)
        ).fetchone()
        conn.close()

        if not product_db_info:
            # نُرجع JSON بدلاً من Flash و redirect
            return jsonify({'success': False, 'message': "المنتج غير موجود أو سعره غير محدد."}), 404 

        name = product_db_info['name']
        price = float(product_db_info['price'])
        image = product_db_info['image']

        quantity_str = request.form.get('quantity', '1')
        quantity = int(quantity_str)

        if quantity <= 0:
            # نُرجع JSON بدلاً من Flash و redirect
            return jsonify({'success': False, 'message': "الكمية يجب أن تكون موجبة."}), 400

    except (ValueError, TypeError) as e:
        print(f"Error converting price/quantity for product_id {product_id}: {e}")
        # نُرجع JSON بدلاً من Flash و redirect
        return jsonify({'success': False, 'message': f"بيانات المنتج غير صالحة. خطأ: {e}"}), 400

    product_item = {
        'product_id': product_id,
        'name': name,
        'price': price,
        'quantity': quantity,
        'image': image
    }

    all_carts_cookie = request.cookies.get('all_user_carts')
    all_user_carts = json.loads(all_carts_cookie) if all_carts_cookie else {}

    current_user_cart = all_user_carts.get(user_key, [])

    found = False
    for item in current_user_cart:
        if item.get('product_id') == product_id:
            item['quantity'] = item.get('quantity', 0) + quantity 
            found = True
            break
    if not found:
        current_user_cart.append(product_item)
    
    all_user_carts[user_key] = current_user_cart

    # إنشاء استجابة make_response لتعيين الكوكي
    response = make_response(jsonify({
        'success': True, 
        'message': f"تم إضافة {quantity} من {name} إلى سلة التسوق.",
        'total_items_count': sum(item['quantity'] for item in current_user_cart) # لإعطاء تحديث فوري لعدد العناصر في السلة
    }))
    
    expires = datetime.now() + timedelta(days=7)
    response.set_cookie('all_user_carts', json.dumps(all_user_carts), expires=expires, httponly=True, secure=True, samesite='Lax') 
    
    return response

# ... (بقية الكود لـ update_cart و clear_cart و get_current_user_key لم يتغير) ...

# ملاحظة: دالتي update_cart و clear_cart لا تزالان تقومان بإعادة توجيه. إذا أردت تغيير سلوكهما
# ليصبحا غير معيدين للتوجيه، ستحتاج لتطبيق نفس مبدأ AJAX عليهما.
# في هذه الإجابة، ركزنا على add_to_cart فقط.

# الكود التالي لم يتغير...
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