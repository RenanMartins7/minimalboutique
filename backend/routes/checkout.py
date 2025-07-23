from flask import Blueprint, jsonify
from models import CartItem, Order


checkout_bp = Blueprint('checkout', __name__, url_prefix = '/checkout')

@checkout_bp.route('/', methods = ['POST'])
def checkout():
    cart_items = CartItem.query.all()
    if not cart_items:
        return jsonify({"error":"Carrinho Vazio"}), 400

    total = sum(item.product.price * item.quantity for item in cart_items)
    
    order = Order(total=total)
    db.session.add(order)

    for item in cart_items:
        db.session.delete(item)
    
    db.session.commit()

    return jsonify({"message": "Compra finalizada", "total": total}), 200


# from flask import Blueprint, jsonify

# checkout_bp = Blueprint('checkout', __name__, url_prefix='/checkout')

# @checkout_bp.route('/', methods=['POST'])
# def checkout():
#     return jsonify({"message": "Pedido realizado com sucesso"})

