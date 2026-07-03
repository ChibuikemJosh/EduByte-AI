import { Routes, Route } from "react-router-dom";

import Login from "./pages/Login";
import Register from "./pages/Register";
import Dashboard from "./pages/Dashboard";
import Chat from "./pages/Chat";
import Course from "./pages/Course";
import Quiz from "./pages/Quiz";
import Profile from "./pages/Profile";
import NotFound from "./pages/NotFound";

function App() {

    return (

        <Routes>

            <Route path="/" element={<Login />} />

            <Route path="/register" element={<Register />} />

            <Route path="/dashboard" element={<Dashboard />} />

            <Route path="/chat/:sessionId" element={<Chat />} />

            <Route path="/course/:courseId" element={<Course />} />

            <Route path="/quiz/:moduleId" element={<Quiz />} />

            <Route path="/profile" element={<Profile />} />

            <Route path="*" element={<NotFound />} />

        </Routes>

    );

}

export default App;