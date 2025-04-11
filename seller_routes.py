from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session, make_response
import sqlite3

seller_bp = Blueprint('seller', __name__) # لا بادئة هنا، مسارات البائع في الجذر

def get_db_connection():
    conn = sqlite3.connect('database/Eshop.db')
    conn.row_factory = sqlite3.Row
    return conn


@seller_bp.route('/get_address/<int:seller_id>', methods=['GET'])
def get_address(seller_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT seller_address.id, seller_address.address
        FROM sellers
        JOIN seller_address ON sellers.SAddress_id = seller_address.id
        WHERE sellers.id = ?
    ''', (seller_id,))

    address = cursor.fetchone()
    conn.close()

    if address:
        return jsonify({'address_id': address[0], 'address': address[1]})
    else:
        return jsonify({'address_id': None, 'address': ''})


@seller_bp.route('/seller/<int:seller_id>/products')
def seller_products(seller_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    # جلب معلومات البائع أولاً
    seller = cursor.execute('SELECT id, store_name FROM sellers WHERE id = ?', (seller_id,)).fetchone()

    if not seller:
        abort(404)  # إذا لم يتم العثور على البائع

    products = cursor.execute('''
        SELECT
            p.id, p.name, p.image, p.description,
            pr.original_price, pr.profit_price,
            s.quantity, c.name AS category,
            sllr.name AS seller, sa.address AS address,
            p.featured, p.seller_id
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
    return render_template('seller_product.html', products=products, seller=seller)