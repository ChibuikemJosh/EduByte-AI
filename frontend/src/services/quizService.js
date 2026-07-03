import api from "./api";

export const submitQuiz = async(data)=>{

    const res = await api.post("/quiz/submit",data);

    return res.data;

}