from flask import Blueprint, request, jsonify

cart = []

cart_bp = Blueprint('cart', __name__, url_prefix = '/cart')

@cart_bp.route('/', methods=['GET'])
def get_cart():
    return jsonify(cart)

@cart_bp.route('/', methods=['POST'])
def add_to_cart():
    data = request.json
    cart.append(data)
    return jsonify({"message": "Item added to cart"})

    