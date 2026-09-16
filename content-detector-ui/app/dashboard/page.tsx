"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { fetchStats, DashboardStats, analyzeContent } from "../../lib/api";
import { 
  ShieldAlert, 
  HelpCircle, 
  CheckCircle2, 
  Layers, 
  RefreshCw, 
  AlertTriangle,
  ArrowUpRight
} from "lucide-react";

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    setLoading(true);
    const data = await fetchStats();
    setStats(data);
    setLoading(false);
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] gap-4">
        <RefreshCw className="animate-spin text-secondaryText" size={32} />
        <p className="text-sm text-secondaryText">Loading operational metrics...</p>
      </div>
    );
  }

  const propagandaCount = stats?.by_classification.propaganda || 0;
  const neutralCount = stats?.by_classification.neutral || 0;
  const opinionCount = stats?.by_classification.opinion || 0;
  const totalCount = stats?.total_analyses || 0;

  return (
    <div className="space-y-8">
      {/* Title */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-primaryText">SOC Operations Dashboard</h1>
          <p className="text-sm text-secondaryText">Real-time surveillance overview of content classification metrics.</p>
        </div>
        <button 
          onClick={loadDashboardData}
          className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-semibold border border-slate-700 text-primaryText transition-colors"
        >
          <RefreshCw size={14} />
          Reload metrics
        </button>
      </div>

      {/* Main KPI Stats Row */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="p-6 rounded-xl bg-card border border-border space-y-2 relative overflow-hidden">
          <div className="absolute right-4 top-4 text-slate-800">
            <Layers size={40} />
          </div>
          <p className="text-xs font-semibold text-secondaryText uppercase tracking-wider">Total Analyses</p>
          <p className="text-3xl font-extrabold text-primaryText">{totalCount.toLocaleString()}</p>
          <div className="text-[10px] text-success flex items-center gap-1 font-mono">
            <span>Online</span>
          </div>
        </div>

        <div className="p-6 rounded-xl bg-card border border-border space-y-2 relative overflow-hidden">
          <div className="absolute right-4 top-4 text-red-950">
            <ShieldAlert size={40} />
          </div>
          <p className="text-xs font-semibold text-secondaryText uppercase tracking-wider">Propaganda Flagged</p>
          <p className="text-3xl font-extrabold text-danger">{propagandaCount.toLocaleString()}</p>
          <div className="text-[10px] text-danger flex items-center gap-1 font-mono">
            <span>{((propagandaCount / Math.max(totalCount, 1)) * 100).toFixed(1)}% density</span>
          </div>
        </div>

        <div className="p-6 rounded-xl bg-card border border-border space-y-2 relative overflow-hidden">
          <div className="absolute right-4 top-4 text-amber-950">
            <AlertTriangle size={40} />
          </div>
          <p className="text-xs font-semibold text-secondaryText uppercase tracking-wider">Opinions Flagged</p>
          <p className="text-3xl font-extrabold text-warning">{opinionCount.toLocaleString()}</p>
          <div className="text-[10px] text-warning flex items-center gap-1 font-mono">
            <span>{((opinionCount / Math.max(totalCount, 1)) * 100).toFixed(1)}% density</span>
          </div>
        </div>

        <div className="p-6 rounded-xl bg-card border border-border space-y-2 relative overflow-hidden">
          <div className="absolute right-4 top-4 text-green-950">
            <CheckCircle2 size={40} />
          </div>
          <p className="text-xs font-semibold text-secondaryText uppercase tracking-wider">Neutral Content</p>
          <p className="text-3xl font-extrabold text-success">{neutralCount.toLocaleString()}</p>
          <div className="text-[10px] text-success flex items-center gap-1 font-mono">
            <span>{((neutralCount / Math.max(totalCount, 1)) * 100).toFixed(1)}% density</span>
          </div>
        </div>
      </div>

      {/* Main Content Layout */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        {/* Left Column - Distribution Pie Visualization (HTML5 CSS Canvas style) */}
        <div className="p-6 rounded-xl bg-card border border-border space-y-6 md:col-span-2">
          <h2 className="text-base font-semibold text-primaryText">Narrative Taxonomy Distribution</h2>
          <div className="flex flex-col md:flex-row items-center justify-between gap-6 py-4">
            <div className="relative w-40 h-40 rounded-full border-8 border-slate-700 flex items-center justify-center">
              {/* Dynamic Inner Circle Stats */}
              <div className="text-center">
                <p className="text-sm font-semibold text-secondaryText">Avg Risk</p>
                <p className="text-2xl font-bold text-primaryText">{stats?.avg_risk_score}%</p>
              </div>
            </div>

            <div className="flex-1 space-y-3 w-full">
              <div>
                <div className="flex justify-between text-xs font-semibold text-secondaryText mb-1">
                  <span>Neutral Content ({neutralCount})</span>
                  <span>{((neutralCount / Math.max(totalCount, 1)) * 100).toFixed(1)}%</span>
                </div>
                <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                  <div className="bg-success h-full" style={{ width: `${(neutralCount / Math.max(totalCount, 1)) * 100}%` }}></div>
                </div>
              </div>
              <div>
                <div className="flex justify-between text-xs font-semibold text-secondaryText mb-1">
                  <span>Propaganda ({propagandaCount})</span>
                  <span>{((propagandaCount / Math.max(totalCount, 1)) * 100).toFixed(1)}%</span>
                </div>
                <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                  <div className="bg-danger h-full" style={{ width: `${(propagandaCount / Math.max(totalCount, 1)) * 100}%` }}></div>
                </div>
              </div>
              <div>
                <div className="flex justify-between text-xs font-semibold text-secondaryText mb-1">
                  <span>Opinion ({opinionCount})</span>
                  <span>{((opinionCount / Math.max(totalCount, 1)) * 100).toFixed(1)}%</span>
                </div>
                <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                  <div className="bg-warning h-full" style={{ width: `${(opinionCount / Math.max(totalCount, 1)) * 100}%` }}></div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column - System Health */}
        <div className="p-6 rounded-xl bg-card border border-border space-y-4">
          <h2 className="text-base font-semibold text-primaryText">Audit Queue Status</h2>
          <div className="space-y-4">
            <div className="p-4 rounded-lg bg-slate-900 border border-border flex items-center justify-between">
              <div>
                <p className="text-xs text-secondaryText">Pending Human Review</p>
                <p className="text-xl font-bold text-warning">{stats?.pending_reviews} items</p>
              </div>
              <Link href="/review" className="p-2 bg-slate-850 hover:bg-slate-800 rounded-lg text-secondaryText hover:text-primaryText border border-border transition-colors">
                <ArrowUpRight size={16} />
              </Link>
            </div>

            <div className="space-y-2 text-xs font-medium text-secondaryText">
              <div className="flex justify-between">
                <span>Model Version:</span>
                <span className="font-mono text-primaryText">models/v3 (RF)</span>
              </div>
              <div className="flex justify-between">
                <span>Cache State:</span>
                <span className="text-success font-semibold">Active / Operational</span>
              </div>
              <div className="flex justify-between">
                <span>Active Learning Loop:</span>
                <span className="text-success font-semibold">Ready</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
