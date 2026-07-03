import {useState} from "react";

import {register} from "../services/auth";

import {useNavigate,Link} from "react-router-dom";

export default function Register(){

const navigate=useNavigate();

const [form,setForm]=useState({

username:"",

email:"",

password:""

})

const submit=async(e)=>{

e.preventDefault();

try{

await register(form);

navigate("/dashboard");

}

catch{

alert("Registration Failed");

}

}

return(

<div className="auth-page">

<form className="auth-card"

onSubmit={submit}

>

<h1>Create Account</h1>

<input

placeholder="Username"

onChange={(e)=>setForm({

...form,

username:e.target.value

})}

/>

<input

placeholder="Email"

onChange={(e)=>setForm({

...form,

email:e.target.value

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

Register

</button>

<Link to="/">

Already have account?

</Link>

</form>

</div>

)

}