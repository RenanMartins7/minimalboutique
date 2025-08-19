from flask import Flask
from routes.cart import cart_bp
from database import init_db
from flask_cors import CORS

app = Flask(__name__)
app.secret_key = 'secret_key'

CORS(app, supports_credentials=True)

app.register_blueprint(cart_bp)

init_db(app)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5005, debug=True)