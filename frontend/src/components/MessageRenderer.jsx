import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import CourseCard from "./CourseCard";
import ModuleViewer from "./ModuleViewer";

export default function MessageRenderer({ message }) {

    // User messages
    if (message.role === "user") {
        return (
            <div className="user">
                {message.content}
            </div>
        );
    }

    // AI normal message
    if (!message.response_type) {

        return (
            <div className="assistant">

                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {message.content}
                </ReactMarkdown>

            </div>
        );

    }

    switch(message.response_type){

        case "COURSE_OUTLINE":

            return <CourseCard data={message.payload}/>

        case "MODULE_CONTENT":

            return <ModuleViewer module={message.payload}/>

        default:

            return(

                <div className="assistant">

                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {message.content}
                    </ReactMarkdown>

                </div>

            )

    }
}