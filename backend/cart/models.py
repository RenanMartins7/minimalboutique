# 1. Imports corrigidos: Tipos vêm de 'sqlalchemy'
from sqlalchemy import Column, Integer

# 2. Importar a Base do seu novo 'database.py' assíncrono
from database import Base

class CartItem(Base):
    # 3. Nome da tabela definido
    __tablename__ = 'cart_item'

    # 4. Colunas usam 'Column' e 'Integer' importados
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    product_id = Column(Integer, nullable=False)
    quantity = Column(Integer, default=1)
