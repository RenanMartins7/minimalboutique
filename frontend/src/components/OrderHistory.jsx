import React, {useState, useEffect} from 'react';
import axios from 'axios';

function OrderHistory(){
    const [orders, setOrders] = useState([]);
    const [loading, setLoading] = useState(true);

    const [error, setError] = useState(false);

    useEffect(()=>{
        axios.get('/orders', {withCredentials: true})
            .then(res => {
                setOrders(res.data);
                setLoading(false);
            })
            .catch(err => {

                if(err.response){
                    console.error("Erro ao buscar histórico de pedidos");
                    console.error("Status:", err.response.status);
                    console.error("Dados:", err.response.data);
                    console.error("Headers:", err.response.headers);
                } else if( err.request){
                    console.error("Nenhuma resposta recebida. Request: ", err.request);
                } else {
                    console.error("Erro na configuração da requisição", err.message);
                }
                // console.error("Erro ao buscar histórico de pedidos:", err);
                setLoading(false);
                setError(true);
            });
    }, []);

    if(loading){
        return <div>Carregando histórico de pedidos...</div>
    }

    if(error) return <div>Erro ao carregar o histórico de pedidos</div>

    if(orders.length === 0){
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