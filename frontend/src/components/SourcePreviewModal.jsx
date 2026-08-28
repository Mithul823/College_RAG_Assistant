export default function SourcePreviewModal({ isOpen, onClose, source }) {
  if (!isOpen || !source) return null;

  const relevancePct = Math.round((source.relevance_score || 0) * 100);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-in fade-in duration-150">
      <div className="bg-slate-900 border border-slate-700/80 rounded-2xl w-full max-w-2xl overflow-hidden shadow-2xl flex flex-col max-h-[85vh] animate-in zoom-in-95 duration-200">
        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-950/60">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 font-bold">
              📄
            </div>
            <div>
              <h3 className="font-semibold text-slate-100 text-lg flex items-center gap-2">
                Source Document Excerpt
              </h3>
              <p className="text-xs text-slate-400">
                {source.document_name} &bull; Page {source.page_number}
                {source.section ? ` &bull; ${source.section}` : ''}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition-colors"
          >
            ✕
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto space-y-4">
          {/* Metadata Cards */}
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-3">
              <span className="text-[11px] font-medium text-slate-400 block mb-1">Document</span>
              <span className="text-xs font-semibold text-slate-200 truncate block" title={source.document_name}>
                {source.document_name}
              </span>
            </div>

            <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-3">
              <span className="text-[11px] font-medium text-slate-400 block mb-1">Page / Section</span>
              <span className="text-xs font-semibold text-indigo-300 truncate block">
                Page {source.page_number} {source.section ? `(${source.section})` : ''}
              </span>
            </div>

            <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-3 col-span-2 sm:col-span-1">
              <span className="text-[11px] font-medium text-slate-400 block mb-1">Relevance Score</span>
              <div className="flex items-center gap-2">
                <div className="flex-1 bg-slate-700 h-2 rounded-full overflow-hidden">
                  <div
                    className="bg-emerald-500 h-full rounded-full transition-all duration-500"
                    style={{ width: `${relevancePct}%` }}
                  />
                </div>
                <span className="text-xs font-bold text-emerald-400">{relevancePct}%</span>
              </div>
            </div>
          </div>

          {/* Excerpt Text Box */}
          <div>
            <label className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2 block">
              Verified PDF Excerpt
            </label>
            <div className="bg-slate-950 border border-slate-800 rounded-xl p-4 font-mono text-xs leading-relaxed text-slate-300 whitespace-pre-wrap selection:bg-indigo-500 selection:text-white max-h-72 overflow-y-auto">
              {source.chunk_text || 'No raw snippet available for this citation.'}
            </div>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-3 border-t border-slate-800 bg-slate-950/40 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 rounded-lg transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

