import api from "./api";

export const getCourses = async()=>{

    const res = await api.get("/courses");

    return res.data;

}

export const getCourse = async(id)=>{

    const res = await api.get(`/courses/${id}`);

    return res.data;

}