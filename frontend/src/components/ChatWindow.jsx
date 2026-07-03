import {useState} from "react";

import {useRef,useEffect} from "react";

import {sendMessage} from "../services/chat";

import MessageRenderer from "./MessageRenderer";

import {generateSession} from "../utils/session";

const bottomRef=useRef();

const session=generateSession();

export default function ChatWindow(){

const[input,setInput]=useState("");

useEffect(()=>{

bottomRef.current?.scrollIntoView({

behavior:"smooth"

})

},[messages]);

const[messages,setMessages]=useState([]);

const send=async()=>{

if(!input)return;

const userMessage={

role:"user",

content:input

}

setMessages(prev=>[...prev,userMessage]);

const res=await sendMessage(input,session);

const ai={

role:"assistant",

content:res.message,

response_type:res.response_type,

payload:res.payload

}

setMessages(prev=>[...prev,ai]);

setInput("");

}

return(

<div className="chat-page">

<div className="messages">

{

messages.map((message,index)=>

<MessageRenderer

key={index}

message={message}

/>

)

}

</div>

<div className="chat-input">

<input

value={input}

onChange={(e)=>setInput(e.target.value)}

placeholder="Ask EduByte AI..."

/>

<button

onClick={send}

>

Send

</button>

</div>

</div>
<div ref={bottomRef}></div>

)

}