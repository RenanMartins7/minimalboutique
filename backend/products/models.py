# 1. Importa a Base do seu novo 'database.py' (que está no Canvas)
from database import Base

# 2. Importa os tipos de coluna do SQLAlchemy
from sqlalchemy import Column, Integer, String, Float, Text

# 3. Herda de 'Base' em vez de 'db.Model'
class Product(Base):
    # 4. Adiciona o nome da tabela
    __tablename__ = 'product'

    # 5. Remove 'db.' das definições de coluna
    id = Column(Integer, primary_key=True)
    name = Column(String(80), nullable=False)
    price = Column(Float, nullable=False)
    description = Column(Text, nullable=True)
    image_url = Column(Text, nullable=True)
    stock = Column(Integer, nullable=False, default=0)