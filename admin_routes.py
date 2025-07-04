from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session, make_response
import sqlite3
import os
import uuid  # أضف هذا السطر مع باقي الاستيرادات
from werkzeug.utils import secure_filename

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}

def get_db_connection():
    conn = sqlite3.connect('database/Eshop.db')
    conn.row_factory = sqlite3.Row
    return conn

@admin_bp.route('/')
def home():
    return render_template('admin/index.html')

@admin_bp.route('/profile')
def profile():
    return render_template('admin/profile.html')

@admin_bp.route('/cate', methods=['GET', 'POST'])
def add_category():
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        name = request.form['name']
        parent_id = request.form.get('parent')
        image = request.files.get('image')
        is_active = 1 if request.form.get('is_active') == '1' else 0

        cursor.execute('SELECT id FROM category WHERE name = ?', (name,))
        if cursor.fetchone():
            flash('هذا القسم موجود بالفعل!', 'danger')
            return redirect(url_for('admin.add_category'))

        parent_id = int(parent_id) if parent_id and parent_id.isdigit() else None

        image_path = None
        if image and image.filename:
            upload_folder = os.path.join(UPLOAD_FOLDER, 'category_img')
            os.makedirs(upload_folder, exist_ok=True)
            filename = secure_filename(image.filename)
            filepath = os.path.join(upload_folder, filename)
            image.save(filepath)
            image_path = f'static/uploads/category_img/{filename}'

        cursor.execute(
            'INSERT INTO category (name, parent_id, image, is_active) VALUES (?, ?, ?, ?)',
            (name, parent_id, image_path, is_active)
        )
        conn.commit()
        conn.close()
        flash('تم إضافة القسم بنجاح!', 'success')
        return redirect(url_for('admin.categories'))

    categories = conn.execute('SELECT id, name FROM category').fetchall()
    conn.close()
    return render_template('admin/cate.html', categories=categories)

@admin_bp.route('/toggle_category/<int:category_id>/<int:status>')
def toggle_category(category_id, status):
    conn = get_db_connection()
    try:
        conn.execute('UPDATE category SET is_active = ? WHERE id = ?', (status, category_id))
        conn.commit()
        flash("تم تغيير حالة القسم", "success")
    except Exception as e:
        flash(f"خطأ في تحديث الحالة: {str(e)}", "danger")
    finally:
        conn.close()
    return redirect(url_for('admin.categories'))

@admin_bp.route('/showcate')
def categories():
    filter_type = request.args.get('filter', 'all')
    try:
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row

        query = """
            SELECT c1.*, c2.name as parent_name,
                   (SELECT COUNT(p.id) FROM product p WHERE p.category_id = c1.id) as product_count
            FROM category c1
            LEFT JOIN category c2 ON c1.parent_id = c2.id
        """

        if filter_type == 'active':
            query += " WHERE c1.is_active = 1"
        elif filter_type == 'inactive':
            query += " WHERE c1.is_active = 0"

        query += " ORDER BY c1.is_active DESC, c1.name"

        categories = conn.execute(query).fetchall()
        return render_template('admin/show_cate.html', categories=categories)

    except Exception as e:
        flash(f"خطأ في جلب البيانات: {str(e)}", "danger")
        return redirect(url_for('admin.categories'))
    finally:
        conn.close()

@admin_bp.route('/edit_category/<int:category_id>', methods=['GET', 'POST'])
def edit_category(category_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM category WHERE id = ?", (category_id,))
    category = cursor.fetchone()

    if not category:
        flash("القسم غير موجود!", "danger")
        return redirect(url_for('admin.categories'))

    if request.method == 'POST':
        name = request.form['name']
        parent_id = request.form.get('parent', None) or None
        image = request.files.get('image')

        image_path = category['image']

        if image and image.filename:
            upload_folder = os.path.join(UPLOAD_FOLDER, 'category_img')
            os.makedirs(upload_folder, exist_ok=True)
            filename = secure_filename(image.filename)
            filepath = os.path.join(upload_folder, filename)
            image.save(filepath)
            image_path = f'static/uploads/category_img/{filename}'

        cursor.execute("""
            UPDATE category
            SET name = ?, parent_id = ?, image = ?
            WHERE id = ?
        """, (name, parent_id, image_path, category_id))

        conn.commit()
        conn.close()
        flash("تم تعديل القسم بنجاح!", "success")
        return redirect(url_for('admin.categories'))

    cursor.execute("SELECT * FROM category WHERE id != ?", (category_id,))
    categories = cursor.fetchall()
    conn.close()
    return render_template('admin/edit_category.html',
                         category=category,
                         categories=categories)
                         
                         
                         
                         
                         
                         
                         


@admin_bp.route('/category_details_admin/<int:category_id>')
def category_details_admin(category_id):
    conn = get_db_connection()
    category = conn.execute('''
        SELECT c1.*, c2.name as parent_name,
               (SELECT COUNT(p.id) FROM product p WHERE p.category_id = c1.id) as product_count
        FROM category c1
        LEFT JOIN category c2 ON c1.parent_id = c2.id
        WHERE c1.id = ?
    ''', (category_id,)).fetchone()
    conn.close()

    if not category:
        flash("القسم غير موجود!", "danger")
        return redirect(url_for('admin.categories'))

    return render_template('admin/category_details_admin.html', category=category)

                         
                         
                         
                         
                         

@admin_bp.route('/add_product', methods=['GET', 'POST'])
def add_product():
    conn = get_db_connection()
    categories = conn.execute('SELECT id, name, parent_id FROM category WHERE parent_id IS NOT NULL').fetchall()
    sellers = conn.execute('SELECT id, name FROM sellers').fetchall()
    conn.close()

    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        original_price = request.form['original_price']
        profit_price = request.form['profit_price']
        quantity = request.form['quantity']
        category_id = request.form['category']
        seller_id = request.form['seller']
        images = request.files.getlist('images')

        upload_folder = os.path.join(UPLOAD_FOLDER, 'products')
        os.makedirs(upload_folder, exist_ok=True)
        main_image_path = 'static/uploads/products/default_product.jpg'

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            # التحقق من عدم تكرار اسم المنتج
            cursor.execute('SELECT id FROM product WHERE name = ?', (name,))
            if cursor.fetchone():
                flash("المنتج موجود بالفعل!", "danger")
                return redirect(url_for('admin.add_product'))

            # إدراج المنتج الأساسي
            cursor.execute('''
                INSERT INTO product (
                    name, description, category_id,
                    seller_id, image,
                    featured, price_id, stock_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                name, description, category_id,
                seller_id, main_image_path,
                0, None, None
            ))
            product_id = cursor.lastrowid

            # إدراج الأسعار
            cursor.execute('''
                INSERT INTO prices (product_id, original_price, profit_price)
                VALUES (?, ?, ?)
            ''', (product_id, original_price, profit_price))
            price_id = cursor.lastrowid

            # إدراج المخزون
            cursor.execute('''
                INSERT INTO stock (product_id, quantity)
                VALUES (?, ?)
            ''', (product_id, quantity))
            stock_id = cursor.lastrowid

            # تحديث المنتج بمعرفات الأسعار والمخزون
            cursor.execute('''
                UPDATE product
                SET price_id = ?, stock_id = ?
                WHERE id = ?
            ''', (price_id, stock_id, product_id))

            # معالجة الصور المرفوعة
            if images and images[0].filename:
                for idx, image in enumerate(images):
                    if image and image.filename:
                        filename = secure_filename(image.filename)
                        unique_filename = f"{uuid.uuid4().hex}_{filename}"
                        filepath = os.path.join(upload_folder, unique_filename)
                        image.save(filepath)
                        image_path = f'static/uploads/products/{unique_filename}'

                        is_main = (idx == 0)
                        cursor.execute('''
                            INSERT INTO product_image (product_id, image_path, is_main)
                            VALUES (?, ?, ?)
                        ''', (product_id, image_path, is_main))

                        if is_main:
                            cursor.execute('''
                                UPDATE product SET image = ? WHERE id = ?
                            ''', (image_path, product_id))
            else:
                # إدراج الصورة الافتراضية إذا لم يتم رفع أي صور
                cursor.execute('''
                    INSERT INTO product_image (product_id, image_path, is_main)
                    VALUES (?, ?, ?)
                ''', (product_id, main_image_path, True))

            conn.commit()
            flash("تمت إضافة المنتج بنجاح!", "success")

        except Exception as e:
            conn.rollback()
            flash(f"حدث خطأ أثناء إضافة المنتج: {str(e)}", "danger")
            print(f"Error: {str(e)}")
            return redirect(url_for('admin.add_product'))

        finally:
            conn.close()

        return redirect(url_for('admin.add_product'))

    return render_template('admin/add_product.html',
                         categories=categories,
                         sellers=sellers)

@admin_bp.route('/product_details_admin/<int:product_id>')
def product_details_admin(product_id):
    conn = get_db_connection()
    product = conn.execute('''
        SELECT
            p.id,
            p.name,
            p.image,
            p.description,
            pr.original_price,
            pr.profit_price,
            COALESCE(s.quantity, 0) AS quantity,
            c.name AS category,
            c.id AS category_id,
            sllr.name AS seller,
            sllr.id AS seller_id,
            sa.address AS address,
            p.featured
        FROM product p
        LEFT JOIN prices pr ON p.price_id = pr.id
        LEFT JOIN stock s ON p.stock_id = s.id
        LEFT JOIN category c ON p.category_id = c.id
        LEFT JOIN sellers sllr ON p.seller_id = sllr.id
        LEFT JOIN seller_address sa ON sllr.SAddress_id = sa.id
        WHERE p.id = ?
    ''', (product_id,)).fetchone()
    conn.close()

    if product is None:
        flash("المنتج غير موجود", "danger")
        return redirect(url_for('admin.show_product'))

    return render_template('admin/product_details_admin.html', product=product)




@admin_bp.route('/show_product', methods=['GET'])
def show_product():
    conn = get_db_connection()
    products = conn.execute('''
        SELECT
            p.id,
            p.name,
            p.image,
            p.description,
            pr.original_price,
            pr.profit_price,
            s.quantity,
            c.name AS category,
            c.id AS category_id,
            sllr.name AS seller,
            sllr.id AS seller_id,
            sa.address AS address,
            p.featured
        FROM product p
        LEFT JOIN prices pr ON p.price_id = pr.id
        LEFT JOIN stock s ON p.stock_id = s.id
        LEFT JOIN category c ON p.category_id = c.id
        LEFT JOIN sellers sllr ON p.seller_id = sllr.id
        LEFT JOIN seller_address sa ON sllr.SAddress_id = sa.id
        ORDER BY p.id DESC
    ''').fetchall()
    conn.close()
    return render_template('admin/show_product.html', products=products)


@admin_bp.route('/toggle_featured/<int:product_id>/<int:status>')
def toggle_featured(product_id, status):
    conn = get_db_connection()
    try:
        conn.execute('UPDATE product SET featured = ? WHERE id = ?', (status, product_id))
        conn.commit()
        flash("تم تحديث حالة العرض بنجاح", "success")
    except Exception as e:
        conn.rollback()
        flash(f"حدث خطأ: {str(e)}", "danger")
    finally:
        conn.close()

    return redirect(url_for('admin.show_product'))

@admin_bp.route('/delete_product/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('SELECT image FROM product WHERE id = ?', (product_id,))
        product = cursor.fetchone()
        if not product:
            flash("المنتج غير موجود!", "danger")
            return redirect(url_for('admin.show_product'))

        image_path = product['image']
        if image_path != 'static/uploads/products/default_seller.jpg':
            image_full_path = os.path.join(os.path.dirname(__file__), image_path)
            if os.path.exists(image_full_path):
                os.remove(image_full_path)

        cursor.execute('DELETE FROM prices WHERE product_id = ?', (product_id,))
        cursor.execute('DELETE FROM stock WHERE product_id = ?', (product_id,))
        cursor.execute('DELETE FROM product WHERE id = ?', (product_id,))
        conn.commit()

        flash("تم حذف المنتج بنجاح!", "success")
    except Exception as e:
        conn.rollback()
        flash(f"حدث خطأ أثناء الحذف: {str(e)}", "danger")
    finally:
        conn.close()

    return redirect(url_for('admin.show_product'))

@admin_bp.route('/edit_product/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    conn = get_db_connection()

    product = conn.execute('''
        SELECT
            p.id,
            p.name,
            p.description,
            p.image,
            p.category_id,
            p.seller_id,
            sa.address AS address,
            pr.original_price,
            pr.profit_price,
            s.quantity
        FROM product p
        LEFT JOIN prices pr ON p.price_id = pr.id
        LEFT JOIN stock s ON p.stock_id = s.id
        LEFT JOIN sellers sllr ON p.seller_id = sllr.id
        LEFT JOIN seller_address sa ON sllr.SAddress_id = sa.id
    WHERE p.id = ?
    ''', (product_id,)).fetchone()

    categories = conn.execute('SELECT id, name FROM category WHERE parent_id IS NOT NULL').fetchall() # Only subcategories
    sellers = conn.execute('SELECT id, name FROM sellers').fetchall()
    conn.close()

    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        original_price = request.form['original_price']
        profit_price = request.form['profit_price']
        quantity = request.form['quantity']
        category_id = request.form['category']
        seller_id = request.form['seller']
        address = request.form['address'] # Assuming address is now passed from form
        image = request.files.get('image')

        image_path = product['image']
        if image and image.filename:
            filename = secure_filename(image.filename)
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            image.save(filepath)
            image_path = f'static/uploads/{filename}'

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE product
            SET name = ?, description = ?, category_id = ?,
                seller_id = ?, address_id = ?, image = ?
            WHERE id = ?
        ''', (name, description, category_id, seller_id, address, image_path, product_id)) # address passed directly

        cursor.execute('''
            UPDATE prices
            SET original_price = ?, profit_price = ?
            WHERE product_id = ?
        ''', (original_price, profit_price, product_id))

        cursor.execute('''
            UPDATE stock
            SET quantity = ?
            WHERE product_id = ?
        ''', (quantity, product_id))

        conn.commit()
        conn.close()
        flash("تم تحديث المنتج بنجاح!", "success")
        return redirect(url_for('admin.show_product'))

    return render_template('admin/edit_product.html', product=product, categories=categories, sellers=sellers)


@admin_bp.route('/add_address', methods=['GET', 'POST'])
def add_address():
    if request.method == 'POST':
        street = request.form['street']

        conn = get_db_connection()
        conn.execute('INSERT INTO addresses (street) VALUES (?)', (street,))
        conn.commit()
        conn.close()

        return redirect(url_for('admin.add_address'))

    return render_template('admin/add_address.html')


@admin_bp.route('/seller', methods=['GET', 'POST'])
def add_seller():
    if request.method == 'GET':
        return render_template('admin/seller.html')

    if request.method == 'POST':
        try:
            name = request.form.get('name')
            store_name = request.form.get('store_name')
            commercial_record = request.form.get('commercial_record')
            latitude = request.form.get('latitude')
            longitude = request.form.get('longitude')
            street_address = request.form.get('addressDisplay')
            number1 = request.form.get('number1')
            number2 = request.form.get('number2')

            store_image = request.files.get('store_image')
            id_image = request.files.get('id_image')
            documents = request.files.get('documents')

            upload_base_folder = UPLOAD_FOLDER
            store_image_folder = os.path.join(upload_base_folder, "store_images")
            id_image_folder = os.path.join(upload_base_folder, "id_images")
            documents_folder = os.path.join(upload_base_folder, "documents")

            os.makedirs(store_image_folder, exist_ok=True)
            os.makedirs(id_image_folder, exist_ok=True)
            os.makedirs(documents_folder, exist_ok=True)

            store_image_path = id_image_path = documents_path = ""

            if store_image and allowed_file(store_image.filename):
                store_image_filename = secure_filename(store_image.filename)
                store_image_path = os.path.join(store_image_folder, store_image_filename)
                store_image.save(store_image_path)

            if id_image and allowed_file(id_image.filename):
                id_image_filename = secure_filename(id_image.filename)
                id_image_path = os.path.join(id_image_folder, id_image_filename)
                id_image.save(id_image_path)

            if documents and allowed_file(documents.filename):
                documents_filename = secure_filename(documents.filename)
                documents_path = os.path.join(documents_folder, documents_filename)
                documents.save(documents_path)

            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute(
                "INSERT INTO seller_address (latitude, longitude, address) VALUES (?, ?, ?)",
                (latitude, longitude, street_address)
            )
            address_id = cursor.lastrowid

            cursor.execute(
                "INSERT INTO numbers (number1, number2) VALUES (?, ?)",
                (number1, number2)
            )
            num_id = cursor.lastrowid

            cursor.execute('''
                INSERT INTO sellers
                (name, store_name, store_image, commercial_record, id_image, documents, SAddress_id, num_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                name, store_name, store_image_path, commercial_record, id_image_path, documents_path, address_id, num_id
            ))

            conn.commit()
            conn.close()

            flash("تمت إضافة البائع بنجاح!", "success")
            return redirect(url_for('admin.add_seller'))

        except Exception as e:
            flash(f"حدث خطأ: {str(e)}", "danger")
            return redirect(url_for('admin.add_seller'))


@admin_bp.route('/show_seller', methods=['POST', 'GET'])
def show_seller():
    conn = sqlite3.connect("database/Eshop.db")
    cursor = conn.cursor()

    sellers = cursor.execute("""
        SELECT
            s.id, s.name, s.store_name, s.store_image,
            s.commercial_record, s.id_image, s.documents,
            s.created_at,
            sa.address, sa.latitude, sa.longitude,
            n.number1, n.number2,
            (SELECT COUNT(p.id) FROM product p WHERE p.seller_id = s.id) as product_count
        FROM sellers s
        JOIN seller_address sa ON s.SAddress_id = sa.id
        JOIN numbers n ON s.num_id = n.id
        ORDER BY s.created_at DESC """).fetchall()

    conn.close()
    return render_template('admin/show_seller.html', sellers=sellers)


@admin_bp.route('/edit_seller/<int:seller_id>', methods=['GET', 'POST'])
def edit_seller(seller_id):
    try:
        conn = sqlite3.connect("database/Eshop.db")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('''
            SELECT s.*, sa.latitude, sa.longitude, sa.address as full_address,
                   n.number1, n.number2
            FROM sellers s
            LEFT JOIN seller_address sa ON s.SAddress_id = sa.id
            LEFT JOIN numbers n ON s.num_id = n.id
            WHERE s.id = ?
        ''', (seller_id,))
        seller = cursor.fetchone()

        if not seller:
            flash("صاحب المتجر غير موجود!", "danger")
            return redirect(url_for('admin.show_seller'))

        if request.method == 'POST':
            name = request.form['name']
            store_name = request.form['store_name']
            commercial_record = request.form['commercial_record']

            latitude = request.form.get('latitude')
            longitude = request.form.get('longitude')
            street_address = request.form.get('addressDisplay')

            number1 = request.form.get('number1')
            number2 = request.form.get('number2')

            store_image = seller['store_image']
            id_image = seller['id_image']
            documents = seller['documents']

            if 'store_image' in request.files:
                file = request.files['store_image']
                if file.filename != '':
                    filename = secure_filename(file.filename)
                    path = os.path.join(UPLOAD_FOLDER, 'store_images', filename)
                    os.makedirs(os.path.dirname(path), exist_ok=True)
                    file.save(path)
                    store_image = path

            if 'id_image' in request.files:
                file = request.files['id_image']
                if file.filename != '':
                    filename = secure_filename(file.filename)
                    path = os.path.join(UPLOAD_FOLDER, 'id_images', filename)
                    os.makedirs(os.path.dirname(path), exist_ok=True)
                    file.save(path)
                    id_image = path

            if 'documents' in request.files:
                file = request.files['documents']
                if file.filename != '':
                    filename = secure_filename(file.filename)
                    path = os.path.join(UPLOAD_FOLDER, 'documents', filename)
                    os.makedirs(os.path.dirname(path), exist_ok=True)
                    file.save(path)
                    documents = path

            cursor.execute("""
                UPDATE sellers SET
                    name = ?,
                    store_name = ?,
                    commercial_record = ?,
                    store_image = ?,
                    id_image = ?,
                    documents = ?
                WHERE id = ?
            """, (name, store_name, commercial_record, store_image, id_image, documents, seller_id))

            cursor.execute("""
                UPDATE seller_address SET
                    latitude = ?,
                    longitude = ?,
                    address = ?
                WHERE id = ?
            """, (latitude, longitude, street_address, seller['SAddress_id']))

            cursor.execute("""
                UPDATE numbers SET
                    number1 = ?,
                    number2 = ?
                WHERE id = ?
            """, (number1, number2, seller['num_id']))

            conn.commit()
            flash("تم تعديل بيانات البائع بنجاح!", "success")
            return redirect(url_for('admin.show_seller'))


        seller_dict = dict(seller)
        seller_dict['has_location'] = bool(seller['latitude'] and seller['longitude'])

        return render_template('admin/edit_seller.html', seller=seller_dict)

    except Exception as e:
        flash(f"حدث خطأ: {str(e)}", "danger")
        return redirect(url_for('admin.show_seller'))
    finally:
        conn.close()

@admin_bp.route('/delete_category/<int:category_id>')
def delete_category(category_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM category WHERE id = ?", (category_id,))
    category = cursor.fetchone()

    if not category:
        flash("القسم غير موجود!", "danger")
        return redirect(url_for('admin.categories'))

    cursor.execute("DELETE FROM category WHERE id = ?", (category_id,))
    conn.commit()
    conn.close()

    flash("تم حذف القسم بنجاح!", "danger")
    return redirect(url_for('admin.categories'))

@admin_bp.route('/delete_seller/<int:seller_id>')
def delete_seller(seller_id):
    conn = sqlite3.connect("database/Eshop.db")
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM sellers WHERE id = ?", (seller_id,))
    seller = cursor.fetchone()

    if not seller:
        flash("صاحب المتجر غير موجود!", "danger")
        return redirect(url_for('admin.show_seller'))

    cursor.execute("DELETE FROM sellers WHERE id = ?", (seller_id,))
    conn.commit()
    conn.close()

    flash("تم حذف صاحب المتجر بنجاح!", "success")
    return redirect(url_for('admin.show_seller'))


@admin_bp.route('/users')
def users():
    try:
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                u.id, u.name, u.num, u.email, u.ud_ia,
                a.address, a.latitude, a.longitude
            FROM user u
            LEFT JOIN user_addresses a ON u.ud_ia = a.id
        """)

        users_data = cursor.fetchall()
        conn.close()

        users = []
        for user in users_data:
            users.append({
                'id': user['id'],
                'name': user['name'] or 'غير محدد',
                'num': user['num'] or 'غير محدد',
                'email': user['email'] or 'غير محدد',
                'address': user['address'] or 'لم يتم إضافة عنوان',
                'latitude': user['latitude'],
                'longitude': user['longitude']
            })

        return render_template('admin/show_users.html', users=users)

    except Exception as e:
        print(f"خطأ مفاجئ: {str(e)}")
        return render_template('admin/show_users.html', error="حدث خطأ أثناء جلب المستخدمين")


@admin_bp.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM user WHERE id = ?", (user_id,))
        conn.commit()
        conn.close()

        return redirect(url_for('admin.users', message="تم حذف المستخدم بنجاح."))

    except Exception as e:
        print(f"خطأ أثناء الحذف: {e}")
        return redirect(url_for('admin.users', error="حدث خطأ أثناء حذف المستخدم."))


@admin_bp.route('/seller_products_admin/<int:seller_id>')
def seller_products_admin(seller_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    seller = cursor.execute('SELECT id, store_name FROM sellers WHERE id = ?', (seller_id,)).fetchone()
    if not seller:
        flash("البائع غير موجود!", "danger")
        return redirect(url_for('admin.show_seller'))

    products = cursor.execute('''
        SELECT
            p.id, p.name, p.image, p.description,
            pr.original_price, pr.profit_price,
            s.quantity, c.name AS category,
            c.id AS category_id,
            sllr.name AS seller,
            sllr.id AS seller_id,
            sa.address AS address,
            p.featured
        FROM product p
        LEFT JOIN prices pr ON p.price_id = pr.id
        LEFT JOIN stock s ON p.stock_id = s.id
        LEFT JOIN category c ON p.category_id = c.id
        LEFT JOIN sellers sllr ON p.seller_id = sllr.id
        LEFT JOIN seller_address sa ON sllr.SAddress_id = sa.id
        WHERE p.seller_id = ?
        ORDER BY p.id DESC
    ''', (seller_id,)).fetchall()

    conn.close()
    return render_template('admin/seller_products_admin.html', products=products, seller=seller)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
