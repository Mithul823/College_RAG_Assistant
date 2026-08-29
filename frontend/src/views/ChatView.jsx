import { useEffect, useRef, useState } from 'react';
import ApiClient from '../api/client';
import ChatInput from '../components/ChatInput';
import ChatMessage from '../components/ChatMessage';
import Header from '../components/Header';
import Sidebar from '../components/Sidebar';
import SourceDrawer from '../components/SourceDrawer';
import SourcePreviewModal from '../components/SourcePreviewModal';

export default function ChatView({ onToggleView, currentView = 'chat' }) {
  const [conversations, setConversations] = useState([]);
  const [activeConversationId, setActiveConversationId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [isLoadingConversations, setIsLoadingConversations] = useState(true);
  const [isLoadingMessages, setIsLoadingMessages] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [activeSources, setActiveSources] = useState([]);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [selectedPreviewSource, setSelectedPreviewSource] = useState(null);
  const [errorBanner, setErrorBanner] = useState(null);

  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isSending]);

  // Load conversations on mount
  const fetchConversations = async () => {
    try {
      setIsLoadingConversations(true);
      const res = await ApiClient.getConversations();
      setConversations(res.conversations || []);
    } catch (err) {
      console.error('Failed to load conversations:', err);
    } finally {
      setIsLoadingConversations(false);
    }
  };

  useEffect(() => {
    fetchConversations();
  }, []);

  // Load messages when activeConversationId changes
  useEffect(() => {
    async function loadConversationDetail() {
      if (!activeConversationId) {
        setMessages([]);
        return;
      }

      try {
        setIsLoadingMessages(true);
        const detail = await ApiClient.getConversation(activeConversationId);
        setMessages(detail.messages || []);
      } catch (err) {
        console.error('Failed to load conversation messages:', err);
        setErrorBanner('Failed to load conversation history.');
      } finally {
        setIsLoadingMessages(false);
      }
    }

    loadConversationDetail();
  }, [activeConversationId]);

  const handleNewConversation = () => {
    setActiveConversationId(null);
    setMessages([]);
    setErrorBanner(null);
  };

  const handleSelectConversation = (convId) => {
    setActiveConversationId(convId);
    setErrorBanner(null);
  };

  const handleDeleteConversation = async (convId) => {
    try {
      await ApiClient.deleteConversation(convId);
      setConversations((prev) => prev.filter((c) => c.id !== convId));
      if (activeConversationId === convId) {
        handleNewConversation();
      }
    } catch (err) {
      console.error('Failed to delete conversation:', err);
      setErrorBanner('Failed to delete conversation.');
    }
  };

  const handleSendMessage = async (text) => {
    setErrorBanner(null);

    // Optimistically add user message to feed
    const tempUserMsg = {
      id: `temp-${Date.now()}`,
      role: 'user',
      content: text,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, tempUserMsg]);
    setIsSending(true);

    try {
      const response = await ApiClient.sendChatMessage(text, activeConversationId);
      const returnedConvId = response.conversation_id;
      const returnedMsg = response.message;

      // Update active conversation ID if it was a new conversation
      if (!activeConversationId) {
        setActiveConversationId(returnedConvId);
      }

      // Add assistant response to messages
      setMessages((prev) => [...prev, returnedMsg]);

      // Refresh sidebar conversations
      fetchConversations();
    } catch (err) {
      console.error('Failed to send message:', err);
      setErrorBanner(err.message || 'An error occurred while generating the answer.');
      // Add error response turn
      setMessages((prev) => [
        ...prev,
        {
          id: `error-${Date.now()}`,
          role: 'assistant',
          content: 'An error occurred while contacting the college knowledge assistant. Please try again.',
          answer_mode: 'error',
          sources: [],
          created_at: new Date().toISOString(),
        },
      ]);
    } finally {
      setIsSending(false);
    }
  };

  const handleOpenSources = (sources) => {
    setActiveSources(sources);
    setIsDrawerOpen(true);
  };

  const handleCloseSources = () => {
    setIsDrawerOpen(false);
  };

  return (
    <div className="flex flex-col h-screen bg-slate-950 text-slate-100">
      <Header
        currentView={currentView}
        onToggleView={onToggleView}
        onNewChat={handleNewConversation}
      />

      <div className="flex flex-1 overflow-hidden">
        <Sidebar
          conversations={conversations}
          activeConversationId={activeConversationId}
          onSelectConversation={handleSelectConversation}
          onNewConversation={handleNewConversation}
          onDeleteConversation={handleDeleteConversation}
          isLoading={isLoadingConversations}
        />

        <main className="flex-1 flex flex-col h-full overflow-hidden bg-slate-950">
          {errorBanner && (
            <div className="bg-rose-950/80 border-b border-rose-800 text-rose-300 text-xs px-6 py-2.5 flex items-center justify-between">
              <span className="flex items-center gap-2">
                <span>⚠️</span> {errorBanner}
              </span>
              <button
                onClick={() => setErrorBanner(null)}
                className="text-rose-400 hover:text-white transition"
              >
                ✕
              </button>
            </div>
          )}

          {/* Message Scroll Area */}
          <div className="flex-1 overflow-y-auto px-6 py-6 sm:px-12 max-w-4xl mx-auto w-full">
            {messages.length === 0 && !isLoadingMessages && (
              <div className="h-full flex flex-col items-center justify-center text-center my-auto py-12">
                <div className="h-16 w-16 rounded-3xl bg-gradient-to-tr from-cyan-600 to-indigo-600 flex items-center justify-center text-3xl shadow-xl shadow-cyan-950/60 mb-5">
                  🎓
                </div>
                <h3 className="text-xl font-bold text-slate-100">
                  Welcome to College RAG Assistant
                </h3>
                <p className="mt-2 text-sm text-slate-400 max-w-md">
                  Ask any questions about attendance rules, exam regulations, tuition deadlines, course prerequisites, or institutional guidelines.
                </p>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-8 max-w-lg w-full text-left">
                  {[
                    'What is the minimum attendance requirement for examinations?',
                    'When is the deadline for semester registration and fee payment?',
                    'What are the grading policies and GPA requirements?',
                    'What are the library borrowing rules and loan periods?',
                  ].map((prompt, i) => (
                    <button
                      key={i}
                      onClick={() => handleSendMessage(prompt)}
                      className="p-3.5 rounded-2xl clay-card hover:border-amber-600/60 text-xs text-slate-300 hover:text-slate-100 transition text-left cursor-pointer"
                    >
                      💡 {prompt}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {isLoadingMessages && (
              <div className="p-8 text-center text-sm text-slate-400 animate-pulse">
                Loading conversation messages...
              </div>
            )}

            {messages.map((msg) => (
              <ChatMessage
                key={msg.id}
                message={msg}
                onOpenSources={handleOpenSources}
                onSelectSource={(src) => setSelectedPreviewSource(src)}
              />
            ))}

            {isSending && (
              <div className="flex justify-start mb-6 animate-pulse">
                <div className="bg-slate-900 border border-slate-800 rounded-2xl rounded-tl-xs px-5 py-4 text-xs text-slate-400 flex items-center gap-3">
                  <svg className="animate-spin h-4 w-4 text-cyan-400" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  <span>Searching verified college documents & generating answer...</span>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Input Area */}
          <div className="p-4 sm:p-6 border-t border-slate-800/80 bg-slate-950/80 max-w-4xl mx-auto w-full">
            <ChatInput onSendMessage={handleSendMessage} disabled={isSending} />
          </div>
        </main>
      </div>

      <SourceDrawer
        isOpen={isDrawerOpen}
        sources={activeSources}
        onClose={handleCloseSources}
      />

      <SourcePreviewModal
        isOpen={!!selectedPreviewSource}
        source={selectedPreviewSource}
        onClose={() => setSelectedPreviewSource(null)}
      />
    </div>
  );
}

