import { useEffect, useState } from 'react';
import ApiClient from '../api/client';

export default function ChunkInspectorModal({ documentId, isOpen, onClose }) {
  const [documentDetail, setDocumentDetail] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    if (isOpen && documentId) {
      loadDocumentDetails(documentId);
    }
  }, [isOpen, documentId]);

  const loadDocumentDetails = async (id) => {
    setIsLoading(true);
    setError('');
    try {
      const data = await ApiClient.getDocument(id);
      setDocumentDetail(data);
    } catch (err) {
      setError(err.message || 'Failed to load document chunks');
    } finally {
      setIsLoading(false);
    }
  };

  if (!isOpen) return null;

  const chunks = documentDetail?.chunks || [];
  const filteredChunks = chunks.filter((c) =>
    searchTerm ? (c.text || c.content || '').toLowerCase().includes(searchTerm.toLowerCase()) : true
  );

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-slate-900 border border-slate-800 w-full max-w-4xl rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-950/50">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-indigo-500/10 border border-indigo-500/30 flex items-center justify-center text-indigo-400 text-sm">
              🔍
            </div>
            <div>
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                Chunk & Vector Inspector
                {documentDetail && (
                  <span className="text-xs font-normal text-slate-400">
                    ({chunks.length} chunks indexed)
                  </span>
                )}
              </h2>
              <p className="text-xs text-slate-400">
                {documentDetail ? documentDetail.title : 'Loading document metadata...'}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-200 p-1.5 rounded-lg hover:bg-slate-800 transition"
          >
            ✕
          </button>
        </div>

        {/* Content Body */}
        <div className="p-6 overflow-y-auto flex-1 space-y-4">
          {isLoading ? (
            <div className="py-16 text-center text-slate-400 space-y-2">
              <div className="w-6 h-6 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin mx-auto" />
              <p className="text-xs">Fetching document chunks from database...</p>
            </div>
          ) : error ? (
            <div className="p-4 bg-red-950/40 border border-red-800/60 rounded-xl text-xs text-red-300">
              ⚠️ {error}
            </div>
          ) : (
            <>
              {/* Document Metadata Summary */}
              {documentDetail && (
                <div className="p-4 bg-slate-950/60 border border-slate-800/80 rounded-xl grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                  <div>
                    <span className="text-slate-500 block">Filename</span>
                    <span className="font-semibold text-slate-300 truncate block">
                      {documentDetail.filename}
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-500 block">Department</span>
                    <span className="font-semibold text-slate-300 block">
                      {documentDetail.department || 'N/A'}
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-500 block">Academic Year</span>
                    <span className="font-semibold text-slate-300 block">
                      {documentDetail.academic_year || 'N/A'}
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-500 block">Ingestion Status</span>
                    <span
                      className={`inline-block px-2 py-0.5 mt-0.5 rounded-full font-semibold uppercase text-[10px] ${
                        documentDetail.status === 'completed'
                          ? 'bg-emerald-950 text-emerald-400 border border-emerald-800/60'
                          : documentDetail.status === 'failed'
                          ? 'bg-red-950 text-red-400 border border-red-800/60'
                          : 'bg-amber-950 text-amber-400 border border-amber-800/60'
                      }`}
                    >
                      {documentDetail.status}
                    </span>
                  </div>
                </div>
              )}

              {/* Search Chunks */}
              <div className="flex items-center gap-3">
                <div className="relative flex-1">
                  <span className="absolute left-3.5 top-2.5 text-xs text-slate-500">🔍</span>
                  <input
                    type="text"
                    placeholder="Search chunk text content..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="w-full pl-9 pr-3 py-2 bg-slate-950 border border-slate-700/80 rounded-xl text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500"
                  />
                </div>
                {searchTerm && (
                  <button
                    onClick={() => setSearchTerm('')}
                    className="text-xs text-slate-400 hover:text-slate-200"
                  >
                    Clear
                  </button>
                )}
              </div>

              {/* Chunks List */}
              <div className="space-y-3">
                {filteredChunks.length === 0 ? (
                  <div className="py-10 text-center text-xs text-slate-500 border border-dashed border-slate-800 rounded-xl">
                    {searchTerm
                      ? 'No chunks match your search query.'
                      : 'No text chunks extracted for this document.'}
                  </div>
                ) : (
                  filteredChunks.map((chunk) => (
                    <div
                      key={chunk.id}
                      className="p-4 bg-slate-950/40 border border-slate-800/80 rounded-xl space-y-2 hover:border-slate-700/80 transition"
                    >
                      <div className="flex items-center justify-between text-xs text-slate-400">
                        <div className="flex items-center gap-2">
                          <span className="px-2 py-0.5 rounded bg-cyan-950 text-cyan-400 font-mono font-semibold border border-cyan-800/50">
                            Chunk #{chunk.chunk_index + 1}
                          </span>
                          <span className="text-slate-400">
                            Page {chunk.page_number}
                          </span>
                          {chunk.token_count && (
                            <span className="text-slate-500">
                              • ~{chunk.token_count} tokens
                            </span>
                          )}
                        </div>
                        <span className="text-[10px] font-mono text-slate-500 truncate max-w-[140px]">
                          ID: {chunk.id.substring(0, 8)}...
                        </span>
                      </div>
                      <div className="text-xs text-slate-300 leading-relaxed font-mono bg-slate-900/60 p-3 rounded-lg border border-slate-800/40 whitespace-pre-wrap">
                        {chunk.text || chunk.content}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-slate-800 flex items-center justify-end bg-slate-950/40">
          <button
            onClick={onClose}
            className="px-4 py-2 text-xs font-semibold text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700/80 rounded-lg transition"
          >
            Close Inspector
          </button>
        </div>
      </div>
    </div>
  );
}

