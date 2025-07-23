import React, {useEffect, useState} from 'react';
import axios from 'axios';

function Cart(){

    const [cart, setCart] = useState([]);

    useEffect(() => {
        axios.get('/cart/')
            .then(res => setCart(res.data))
            .catch(err => console.error(err));

    },  []);

    return(
        <div>
            <h2>Carrinho</h2>
            <ul>
                {cart.map((item, index) => (
                    <li key = {index}>Produto ID: {item.product_id}, Quantidade: {item.quantity}</li>
                ))}
            </ul>
        </div>
    );
}

export default Cart;