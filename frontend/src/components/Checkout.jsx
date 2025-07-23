import React from 'react';
import axios from 'axios';

function Checkout(){

    const handleCheckout = () => {
        axios.post('/checkout')
            .then(res => alert(res.data.message))
            .catch(err => console.error(err));
    };

    return (
        <div>
            <h2>Checkout</h2>
            <button onClick={handleCheckout}>Finalizar Compra</button>
        </div>
    );
}

export default Checkout;
