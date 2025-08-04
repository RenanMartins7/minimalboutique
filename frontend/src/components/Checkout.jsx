import React from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';

function Checkout(){
    const navigate = useNavigate();

    const handleCheckout = () => {
        axios.post('/checkout/')
            .then(res => {
                alert(`${res.data.message}! Total: R$ ${res.data.total.toFixed(2)}`);
                navigate('/');
            })
            .catch(err => {
                if(err.response && err.response.data && err.response.data.error){
                    alert(err.response.data.error);
                } else {
                    alert('Ocorreu um erro ao finalizar a compra. Por favor, tente novamente.');
                }
                console.error(err)
            });
    };

    return (
        <div>
            <h2>Checkout</h2>
            <button onClick={handleCheckout}>Finalizar Compra</button>
        </div>
    );
}

export default Checkout;