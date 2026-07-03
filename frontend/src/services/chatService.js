import api from "./api";

export const sendMessage = async(message,session_id)=>{

    const res = await api.post("/ai/chat",{

        session_id,

        message

    });

    return res.data;

}