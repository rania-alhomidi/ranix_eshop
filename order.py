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

# *** دالة مساعدة جديدة (منقولة من cart_routes.py) ***
def get_current_user_key():
    """
    يحصل على المفتاح الفريد لسلة التسوق للمستخدم الحالي (المسجل دخوله أو الضيف).
    يعتمد على كوكي 'user_auth' لتحديد المستخدم المسجل دخوله.
    """
    user_id = request.cookies.get('user_auth')
    if user_id:
        return str(user_id) # يجب أن يكون المفتاح string في قاموس JSON
    return 'guest_cart' # المفتاح الافتراضي لجميع المستخدمين غير المسجلين (الضيوف)

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

# --- مسارات (Routes) للطلبات ---
@order_bp.route('/confirm_order_page')
def confirm_order_page():
    user_id_cookie = request.cookies.get('user_auth') 
    if not user_id_cookie:  # التحقق من تسجيل الدخول
        flash("يجب تسجيل الدخول أولاً.", "error")
        return redirect(url_for('user.login'))
    
    user_key = get_current_user_key()  # مفتاح سلة المستخدم الحالي
    
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

        # جلب سعر الربح (profit_price) من جدول prices
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


@order_bp.route('/set_default_address/<int:address_id>')
def set_default_address(address_id):
    user_id_cookie = request.cookies.get('user_auth') 
    if not user_id_cookie:
        return jsonify({'success': False, 'message': 'يجب تسجيل الدخول أولاً.'}), 401 

    user_id = int(user_id_cookie) # تحويل user_id إلى عدد صحيح

    conn = get_db_connection()
    try:
        address_row = conn.execute("SELECT * FROM cust_addresses WHERE id = ? AND user_id = ?", (address_id, user_id)).fetchone()
        if not address_row:
            return jsonify({'success': False, 'message': 'الوصول غير مصرح به لهذا العنوان.'}), 403 

        conn.execute("UPDATE cust_addresses SET is_default = 0 WHERE user_id = ?", (user_id,))
        conn.execute("UPDATE cust_addresses SET is_default = 1 WHERE id = ? AND user_id = ?", (address_id, user_id))
        conn.commit()

        updated_address_details = dict(conn.execute("SELECT * FROM cust_addresses WHERE id = ?", (address_id,)).fetchone())
        
        return jsonify({
            'success': True, 
            'message': 'تم تحديث العنوان الافتراضي بنجاح.',
            'address': updated_address_details
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
            return redirect(url_for('order.confirm_order_page')) 
        except sqlite3.Error as e:
            conn.rollback()
            flash(f"حدث خطأ في قاعدة البيانات عند إضافة العنوان: {e}", "danger")
        except Exception as e:
            conn.rollback()
            flash(f"حدث خطأ غير متوقع: {e}", "danger")
        finally:
            conn.close()

    return render_template('add_address.html')

@order_bp.route('/process_order', methods=['POST'])
def process_order():
    user_id_cookie = request.cookies.get('user_auth') 
    if not user_id_cookie:
        flash("يجب تسجيل الدخول أولاً لإتمام الطلب.", "error")
        return redirect(url_for('user.login'))
    
    user_id = int(user_id_cookie) # تحويل user_id إلى عدد صحيح
    user_key = get_current_user_key() # جلب مفتاح سلة المستخدم الحالي

    # *** التعديل هنا: قراءة الكوكي 'all_user_carts' ***
    all_carts_cookie = request.cookies.get('all_user_carts')
    all_user_carts = json.loads(all_carts_cookie) if all_carts_cookie else {}
    
    # جلب سلة التسوق الخاصة بالمستخدم الحالي
    cart_items_raw = all_user_carts.get(user_key, [])

    if not cart_items_raw:
        flash("عربة التسوق فارغة، لا يمكن معالجة الطلب.", "warning")
        return redirect(url_for('product.index')) 

    selected_address_id = request.form.get('selected_address_id')
    order_notes = request.form.get('order_notes')
    payment_method = request.form.get('payment_method') 

    total_items_price = sum(float(item.get('price', 0.0)) * int(item.get('quantity', 0)) for item in cart_items_raw)
    delivery_cost = 1500.0
    total_order_price = total_items_price + delivery_cost
    
    current_user_balance = get_user_balance_from_db(user_id) 

    if payment_method == 'from_balance':
        if current_user_balance >= total_order_price:
            conn = get_db_connection()
            try:
                new_balance = current_user_balance - total_order_price
                conn.execute("UPDATE users SET balance = ? WHERE id = ?", (new_balance, user_id))
                
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
                        conn.rollback() 
                        return redirect(url_for('order.confirm_order_page'))

                created_at = datetime.now()
                conn.execute(
                    "INSERT INTO orders1 (user_id, total_price, status, created_at, delivery_address_id) VALUES (?, ?, ?, ?, ?)",
                    (user_id, total_order_price, 'pending', created_at, delivery_address_id)
                )
                order_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

                for item in cart_items_raw:
                    conn.execute(
                        "INSERT INTO Order_Items (order_id, product_id, quantity, price) VALUES (?, ?, ?, ?)",
                        (order_id, item.get('product_id'), int(item.get('quantity', 0)), float(item.get('price', 0.0)))
                    )
                
                conn.execute(
                    "INSERT INTO balance_tracking (user_id, payment_method, amount, transaction_date) VALUES (?, ?, ?, ?)",
                    (user_id, 'رصيد التطبيق', -total_order_price, created_at)
                )

                conn.commit()
                flash("تم تأكيد طلبك بنجاح! شكراً لطلبك.", "success")
                
                response = make_response(redirect(url_for('order.order_success_page', order_id=order_id)))
                
                # *** التعديل هنا: إزالة سلة المستخدم الحالية من الكوكي 'all_user_carts' ***
                if user_key in all_user_carts:
                    del all_user_carts[user_key]
                # حفظ الكوكي المحدث بعد إزالة سلة المستخدم
                response.set_cookie('all_user_carts', json.dumps(all_user_carts), expires=datetime.now() + timedelta(days=7), httponly=True, secure=True, samesite='Lax') 
                
                return response

            except sqlite3.Error as e:
                conn.rollback()
                flash(f"حدث خطأ أثناء معالجة طلبك: {e}", "error")
                return redirect(url_for('order.confirm_order_page'))
            finally:
                conn.close()
        else:
            flash("رصيدك غير كافٍ لإتمام الطلب. يرجى شحن رصيدك.", "warning")
            return redirect(url_for('order.confirm_order_page'))
    else:
        flash("طريقة دفع غير مدعومة حالياً.", "error")
        return redirect(url_for('order.confirm_order_page'))

@order_bp.route('/order_success_page/<int:order_id>')
def order_success_page(order_id):
    conn = get_db_connection()
    order = conn.execute("SELECT * FROM orders1 WHERE id = ?", (order_id,)).fetchone()
    
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