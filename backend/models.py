from database import db


class Product(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    name = db.Column(db.String(80), nullable = False)
    price = db.Column(db.Float, nullable = False)
    description = db.Column(db.Text, nullable = True)
    image_url = db.Column(db.Text, nullable = True)


class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    product = db.relationship('Product')

class Order(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    total = db.Column(db.Float, nullable = False)



# from dataclasses import dataclass

# @dataclass
# class Product:
#     id: int 
#     name: str 
#     price: float 
#     description: str

# @dataclass
# class CartItem:
#     product_id: int 
#     quantity: int 

# @dataclass
# class Order:
#     id: int
#     total: float 
#     itens: list