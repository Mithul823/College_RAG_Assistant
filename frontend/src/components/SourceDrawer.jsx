export default function SourceDrawer({ isOpen, sources, onClose }) {
  if (!isOpen || !sources || sources.length === 0) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-black/60 backdrop-blur-xs flex justify-end animate-fade-in">
      <div className="w-full max-w-md bg-slate-900 border-l border-slate-800 h-full p-6 flex flex-col shadow-2xl">
        <div className="flex items-center justify-between pb-4 border-b border-slate-800">
          <div className="flex items-center gap-2">
            <span className="p-1.5 rounded-lg bg-cyan-950 text-cyan-400 border border-cyan-800/60 text-sm">
              📄
            </span>
            <h3 className="font-semibold text-white text-base">Supporting Institutional Sources</h3>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <p className="text-xs text-slate-400 my-4">
          The answers provided by the assistant are strictly grounded in these verified institutional records.
        </p>

        <div className="flex-1 overflow-y-auto space-y-4 pr-1">
          {sources.map((src, index) => {
            const scorePercent = Math.round((src.relevance_score || 0) * 100);
            return (
              <div
                key={index}
                className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 hover:border-cyan-800/50 transition flex flex-col gap-2.5"
              >
                <div className="flex items-start justify-between gap-2">
                  <span className="text-[11px] font-bold uppercase tracking-wider text-cyan-400 px-2 py-0.5 rounded bg-cyan-950/80 border border-cyan-800/60">
                    Source {index + 1}
                  </span>
                  <span className="text-[11px] font-medium text-slate-400 bg-slate-800/80 px-2 py-0.5 rounded">
                    Relevance: {scorePercent}%
                  </span>
                </div>

                <div>
                  <h4 className="text-sm font-semibold text-slate-100 break-words">
                    {src.document_name}
                  </h4>
                  <div className="flex flex-wrap items-center gap-2 mt-2 text-xs text-slate-400">
                    <span className="flex items-center gap-1 bg-slate-900 px-2 py-0.5 rounded border border-slate-800">
                      📖 Page <strong className="text-slate-200">{src.page_number}</strong>
                    </span>
                    {src.section && (
                      <span className="flex items-center gap-1 bg-slate-900 px-2 py-0.5 rounded border border-slate-800">
                        🏷️ Section <strong className="text-slate-200">{src.section}</strong>
                      </span>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        <div className="pt-4 border-t border-slate-800 text-center">
          <button
            onClick={onClose}
            className="w-full py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-sm font-medium text-slate-200 transition"
          >
            Close Source Inspector
          </button>
        </div>
      </div>
    </div>
  );
}

