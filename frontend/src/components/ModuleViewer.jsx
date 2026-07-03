import ReactMarkdown from "react-markdown";

export default function ModuleViewer({module}){

return(

<div className="module-card">

<h1>

{module.module_title}

</h1>

{

module.subtopics.map((sub,index)=>

<div

key={index}

>

<h3>

{sub.title}

</h3>

<ReactMarkdown>

{sub.content_markdown}

</ReactMarkdown>

</div>

)

}

</div>

)

}