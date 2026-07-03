import {
    BrowserRouter,
    Routes,
    Route
} from "react-router-dom";

import Login from "./pages/Login";
import Register from "./pages/Register";
import Dashboard from "./pages/Dashboard";

export default function Router(){

    return(

        <BrowserRouter>

            <Routes>

                <Route path="/" element={<Login/>}/>

                <Route path="/register" element={<Register/>}/>

                <Route path="/dashboard" element={<Dashboard/>}/>

            </Routes>

        </BrowserRouter>

    )

}