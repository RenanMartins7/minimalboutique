# backend/seed.py
from models import db, Product
from database import init_db
from app import app

with app.app_context():
    #init_db(app)  # Garante que as tabelas existem

    # Adiciona produtos

    db.create_all()

    prod1 = Product(name="Tênis Esportivo", price=199.90, description="Tênis para corrida", image_url="https://upload.wikimedia.org/wikipedia/en/7/7b/Addison_Rae_-_Addison.png")
    prod2 = Product(name="Camiseta DryFit", price=89.90, description="Ideal para esportes", image_url="https://upload.wikimedia.org/wikipedia/en/7/7b/Addison_Rae_-_Addison.png")
    prod3 = Product(name="Relógio de Corrida", price=90.92, description="Ideal para esportes", image_url="https://upload.wikimedia.org/wikipedia/en/7/7b/Addison_Rae_-_Addison.png") 
    prod4 = Product(name="Whey Protein 500g", price=25.12, description="Dieta e nutrição", image_url="https://upload.wikimedia.org/wikipedia/en/7/7b/Addison_Rae_-_Addison.png")
    
    db.session.add_all([prod1, prod2, prod3, prod4])
    db.session.commit()
    
    print("Produtos adicionados com sucesso.")
