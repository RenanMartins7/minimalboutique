from flask import Flask 
from routes.payment import payment_bp

app = Flask(__name__)
app.register_blueprint(payment_bp)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5004, debug=True)