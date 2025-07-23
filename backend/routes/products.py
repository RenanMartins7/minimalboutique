from flask import Blueprint, jsonify
from database import get_db_connection


products_bp = Blueprint('products', __name__, url_prefix='/products')

@products_bp.route('/', methods=['GET'])
def list_products():
    conn = get_db_connection()
    products = conn.execute('SELECT * FROM products').fetchall()
    conn.close()
    return jsonify([dict(row) for row in products])

