from flask import Blueprint, jsonify, session, request
import requests


gateway_bp = Blueprint('gateway', __name__)

ORDERS_API_URL = "http://orders:5002/orders/"

@gateway_bp.route('/orders/', methods=['GET'])
def get_user_orders():
    user_id = session.get('user_id')

    if not user_id:
        return jsonify({"error":"Usuário não autenticado"}), 401

    try:
        response = requests.get(ORDERS_API_URL, params={'user_id': user_id})
        return response.content, response.status_code, response.headers.items()
    
    except requests.exceptions.RequestException as e:
        return jsonify({"error": "Não foi possível conectar ao serviço de pedidos", "details:":str(e)}), 503