"use client";

import React, { useEffect, useState } from "react";
import { fetchQueue, submitDecision, ReviewItem } from "../../lib/api";
import { CheckCircle2, XCircle, RefreshCw, AlertCircle, Edit2 } from "lucide-react";

export default function ReviewQueue() {
  const [queue, setQueue] = useState<ReviewItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [notes, setNotes] = useState<{ [key: number]: string }>({});

  useEffect(() => {
    loadQueue();
  }, []);

  const loadQueue = async () => {
    setLoading(true);
    const data = await fetchQueue();
    setQueue(data);
    setLoading(false);
  };

  const handleDecision = async (id: number, verdict: string) => {
    const itemNotes = notes[id] || "";
    const success = await submitDecision(id, verdict, itemNotes);
    if (success) {
      // Remove from view
      setQueue(prev => prev.filter(item => item.id !== id));
    }
  };

  const getBadgeStyle = (label: string) => {
    switch (label) {
      case "propaganda":
        return "bg-red-500/10 border-red-500/30 text-danger";
      case "opinion":
        return "bg-amber-500/10 border-amber-500/30 text-warning";
      default:
        return "bg-green-500/10 border-green-500/30 text-success";
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[55vh] gap-4">
        <RefreshCw className="animate-spin text-secondaryText" size={32} />
        <p className="text-sm text-secondaryText">Loading review queue...</p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-primaryText">Human Review Queue</h1>
        <p className="text-sm text-secondaryText">Audit low-confidence classifications and verify annotations for retraining.</p>
      </div>

      {queue.length === 0 ? (
        <div className="p-8 rounded-xl bg-card border border-border text-center space-y-4">
          <AlertCircle className="mx-auto text-secondaryText" size={36} />
          <div>
            <p className="text-sm font-semibold text-primaryText">Queue is empty</p>
            <p className="text-xs text-secondaryText">All flagged content has been successfully annotated.</p>
          </div>
          <button 
            onClick={loadQueue}
            className="px-4 py-2 rounded bg-slate-800 hover:bg-slate-700 text-xs font-semibold border border-slate-700 text-primaryText transition-colors"
          >
            Refresh queue
          </button>
        </div>
      ) : (
        <div className="space-y-6">
          {queue.map((item) => (
            <div key={item.id} className="p-6 rounded-xl bg-card border border-border space-y-4">
              <div className="flex justify-between items-start gap-4">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-mono uppercase tracking-wider border ${getBadgeStyle(item.classification)}`}>
                      {item.classification}
                    </span>
                    <span className="text-xs text-secondaryText">
                      Confidence: {(item.confidence * 100).toFixed(0)}%
                    </span>
                  </div>
                  <p className="text-xs text-secondaryText font-mono">
                    Submitted: {new Date(item.submitted_at).toLocaleString()}
                  </p>
                </div>

                <div className="flex gap-2">
                  <button
                    onClick={() => handleDecision(item.id, "confirmed")}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-success/15 hover:bg-success/25 border border-success/30 text-xs font-semibold text-success transition-colors"
                  >
                    <CheckCircle2 size={14} />
                    Approve
                  </button>
                  <button
                    onClick={() => handleDecision(item.id, "false_positive")}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-danger/15 hover:bg-danger/25 border border-danger/30 text-xs font-semibold text-danger transition-colors"
                  >
                    <XCircle size={14} />
                    Reject
                  </button>
                </div>
              </div>

              {/* Text Snippet */}
              <div className="p-4 rounded-lg bg-slate-900 border border-border text-sm text-primaryText leading-relaxed">
                {item.text}
              </div>

              {/* Notes Form */}
              <div className="flex gap-4 items-center">
                <Edit2 size={14} className="text-secondaryText shrink-0" />
                <input
                  type="text"
                  placeholder="Add analyst verification notes..."
                  value={notes[item.id] || ""}
                  onChange={(e) => setNotes({ ...notes, [item.id]: e.target.value })}
                  className="flex-1 bg-slate-900 border border-border rounded px-3 py-1.5 text-xs text-primaryText placeholder-secondaryText outline-none focus:border-slate-500 transition-colors"
                />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
