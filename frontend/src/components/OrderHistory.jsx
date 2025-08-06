import React, {useState, useEffect} from 'react';
import axios from 'axios';

function OrderHistory(){
    const [orders, setOrders] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(()=>{
        axios.get('/orders')
            .then(res => {
                setOrders(res.data);
                setLoading(false);
            })
            .catch(err => {
                console.error("Erro ao buscar histórico de pedidos:", err);
                setLoading(false);
                alert("Não foi possível buscar o histórico de pedidos");
            });
    }, []);

    if(loading){
        return <div>Carregando histórico de pedidos...</div>
    }

    if(orders.lenght === 0){
        return (
            <div>
                <h2>Meus Pedidos</h2>
                <p>Você ainda não fez nenhum pedido</p>
            </div>
        );
    }
    
    return(
        <div>
            <h2>Meus Pedidos</h2>
            {orders.map(order=> (
                <div key = {order.id} style={{border:'1px solid #ccc', margin: '10px', padding: '10px', borderRadius:'5px'}}>
                    <h4>Pedido #{order.id}</h4>
                    <ul>
                        {order.items.map((item,index)=> (
                            <li key = {index}>
                                {item.product_name} (Quantidade: {item.quantity}) - R$ {(item.price * item.quantity).toFixed(2)}

                            </li>
                        ))}
                    </ul>
                    <p><strong>Total do Pedido: R$ {order.total.toFixed(2)}</strong></p>
                </div>
            ))}
        </div>
    );
}

export default OrderHistory;