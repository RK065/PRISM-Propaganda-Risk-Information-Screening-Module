"use client";

import React, { useState } from "react";
import { analyzeContent, AnalysisResult } from "../../lib/api";
import { 
  ShieldAlert, 
  CheckCircle2, 
  HelpCircle, 
  RefreshCw, 
  Loader2, 
  Info,
  ChevronDown
} from "lucide-react";

export default function ContentAnalyzer() {
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState("");

  const [progress, setProgress] = useState(0);
  const [statusText, setStatusText] = useState("");
  const [elapsed, setElapsed] = useState(0.0);

  const handleClear = () => {
    setText("");
    setResult(null);
    setError("");
    setProgress(0);
  };

  const handleExample = () => {
    setText(
      "WAKE UP!!! They're stealing our future and NTA refuses to answer the real question: were the papers leaked? Dharmendra Pradhan's resignation is just the first step! Spread the word before it's deleted!!!"
    );
  };

  const handleAnalyze = async () => {
    if (!text.trim() || text.trim().length < 10) {
      setError("Text must be at least 10 characters long.");
      return;
    }
    setError("");
    setLoading(true);
    setProgress(0);
    setStatusText("Extracting linguistic markers & readability indices...");
    setElapsed(0.0);

    const startTime = Date.now();
    const interval = setInterval(() => {
      const duration = (Date.now() - startTime) / 1000;
      setElapsed(duration);

      if (duration < 0.4) {
        setProgress(Math.min(duration * 75, 30));
        setStatusText("Extracting linguistic markers & readability indices...");
      } else if (duration < 0.8) {
        setProgress(30 + Math.min((duration - 0.4) * 75, 30));
        setStatusText("Generating character/word TF-IDF matrices...");
      } else if (duration < 1.2) {
        setProgress(60 + Math.min((duration - 0.8) * 75, 30));
        setStatusText("Retrieving SBERT sentence embeddings...");
      } else {
        setProgress(Math.min(90 + (duration - 1.2) * 5, 95));
        setStatusText("Running VotingClassifier ensemble classification...");
      }
    }, 50);

    try {
      const data = await analyzeContent(text);
      setResult(data);
      setProgress(100);
      setStatusText("Analysis complete!");
    } catch (err) {
      setError("Failed to run analysis.");
    } finally {
      clearInterval(interval);
      setLoading(false);
      setElapsed((Date.now() - startTime) / 1000);
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

  return (
    <div className="space-y-8 max-w-4xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-primaryText">AI Narrative Analyzer</h1>
        <p className="text-sm text-secondaryText">Analyze linguistic features and classify content instantly.</p>
      </div>

      {/* Input box */}
      <div className="p-6 rounded-xl bg-card border border-border space-y-4">
        <textarea
          rows={6}
          placeholder="Paste articles, posts, or transcripts here..."
          value={text}
          onChange={(e) => setText(e.target.value)}
          className="w-full bg-slate-900 border border-border rounded-lg p-4 text-sm text-primaryText placeholder-secondaryText outline-none focus:border-slate-500 resize-none transition-colors"
        />

        {error && (
          <p className="text-xs font-semibold text-danger">{error}</p>
        )}

        <div className="flex justify-between items-center">
          <div className="flex gap-2">
            <button 
              onClick={handleExample}
              className="px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-xs font-semibold border border-slate-700 text-primaryText transition-colors"
            >
              Load Example
            </button>
            <button 
              onClick={handleClear}
              className="px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-xs font-semibold border border-slate-700 text-primaryText transition-colors"
            >
              Clear
            </button>
          </div>

          <button
            onClick={handleAnalyze}
            disabled={loading}
            className="flex items-center gap-2 px-5 py-2 rounded bg-danger hover:bg-red-600 font-semibold text-sm text-white disabled:bg-slate-700 transition-colors"
          >
            {loading ? (
              <>
                <Loader2 size={16} className="animate-spin" />
                Analyzing...
              </>
            ) : (
              "Analyze"
            )}
          </button>
        </div>

        {(loading || progress > 0) && (
          <div className="space-y-2 pt-2 border-t border-border">
            <div className="flex justify-between text-xs text-secondaryText">
              <span>{statusText}</span>
              <span>Elapsed: {elapsed.toFixed(1)}s</span>
            </div>
            <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
              <div 
                className="bg-danger h-full transition-all duration-300" 
                style={{ width: `${progress}%` }}
              ></div>
            </div>
          </div>
        )}
      </div>

      {/* Result Output Layout */}
      {result && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Main Prediction Score Card */}
          <div className="p-6 rounded-xl bg-card border border-border space-y-6 md:col-span-2">
            <div className="flex items-center justify-between border-b border-border pb-4">
              <h2 className="text-base font-semibold text-primaryText">Narrative Assessment</h2>
              <span className={`px-2.5 py-0.5 rounded-full border text-xs font-mono uppercase tracking-wider ${getBadgeStyle(result.classification)}`}>
                {result.classification}
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-2">
                <p className="text-xs text-secondaryText uppercase tracking-wider font-semibold">Model Confidence</p>
                <div className="flex items-baseline gap-2">
                  <span className="text-4xl font-extrabold text-primaryText">{(result.confidence * 100).toFixed(0)}%</span>
                  <span className="text-xs text-secondaryText">calibrated prob</span>
                </div>
              </div>

              <div className="space-y-2">
                <p className="text-xs text-secondaryText uppercase tracking-wider font-semibold">Risk Score Assessment</p>
                <div className="flex items-baseline gap-2">
                  <span className={`text-4xl font-extrabold ${result.risk_score > 60 ? "text-danger" : result.risk_score > 30 ? "text-warning" : "text-success"}`}>
                    {result.risk_score.toFixed(0)}
                  </span>
                  <span className="text-xs text-secondaryText">/ 100 threshold</span>
                </div>
              </div>
            </div>

            {/* Explainability Breakdown (SHAP fallback) */}
            <div className="space-y-4 pt-4 border-t border-border">
              <h3 className="text-sm font-semibold text-primaryText flex items-center gap-1.5">
                <Info size={14} className="text-secondaryText" />
                Linguistic Features & Feature Attribution
              </h3>
              <div className="space-y-2.5">
                <div>
                  <div className="flex justify-between text-xs text-secondaryText mb-1">
                    <span>Propaganda Attribution Flag</span>
                    <span className="font-mono">{(result.reasoning.propaganda_score * 100).toFixed(0)}%</span>
                  </div>
                  <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                    <div className="bg-danger h-full" style={{ width: `${result.reasoning.propaganda_score * 100}%` }}></div>
                  </div>
                </div>
                <div>
                  <div className="flex justify-between text-xs text-secondaryText mb-1">
                    <span>Emotional Bias & Extremity Ratio</span>
                    <span className="font-mono">{(result.reasoning.sentiment_extremity * 100).toFixed(0)}%</span>
                  </div>
                  <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                    <div className="bg-warning h-full" style={{ width: `${result.reasoning.sentiment_extremity * 100}%` }}></div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Trigger Flags & Alerts */}
          <div className="p-6 rounded-xl bg-card border border-border space-y-4">
            <h2 className="text-base font-semibold text-primaryText">Detected Signals</h2>
            <ul className="space-y-3">
              {result.flags.map((flag, idx) => (
                <li key={idx} className="flex gap-2.5 items-start text-xs font-medium text-secondaryText">
                  <span className="text-danger mt-0.5">✓</span>
                  {flag}
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}
