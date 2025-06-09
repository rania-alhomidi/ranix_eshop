# cart_routes.py

from flask import Blueprint, render_template, request, redirect, url_for, flash, make_response
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
# هذه الدالة تحدد مفتاح سلة التسوق الذي سيتم استخدامه في الكوكي 'all_user_carts'.
# إذا كان المستخدم مسجلاً للدخول، يتم استخدام user_id الخاص به.
# إذا لم يكن مسجلاً للدخول، يتم استخدام مفتاح عام 'guest_cart'.
def get_current_user_key():
    """
    يحصل على المفتاح الفريد لسلة التسوق للمستخدم الحالي (المسجل دخوله أو الضيف).
    يعتمد على كوكي 'user_auth' لتحديد المستخدم المسجل دخوله.
    """
    user_id = request.cookies.get('user_auth')
    if user_id:
        return str(user_id) # يجب أن يكون المفتاح string في قاموس JSON
    return 'guest_cart' # المفتاح الافتراضي لجميع المستخدمين غير المسجلين (الضيوف)

# --- مسارات (Routes) عربة التسوق ---

# cart_routes.py (داخل دالة view_cart)

@cart_bp.route('/view_cart')
def view_cart():
    user_key = get_current_user_key()

    all_carts_cookie = request.cookies.get('all_user_carts')
    all_user_carts = json.loads(all_carts_cookie) if all_carts_cookie else {}

    cart_items = all_user_carts.get(user_key, [])

    total_price = 0.0
    total_items_count = 0 # <--- متغير جديد لحساب إجمالي عدد الوحدات

    for item in cart_items:
        item_price = float(item.get('price', 0))
        item_quantity = int(item.get('quantity', 0))
        
        total_price += item_price * item_quantity
        total_items_count += item_quantity # <--- إضافة الكمية إلى الإجمالي

    # عرض القالب 'cart_view.html' مع بيانات سلة التسوق الحالية
    return render_template('cart.html', 
                           cart=cart_items, 
                           total_price=total_price,
                           total_items_count=total_items_count) # <--- تمرير المتغير الجديد

# cart_routes.py

# ... (الكود السابق بدون تغيير حتى الدالة add_to_cart) ...

@cart_bp.route('/add_to_cart/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    user_key = get_current_user_key() 

    try:
        conn = get_db_connection()
        # *** التعديل هنا: استخدام JOIN لجلب السعر ***
        # سنستخدم original_price من جدول prices
        product_db_info = conn.execute(
            """
            SELECT 
                p.name, 
                pr.original_price as price, -- <--- هنا نستخدم "pr.original_price" ونعطيه اسم مستعار "price"
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
            flash("المنتج غير موجود أو سعره غير محدد.", "danger")
            return redirect(url_for('product.index')) 

        name = product_db_info['name']
        price = float(product_db_info['price']) # الآن سيجد 'price' لأنه الاسم المستعار
        image = product_db_info['image']

        quantity_str = request.form.get('quantity', '1')
        quantity = int(quantity_str)

        if quantity <= 0:
            flash("الكمية يجب أن تكون موجبة.", "warning")
            return redirect(url_for('product.index')) 

    except (ValueError, TypeError) as e:
        flash(f"بيانات المنتج غير صالحة. خطأ: {e}", "error")
        print(f"Error converting price/quantity for product_id {product_id}: {e}")
        return redirect(url_for('product.index'))

    # ... (بقية الكود من هنا هو نفسه، لا حاجة لتغييره) ...
    # تهيئة قاموس المنتج ليتم إضافته إلى السلة
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

    response = make_response(redirect(url_for('cart.view_cart')))
    expires = datetime.now() + timedelta(days=7)
    response.set_cookie('all_user_carts', json.dumps(all_user_carts), expires=expires, httponly=True, secure=True, samesite='Lax') 
    
    flash(f"تم إضافة {quantity} من {name} إلى سلة التسوق.", "success")
    return response

# ... (بقية الكود لـ update_cart و clear_cart و get_current_user_key لم يتغير) ...

@cart_bp.route('/update_cart/<int:product_id>', methods=['POST'])
def update_cart(product_id):
    user_key = get_current_user_key() # جلب مفتاح سلة المستخدم الحالي

    # قراءة الكوكي الذي يحتوي على جميع سلال المستخدمين
    all_carts_cookie = request.cookies.get('all_user_carts')
    all_user_carts = json.loads(all_carts_cookie) if all_carts_cookie else {}

    # جلب سلة التسوق الخاصة بالمستخدم الحالي
    current_user_cart = all_user_carts.get(user_key, [])

    if not current_user_cart:
        flash("عربة التسوق فارغة", "warning")
        return redirect(url_for('cart.view_cart'))

    action = request.form.get('action') # 'remove', 'increase', 'decrease'

    new_user_cart = []
    item_found = False
    for item in current_user_cart:
        if item['product_id'] == product_id:
            item_found = True
            if action == 'remove':
                # إذا كان الإجراء 'remove'، لا نضيف هذا العنصر إلى السلة الجديدة
                flash(f"تمت إزالة {item.get('name', 'المنتج')} من سلة التسوق.", "info")
                continue 
            elif action == 'increase':
                item['quantity'] += 1
                flash(f"تمت زيادة كمية {item.get('name', 'المنتج')} إلى {item['quantity']}.", "info")
            elif action == 'decrease' and item['quantity'] > 1:
                item['quantity'] -= 1
                flash(f"تمت تقليل كمية {item.get('name', 'المنتج')} إلى {item['quantity']}.", "info")
            elif action == 'decrease' and item['quantity'] == 1:
                # إذا كانت الكمية 1 ونريد تقليلها، نعتبرها إزالة
                flash(f"تمت إزالة {item.get('name', 'المنتج')} من سلة التسوق.", "info")
                continue # لا تضيف هذا العنصر إلى السلة الجديدة
        new_user_cart.append(item) # أضف العناصر غير المحذوفة أو المعدلة

    if not item_found:
        flash("المنتج غير موجود في سلة التسوق.", "danger")
        # لا نعود هنا مباشرة، بل نكمل تحديث الكوكي لضمان الاتساق
    
    # تحديث سلة التسوق الخاصة بالمستخدم الحالي في القاموس العام
    all_user_carts[user_key] = new_user_cart

    # إنشاء الاستجابة وحفظ الكوكي المحدث
    response = make_response(redirect(url_for('cart.view_cart')))
    expires = datetime.now() + timedelta(days=7)
    response.set_cookie('all_user_carts', json.dumps(all_user_carts), expires=expires, httponly=True, secure=True, samesite='Lax')
    return response


@cart_bp.route('/clear_cart', methods=['POST'])
def clear_cart():
    user_key = get_current_user_key() # جلب مفتاح سلة المستخدم الحالي

    # قراءة الكوكي الذي يحتوي على جميع سلال المستخدمين
    all_carts_cookie = request.cookies.get('all_user_carts')
    all_user_carts = json.loads(all_carts_cookie) if all_carts_cookie else {}

    # حذف سلة التسوق الخاصة بالمستخدم الحالي من القاموس العام
    if user_key in all_user_carts:
        del all_user_carts[user_key] 

    # إنشاء الاستجابة وحفظ الكوكي المحدث (بدون سلة المستخدم الحالية)
    response = make_response(redirect(url_for('cart.view_cart')))
    expires = datetime.now() + timedelta(days=7)
    response.set_cookie('all_user_carts', json.dumps(all_user_carts), expires=expires, httponly=True, secure=True, samesite='Lax')
    
    flash("تم تفريغ عربة التسوق.", "info")
    return response