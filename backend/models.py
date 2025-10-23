# 1. Imports corrigidos: Tipos vêm de 'sqlalchemy'
from sqlalchemy import Column, Integer, String, Float, Text, ForeignKey

# 'relationship' vem de 'sqlalchemy.orm'
from sqlalchemy.orm import relationship

# Sua Base declarativa
from database import Base


class Product(Base):
    # 2. Nome da tabela definido
    __tablename__ = 'product'

    # 1. Colunas corrigidas (sem "Base.")
    id = Column(Integer, primary_key=True)
    name = Column(String(80), nullable=False)
    price = Column(Float, nullable=False)
    description = Column(Text, nullable=True)
    image_url = Column(Text, nullable=True)


class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    username = Column(String(80), unique=True, nullable=False)
    password = Column(String(120), nullable=False)

    # 3. Relacionamento bidirecional corrigido para async
    orders = relationship('Order', back_populates='user', lazy='selectin')


class OrderItem(Base):
    __tablename__ = 'order_item' # Nome de tabela presumido

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('order.id'), nullable=False)
    product_id = Column(Integer, ForeignKey('product.id'), nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)

    # 3. Relacionamentos corrigidos para async
    product = relationship('Product', lazy='selectin')
    order = relationship('Order', back_populates='items', lazy='selectin')


class Order(Base):
    __tablename__ = 'order'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    total = Column(Float, nullable=False)

    # 3. Relacionamentos bidirecionais corrigidos para async
    user = relationship('User', back_populates='orders', lazy='selectin')
    items = relationship('OrderItem', back_populates='order', lazy='selectin')



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