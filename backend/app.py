from flask import Flask
from routes.products import products_bp
from routes.cart import cart_bp
from routes.checkout import checkout_bp
from database import init_db

app = Flask(__name__)
app.register_blueprint(products_bp)
app.register_blueprint(cart_bp)
app.register_blueprint(checkout_bp)

init_db(app)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

