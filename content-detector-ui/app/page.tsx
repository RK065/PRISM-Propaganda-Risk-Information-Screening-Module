import React from "react";
import Link from "next/link";
import { ShieldCheck, Cpu, HardDrive, FileText, ArrowRight } from "lucide-react";

export default function LandingPage() {
  return (
    <div className="max-w-5xl mx-auto space-y-16 py-8">
      {/* Hero Section */}
      <section className="text-center space-y-6 py-12">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-slate-800 border border-slate-700 text-xs font-medium text-danger">
          <span className="w-1.5 h-1.5 bg-danger rounded-full animate-pulse"></span>
          PRISM — Coordinated Influence Campaign Detection
        </div>
        <h1 className="text-5xl font-extrabold tracking-tight text-primaryText sm:text-6xl">
          <span className="font-syncopate font-bold tracking-[0.16em] text-4xl block mb-4">PRISM</span>
          <span className="text-danger text-3xl font-bold block">Propaganda Recognition, Intelligence & Source Monitoring</span>
        </h1>
        <p className="text-lg text-secondaryText max-w-2xl mx-auto">
          Identify coordinated manipulative narratives, extract subtle emotional bias flags,
          and ground claims using real-time Retrieval-Augmented Generation (RAG).
        </p>
        <div className="flex justify-center gap-4 pt-4">
          <Link href="/analyzer" className="flex items-center gap-2 px-6 py-3 rounded-lg bg-danger hover:bg-red-600 font-semibold text-white transition-colors">
            Analyze Content
            <ArrowRight size={18} />
          </Link>
          <Link href="/dashboard" className="px-6 py-3 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 font-semibold text-primaryText transition-colors">
            View Operations Dashboard
          </Link>
        </div>
      </section>

      {/* Stats Quick Cards */}
      <section className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="p-6 rounded-xl bg-card border border-border space-y-2">
          <p className="text-sm font-medium text-secondaryText">Target Corpus Size</p>
          <p className="text-3xl font-bold text-primaryText">40,005 items</p>
        </div>
        <div className="p-6 rounded-xl bg-card border border-border space-y-2">
          <p className="text-sm font-medium text-secondaryText">Model Accuracy</p>
          <p className="text-3xl font-bold text-success">92.8%</p>
        </div>
        <div className="p-6 rounded-xl bg-card border border-border space-y-2">
          <p className="text-sm font-medium text-secondaryText">F1 Macro Score</p>
          <p className="text-3xl font-bold text-primaryText">0.9207</p>
        </div>
        <div className="p-6 rounded-xl bg-card border border-border space-y-2">
          <p className="text-sm font-medium text-secondaryText">Features Extracted</p>
          <p className="text-3xl font-bold text-warning">8,455 dimensions</p>
        </div>
      </section>

      {/* Detection Pipeline Section */}
      <section className="space-y-6">
        <h2 className="text-2xl font-bold text-primaryText text-center">Pipeline Architecture</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          <div className="p-6 rounded-xl bg-slate-900 border border-border space-y-4">
            <div className="w-12 h-12 rounded bg-danger/10 border border-danger/30 flex items-center justify-center text-danger">
              <FileText size={24} />
            </div>
            <h3 className="text-lg font-semibold text-primaryText">1. Preprocessing & NLP</h3>
            <p className="text-sm text-secondaryText">
              Linguistic lemmatization, emoji sentiment extractors, readability scores (Flesch/Gunning Fog),
              and spaCy POS/NER tagging.
            </p>
          </div>

          <div className="p-6 rounded-xl bg-slate-900 border border-border space-y-4">
            <div className="w-12 h-12 rounded bg-warning/10 border border-warning/30 flex items-center justify-center text-warning">
              <Cpu size={24} />
            </div>
            <h3 className="text-lg font-semibold text-primaryText">2. Feature Engineering</h3>
            <p className="text-sm text-secondaryText">
              Word & Char TF-IDF combined with 71 engineered semantic dimensions and 384 SBERT embeddings.
            </p>
          </div>

          <div className="p-6 rounded-xl bg-slate-900 border border-border space-y-4">
            <div className="w-12 h-12 rounded bg-success/10 border border-success/30 flex items-center justify-center text-success">
              <ShieldCheck size={24} />
            </div>
            <h3 className="text-lg font-semibold text-primaryText">3. Soft Voting Classifier</h3>
            <p className="text-sm text-secondaryText">
              Ensemble predictions from Random Forest, Linear SVC, and Logistic Regression with Platt calibration.
            </p>
          </div>
        </div>
      </section>

      {/* Grounding Fact Verification info */}
      <section className="p-8 rounded-2xl bg-card border border-border flex flex-col md:flex-row items-center justify-between gap-6">
        <div className="space-y-2">
          <h3 className="text-xl font-bold text-primaryText">RAG-Backed Fact Grounding</h3>
          <p className="text-sm text-secondaryText max-w-2xl">
            Our pipeline automatically retrieves claims and checks them against a vector-indexed fact repository using FAISS IndexFlatIP.
          </p>
        </div>
        <Link href="/fact-check" className="px-5 py-2.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-sm font-semibold text-primaryText whitespace-nowrap transition-colors">
          Verify Claims
        </Link>
      </section>
    </div>
  );
}
