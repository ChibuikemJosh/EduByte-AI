import api from "./api";

export const saveProgress = async(data)=>{

    const res = await api.post("/progress",data);

    return res.data;

}

export const getProgress = async(id)=>{

    const res = await api.get(`/progress/${id}`);

    return res.data;

}