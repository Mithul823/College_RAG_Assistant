export default function Sidebar({
  conversations,
  activeConversationId,
  onSelectConversation,
  onNewConversation,
  onDeleteConversation,
  onClearAll,
  isLoading,
}) {
  return (
    <aside className="w-72 bg-slate-900 border-r border-slate-800 flex flex-col h-full shrink-0">
      <div className="p-4 border-b border-slate-800">
        <button
          onClick={onNewConversation}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl glass-btn-primary font-medium text-sm transition cursor-pointer"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          New Conversation
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-1">
        <div className="px-3 py-1.5 flex items-center justify-between text-[11px] font-semibold uppercase tracking-wider text-slate-400">
          <span>History</span>
          {conversations.length > 0 && onClearAll && (
            <button
              onClick={onClearAll}
              className="text-[10px] text-rose-400 hover:text-rose-300 font-medium normal-case transition hover:underline cursor-pointer"
            >
              Clear all
            </button>
          )}
        </div>

        {isLoading && (
          <div className="p-4 text-center text-xs text-slate-400">Loading conversations...</div>
        )}

        {!isLoading && conversations.length === 0 && (
          <div className="p-4 text-center text-xs text-slate-400">
            No previous conversations yet. Ask your first question!
          </div>
        )}

        {conversations.map((conv) => {
          const isActive = conv.id === activeConversationId;
          return (
            <div
              key={conv.id}
              onClick={() => onSelectConversation(conv.id)}
              className={`group flex items-center justify-between px-3 py-2.5 rounded-xl text-xs font-medium cursor-pointer transition ${
                isActive
                  ? 'bg-slate-800/80 text-white border border-slate-700/80 shadow-sm'
                  : 'text-slate-400 hover:bg-slate-800/40 hover:text-slate-200'
              }`}
            >
              <div className="flex items-center gap-2.5 truncate">
                <svg
                  className={`w-3.5 h-3.5 shrink-0 ${isActive ? 'text-cyan-400' : 'text-slate-400'}`}
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"
                  />
                </svg>
                <span className="truncate">{conv.title || 'Untitled Conversation'}</span>
              </div>

              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onDeleteConversation(conv.id);
                }}
                title="Delete conversation"
                className="opacity-70 group-hover:opacity-100 p-1 text-slate-400 hover:text-rose-400 rounded transition cursor-pointer"
              >
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                  />
                </svg>
              </button>
            </div>
          );
        })}
      </div>
    </aside>
  );
}
