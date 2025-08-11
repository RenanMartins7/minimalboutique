from flask import Blueprint, jsonify, request
from models import Product
from database import db


products_bp = Blueprint('products', __name__, url_prefix = '/products')

@products_bp.route('/', methods=['GET'])
def list_products():
    products = Product.query.all()
    return jsonify([{
        "id": p.id,
        "name": p.name,
        "price": p.price,
        "description": p.description,
        "image_url": p.image_url
        } for p in products])

@products_bp.route('/', methods=['POST'])
def add_product():
    data = request.json
    product = Product(
        name=data['name'], 
        price=data['price'],
        description=data.get('description'),
        image_url=data.get('image_url')
        )
    db.session.add(product)
    db.session.commit()
    return jsonify({"id": product.id}), 201

@products_bp.route('/<int:product_id>', methods=['DELETE'])
def delete_product(product_id):
    product = Product.query.get(product_id)
    if product is None:
        return jsonify({'error': 'Producto não encontrado'}), 404
    db.session.delete(product)
    db.session.commit()
    return jsonify({'message':'Producto removido com sucesso'}), 200

@products_bp.route('/<int:product_id>', methods=['GET'])
def get_product(product_id):
    product = Product.query.get(product_id)
    if product is None:
        return jsonify({'error': 'Produto não encontrado'}), 404
    return jsonify({
        "id": product.id,
        "name": product.name,
        "price": product.price,
        "description": product.description,
        "image_url": product.image_url
    })



# from flask import Blueprint, jsonify
# from database import get_db_connection


# products_bp = Blueprint('products', __name__, url_prefix='/products')

# @products_bp.route('/', methods=['GET'])
# def list_products():
#     conn = get_db_connection()
#     products = conn.execute('SELECT * FROM products').fetchall()
#     conn.close()
#     return jsonify([dict(row) for row in products])

