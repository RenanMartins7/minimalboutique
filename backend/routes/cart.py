from flask import Blueprint, request, jsonify, session
from models import CartItem, Product
from database import db

cart_bp = Blueprint('cart', __name__, url_prefix = '/cart')

@cart_bp.route('/', methods = ['GET'])
def get_cart():

    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Usuário não encontrado'}), 401

    items = CartItem.query.filter_by(user_id=user_id).all()
    result = []
    for item in items:
        result.append({
            "id": item.id,
            "product_id": item.product.id,
            "product_name": item.product.name,
            "quantity": item.quantity,
            "price": item.product.price
        })
    return jsonify(result)


@cart_bp.route('/', methods = ['POST'])
def add_to_cart():

    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Faça login para adicionar itens ao carrinho'})
    
    data = request.json
    product_id = data.get("product_id")
    quantity = data.get("quantity", 1)

    product = Product.query.get(product_id)
    if not product:
        return jsonify({"error": "Produto não encontrado"}), 404
    item = CartItem.query.filter_by(user_id=user_id,product_id=product_id).first()

    if item:
        item.quantity += quantity
    else:
        item = CartItem(user_id=user_id,product_id=product_id, quantity=quantity)
        db.session.add(item)
    
    db.session.commit()
    return jsonify({"message": "Item removido"}), 201

@cart_bp.route('/<int:item_id>', methods=['DELETE'])
def remove_from_cart(item_id):

    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Usuário não autenticado'}), 401

    item = CartItem.query.filter_by(id=item_id, user_id=user_id).first()
    if not item:
        return jsonify({"error": "Item não encontrado"}), 404
    
    db.session.delete(item)
    db.session.commit()
    return jsonify({"message": "Item removido"}), 200



# from flask import Blueprint, request, jsonify
# from models import CartItem, Product


# cart = []

# cart_bp = Blueprint('cart', __name__, url_prefix = '/cart')

# @cart_bp.route('/', methods=['GET'])
# def get_cart():
#     return jsonify(cart)

# @cart_bp.route('/', methods=['POST'])
# def add_to_cart():
#     data = request.json
#     cart.append(data)
#     return jsonify({"message": "Item added to cart"})

    