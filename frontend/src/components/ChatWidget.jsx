import React, { useRef, useState } from 'react';
import { toast, ToastContainer } from 'react-toastify';
import apiClient from '../apiClient';
import './ChatWidget.css'; // We will create this file next
import 'react-toastify/dist/ReactToastify.css';

const NAMESPACE_REGEX = /^[A-Za-z0-9_-]+$/;
const MAX_NAMESPACE_LENGTH = 64;
const RATE_LIMIT_MS = 800;

const ChatWidget = () => {
    const [isOpen, setIsOpen] = useState(false);
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const [namespace, setNamespace] = useState('');
    const [namespaceError, setNamespaceError] = useState('');
    const [isSending, setIsSending] = useState(false);
    const lastSendRef = useRef(0);

    const toggleChat = () => {
        setIsOpen(!isOpen);
    };

    const validateNamespace = (value) => {
        const trimmedValue = value.trim();

        if (!trimmedValue) {
            return 'Inserisci un namespace.';
        }

        if (trimmedValue.length > MAX_NAMESPACE_LENGTH) {
            return `Il namespace deve essere lungo al massimo ${MAX_NAMESPACE_LENGTH} caratteri.`;
        }

        if (!NAMESPACE_REGEX.test(trimmedValue)) {
            return 'Il namespace può contenere solo lettere, numeri, trattini e underscore.';
        }

        return '';
    };

    const handleNamespaceChange = (value) => {
        setNamespace(value);
        setNamespaceError(validateNamespace(value));
    };

    const handleSendMessage = async () => {
        const namespaceValidation = validateNamespace(namespace);
        const trimmedInput = input.trim();

        if (!trimmedInput) {
            toast.error('Inserisci un messaggio da inviare.');
            return;
        }

        if (namespaceValidation) {
            setNamespaceError(namespaceValidation);
            toast.error(namespaceValidation);
            return;
        }

        const now = Date.now();

        if (isSending) {
            toast.info('Attendi il completamento del messaggio in invio.');
            return;
        }

        if (now - lastSendRef.current < RATE_LIMIT_MS) {
            toast.info('Stai inviando messaggi troppo rapidamente. Riprova tra un istante.');
            return;
        }

        lastSendRef.current = now;

        const userMessage = { sender: 'user', text: trimmedInput };
        setMessages((prev) => [...prev, userMessage]);
        setInput('');
        setIsSending(true);

        try {
            const response = await apiClient.post('/api/chat', {
                question: trimmedInput,
                namespace: namespace.trim(),
            });

            const botMessage = response?.data?.answer?.trim()
                ? response.data.answer
                : 'Mi dispiace, si è verificato un problema nel recupero della risposta.';
            setMessages((prev) => [...prev, { sender: 'bot', text: botMessage }]);
        } catch (error) {
            console.error('Error sending message:', error);
            toast.error('Errore di comunicazione con l\'assistente. Riprova più tardi.');
            setMessages((prev) => [...prev, { sender: 'bot', text: 'Non è stato possibile ottenere una risposta.' }]);
        } finally {
            setIsSending(false);
        }
    };

    if (!isOpen) {
        return (
            <>
                <button className="chat-bubble" onClick={toggleChat}>
                    {/* Simple chat icon, can be replaced with an SVG or image */}
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="white"><path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z"/></svg>
                </button>
                <ToastContainer position="bottom-left" autoClose={3500} newestOnTop closeOnClick pauseOnHover theme="colored" />
            </>
        );
    }

    return (
        <>
            <div className="chat-window">
                <div className="chat-header">
                    <h3>AI Assistant</h3>
                    <button onClick={toggleChat} className="close-btn" aria-label="Chiudi la chat">&times;</button>
                </div>
                <div className="chat-body">
                    {/* This is a temporary control for the Super Admin */}
                    <div className="namespace-selector">
                        <input
                            type="text"
                            placeholder="Enter namespace (e.g., societa_A-struttura_1)"
                            value={namespace}
                            onChange={(e) => handleNamespaceChange(e.target.value)}
                            aria-invalid={Boolean(namespaceError)}
                            aria-describedby={namespaceError ? 'namespace-error' : undefined}
                        />
                        {namespaceError && (
                            <p id="namespace-error" className="namespace-error" role="alert">
                                {namespaceError}
                            </p>
                        )}
                    </div>
                    <div className="messages-container">
                        {messages.map((msg, index) => (
                            <div key={index} className={`message ${msg.sender}`}>
                               {msg.text}
                            </div>
                        ))}
                    </div>
                </div>
                <div className="chat-footer">
                    <input
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
                        placeholder="Ask something..."
                        aria-label="Messaggio da inviare"
                    />
                    <button onClick={handleSendMessage} disabled={isSending}>
                        {isSending ? 'Sending...' : 'Send'}
                    </button>
                </div>
            </div>
            <ToastContainer position="bottom-left" autoClose={3500} newestOnTop closeOnClick pauseOnHover theme="colored" />
        </>
    );
};

export default ChatWidget;
