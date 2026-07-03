import {useState} from "react";
import {login} from "../services/auth";
import {useNavigate,Link} from "react-router-dom";

export default function Login(){

const navigate=useNavigate();

const [form,setForm]=useState({

login_identifier:"",

password:""

})

const submit=async(e)=>{

e.preventDefault();

try{

await login(form);

navigate("/dashboard");

}

catch{

alert("Login Failed");

}

}

return(

<div className="auth-page">

<form className="auth-card" onSubmit={submit}>

<h1>EduByte AI</h1>

<input

placeholder="Email"

onChange={(e)=>setForm({

...form,

login_identifier:e.target.value

})}

/>

<input

type="password"

placeholder="Password"

onChange={(e)=>setForm({

...form,

password:e.target.value

})}

/>

<button>

Login

</button>

<p>

No account?

<Link to="/register">

Register

</Link>

</p>

</form>

</div>

)

}