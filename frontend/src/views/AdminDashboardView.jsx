import { useEffect, useState } from 'react';
import ApiClient from '../api/client';
import DocumentUploadModal from '../components/DocumentUploadModal';
import ChunkInspectorModal from '../components/ChunkInspectorModal';

export default function AdminDashboardView({ onNavigateToChat }) {
  const [documents, setDocuments] = useState([]);
  const [metrics, setMetrics] = useState(null);
  const [feedbackStats, setFeedbackStats] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [searchQuery, setSearchQuery] = useState('');

  // Modals
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [selectedDocIdForInspection, setSelectedDocIdForInspection] = useState(null);
  const [docToDelete, setDocToDelete] = useState(null);
  const [isDeleting, setIsDeleting] = useState(false);

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    setIsLoading(true);
    setError('');
    try {
      const [docsResponse, metricsResponse, feedbackResponse] = await Promise.all([
        ApiClient.listDocuments(0, 100),
        ApiClient.getAdminMetrics().catch(() => null),
        ApiClient.getFeedbackAnalytics().catch(() => null),
      ]);
      setDocuments(docsResponse.documents || []);
      setMetrics(metricsResponse);
      setFeedbackStats(feedbackResponse);
    } catch (err) {
      setError(err.message || 'Failed to load administrative data');
    } finally {
      setIsLoading(false);
    }
  };

  const handleDeleteDocument = async () => {
    if (!docToDelete) return;
    setIsDeleting(true);
    try {
      await ApiClient.deleteDocument(docToDelete.id);
      setDocToDelete(null);
      await loadDashboardData();
    } catch (err) {
      alert(`Failed to delete document: ${err.message}`);
    } finally {
      setIsDeleting(false);
    }
  };

  const filteredDocuments = documents.filter((doc) => {
    const q = searchQuery.toLowerCase();
    return (
      doc.title.toLowerCase().includes(q) ||
      doc.filename.toLowerCase().includes(q) ||
      (doc.department && doc.department.toLowerCase().includes(q)) ||
      (doc.document_type && doc.document_type.toLowerCase().includes(q))
    );
  });

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      {/* Top Admin Sub-Header */}
      <div className="bg-slate-900/60 border-b border-slate-800 px-6 py-4 flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs uppercase font-bold px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/30">
              Admin Portal
            </span>
            <h1 className="text-lg font-bold text-white">Document Management & Knowledge Base</h1>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Ingest institutional PDFs, monitor chunk embeddings, and manage vector indices
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={onNavigateToChat}
            className="px-3.5 py-2 text-xs font-semibold text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700/80 border border-slate-700 rounded-xl transition flex items-center gap-1.5"
          >
            <span>💬</span> Test Student Chat
          </button>
          <button
            onClick={() => setIsUploadOpen(true)}
            className="px-4 py-2 text-xs font-bold text-white bg-gradient-to-r from-cyan-600 to-indigo-600 hover:from-cyan-500 hover:to-indigo-500 rounded-xl shadow-lg shadow-cyan-950/40 transition flex items-center gap-1.5"
          >
            <span>➕</span> Upload New PDF
          </button>
        </div>
      </div>

      {/* Main Content */}
      <main className="flex-1 p-6 max-w-7xl mx-auto w-full space-y-6">
        {/* KPI Metrics Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
          <div className="p-4 bg-slate-900/60 border border-slate-800 rounded-2xl">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-400">Total Documents</span>
              <span className="text-base">📄</span>
            </div>
            <div className="text-2xl font-black text-white mt-2">
              {metrics ? metrics.total_documents : documents.length}
            </div>
            <div className="text-[11px] text-emerald-400 mt-1 flex items-center gap-1">
              <span>●</span> {metrics ? metrics.status_breakdown.completed : documents.length} indexed & verified
            </div>
          </div>

          <div className="p-4 bg-slate-900/60 border border-slate-800 rounded-2xl">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-400">Indexed Chunks</span>
              <span className="text-base">🧩</span>
            </div>
            <div className="text-2xl font-black text-white mt-2">
              {metrics ? metrics.total_chunks : '—'}
            </div>
            <div className="text-[11px] text-slate-400 mt-1">
              Page & section-aware vectors
            </div>
          </div>

          <div className="p-4 bg-slate-900/60 border border-slate-800 rounded-2xl">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-400">Student Conversations</span>
              <span className="text-base">💬</span>
            </div>
            <div className="text-2xl font-black text-white mt-2">
              {metrics ? metrics.total_conversations : '—'}
            </div>
            <div className="text-[11px] text-cyan-400 mt-1">
              {metrics ? `${metrics.total_messages} queries logged` : 'Multi-turn memory'}
            </div>
          </div>

          <div className="p-4 bg-slate-900/60 border border-slate-800 rounded-2xl">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-400">Satisfaction Rate</span>
              <span className="text-base">🌟</span>
            </div>
            <div className="text-2xl font-black text-amber-400 mt-2">
              {feedbackStats ? `${feedbackStats.satisfaction_rate}%` : '100%'}
            </div>
            <div className="text-[11px] text-slate-400 mt-1">
              {feedbackStats ? `${feedbackStats.positive_count} 👍 / ${feedbackStats.negative_count} 👎` : 'Student ratings'}
            </div>
          </div>

          <div className="p-4 bg-slate-900/60 border border-slate-800 rounded-2xl sm:col-span-2 lg:col-span-1">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-400">Vector Store Status</span>
              <span className="text-base">⚡</span>
            </div>
            <div className="text-2xl font-black text-emerald-400 mt-2">
              ChromaDB Active
            </div>
            <div className="text-[11px] text-slate-400 mt-1">
              MiniLM-L6-v2 (384d)
            </div>
          </div>
        </div>

        {/* Document Inventory Section */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl overflow-hidden flex flex-col">
          {/* Table Toolbar */}
          <div className="p-4 border-b border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-3 bg-slate-950/40">
            <div className="flex items-center gap-3 w-full sm:w-auto">
              <h2 className="text-sm font-bold text-white">Institutional Document Repository</h2>
              <button
                onClick={loadDashboardData}
                disabled={isLoading}
                className="text-xs text-slate-400 hover:text-white p-1 rounded hover:bg-slate-800 transition"
                title="Refresh table"
              >
                🔄
              </button>
            </div>

            <div className="w-full sm:w-80">
              <div className="relative">
                <span className="absolute left-3 top-2.5 text-xs text-slate-500">🔍</span>
                <input
                  type="text"
                  placeholder="Filter by title, department, or type..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-8 pr-3 py-1.5 bg-slate-950 border border-slate-700/80 rounded-xl text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500"
                />
              </div>
            </div>
          </div>

          {/* Table Container */}
          <div className="overflow-x-auto">
            {isLoading ? (
              <div className="py-20 text-center text-slate-400 space-y-2">
                <div className="w-7 h-7 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin mx-auto" />
                <p className="text-xs font-medium">Loading documents...</p>
              </div>
            ) : error ? (
              <div className="p-6 text-center text-xs text-red-400 space-y-2">
                <p>⚠️ {error}</p>
                <button
                  onClick={loadDashboardData}
                  className="px-3 py-1 bg-slate-800 text-slate-200 rounded-lg text-xs hover:bg-slate-700"
                >
                  Retry
                </button>
              </div>
            ) : filteredDocuments.length === 0 ? (
              <div className="py-20 text-center space-y-3">
                <div className="text-4xl">📂</div>
                <h3 className="text-sm font-semibold text-slate-300">
                  {searchQuery ? 'No documents match your filter' : 'No documents uploaded yet'}
                </h3>
                <p className="text-xs text-slate-500 max-w-sm mx-auto">
                  {searchQuery
                    ? 'Try adjusting your search keywords.'
                    : 'Upload your first official college PDF (academic handbook, regulations, fee schedule) to enable grounded student queries.'}
                </p>
                {!searchQuery && (
                  <button
                    onClick={() => setIsUploadOpen(true)}
                    className="px-4 py-2 text-xs font-bold text-cyan-400 hover:text-cyan-300 bg-cyan-950/60 border border-cyan-800/60 rounded-xl transition"
                  >
                    Upload College PDF
                  </button>
                )}
              </div>
            ) : (
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-950/60 text-slate-400 font-semibold border-b border-slate-800">
                  <tr>
                    <th className="py-3 px-4">Title & Details</th>
                    <th className="py-3 px-4">Category / Dept</th>
                    <th className="py-3 px-4">Year / Sem</th>
                    <th className="py-3 px-4">Status</th>
                    <th className="py-3 px-4">Uploaded</th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {filteredDocuments.map((doc) => (
                    <tr key={doc.id} className="hover:bg-slate-900/40 transition">
                      {/* Title & File */}
                      <td className="py-3 px-4">
                        <div className="font-semibold text-slate-200">{doc.title}</div>
                        <div className="text-[11px] text-slate-400 font-mono flex items-center gap-2 mt-0.5">
                          <span>{doc.filename}</span>
                          {doc.version && (
                            <span className="px-1.5 py-0.2 rounded bg-slate-800 text-[10px]">
                              v{doc.version}
                            </span>
                          )}
                        </div>
                      </td>

                      {/* Category & Dept */}
                      <td className="py-3 px-4">
                        <span className="px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 font-medium">
                          {doc.document_type || 'General'}
                        </span>
                        <div className="text-[11px] text-slate-400 mt-1">
                          {doc.department || 'All Departments'}
                        </div>
                      </td>

                      {/* Year & Semester */}
                      <td className="py-3 px-4">
                        <div className="text-slate-300 font-medium">
                          {doc.academic_year || '—'}
                        </div>
                        <div className="text-[11px] text-slate-500">
                          {doc.semester || 'All Semesters'}
                        </div>
                      </td>

                      {/* Status */}
                      <td className="py-3 px-4">
                        <span
                          className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full font-semibold uppercase text-[10px] ${
                            doc.status === 'completed'
                              ? 'bg-emerald-950 text-emerald-400 border border-emerald-800/60'
                              : doc.status === 'failed'
                              ? 'bg-red-950 text-red-400 border border-red-800/60'
                              : 'bg-amber-950 text-amber-400 border border-amber-800/60'
                          }`}
                        >
                          <span
                            className={`w-1.5 h-1.5 rounded-full ${
                              doc.status === 'completed'
                                ? 'bg-emerald-400'
                                : doc.status === 'failed'
                                ? 'bg-red-400'
                                : 'bg-amber-400 animate-ping'
                            }`}
                          />
                          {doc.status}
                        </span>
                      </td>

                      {/* Upload Date */}
                      <td className="py-3 px-4 text-slate-400 text-[11px]">
                        {new Date(doc.created_at).toLocaleDateString(undefined, {
                          month: 'short',
                          day: 'numeric',
                          year: 'numeric',
                        })}
                      </td>

                      {/* Actions */}
                      <td className="py-3 px-4 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={() => setSelectedDocIdForInspection(doc.id)}
                            className="px-2.5 py-1 text-xs text-cyan-400 hover:text-cyan-300 bg-cyan-950/40 hover:bg-cyan-950/70 border border-cyan-800/40 rounded-lg transition"
                          >
                            Inspect Chunks
                          </button>
                          <button
                            onClick={() => setDocToDelete(doc)}
                            className="px-2 py-1 text-xs text-slate-400 hover:text-rose-400 hover:bg-rose-950/30 rounded-lg transition"
                            title="Delete document and vector index"
                          >
                            🗑️
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </main>

      {/* Upload Modal */}
      <DocumentUploadModal
        isOpen={isUploadOpen}
        onClose={() => setIsUploadOpen(false)}
        onUploadSuccess={loadDashboardData}
      />

      {/* Chunk Inspector Modal */}
      <ChunkInspectorModal
        documentId={selectedDocIdForInspection}
        isOpen={Boolean(selectedDocIdForInspection)}
        onClose={() => setSelectedDocIdForInspection(null)}
      />

      {/* Delete Confirmation Modal */}
      {docToDelete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-in fade-in duration-150">
          <div className="bg-slate-900 border border-slate-800 w-full max-w-md rounded-2xl p-6 shadow-2xl space-y-4">
            <div className="w-10 h-10 rounded-xl bg-rose-500/10 border border-rose-500/30 flex items-center justify-center text-rose-400 text-lg">
              ⚠️
            </div>
            <div>
              <h3 className="text-base font-bold text-white">Delete Institutional Document?</h3>
              <p className="text-xs text-slate-400 mt-1 leading-relaxed">
                Are you sure you want to delete <span className="text-slate-200 font-semibold">"{docToDelete.title}"</span>?
                This will permanently delete the document record, all associated text chunks, and their vector embeddings from ChromaDB.
              </p>
            </div>
            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                onClick={() => setDocToDelete(null)}
                disabled={isDeleting}
                className="px-4 py-2 text-xs font-semibold text-slate-400 hover:text-white transition"
              >
                Cancel
              </button>
              <button
                onClick={handleDeleteDocument}
                disabled={isDeleting}
                className="px-4 py-2 text-xs font-bold text-white bg-rose-600 hover:bg-rose-500 rounded-xl transition flex items-center gap-1.5"
              >
                {isDeleting ? 'Deleting...' : 'Confirm Delete'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

