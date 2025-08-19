from flask import Flask
# from routes.cart import cart_bp
#from routes.checkout import checkout_bp
from routes.auth import auth_bp
from routes.gateway import gateway_bp
# from routes.orders import orders_bp
from database import init_db

from flask_cors import CORS





app = Flask(__name__)
app.secret_key = 'secret_key'

CORS(app, supports_credentials=True)

# app.register_blueprint(cart_bp)
#app.register_blueprint(checkout_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(gateway_bp)
# app.register_blueprint(orders_bp)

init_db(app)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

