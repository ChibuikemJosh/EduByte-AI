import { useState, useRef, useEffect } from "react";
import { sendMessage } from "../services/chatService";
import MessageRenderer from "./MessageRenderer";
import { generateSession } from "../utils/session";

const session = generateSession();

export default function ChatWindow() {

    const [input, setInput] = useState("");
    const [messages, setMessages] = useState([]);
    const [loading, setLoading] = useState(false);

    const bottomRef = useRef(null);

    useEffect(() => {
        bottomRef.current?.scrollIntoView({
            behavior: "smooth"
        });
    }, [messages]);

    const send = async () => {

        if (!input.trim()) return;

        const text = input;

        setInput("");

        setMessages(prev => [
            ...prev,
            {
                role: "user",
                content: text
            }
        ]);

        try {

            setLoading(true);

            const res = await sendMessage(text, session);

            setMessages(prev => [
                ...prev,
                {
                    role: "assistant",
                    content: res.message,
                    response_type: res.response_type,
                    payload: res.payload
                }
            ]);

        } catch {

            setMessages(prev => [
                ...prev,
                {
                    role: "assistant",
                    content: "Something went wrong."
                }
            ]);

        } finally {

            setLoading(false);

        }

    };

    return (

        <div className="chat-page">

            <div className="messages">

                {

                    messages.map((message, index) => (

                        <MessageRenderer
                            key={index}
                            message={message}
                        />

                    ))

                }

                <div ref={bottomRef}></div>

            </div>

            <div className="chat-input">

                <input

                    value={input}

                    onChange={(e) => setInput(e.target.value)}

                    onKeyDown={(e) => {

                        if (e.key === "Enter") {

                            send();

                        }

                    }}

                    placeholder="Ask EduByte AI..."

                />

                <button

                    disabled={loading}

                    onClick={send}

                >

                    {loading ? "Thinking..." : "Send"}

                </button>

            </div>

        </div>

    );

}