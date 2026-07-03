import api from "./api";

export const register = async(data)=>{
    const res = await api.post("/auth/register",data);

    localStorage.setItem("token",res.data.access_token);

    return res.data;
}

export const login = async(data)=>{
    const res = await api.post("/auth/login",data);

    localStorage.setItem("token",res.data.access_token);

    return res.data;
}

export const getCurrentUser = async()=>{
    const res = await api.get("/auth/me");

    return res.data;
}