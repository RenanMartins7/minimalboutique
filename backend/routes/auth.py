from flask import Blueprint, request, jsonify, session
from models import db, User

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.json

    if User.query.filter_by(username=data['email']).first():
        return jsonify({"error": "Usuário já existe"}), 400

    user = User(username=data['email'], password=data['password'])
    db.session.add(user)
    db.session.commit()

    return jsonify({'message': 'Usuário Criado com sucesso'}), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.json
    user = User.query.filter_by(username=data['email'], password = data['password']).first()
    
    if not user:
        return jsonify({'error': 'Credenciais inválidas'}), 401
    
    session['user_id'] = user.id

    return jsonify({'message': 'Login realizado com sucesso'})

@auth_bp.route('/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)
    return jsonify({'message':'Logout realizado com sucesso'})
    