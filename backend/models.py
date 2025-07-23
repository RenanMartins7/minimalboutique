from dataclasses import dataclass

@dataclass
class Product:
    id: int 
    name: str 
    price: float 
    description: str

@dataclass
class CartItem:
    product_id: int 
    quantity: int 

@dataclass
class Order:
    id: int
    total: float 
    itens: list