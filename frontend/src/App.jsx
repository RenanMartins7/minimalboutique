import React from 'react';
import {BrowserRouter as Router, Routes, Route, Link} from 'react-router-dom';
import ProductList from './components/ProductList';
import Cart from './components/Cart';
import Checkout from './components/Checkout';

function App(){
    return(
        <Router>
            <nav>
                <Link to= "/">Produtos</Link> | <Link to= "/cart">Carrinho</Link> | <Link to= "/checkout">Checkout</Link>
            </nav>
            <Routes>
                <Route path = "/" element={<ProductList/>}/>
                <Route path = "/cart" element={<Cart/>}/>
                <Route path = "/checkout" element = {<Checkout/>}/>
            </Routes>
        </Router>
    );
}

export default App;