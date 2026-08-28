import { useState } from 'react';
import { useAuth } from './context/AuthContext';
import Header from './components/Header';
import AdminDashboardView from './views/AdminDashboardView';
import ChatView from './views/ChatView';
import LoginView from './views/LoginView';
import RegisterView from './views/RegisterView';

export default function App() {
  const { user, isAuthenticated, isLoading } = useAuth();
  const [authView, setAuthView] = useState('login'); // 'login' | 'register'
  const [activeView, setActiveView] = useState('chat'); // 'chat' | 'admin'

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center text-slate-100">
        <div className="h-12 w-12 rounded-2xl bg-gradient-to-tr from-cyan-600 to-indigo-600 flex items-center justify-center font-bold text-xl text-white shadow-xl shadow-cyan-950/60 mb-4 animate-pulse">
          🎓
        </div>
        <p className="text-sm font-medium text-slate-400">Loading College RAG Assistant...</p>
      </div>
    );
  }

  if (!isAuthenticated) {
    if (authView === 'register') {
      return <RegisterView onNavigateToLogin={() => setAuthView('login')} />;
    }
    return <LoginView onNavigateToRegister={() => setAuthView('register')} />;
  }

  // If admin is viewing admin portal
  if (activeView === 'admin' && user?.role === 'admin') {
    return (
      <div className="min-h-screen flex flex-col bg-slate-950 text-slate-100">
        <Header currentView="admin" onToggleView={setActiveView} />
        <AdminDashboardView onNavigateToChat={() => setActiveView('chat')} />
      </div>
    );
  }

  // Default student chat view
  return (
    <ChatView
      currentView="chat"
      onToggleView={setActiveView}
    />
  );
}
