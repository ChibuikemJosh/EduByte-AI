import api from "./api";

export const getModule = async(id)=>{

    const res = await api.get(`/modules/${id}`);

    return res.data;

}