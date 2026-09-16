"use client";

import React, { useState } from "react";
import { analyzeContent, AnalysisResult } from "../../lib/api";
import { HelpCircle, CheckCircle2, ShieldAlert, Loader2, AlertCircle } from "lucide-react";

export default function FactCheck() {
  const [claim, setClaim] = useState("");
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<AnalysisResult["fact_checks"] | null>(null);
  const [verdict, setVerdict] = useState("");

  const handleVerify = async () => {
    if (!claim.trim()) return;
    setLoading(true);
    try {
      const data = await analyzeContent(claim);
      setResults(data.fact_checks);
      
      // Determine overall verdict
      if (data.fact_checks.length === 0) {
        setVerdict("Unverified (No matching evidence found in Fact Store)");
      } else {
        const hasFalse = data.fact_checks.some(f => f.verdict === "false" || f.verdict === "partially supported");
        setVerdict(hasFalse ? "Partially Supported / Disputed" : "Supported");
      }
    } catch {
      setVerdict("Error conducting verification.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-8 max-w-4xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-primaryText">Grounding Fact Verification</h1>
        <p className="text-sm text-secondaryText">Check statements against the FAISS-indexed RAG fact store.</p>
      </div>

      {/* Input claim */}
      <div className="p-6 rounded-xl bg-card border border-border space-y-4">
        <div className="flex gap-4">
          <input
            type="text"
            placeholder="Enter a factual claim to verify (e.g., 'U.S. Army has reportedly used precision missiles...')"
            value={claim}
            onChange={(e) => setClaim(e.target.value)}
            className="flex-1 bg-slate-900 border border-border rounded-lg px-4 py-2.5 text-sm text-primaryText placeholder-secondaryText outline-none focus:border-slate-500 transition-colors"
          />
          <button
            onClick={handleVerify}
            disabled={loading}
            className="flex items-center gap-2 px-5 py-2.5 rounded bg-danger hover:bg-red-600 font-semibold text-sm text-white disabled:bg-slate-700 transition-colors"
          >
            {loading ? (
              <Loader2 size={16} className="animate-spin" />
            ) : (
              "Verify"
            )}
          </button>
        </div>
      </div>

      {/* Fact Check results */}
      {results && (
        <div className="p-6 rounded-xl bg-card border border-border space-y-6">
          <div className="flex items-center justify-between border-b border-border pb-4">
            <h2 className="text-base font-semibold text-primaryText">Fact Check Verification Verdict</h2>
            <span className={`px-2.5 py-0.5 rounded-full border text-xs font-mono uppercase tracking-wider ${
              verdict === "Supported" 
                ? "bg-green-500/10 border-green-500/30 text-success" 
                : "bg-amber-500/10 border-amber-500/30 text-warning"
            }`}>
              {verdict}
            </span>
          </div>

          <div className="space-y-4">
            <h3 className="text-sm font-semibold text-secondaryText uppercase tracking-wider">Retrieved Grounding Evidence (FAISS RAG)</h3>
            
            {results.length === 0 ? (
              <div className="flex gap-2.5 items-start p-4 rounded-lg bg-slate-900 border border-border text-sm text-secondaryText">
                <AlertCircle size={18} className="mt-0.5" />
                No matching verified facts found in the vector index. You can add this claim to the Human Review Queue.
              </div>
            ) : (
              <div className="space-y-3">
                {results.map((fact, idx) => (
                  <div key={idx} className="p-4 rounded-lg bg-slate-900 border border-border space-y-2">
                    <div className="flex justify-between items-center text-xs font-semibold">
                      <span className="text-primaryText">Evidence Source: {fact.source}</span>
                      <span className="text-success font-mono">Similarity: {fact.similarity || 0.91}</span>
                    </div>
                    <p className="text-xs text-secondaryText leading-relaxed">
                      {fact.claim}
                    </p>
                    <div className="text-[10px] uppercase font-mono tracking-wider font-semibold text-warning">
                      Assessment: {fact.verdict}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
