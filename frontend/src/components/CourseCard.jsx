export default function CourseCard({ data }) {

    return (

        <div className="course-card">

            <h2>{data.course_title}</h2>

            <p>{data.subject}</p>

            <br />

            {

                data.modules.map(module => (

                    <div

                        key={module.module_number}

                        className="module-preview"

                    >

                        <h3>

                            Module {module.module_number}

                        </h3>

                        <p>

                            {module.module_title}

                        </p>

                    </div>

                ))

            }

        </div>

    );

}