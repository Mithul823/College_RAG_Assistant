import { useAuth } from '../context/AuthContext';

export default function Header({ currentView, onToggleView }) {
  const { user, logout } = useAuth();

  return (
    <header className="h-16 border-b border-slate-800 bg-slate-900/80 px-6 backdrop-blur-md flex items-center justify-between z-10">
      <div className="flex items-center gap-3">
        <div className="h-9 w-9 rounded-xl bg-gradient-to-tr from-cyan-600 to-indigo-600 flex items-center justify-center font-bold text-white shadow-lg shadow-cyan-900/30">
          🎓
        </div>
        <div>
          <h1 className="text-base font-bold tracking-tight text-white flex items-center gap-2">
            College RAG Assistant
            <span className="text-[10px] uppercase font-semibold px-2 py-0.5 rounded-full bg-cyan-950 text-cyan-400 border border-cyan-800/60">
              Verified Knowledge
            </span>
          </h1>
          <p className="text-xs text-slate-400">Grounded institutional query engine</p>
        </div>
      </div>

      <div className="flex items-center gap-4">
        {user?.role === 'admin' && (
          <div className="flex items-center bg-slate-950 p-1 rounded-xl border border-slate-800">
            <button
              onClick={() => onToggleView && onToggleView('chat')}
              className={`px-3 py-1 text-xs font-semibold rounded-lg transition flex items-center gap-1.5 ${
                currentView === 'chat'
                  ? 'bg-cyan-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <span>💬</span> Chat
            </button>
            <button
              onClick={() => onToggleView && onToggleView('admin')}
              className={`px-3 py-1 text-xs font-semibold rounded-lg transition flex items-center gap-1.5 ${
                currentView === 'admin'
                  ? 'bg-amber-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <span>⚙️</span> Admin Portal
            </button>
          </div>
        )}

        {user && (
          <div className="flex items-center gap-3">
            <div className="text-right hidden sm:block">
              <p className="text-xs font-semibold text-slate-200">{user.name}</p>
              <p className="text-[10px] text-slate-400 capitalize flex items-center gap-1 justify-end">
                <span
                  className={`inline-block w-1.5 h-1.5 rounded-full ${
                    user.role === 'admin' ? 'bg-amber-400' : 'bg-cyan-400'
                  }`}
                />
                {user.role}
              </p>
            </div>

            <button
              onClick={logout}
              className="px-3 py-1.5 text-xs font-medium text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700/80 border border-slate-700 rounded-lg transition"
            >
              Sign out
            </button>
          </div>
        )}
      </div>
    </header>
  );
}
