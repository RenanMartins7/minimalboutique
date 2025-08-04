import React from 'react';
import {BrowserRouter as Router, Routes, Route, Link} from 'react-router-dom';
import ProductList from './components/ProductList';
import Cart from './components/Cart';
import Checkout from './components/Checkout';
import Login from './components/Login';
import Register from './components/Register';

function App(){
    return(
        <Router>
            <nav>
                <Link to= "/">Produtos</Link> | <Link to= "/cart">Carrinho</Link> | <Link to= "/checkout">Checkout</Link>
            </nav>
            <Routes>
                <Route path = "/products" element={<ProductList/>}/>
                <Route path = "/cart" element={<Cart/>}/>
                <Route path = "/checkout" element = {<Checkout/>}/>
                <Route path = "/login" element = {<Login/>}/>
                <Route path = "/register" element = {<Register/>}/>
                <Route path = "/" element={<Login/>}/>
            </Routes>
        </Router>
    );
}

export default App;