# 1. Importa a Base do seu novo 'database.py'
from database import Base

# 2. Importa os tipos de coluna do SQLAlchemy
from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship

class OrderItem(Base):
    # 3. Adiciona o nome da tabela
    __tablename__ = 'order_item'

    # 4. Remove 'db.' das definições de coluna
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('order.id'), nullable=False)
    product_id = Column(Integer, nullable=False)
    quantity = Column(Float, nullable=False) # Mantido como Float, conforme original
    price = Column(Float, nullable=False)

    # 5. Configura o relacionamento reverso (back_populates)
    order = relationship('Order', back_populates='items', lazy='selectin')


class Order(Base):
    # 3. Adiciona o nome da tabela
    __tablename__ = 'order'

    # 4. Remove 'db.' das definições de coluna
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    total = Column(Float, nullable=False)
    status = Column(String(20), nullable=False, default='pending')

    # 5. Atualiza o relacionamento para async
    items = relationship(
        'OrderItem', 
        back_populates='order', 
        lazy='selectin',  # 'selectin' é crucial para async
        cascade="all, delete-orphan"
    )