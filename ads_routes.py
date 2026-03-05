<<<<<<< HEAD
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session, make_response
import sqlite3
from datetime import datetime, timedelta
import os
from werkzeug.utils import secure_filename
from employee_routes import login_required_employee, role_required_employee

ads_bp = Blueprint('ads', __name__)

UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'static', 'uploads', 'ads')

# الامتدادات المسموح بها للملفات
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mov', 'avi', 'webp'} # أضف 'webp' أو أي امتدادات أخرى تحتاجها

# تأكد من إنشاء مجلد الرفع إذا لم يكن موجودًا
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def get_db_connection():
    conn = sqlite3.connect('database/Eshop.db')
    conn.row_factory = sqlite3.Row
    return conn


# Endpoint to track impressions
@ads_bp.route('/track_impression/<int:ad_id>', methods=['POST'])
def track_impression(ad_id):
    conn = get_db_connection()
    try:
        conn.execute('UPDATE ads SET impression_count = impression_count + 1 WHERE id = ?', (ad_id,))
        conn.commit()
        return jsonify({'status': 'success', 'message': 'Impression tracked'}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        conn.close()

# Endpoint to track clicks
@ads_bp.route('/track_click/<int:ad_id>', methods=['POST'])
@login_required_employee
@role_required_employee(['super_admin', 'product_and_ads_manager'])
def track_click(ad_id):
    conn = get_db_connection()
    try:
        conn.execute('UPDATE ads SET click_count = click_count + 1 WHERE id = ?', (ad_id,))
        conn.commit()
        return jsonify({'status': 'success', 'message': 'Click tracked'}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        conn.close()


@ads_bp.route('/management')
@login_required_employee
@role_required_employee(['super_admin', 'product_and_ads_manager'])
def ads_management():
    conn = get_db_connection()
    ads = conn.execute('''
        SELECT 
            a.id, a.title, a.description, a.content_type, a.content_path, 
            a.link_url, a.start_date, a.end_date, a.click_count, 
            a.impression_count, a.is_active, s.store_name 
        FROM ads a 
        JOIN sellers s ON a.seller_id = s.id
        ORDER BY a.id DESC
    ''').fetchall()
    sellers = conn.execute('SELECT id, store_name FROM sellers').fetchall()
    conn.close()
    return render_template('admin/admin_ads_management.html', ads=ads, sellers=sellers)

@ads_bp.route('/add', methods=['POST'])
@login_required_employee
@role_required_employee(['super_admin', 'product_and_ads_manager'])
def add_ad():
    seller_id = request.form.get('seller_id')
    title = request.form.get('title')
    content_type = request.form.get('content_type')
    link_url = request.form.get('link_url')
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')
    description = request.form.get('description', '')
    
    content_path = None
    if 'content_file' in request.files:
        file = request.files['content_file']
        if file.filename != '' and '.' in file.filename and \
           file.filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS:
            filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{secure_filename(file.filename)}"
            file.save(os.path.join(UPLOAD_FOLDER, filename))
            content_path = f"/static/uploads/ads/{filename}" 
        else:
            flash('Invalid file type or no file selected.', 'danger')
            return redirect(url_for('ads.ads_management'))
    
    conn = get_db_connection()
    try:
        conn.execute('''
            INSERT INTO ads (
                seller_id, title, description, content_type, 
                content_path, link_url, start_date, end_date,
                click_count, impression_count, is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (seller_id, title, description, content_type, 
              content_path, link_url, start_date, end_date,
              0, 0, 1)) # Initialize click_count, impression_count to 0, is_active to 1
        conn.commit()
        flash('Ad added successfully!', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'An error occurred: {str(e)}', 'danger')
    finally:
        conn.close()
    
    return redirect(url_for('ads.ads_management'))

@ads_bp.route('/toggle/<int:ad_id>')
@login_required_employee
@role_required_employee(['super_admin', 'product_and_ads_manager'])
def toggle_ad(ad_id):
    conn = get_db_connection()
    try:
        ad = conn.execute('SELECT is_active FROM ads WHERE id = ?', (ad_id,)).fetchone()
        if ad:
            new_status = 0 if ad['is_active'] else 1
            conn.execute('UPDATE ads SET is_active = ? WHERE id = ?', (new_status, ad_id))
            conn.commit()
            flash('Ad status updated successfully!', 'success')
        else:
            flash('Ad not found.', 'danger')
    except Exception as e:
        conn.rollback()
        flash(f'An error occurred: {str(e)}', 'danger')
    finally:
        conn.close()
    
    return redirect(url_for('ads.ads_management'))

@ads_bp.route('/delete/<int:ad_id>')
@login_required_employee
@role_required_employee(['super_admin', 'product_and_ads_manager'])
def delete_ad(ad_id):
    conn = get_db_connection()
    try:
        ad = conn.execute('SELECT content_path FROM ads WHERE id = ?', (ad_id,)).fetchone()
        if ad and ad['content_path']:
            filename_from_path = os.path.basename(ad['content_path'])
            file_to_delete = os.path.join(UPLOAD_FOLDER, filename_from_path)
            
            if os.path.exists(file_to_delete):
                os.remove(file_to_delete)
        
        conn.execute('DELETE FROM ads WHERE id = ?', (ad_id,))
        conn.commit()
        flash('Ad deleted successfully!', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'An error occurred: {str(e)}', 'danger')
    finally:
        conn.close()
    
    return redirect(url_for('ads.ads_management'))

@ads_bp.route('/stats')
@login_required_employee
@role_required_employee(['super_admin', 'product_and_ads_manager'])
def ads_stats():
    conn = get_db_connection()
    
    stats = conn.execute('''
        SELECT 
            COUNT(*) as total_ads,
            SUM(click_count) as total_clicks,
            SUM(impression_count) as total_impressions
        FROM ads
    ''').fetchone()
    
    top_ads = conn.execute('''
        SELECT 
            ads.id, ads.title, ads.click_count, ads.impression_count, sellers.store_name 
        FROM ads
        JOIN sellers ON ads.seller_id = sellers.id
        ORDER BY ads.click_count DESC
        LIMIT 5
    ''').fetchall()
    
    conn.close()
    
    return render_template('admin/admin_ads_stats.html',
                           stats=stats,
                           top_ads=top_ads)


# ... (الجزء العلوي من ملف ads_bp.py)


@ads_bp.route('/edit/<int:ad_id>', methods=['GET', 'POST'])
@login_required_employee
@role_required_employee(['super_admin', 'product_and_ads_manager'])
def edit_ad(ad_id):
    conn = get_db_connection()
    ad = conn.execute('SELECT * FROM ads WHERE id = ?', (ad_id,)).fetchone()

    if ad is None:
        flash('Ad not found.', 'danger')
        conn.close()
        return redirect(url_for('ads.ads_management'))

    ad_data = dict(ad) # تحويل Row object إلى قاموس للوصولة المرنة

    # لا تزال هذه الأجزاء مهمة لتنسيق التاريخ للعرض الأولي، كما ناقشنا سابقًا
    try:
        if ad_data['start_date']:
            ad_data['start_date'] = ad_data['start_date']
        if ad_data['end_date']:
            ad_data['end_date'] = ad_data['end_date']
    except Exception as e:
        print(f"Error parsing date from DB for display: {e}")
        ad_data['start_date'] = ''
        ad_data['end_date'] = ''

    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description', '')
        link_url = request.form.get('link_url')
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')
        content_type = request.form.get('content_type')
        # *** الجديد: جلب seller_id من النموذج ***
        seller_id = request.form.get('seller_id')

        new_content_path = ad_data['content_path']
        # ... (بقية كود معالجة الملفات كما هو، لم يتغير هذا الجزء) ...
        if 'content_file' in request.files and request.files['content_file'].filename != '':
            file = request.files['content_file']
            file_extension = file.filename.rsplit('.', 1)[1].lower()

            if file_extension in ALLOWED_EXTENSIONS:
                if ad_data['content_path']:
                    old_filename = os.path.basename(ad_data['content_path'])
                    old_file_full_path = os.path.join(UPLOAD_FOLDER, old_filename)
                    if os.path.exists(old_file_full_path):
                        os.remove(old_file_full_path)

                filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{secure_filename(file.filename)}"
                save_path = os.path.join(UPLOAD_FOLDER, filename)
                file.save(save_path)
                new_content_path = f"/static/uploads/ads/{filename}"
            else:
                flash('نوع ملف غير صالح. لم يتم تحديث الإعلان.', 'danger')
                conn.close()
                return redirect(url_for('ads.ads_management'))

        try:
            conn.execute('''
                UPDATE ads SET
                    title = ?,
                    description = ?,
                    content_type = ?,
                    content_path = ?,
                    link_url = ?,
                    start_date = ?,
                    end_date = ?,
                    seller_id = ?  -- *** الجديد: تحديث حقل seller_id ***
                WHERE id = ?
            ''', (title, description, content_type, new_content_path, link_url,
                  start_date_str, end_date_str, seller_id, ad_id)) # *** الجديد: تمرير seller_id هنا ***
            conn.commit()
            flash('تم تحديث الإعلان بنجاح!', 'success')
            return redirect(url_for('ads.ads_management'))
        except Exception as e:
            conn.rollback()
            flash(f'حدث خطأ أثناء تحديث الإعلان: {str(e)}', 'danger')
        finally:
            conn.close()

    # إذا كان طلب GET، اعرض النموذج (لا تنسَ أنك قمت بإنشاء ad_data بالفعل)
    sellers = conn.execute('SELECT id, store_name FROM sellers').fetchall()
    conn.close()
=======
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session, make_response
import sqlite3
from datetime import datetime, timedelta
import os
from werkzeug.utils import secure_filename
from employee_routes import login_required_employee, role_required_employee

ads_bp = Blueprint('ads', __name__)

UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'static', 'uploads', 'ads')

# الامتدادات المسموح بها للملفات
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mov', 'avi', 'webp'} # أضف 'webp' أو أي امتدادات أخرى تحتاجها

# تأكد من إنشاء مجلد الرفع إذا لم يكن موجودًا
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def get_db_connection():
    conn = sqlite3.connect('database/Eshop.db')
    conn.row_factory = sqlite3.Row
    return conn


# Endpoint to track impressions
@ads_bp.route('/track_impression/<int:ad_id>', methods=['POST'])
def track_impression(ad_id):
    conn = get_db_connection()
    try:
        conn.execute('UPDATE ads SET impression_count = impression_count + 1 WHERE id = ?', (ad_id,))
        conn.commit()
        return jsonify({'status': 'success', 'message': 'Impression tracked'}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        conn.close()

# Endpoint to track clicks
@ads_bp.route('/track_click/<int:ad_id>', methods=['POST'])
@login_required_employee
@role_required_employee(['super_admin', 'product_and_ads_manager'])
def track_click(ad_id):
    conn = get_db_connection()
    try:
        conn.execute('UPDATE ads SET click_count = click_count + 1 WHERE id = ?', (ad_id,))
        conn.commit()
        return jsonify({'status': 'success', 'message': 'Click tracked'}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        conn.close()


@ads_bp.route('/management')
@login_required_employee
@role_required_employee(['super_admin', 'product_and_ads_manager'])
def ads_management():
    conn = get_db_connection()
    ads = conn.execute('''
        SELECT 
            a.id, a.title, a.description, a.content_type, a.content_path, 
            a.link_url, a.start_date, a.end_date, a.click_count, 
            a.impression_count, a.is_active, s.store_name 
        FROM ads a 
        JOIN sellers s ON a.seller_id = s.id
        ORDER BY a.id DESC
    ''').fetchall()
    sellers = conn.execute('SELECT id, store_name FROM sellers').fetchall()
    conn.close()
    return render_template('admin/admin_ads_management.html', ads=ads, sellers=sellers)

@ads_bp.route('/add', methods=['POST'])
@login_required_employee
@role_required_employee(['super_admin', 'product_and_ads_manager'])
def add_ad():
    seller_id = request.form.get('seller_id')
    title = request.form.get('title')
    content_type = request.form.get('content_type')
    link_url = request.form.get('link_url')
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')
    description = request.form.get('description', '')
    
    content_path = None
    if 'content_file' in request.files:
        file = request.files['content_file']
        if file.filename != '' and '.' in file.filename and \
           file.filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS:
            filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{secure_filename(file.filename)}"
            file.save(os.path.join(UPLOAD_FOLDER, filename))
            content_path = f"/static/uploads/ads/{filename}" 
        else:
            flash('Invalid file type or no file selected.', 'danger')
            return redirect(url_for('ads.ads_management'))
    
    conn = get_db_connection()
    try:
        conn.execute('''
            INSERT INTO ads (
                seller_id, title, description, content_type, 
                content_path, link_url, start_date, end_date,
                click_count, impression_count, is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (seller_id, title, description, content_type, 
              content_path, link_url, start_date, end_date,
              0, 0, 1)) # Initialize click_count, impression_count to 0, is_active to 1
        conn.commit()
        flash('Ad added successfully!', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'An error occurred: {str(e)}', 'danger')
    finally:
        conn.close()
    
    return redirect(url_for('ads.ads_management'))

@ads_bp.route('/toggle/<int:ad_id>')
@login_required_employee
@role_required_employee(['super_admin', 'product_and_ads_manager'])
def toggle_ad(ad_id):
    conn = get_db_connection()
    try:
        ad = conn.execute('SELECT is_active FROM ads WHERE id = ?', (ad_id,)).fetchone()
        if ad:
            new_status = 0 if ad['is_active'] else 1
            conn.execute('UPDATE ads SET is_active = ? WHERE id = ?', (new_status, ad_id))
            conn.commit()
            flash('Ad status updated successfully!', 'success')
        else:
            flash('Ad not found.', 'danger')
    except Exception as e:
        conn.rollback()
        flash(f'An error occurred: {str(e)}', 'danger')
    finally:
        conn.close()
    
    return redirect(url_for('ads.ads_management'))

@ads_bp.route('/delete/<int:ad_id>')
@login_required_employee
@role_required_employee(['super_admin', 'product_and_ads_manager'])
def delete_ad(ad_id):
    conn = get_db_connection()
    try:
        ad = conn.execute('SELECT content_path FROM ads WHERE id = ?', (ad_id,)).fetchone()
        if ad and ad['content_path']:
            filename_from_path = os.path.basename(ad['content_path'])
            file_to_delete = os.path.join(UPLOAD_FOLDER, filename_from_path)
            
            if os.path.exists(file_to_delete):
                os.remove(file_to_delete)
        
        conn.execute('DELETE FROM ads WHERE id = ?', (ad_id,))
        conn.commit()
        flash('Ad deleted successfully!', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'An error occurred: {str(e)}', 'danger')
    finally:
        conn.close()
    
    return redirect(url_for('ads.ads_management'))

@ads_bp.route('/stats')
@login_required_employee
@role_required_employee(['super_admin', 'product_and_ads_manager'])
def ads_stats():
    conn = get_db_connection()
    
    stats = conn.execute('''
        SELECT 
            COUNT(*) as total_ads,
            SUM(click_count) as total_clicks,
            SUM(impression_count) as total_impressions
        FROM ads
    ''').fetchone()
    
    top_ads = conn.execute('''
        SELECT 
            ads.id, ads.title, ads.click_count, ads.impression_count, sellers.store_name 
        FROM ads
        JOIN sellers ON ads.seller_id = sellers.id
        ORDER BY ads.click_count DESC
        LIMIT 5
    ''').fetchall()
    
    conn.close()
    
    return render_template('admin/admin_ads_stats.html',
                           stats=stats,
                           top_ads=top_ads)


# ... (الجزء العلوي من ملف ads_bp.py)


@ads_bp.route('/edit/<int:ad_id>', methods=['GET', 'POST'])
@login_required_employee
@role_required_employee(['super_admin', 'product_and_ads_manager'])
def edit_ad(ad_id):
    conn = get_db_connection()
    ad = conn.execute('SELECT * FROM ads WHERE id = ?', (ad_id,)).fetchone()

    if ad is None:
        flash('Ad not found.', 'danger')
        conn.close()
        return redirect(url_for('ads.ads_management'))

    ad_data = dict(ad) # تحويل Row object إلى قاموس للوصولة المرنة

    # لا تزال هذه الأجزاء مهمة لتنسيق التاريخ للعرض الأولي، كما ناقشنا سابقًا
    try:
        if ad_data['start_date']:
            ad_data['start_date'] = ad_data['start_date']
        if ad_data['end_date']:
            ad_data['end_date'] = ad_data['end_date']
    except Exception as e:
        print(f"Error parsing date from DB for display: {e}")
        ad_data['start_date'] = ''
        ad_data['end_date'] = ''

    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description', '')
        link_url = request.form.get('link_url')
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')
        content_type = request.form.get('content_type')
        # *** الجديد: جلب seller_id من النموذج ***
        seller_id = request.form.get('seller_id')

        new_content_path = ad_data['content_path']
        # ... (بقية كود معالجة الملفات كما هو، لم يتغير هذا الجزء) ...
        if 'content_file' in request.files and request.files['content_file'].filename != '':
            file = request.files['content_file']
            file_extension = file.filename.rsplit('.', 1)[1].lower()

            if file_extension in ALLOWED_EXTENSIONS:
                if ad_data['content_path']:
                    old_filename = os.path.basename(ad_data['content_path'])
                    old_file_full_path = os.path.join(UPLOAD_FOLDER, old_filename)
                    if os.path.exists(old_file_full_path):
                        os.remove(old_file_full_path)

                filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{secure_filename(file.filename)}"
                save_path = os.path.join(UPLOAD_FOLDER, filename)
                file.save(save_path)
                new_content_path = f"/static/uploads/ads/{filename}"
            else:
                flash('نوع ملف غير صالح. لم يتم تحديث الإعلان.', 'danger')
                conn.close()
                return redirect(url_for('ads.ads_management'))

        try:
            conn.execute('''
                UPDATE ads SET
                    title = ?,
                    description = ?,
                    content_type = ?,
                    content_path = ?,
                    link_url = ?,
                    start_date = ?,
                    end_date = ?,
                    seller_id = ?  -- *** الجديد: تحديث حقل seller_id ***
                WHERE id = ?
            ''', (title, description, content_type, new_content_path, link_url,
                  start_date_str, end_date_str, seller_id, ad_id)) # *** الجديد: تمرير seller_id هنا ***
            conn.commit()
            flash('تم تحديث الإعلان بنجاح!', 'success')
            return redirect(url_for('ads.ads_management'))
        except Exception as e:
            conn.rollback()
            flash(f'حدث خطأ أثناء تحديث الإعلان: {str(e)}', 'danger')
        finally:
            conn.close()

    # إذا كان طلب GET، اعرض النموذج (لا تنسَ أنك قمت بإنشاء ad_data بالفعل)
    sellers = conn.execute('SELECT id, store_name FROM sellers').fetchall()
    conn.close()
>>>>>>> 4599de10fc9ce5b841b06e1a07fc9d42449f6463
    return render_template('admin/edit_ads.html', ad=ad_data, sellers=sellers)