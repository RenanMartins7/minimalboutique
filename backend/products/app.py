from flask import Flask
from routes.products import products_bp
from database import init_db, db
from models import Product
from flask_cors import CORS
from telemetry import configure_telemetry
import json
import os


app = Flask(__name__)
app.secret_key = 'secret_key_products'

CORS(app, supports_credentials=True)

app.register_blueprint(products_bp)

init_db(app)

with app.app_context():
    if db.session.query(Product.id).count() == 0:
        print("Banco de dados de produtos vazio. Tentando popular com dados do JSON...")
        try:
            json_path = os.path.join(app.root_path, 'products.json')
            
            
            with open(json_path, 'r', encoding='utf-8') as f:
                products_to_seed = json.load(f)

            products = [Product(**p_data) for p_data in products_to_seed]
            
            db.session.bulk_save_objects(products)
            db.session.commit()
            print(f"Sucesso! {len(products)} produtos foram carregados no banco de dados.")
            
        except FileNotFoundError:
            print(f"ERRO CRÍTICO: O arquivo 'products.json' não foi encontrado no caminho esperado: {json_path}")
        except Exception as e:
            print(f"ERRO CRÍTICO ao carregar dados de produtos: {e}")
            db.session.rollback()
    else:
        print("Banco de dados de produtos já contém dados.")

configure_telemetry(app, "products")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)