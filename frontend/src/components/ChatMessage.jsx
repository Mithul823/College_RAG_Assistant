import { useState } from 'react';
import ApiClient from '../api/client';

export default function ChatMessage({ message, onOpenSources, onSelectSource }) {
  const isUser = message.role === 'user';
  const isGrounded = message.answer_mode === 'grounded';
  const isUnknown = message.answer_mode === 'unknown';
  const isError = message.answer_mode === 'error';
  const hasSources = message.sources && message.sources.length > 0;

  const [feedbackRating, setFeedbackRating] = useState(message.user_feedback || null);
  const [isSubmittingFeedback, setIsSubmittingFeedback] = useState(false);
  const [feedbackSaved, setFeedbackSaved] = useState(false);

  const handleFeedback = async (rating) => {
    if (!message.id || isSubmittingFeedback) return;
    setIsSubmittingFeedback(true);
    try {
      const newRating = feedbackRating === rating ? null : rating;
      setFeedbackRating(newRating);
      if (newRating !== null) {
        await ApiClient.submitMessageFeedback(message.id, newRating);
        setFeedbackSaved(true);
        setTimeout(() => setFeedbackSaved(false), 2000);
      }
    } catch (err) {
      console.error('Failed to submit feedback', err);
    } finally {
      setIsSubmittingFeedback(false);
    }
  };

  if (isUser) {
    return (
      <div className="flex justify-end mb-6">
        <div className="max-w-2xl bg-cyan-600 text-white rounded-2xl rounded-tr-xs px-5 py-3.5 shadow-md shadow-cyan-950/30">
          <p className="text-sm whitespace-pre-wrap leading-relaxed">{message.content}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-start mb-6">
      <div className="max-w-2xl clay-card rounded-2xl rounded-tl-xs px-5 py-4 w-full">
        {/* Header with status badge & latency */}
        <div className="flex items-center justify-between gap-3 mb-2.5 pb-2 border-b border-slate-800/80">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs font-semibold text-slate-300">Assistant</span>
            {isGrounded && (
              <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-400 bg-emerald-950/80 border border-emerald-800/60 px-2 py-0.5 rounded-full">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                Verified Grounded
              </span>
            )}
            {isUnknown && (
              <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-amber-400 bg-amber-950/80 border border-amber-800/60 px-2 py-0.5 rounded-full">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
                Information Unavailable
              </span>
            )}
            {isError && (
              <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-rose-400 bg-rose-950/80 border border-rose-800/60 px-2 py-0.5 rounded-full">
                <span className="w-1.5 h-1.5 rounded-full bg-rose-400" />
                Error
              </span>
            )}
          </div>

          {message.latency_ms && (
            <span className="text-[10px] font-mono text-slate-500 flex items-center gap-1">
              ⚡ {message.latency_ms}ms
            </span>
          )}
        </div>

        {/* Message body */}
        <div className="text-sm text-slate-200 whitespace-pre-wrap leading-relaxed mb-3">
          {message.content}
        </div>

        {/* Source Citations summary chips */}
        {hasSources && (
          <div className="mt-3 pt-3 border-t border-slate-800/80">
            <div className="flex items-center justify-between mb-2">
              <span className="text-[11px] uppercase font-bold tracking-wider text-slate-400">
                Sources Cited ({message.sources.length})
              </span>
              <button
                onClick={() => onOpenSources(message.sources)}
                className="text-xs text-cyan-400 hover:text-cyan-300 font-medium transition cursor-pointer flex items-center gap-1"
              >
                Inspect all →
              </button>
            </div>

            <div className="flex flex-wrap gap-1.5">
              {message.sources.map((src, i) => (
                <button
                  key={i}
                  onClick={() => onSelectSource ? onSelectSource(src) : onOpenSources(message.sources)}
                  className="inline-flex items-center gap-1.5 text-xs bg-slate-950 hover:bg-slate-800 border border-slate-800 hover:border-cyan-700/60 px-2.5 py-1 rounded-lg text-slate-300 transition cursor-pointer text-left group"
                  title="Click to preview exact PDF snippet"
                >
                  <span className="text-cyan-400 group-hover:scale-110 transition-transform">📄</span>
                  <span className="font-medium truncate max-w-[150px]">{src.document_name}</span>
                  <span className="text-[10px] text-slate-400 font-mono">p.{src.page_number}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Message Footer: Feedback Buttons */}
        {!isUser && message.id && (
          <div className="mt-3 pt-2.5 border-t border-slate-800/50 flex items-center justify-between">
            <span className="text-[11px] text-slate-500">
              {feedbackSaved ? (
                <span className="text-emerald-400 font-medium animate-in fade-in">✓ Feedback submitted</span>
              ) : (
                'Was this answer helpful?'
              )}
            </span>

            <div className="flex items-center gap-1.5">
              <button
                onClick={() => handleFeedback(1)}
                className={`p-1.5 rounded-lg text-xs transition flex items-center gap-1 ${
                  feedbackRating === 1
                    ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
                }`}
                title="Helpful answer"
              >
                👍
              </button>
              <button
                onClick={() => handleFeedback(-1)}
                className={`p-1.5 rounded-lg text-xs transition flex items-center gap-1 ${
                  feedbackRating === -1
                    ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
                }`}
                title="Unhelpful answer"
              >
                👎
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
