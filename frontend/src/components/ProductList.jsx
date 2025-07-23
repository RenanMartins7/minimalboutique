import React, {useEffect, useState} from 'react';
import axios from 'axios';

function ProductList(){
    const [products, setProducts] = useState([]);

    useEffect(() => {
        axios.get('/products/')
            .then(res => setProducts(res.data))
            .catch(err => console.error(err));

    },[]);

    const addToCart = (product) => {
        axios.post('/cart/', {product_id: product.id, quantity: 1})
            .then(()=> alert('Adicionado ao carrinho!'))
            .catch(err => console.error(err));

    };

    return (
        <div>
            <h2>Produtos</h2>
            <ul>
                {products.map(prod =>(
                    <li key={prod.id}>
                        {prod.name} - R$ {prod.price.toFixed(2)}
                        <button onClick={()=> addToCart(prod)}>Adicionar</button>
                    </li>
                ))}
            </ul>
        </div>

    );
}

export default ProductList;