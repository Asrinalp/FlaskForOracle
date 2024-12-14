from flask import Blueprint, render_template, request, redirect, url_for, session, current_app
import cx_Oracle

DATABASE_CONFIG = {
    'user': 'USER1',
    'password': '1234',
    'dsn': 'localhost:1521/XEPDB1'
}


def get_db_connection():
    connection = cx_Oracle.connect(
        DATABASE_CONFIG['user'],
        DATABASE_CONFIG['password'],
        DATABASE_CONFIG['dsn']
    )
    return connection


product_bp = Blueprint('product', __name__)


@product_bp.route('/product', methods=['GET'])
def pi_index():
    if 'email' not in session:
        current_app.logger.warning("Unauthorized access attempt to product information page.")
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    # Verileri birleştirerek çekme sorgusu
    query = '''
        SELECT 
            pi.product_id,
            pi.product_name,
            pc.category_name,
            psc.subcategory_name,
            s.supplier_name,
            pi.product_status,
            pi.list_price,
            pi.min_price

        FROM 
            product_information pi
        LEFT JOIN 
            prod_category pc
        ON 
            pc.category_id = pi.category_id
        LEFT JOIN 
            prod_subcategory psc
        ON 
            psc.subcategory_id = pi.subcategory_id
        LEFT JOIN
            supplier s
        ON
            s.supplier_id = pi.supplier_id
        WHERE pi.product_name IS NOT NULL

    '''
    cursor.execute(query)
    inventory_data = cursor.fetchall()
    
    conn.close()
    current_app.logger.info(f"User {session['email']} accessed product information page.")
    return render_template('pi_index.html', inventory_data=inventory_data)

@product_bp.route('/product/add', methods=['GET', 'POST'])
def add_product():
    if 'email' not in session:
        current_app.logger.warning("Unauthorized access attempt to add product.")
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        # Collect data from the form
        product_name = request.form['product_name']
        category_id = request.form['category_id']
        subcategory_id = request.form['subcategory_id']
        supplier_id = request.form['supplier_id']
        product_status = request.form['product_status']
        list_price = request.form['list_price']
        min_price = request.form['min_price']

        # Fetch the maximum product_id from the product_information table
        cursor.execute('SELECT MAX(product_id) FROM product_information')
        max_product_id = cursor.fetchone()[0]
        
        # Increment the max product_id by 1 for the new product
        new_product_id = max_product_id + 1 if max_product_id is not None else 1

        # Insert product into database with the new product_id
        query = '''
        INSERT INTO product_information (product_id, product_name, category_id, subcategory_id, supplier_id, product_status, list_price, min_price)
        VALUES (:product_id, :product_name, :category_id, :subcategory_id, :supplier_id, :product_status, :list_price, :min_price)
        '''
        cursor.execute(query, {
            'product_id': new_product_id,  # Use the calculated product_id
            'product_name': product_name,
            'category_id': category_id,
            'subcategory_id': subcategory_id,
            'supplier_id': supplier_id,
            'product_status': product_status,
            'list_price': list_price,
            'min_price': min_price
        })
        conn.commit()

        conn.close()
        current_app.logger.info(f"User {session['email']} added a new product with ID {new_product_id}.")
        return redirect(url_for('product.pi_index'))

    # Fetch categories, subcategories, and suppliers for the form
    cursor.execute('SELECT category_id, category_name FROM prod_category')
    categories = cursor.fetchall()
    cursor.execute('SELECT subcategory_id, subcategory_name FROM prod_subcategory')
    subcategories = cursor.fetchall()
    cursor.execute('SELECT supplier_id, supplier_name FROM supplier')
    suppliers = cursor.fetchall()

    conn.close()

    # Render form with categories, subcategories, and suppliers
    return render_template('pi_add.html', categories=categories, subcategories=subcategories, suppliers=suppliers)


@product_bp.route('/product/edit/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    if 'email' not in session:
        current_app.logger.warning(f"Unauthorized access attempt to edit product {product_id}.")
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    # Fetch existing product details
    cursor.execute('SELECT * FROM product_information WHERE product_id = :product_id', {'product_id': product_id})
    product = cursor.fetchone()

    if not product:
        current_app.logger.warning(f"Product with ID {product_id} not found.")
        return redirect(url_for('product.pi_index'))

    if request.method == 'POST':
        # Use .get() to avoid KeyError if a key is missing from the form
        product_name = request.form.get('product_name')
        category_id = request.form.get('category_id')
        subcategory_id = request.form.get('subcategory_id')
        supplier_id = request.form.get('supplier_id')
        product_status = request.form.get('product_status')
        list_price = request.form.get('list_price')
        min_price = request.form.get('min_price')

        if not product_name or not category_id or not subcategory_id or not supplier_id or not product_status or not list_price or not min_price:
            current_app.logger.warning(f"Missing data in form submission for product {product_id}.")
            return redirect(url_for('product.edit_product', product_id=product_id))

        # Update the product information
        update_query = '''
        UPDATE product_information
        SET product_name = :product_name,
            category_id = :category_id,
            subcategory_id = :subcategory_id,
            supplier_id = :supplier_id,
            product_status = :product_status,
            list_price = :list_price,
            min_price = :min_price
        WHERE product_id = :product_id
        '''
        cursor.execute(update_query, {
            'product_name': product_name,
            'category_id': category_id,
            'subcategory_id': subcategory_id,
            'supplier_id': supplier_id,
            'product_status': product_status,
            'list_price': list_price,
            'min_price': min_price,
            'product_id': product_id
        })
        conn.commit()
        conn.close()

        current_app.logger.info(f"User {session['email']} edited product {product_id}.")
        return redirect(url_for('product.pi_index'))

    # Fetch categories, subcategories, and suppliers for the form
    cursor.execute('SELECT category_id, category_name FROM prod_category')
    categories = cursor.fetchall()
    cursor.execute('SELECT subcategory_id, subcategory_name FROM prod_subcategory')
    subcategories = cursor.fetchall()
    cursor.execute('SELECT supplier_id, supplier_name FROM supplier')
    suppliers = cursor.fetchall()

    conn.close()

    # Render form with the product data
    return render_template('pi_edit.html', product=product, categories=categories, subcategories=subcategories, suppliers=suppliers)


@product_bp.route('/product/delete/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    if 'email' not in session:
        current_app.logger.warning(f"Unauthorized access attempt to delete product {product_id}.")
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    # Delete the product
    delete_query = 'DELETE FROM product_information WHERE product_id = :product_id'
    cursor.execute(delete_query, {'product_id': product_id})
    conn.commit()
    conn.close()

    current_app.logger.info(f"User {session['email']} deleted product {product_id}.")
    return redirect(url_for('product.pi_index'))
