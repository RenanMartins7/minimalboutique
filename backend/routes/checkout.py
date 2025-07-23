from flask import Blueprint, jsonify

checkout_bp = Blueprint('checkout', __name__, url_prefix='/checkout')

@checkout_bp.route('/', methods=['POST'])
def checkout():
    return jsonify({"message": "Pedido realizado com sucesso"})

