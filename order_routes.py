# order_routes.py
from flask import Blueprint, render_template, request, session, redirect, url_for, flash, make_response, jsonify
import sqlite3
import json
from datetime import datetime, timedelta

order_bp = Blueprint('order', __name__)

# --- دالات المساعدة (Helper Functions) ---

def get_db_connection():
    conn = sqlite3.connect('database/Eshop.db')
    conn.row_factory = sqlite3.Row
    return conn

def get_current_user_key():
    user_id = request.cookies.get('user_auth')
    if user_id:
        return str(user_id)
    return 'guest_cart'

def get_user_balance_from_db(user_id):
    conn = get_db_connection()
    try:
        balance_row = conn.execute("SELECT balance FROM users WHERE id = ?", (user_id,)).fetchone()
        return float(balance_row['balance']) if balance_row and balance_row['balance'] is not None else 0.0
    except Exception as e:
        print(f"Error fetching user balance for user_id {user_id}: {e}")
        return 0.0
    finally:
        conn.close()

def get_user_addresses_and_default(user_id):
    conn = get_db_connection()
    recipient_address_obj = {
        'id': None,
        'address_type': "عام",
        'full_address_description': "لا يوجد عنوان محدد",
        'region': "",
        'city': "",
        'recipient_name': "غير محدد",
        'recipient_phone': "لا يوجد رقم",
        'is_default': False
    }
    all_addresses_list = []

    try:
        all_addresses_rows = conn.execute(
            "SELECT * FROM cust_addresses WHERE user_id = ? ORDER BY is_default DESC, id ASC", 
            (user_id,)
        ).fetchall()
        all_addresses_list = [dict(row) for row in all_addresses_rows]

        if all_addresses_list:
            default_address_found = False
            for addr in all_addresses_list:
                if addr['is_default'] == 1:
                    recipient_address_obj = addr
                    default_address_found = True
                    break
            
            if not default_address_found:
                recipient_address_obj = all_addresses_list[0]
        
        user_info_row = conn.execute("SELECT phone_number FROM users WHERE id = ?", (user_id,)).fetchone()
        if user_info_row and user_info_row['phone_number'] is not None:
            if recipient_address_obj.get('recipient_phone') in [None, "لا يوجد رقم", ""]:
                recipient_address_obj['recipient_phone'] = user_info_row['phone_number']

    except Exception as e:
        print(f"Error fetching user addresses/info for user_id {user_id}: {e}")
    finally:
        conn.close()
    
    return recipient_address_obj, all_addresses_list

def set_default_address_in_db(user_id, address_id):
    conn = get_db_connection()
    try:
        conn.execute("UPDATE cust_addresses SET is_default = 0 WHERE user_id = ?", (user_id,))
        conn.execute("UPDATE cust_addresses SET is_default = 1 WHERE id = ? AND user_id = ?", (address_id, user_id))
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"Database error setting default address: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


# خاص باشعارات المستخدم
# في نفس ملف order.py مع الدوال المساعدة الأخرى
def create_notification(user_id, title, message, notification_type, related_id=None):
    conn = get_db_connection()
    try:
        conn.execute(
            "INSERT INTO notifications (user_id, title, message, notification_type, related_id) VALUES (?, ?, ?, ?, ?)",
            (user_id, title, message, notification_type, related_id)
        )
        conn.commit()
    finally:
        conn.close()

def get_unread_notifications_count(user_id):
    conn = get_db_connection()
    try:
        count = conn.execute("SELECT COUNT(*) FROM notifications WHERE user_id = ? AND is_read = 0", (user_id,)).fetchone()[0]
        return count
    finally:
        conn.close()

def get_user_notifications(user_id, limit=10):
    conn = get_db_connection()
    try:
        notifications = conn.execute(
            "SELECT * FROM notifications WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit)
        ).fetchall()
        return [dict(notif) for notif in notifications]
    finally:
        conn.close()

# --- مسارات (Routes) للطلبات ---
@order_bp.route('/confirm_order_page')
def confirm_order_page():
    user_id_cookie = request.cookies.get('user_auth') 
    if not user_id_cookie:
        flash("يجب تسجيل الدخول أولاً.", "error")
        return redirect(url_for('user.login'))
    
    user_key = get_current_user_key()
    
    all_carts_cookie = request.cookies.get('all_user_carts')
    all_user_carts = json.loads(all_carts_cookie) if all_carts_cookie else {}
    
    cart_items_raw = all_user_carts.get(user_key, [])
    if not cart_items_raw:
        flash("عربة التسوق فارغة، يرجى إضافة منتجات قبل إتمام الشراء.", "info")
        return redirect(url_for('product.index')) 

    processed_order_items = []
    total_items_price = 0.0

    conn = get_db_connection()

    for item in cart_items_raw:
        product_id = item.get('product_id')
        price_row = conn.execute(
            "SELECT profit_price FROM prices WHERE product_id = ? ORDER BY id DESC LIMIT 1",
            (product_id,)
        ).fetchone()

        item_price = float(price_row['profit_price']) if price_row else float(item.get('price', 0.0))
        item_quantity = int(item.get('quantity', 0))
        item_total_price = item_price * item_quantity
        total_items_price += item_total_price

        processed_order_items.append({
            'product_id': product_id,
            'name': item.get('name'),
            'price': item_price,
            'quantity': item_quantity,
            'image': item.get('image', 'default_product.jpg'),
            'total_item_price': item_total_price
        })

    delivery_cost = 1500.0 
    total_order_price = total_items_price + delivery_cost
    
    recipient_address_obj, all_addresses = get_user_addresses_and_default(int(user_id_cookie))
    user_balance_display = get_user_balance_from_db(int(user_id_cookie))

    conn.close()

    return render_template(
        'confirm_order.html',
        order_items=processed_order_items, 
        recipient_address=recipient_address_obj, 
        all_addresses=all_addresses, 
        user_balance=user_balance_display,
        total_order_price=total_order_price,
        delivery_cost=delivery_cost,
        total_items_price=total_items_price 
    )


@order_bp.route('/set_default_address/<int:address_id>', methods=['POST'])
def set_default_address(address_id):
    # 1. التحقق من المصادقة وجلب معرف المستخدم
    user_id_cookie = request.cookies.get('user_auth') 
    if not user_id_cookie:
        # 💡 إرجاع JSON للـ AJAX
        return jsonify({'success': False, 'message': 'يجب تسجيل الدخول أولاً.'}), 401 

    user_id = int(user_id_cookie)

    conn = get_db_connection()
    try:
        # 2. التحقق من وجود العنوان وملكية المستخدم له
        # ملاحظة: تم تعديل الاستعلام لجلب جميع البيانات (لإرسالها لاحقًا)
        address_row = conn.execute("SELECT * FROM cust_addresses WHERE id = ? AND user_id = ?", (address_id, user_id)).fetchone()
        
        if not address_row:
            conn.close()
            return jsonify({'success': False, 'message': 'العنوان غير موجود أو لا يخص حسابك.'}), 403 

        # 3. تحديث قاعدة البيانات: إزالة الافتراضية السابقة وتعيين الجديدة
        conn.execute("UPDATE cust_addresses SET is_default = 0 WHERE user_id = ?", (user_id,))
        conn.execute("UPDATE cust_addresses SET is_default = 1 WHERE id = ? AND user_id = ?", (address_id, user_id))
        conn.commit()
        
        address_data = dict(address_row)

        # 6. إرجاع استجابة JSON للنجاح (مع بيانات العنوان المطلوبة)
        return jsonify({
            'success': True, 
            'message': 'تم تحديث العنوان الافتراضي بنجاح. ✅',
            # 💡 هذه البيانات ضرورية لـ updateAddressUI في الـ JavaScript
            'address': {
                'id': address_data['id'],
                'recipient_name': address_data['recipient_name'],
                'recipient_phone': address_data['recipient_phone'],
                'address_type': address_data['address_type'],
                'city': address_data['city'],
                'region': address_data['region'],
                'full_address_description': address_data['full_address_description'],
            }
        })
        
    except sqlite3.Error as e:
        conn.rollback()
        print(f"Database error setting default address: {e}")
        return jsonify({'success': False, 'message': f'حدث خطأ في قاعدة البيانات: {e}'}), 500
    except Exception as e:
        conn.rollback()
        print(f"Error setting default address: {e}")
        return jsonify({'success': False, 'message': f'حدث خطأ غير متوقع: {e}'}), 500
    finally:
        conn.close()

@order_bp.route('/add_address_page', methods=['GET', 'POST'])
def add_address_page():
    user_id_cookie = request.cookies.get('user_auth') 
    if not user_id_cookie:
        flash("عذراً، لا يمكن إضافة عنوان بدون تسجيل دخول.", "error")
        return redirect(url_for('user.login'))
    
    user_id = int(user_id_cookie)

    if request.method == 'POST':
        recipient_name = request.form.get('recipient_name')
        recipient_phone = request.form.get('recipient_phone')
        address_type = request.form.get('address_type')
        city = request.form.get('city')
        region = request.form.get('region')
        full_address_description = request.form.get('full_address_description')
        is_default = request.form.get('is_default') == 'on' 

        if not all([recipient_name, recipient_phone, address_type, city, region, full_address_description]):
            flash("الرجاء تعبئة جميع الحقول المطلوبة لإضافة العنوان.", "error")
            return render_template('add_address.html', 
                                    address_type=address_type, 
                                    full_address_description=full_address_description, 
                                    region=region, city=city, 
                                    recipient_name=recipient_name, 
                                    recipient_phone=recipient_phone, 
                                    is_default=is_default)

        conn = get_db_connection()
        try:
            cursor = conn.cursor()

            if is_default:
                cursor.execute("UPDATE cust_addresses SET is_default = 0 WHERE user_id = ?", (user_id,))

            cursor.execute(
                """
                INSERT INTO cust_addresses 
                (user_id, recipient_name, recipient_phone, address_type, city, region, full_address_description, is_default)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (user_id, recipient_name, recipient_phone, address_type, city, region, full_address_description, int(is_default))
            )
            conn.commit()
            flash("تم إضافة العنوان بنجاح!", "success")
            return redirect(url_for('order.manage_addresses')) 
        except sqlite3.Error as e:
            conn.rollback()
            flash(f"حدث خطأ في قاعدة البيانات عند إضافة العنوان: {e}", "danger")
        except Exception as e:
            conn.rollback()
            flash(f"حدث خطأ غير متوقع: {e}", "danger")
        finally:
            conn.close()

    return render_template('add_address.html')



  # أضف هذا المسار الجديد الذي يعرض صفحة إدارة العناوين
@order_bp.route('/manage_addresses')
def manage_addresses():
    user_id_cookie = request.cookies.get('user_auth')
    if not user_id_cookie:
        flash("يجب تسجيل الدخول أولاً.", "error")
        return redirect(url_for('user.login'))
    
    user_id = int(user_id_cookie)
    
    # جلب جميع عناوين المستخدم
    _, all_addresses = get_user_addresses_and_default(user_id)
    
    return render_template('manage_addresses_user.html', addresses=all_addresses)

# --- مسار تعديل العنوان ---
@order_bp.route('/edit_address_page/<int:address_id>', methods=['GET', 'POST'])
def edit_address_page(address_id):
    user_id_cookie = request.cookies.get('user_auth') 
    if not user_id_cookie:
        flash("يجب تسجيل الدخول أولاً.", "error")
        return redirect(url_for('user.login'))
    
    user_id = int(user_id_cookie)
    
    conn = get_db_connection()
    address = conn.execute("SELECT * FROM cust_addresses WHERE id = ? AND user_id = ?", 
                          (address_id, user_id)).fetchone()
    conn.close()
    
    if not address:
        flash("العنوان غير موجود أو لا تملك الصلاحية لتعديله.", "danger")
        return redirect(url_for('order.manage_addresses'))
    
    if request.method == 'POST':
        recipient_name = request.form.get('recipient_name')
        recipient_phone = request.form.get('recipient_phone')
        address_type = request.form.get('address_type')
        city = request.form.get('city')
        region = request.form.get('region')
        full_address_description = request.form.get('full_address_description')
        is_default = request.form.get('is_default') == 'on'

        if not all([recipient_name, recipient_phone, address_type, city, region, full_address_description]):
            flash("الرجاء تعبئة جميع الحقول المطلوبة.", "error")
            return render_template('edit_add_user.html', address=dict(address),
                                   recipient_name=recipient_name,
                                   recipient_phone=recipient_phone,
                                   address_type=address_type,
                                   city=city,
                                   region=region,
                                   full_address_description=full_address_description,
                                   is_default=is_default)

        conn = get_db_connection()
        try:
            if is_default:
                conn.execute("UPDATE cust_addresses SET is_default = 0 WHERE user_id = ?", (user_id,))
            
            conn.execute(
                """
                UPDATE cust_addresses 
                SET recipient_name = ?, recipient_phone = ?, address_type = ?, 
                    city = ?, region = ?, full_address_description = ?, is_default = ?
                WHERE id = ? AND user_id = ?
                """,
                (recipient_name, recipient_phone, address_type, city, region, 
                 full_address_description, int(is_default), address_id, user_id)
            )
            conn.commit()
            flash("تم تحديث العنوان بنجاح!", "success")
            return redirect(url_for('order.manage_addresses'))
        except sqlite3.Error as e:
            conn.rollback()
            flash(f"حدث خطأ في قاعدة البيانات: {e}", "danger")
        except Exception as e:
            conn.rollback()
            flash(f"حدث خطأ غير متوقع: {e}", "danger")
        finally:
            conn.close()
    
    return render_template('edit_add_user.html', address=dict(address))

# --- المسار الخاص بحذف العنوان ---
@order_bp.route('/delete_address/<int:address_id>', methods=['POST'])
def delete_address(address_id):
    user_id_cookie = request.cookies.get('user_auth')
    if not user_id_cookie:
        flash("يجب تسجيل الدخول أولاً.", "error")
        return redirect(url_for('user.login'))
    user_id = int(user_id_cookie)

    conn = get_db_connection()
    try:
        address_row = conn.execute("SELECT * FROM cust_addresses WHERE id = ? AND user_id = ?", (address_id, user_id)).fetchone()
        if not address_row:
            flash('العنوان غير موجود أو لا تملك الصلاحية لحذفه.', 'danger')
            return redirect(url_for('order.manage_addresses'))
        
        conn.execute('DELETE FROM cust_addresses WHERE id = ? AND user_id = ?', (address_id, user_id))
        conn.commit()
        flash('تم حذف العنوان بنجاح.', 'success')
    except Exception as e:
        conn.rollback()
        flash(f"حدث خطأ أثناء الحذف: {e}", "danger")
    finally:
        conn.close()
    
    return redirect(url_for('order.manage_addresses'))


@order_bp.route('/process_order', methods=['POST'])
def process_order():
    user_id_cookie = request.cookies.get('user_auth') 
    if not user_id_cookie:
        flash("يجب تسجيل الدخول أولاً لإتمام الطلب.", "error")
        return redirect(url_for('user.login'))
    
    user_id = int(user_id_cookie)
    user_key = get_current_user_key()

    all_carts_cookie = request.cookies.get('all_user_carts')
    all_user_carts = json.loads(all_carts_cookie) if all_carts_cookie else {}
    cart_items_raw = all_user_carts.get(user_key, [])

    if not cart_items_raw:
        flash("عربة التسوق فارغة، لا يمكن معالجة الطلب.", "warning")
        return redirect(url_for('product.index')) 

    selected_address_id = request.form.get('selected_address_id')
    payment_method = request.form.get('payment_method')
    
    conn = get_db_connection()
    try:
        total_items_price = sum(float(item.get('price', 0.0)) * int(item.get('quantity', 0)) for item in cart_items_raw)
        delivery_cost = 1500.0
        total_order_price = total_items_price + delivery_cost
        
        delivery_address_id = None
        if selected_address_id:
            try:
                delivery_address_id = int(selected_address_id)
                check_address = conn.execute("SELECT id FROM cust_addresses WHERE id = ? AND user_id = ?", (delivery_address_id, user_id)).fetchone()
                if not check_address:
                    delivery_address_id = None
            except ValueError:
                delivery_address_id = None

        if delivery_address_id is None:
            default_address_obj, _ = get_user_addresses_and_default(user_id)
            if default_address_obj and default_address_obj['id'] is not None:
                delivery_address_id = default_address_obj['id']
            else:
                flash("لا يوجد عنوان توصيل محدد لحسابك. يرجى إضافة عنوان.", "danger")
                return redirect(url_for('order.confirm_order_page'))

        if payment_method == 'from_balance':
            current_user_balance = get_user_balance_from_db(user_id)
            if current_user_balance < total_order_price:
                flash("رصيدك غير كافٍ لإتمام الطلب. يرجى شحن رصيدك.", "warning")
                return redirect(url_for('order.confirm_order_page'))
            new_balance = current_user_balance - total_order_price
            conn.execute("UPDATE users SET balance = ? WHERE id = ?", (new_balance, user_id))
            conn.execute("INSERT INTO balance_tracking (user_id, payment_method, amount, transaction_date) VALUES (?, ?, ?, ?)",
                         (user_id, 'رصيد التطبيق', -total_order_price, datetime.now()))
        
        elif payment_method == 'cash_on_delivery':
            pass
            
        else:
            flash("طريقة دفع غير مدعومة حالياً.", "error")
            return redirect(url_for('order.confirm_order_page'))

        # --- هذا هو السطر الذي تم تصحيحه ---
        created_at = datetime.now()
        conn.execute(
            "INSERT INTO orders (user_id, total_price, status, created_at, delivery_address_id, payment_method) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, total_order_price, 'قيد الانتظار', created_at, delivery_address_id, payment_method)
        )
        
        order_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        
        for item in cart_items_raw:
            conn.execute(
                "INSERT INTO Order_Items (order_id, product_id, quantity, price) VALUES (?, ?, ?, ?)",
                (order_id, item.get('product_id'), int(item.get('quantity', 0)), float(item.get('price', 0.0)))
            )
        
        conn.commit()
        
        notification_title = "تم استلام طلبك بنجاح!"
        notification_message = f"طلبك رقم #{order_id} قيد المعالجة. شكراً لثقتك!"
        create_notification(user_id, notification_title, notification_message, 'order', order_id)
        
        if user_key in all_user_carts:
            del all_user_carts[user_key]
        
        response = make_response(redirect(url_for('order.order_success_page', order_id=order_id)))
        expires = datetime.now() + timedelta(days=7)
        response.set_cookie('all_user_carts', json.dumps(all_user_carts), expires=expires, httponly=True, samesite='Lax')
        flash("تم تأكيد طلبك بنجاح! شكراً لطلبك.", "success")
        
        return response

    except sqlite3.Error as e:
        conn.rollback()
        flash(f"حدث خطأ أثناء معالجة طلبك: {e}", "error")
        return redirect(url_for('order.confirm_order_page'))
    finally:
        conn.close()


@order_bp.route('/order_success_page/<int:order_id>')
def order_success_page(order_id):
    conn = get_db_connection()
    order = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    
    items = conn.execute('''
        SELECT oi.quantity, oi.price, p.name, p.image 
        FROM Order_Items oi
        JOIN product p ON oi.product_id = p.id
        WHERE oi.order_id = ?
    ''', (order_id,)).fetchall()

    delivery_address = None
    if order and order['delivery_address_id']:
        delivery_address_row = conn.execute("SELECT * FROM cust_addresses WHERE id = ?", (order['delivery_address_id'],)).fetchone()
        if delivery_address_row:
            delivery_address = dict(delivery_address_row)

    conn.close()

    if not order:
        flash("الطلب غير موجود.", "danger")
        return redirect(url_for('product.index')) 
    
    return render_template('order_success.html', order=order, items=items, delivery_address=delivery_address)

# في ملف order.py
@order_bp.route('/admin/orders')
def admin_orders():
    status_filter = request.args.get('status', 'all')
    conn = get_db_connection()
    orders = []
    try:
        query = '''
            SELECT 
                o.id AS order_id, 
                o.total_price, 
                o.status, 
                o.created_at,
                o.payment_method,
                u.name AS username,  -- جلب اسم المستخدم
                u.num AS phone_number,  -- جلب رقم الهاتف
                ca.recipient_name AS recipient_name,
                ca.full_address_description AS full_address_description
            FROM orders o
            LEFT JOIN users u ON o.user_id = u.id
            LEFT JOIN cust_addresses ca ON o.delivery_address_id = ca.id
        '''
        params = []
        if status_filter != 'all':
            query += " WHERE o.status = ?"
            params.append(status_filter)
        query += " ORDER BY o.created_at DESC"
        orders = conn.execute(query, tuple(params)).fetchall()
    except sqlite3.Error as e:
        print(f"Database error in admin_orders: {e}")
        flash("حدث خطأ في قاعدة البيانات أثناء جلب الطلبات.", "danger")
    finally:
        conn.close()
    return render_template('admin/admin_orders.html', orders=orders, current_status=status_filter)


# في ملف order_routes.py
# ...
# في ملف order_routes.py
# ...

@order_bp.route('/admin/order_details/<int:order_id>')
def admin_order_details(order_id):
    conn = get_db_connection()
    order_details = None
    order_items = []
    total_items_price = 0

    try:
        # جلب تفاصيل الطلب
        order_details = conn.execute('''
            SELECT 
                o.id, 
                o.total_price, 
                o.status, 
                o.created_at,
                o.payment_method,
                u.name AS username,
                u.num AS phone_number,
                ca.recipient_name,
                ca.recipient_phone,
                ca.full_address_description
            FROM orders o
            LEFT JOIN users u ON o.user_id = u.id
            LEFT JOIN cust_addresses ca ON o.delivery_address_id = ca.id
            WHERE o.id = ?
        ''', (order_id,)).fetchone()

        # إذا لم يتم العثور على الطلب، توقف هنا وأعد توجيه المستخدم
        if order_details is None:
            flash(f"لا يوجد طلب بهذا الرقم: #{order_id}", "danger")
            return redirect(url_for('order.admin_orders'))

        # جلب المنتجات في الطلب
        order_items = conn.execute('''
            SELECT 
                oi.quantity, 
                oi.price, 
                p.name AS product_name, 
                pi.image_path AS product_image
            FROM Order_Items oi
            JOIN product p ON oi.product_id = p.id
            LEFT JOIN product_image pi ON p.id = pi.product_id AND pi.is_main = 1
            WHERE oi.order_id = ?
        ''', (order_id,)).fetchall()
        
        # حساب المجموع الفرعي لأسعار المنتجات
        for item in order_items:
            total_items_price += item['price'] * item['quantity']

    except sqlite3.Error as e:
        print(f"Database error in admin_order_details: {e}")
        flash("حدث خطأ في قاعدة البيانات أثناء جلب تفاصيل الطلب.", "danger")
        return redirect(url_for('order.admin_orders'))
    finally:
        conn.close()

    # تمرير المتغيرات إلى القالب
    return render_template('admin/admin_order_details.html', 
                           order=order_details, 
                           items=order_items, 
                           total_items_price=total_items_price)

@order_bp.route('/admin/update_order_status/<int:order_id>', methods=['POST'])
def update_order_status(order_id):
    conn = get_db_connection()
    try:
        data = request.get_json()
        new_status = data.get('status')
        
        if not new_status:
            return jsonify({'success': False, 'message': 'الحالة الجديدة مفقودة'}), 400

        # جلب معلومات الطلب
        order = conn.execute('''
            SELECT user_id, id FROM orders WHERE id = ?
        ''', (order_id,)).fetchone()
        
        if not order:
            return jsonify({'success': False, 'message': 'الطلب غير موجود'}), 404

        # تحديث حالة الطلب
        conn.execute('UPDATE orders SET status = ? WHERE id = ?', (new_status, order_id))
        
        # إنشاء رسالة الإشعار مع ذكر حالة الطلب
        status_messages = {
            'قيد الانتظار': 'تم وضع طلبك في حالة "قيد الانتظار" وسيتم مراجعته قريباً',
            'قيد التجهيز': 'طلبك الآن في مرحلة "قيد التجهيز" وسيتم تحضيره للإرسال',
            'تم الشحن': 'تهانينا! تم شحن طلبك وهو في طريقه إليك',
            'ملغى': 'نأسف لإعلامك أنه تم إلغاء طلبك'
        }
        
        message = status_messages.get(new_status, f'تم تحديث حالة طلبك إلى: {new_status}')
        
        # إضافة رقم الطلب في الرسالة
        full_message = f"{message}\nرقم الطلب: {order_id}"
        
        conn.execute('''
            INSERT INTO notifications (user_id, title, message, notification_type, related_id)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            order['user_id'],
            f'تحديث حالة الطلب #{order_id}',
            full_message,
            'order',
            order_id
        ))
        
        conn.commit()
        return jsonify({
            'success': True,
            'message': f'تم تحديث حالة الطلب إلى {new_status} وإرسال الإشعار'
        })
    
    except Exception as e:
        conn.rollback()
        return jsonify({
            'success': False,
            'message': f'حدث خطأ: {str(e)}'
        }), 500
    finally:
        conn.close()

# اشعارات المستخدم
# اشعارات المستخدم
@order_bp.route('/notifications')
def user_notifications():
    user_id = request.cookies.get('user_auth')
    if not user_id:
        return redirect(url_for('user.login'))
    
    conn = get_db_connection()
    try:
        # تحديث حالة الإشعارات غير المقروءة إلى مقروءة
        conn.execute("UPDATE notifications SET is_read = 1 WHERE user_id = ? AND is_read = 0", (user_id,))
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Error marking notifications as read: {e}")
    finally:
        conn.close()

    # الآن استرجع الإشعارات بعد التحديث
    notifications = get_user_notifications(user_id)
    return render_template('notifications.html', notifications=notifications)

@order_bp.route('/api/notifications/count')
def notifications_count():
    user_id = request.cookies.get('user_auth')
    if not user_id:
        return jsonify({'count': 0})
    count = get_unread_notifications_count(user_id)
    return jsonify({'count': count})



@order_bp.route('/check_notifications')
def check_notifications():
    user_id = request.cookies.get('user_auth')
    if not user_id:
        return "يجب تسجيل الدخول أولاً"
    
    conn = get_db_connection()
    notifications = conn.execute("SELECT * FROM notifications WHERE user_id = ?", (user_id,)).fetchall()
    conn.close()
    
    if not notifications:
        return "لا توجد إشعارات مسجلة لهذا المستخدم"
    
    result = []
    for notif in notifications:
        result.append(dict(notif))
    
    return jsonify(result)

@order_bp.route('/mark_all_read', methods=['POST'])
def mark_all_notifications_read():
    user_id = request.cookies.get('user_auth')
    if not user_id:
        return jsonify({'success': False}), 401

    conn = get_db_connection()
    try:
        conn.execute("UPDATE notifications SET is_read = 1 WHERE user_id = ?", (user_id,))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        print(f"Error marking notifications as read: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()

# Place this route inside your 'order_bp' Blueprint in order.py

@order_bp.route('/admin/sales_data')
def get_sales_data():
    conn = get_db_connection()
    try:
        # Get sales data by date
        sales_data_raw = conn.execute('''
            SELECT 
                STRFTIME('%Y-%m-%d', created_at) AS order_date,
                SUM(total_price) AS total_sales
            FROM orders
            GROUP BY order_date
            ORDER BY order_date
        ''').fetchall()
        
        # Convert fetched data to a list of dictionaries
        sales_data = [dict(row) for row in sales_data_raw]
        
        return jsonify(sales_data)
        
    except Exception as e:
        print(f"Error fetching sales data: {e}")
        return jsonify({'error': 'Failed to fetch sales data'}), 500
    finally:
        conn.close()

# Add this new route to your Flask blueprint
@order_bp.route('/admin/sales_by_category')
def get_sales_by_category():
    conn = get_db_connection()
    try:
        sales_data_raw = conn.execute('''
            SELECT 
                pc.category_name,
                SUM(oi.price * oi.quantity) AS total_sales
            FROM Order_Items oi
            JOIN product p ON oi.product_id = p.id
            JOIN product_categories pc ON p.category_id = pc.id
            GROUP BY pc.category_name
            ORDER BY total_sales DESC
        ''').fetchall()
        
        sales_data = [dict(row) for row in sales_data_raw]
        return jsonify(sales_data)
        
    except Exception as e:
        print(f"Error fetching sales by category: {e}")
        return jsonify({'error': 'Failed to fetch sales data'}), 500
    finally:
        conn.close()

# أضف هذا المسار لعرض قائمة الطلبات للمستخدم
@order_bp.route('/my_orders')
def my_orders():
    user_id_cookie = request.cookies.get('user_auth')
    if not user_id_cookie:
        flash("يجب تسجيل الدخول أولاً لعرض طلباتك.", "error")
        return redirect(url_for('user.login'))

    user_id = int(user_id_cookie)
    conn = get_db_connection()
    orders = []
    try:
        orders = conn.execute(
            "SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC", 
            (user_id,)
        ).fetchall()
        # تحويل الصفوف إلى قاموس لسهولة الوصول في القالب
        orders = [dict(row) for row in orders]
    except Exception as e:
        flash(f"حدث خطأ أثناء جلب طلباتك: {e}", "danger")
    finally:
        conn.close()

    return render_template('my_orders.html', orders=orders)

# ... (rest of your imports)

@order_bp.route('/my_orders/<int:order_id>')
def my_order_details(order_id):
    user_id_cookie = request.cookies.get('user_auth')
    if not user_id_cookie:
        flash("يجب تسجيل الدخول أولاً.", "error")
        return redirect(url_for('user.login'))
    
    user_id = int(user_id_cookie)
    conn = get_db_connection()
    order_details = None
    order_items = []
    
    try:
        # الاستعلام الصحيح: يربط جدول orders مع cust_addresses
        # ... (داخل دالة my_order_details)

        order_details_row = conn.execute(
            """
            SELECT 
                o.*, 
                a.recipient_name, 
                a.recipient_phone, 
                a.full_address_description, 
                a.city, 
                a.region
            FROM orders o
            LEFT JOIN cust_addresses a ON o.delivery_address_id = a.id
            WHERE o.id = ? AND o.user_id = ?
            """, 
            (order_id, user_id)
        ).fetchone()

        if not order_details_row:
            flash("الطلب غير موجود أو لا تملك الصلاحية لعرضه.", "danger")
            return redirect(url_for('order.my_orders'))
        
        order_details = dict(order_details_row)

        # جلب المنتجات المرتبطة بالطلب
        order_items = conn.execute('''
            SELECT 
                oi.quantity, 
                oi.price, 
                oi.product_id,
                p.name AS product_name, 
                pi.image_path AS product_image
            FROM Order_Items oi
            JOIN product p ON oi.product_id = p.id
            LEFT JOIN product_image pi ON p.id = pi.product_id AND pi.is_main = 1
            WHERE oi.order_id = ?
        ''', (order_id,)).fetchall()

    except Exception as e:
        flash(f"حدث خطأ أثناء جلب تفاصيل الطلب: {e}", "danger")
        return redirect(url_for('order.my_orders'))
    finally:
        conn.close()

    return render_template('my_order_details.html', order=order_details, items=order_items)