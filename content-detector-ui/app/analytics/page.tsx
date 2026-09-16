"use client";

import React, { useEffect, useState } from "react";
import { fetchStats, DashboardStats } from "../../lib/api";
import { RefreshCw, BarChart2, PieChart, Activity } from "lucide-react";

export default function Analytics() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadStats();
  }, []);

  const loadStats = async () => {
    setLoading(true);
    const data = await fetchStats();
    setStats(data);
    setLoading(false);
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] gap-4">
        <RefreshCw className="animate-spin text-secondaryText" size={32} />
        <p className="text-sm text-secondaryText">Loading analytics platform...</p>
      </div>
    );
  }

  const propagandaCount = stats?.by_classification.propaganda || 0;
  const neutralCount = stats?.by_classification.neutral || 0;
  const opinionCount = stats?.by_classification.opinion || 0;
  const totalCount = stats?.total_analyses || 1;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-primaryText">Narrative Analytics Platform</h1>
        <p className="text-sm text-secondaryText">Metric aggregation, probability density, and platform breakdowns.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        {/* Narrative Distribution Graph */}
        <div className="p-6 rounded-xl bg-card border border-border space-y-6">
          <div className="flex items-center gap-2 border-b border-border pb-4">
            <PieChart size={18} className="text-danger" />
            <h2 className="text-base font-semibold text-primaryText">Class Density Distribution</h2>
          </div>

          <div className="space-y-4">
            <div>
              <div className="flex justify-between text-xs font-semibold text-secondaryText mb-1">
                <span>Propaganda Flagged</span>
                <span>{((propagandaCount / totalCount) * 100).toFixed(1)}%</span>
              </div>
              <div className="w-full bg-slate-800 h-3 rounded-full overflow-hidden">
                <div className="bg-danger h-full" style={{ width: `${(propagandaCount / totalCount) * 100}%` }}></div>
              </div>
            </div>

            <div>
              <div className="flex justify-between text-xs font-semibold text-secondaryText mb-1">
                <span>Subjective Opinion</span>
                <span>{((opinionCount / totalCount) * 100).toFixed(1)}%</span>
              </div>
              <div className="w-full bg-slate-800 h-3 rounded-full overflow-hidden">
                <div className="bg-warning h-full" style={{ width: `${(opinionCount / totalCount) * 100}%` }}></div>
              </div>
            </div>

            <div>
              <div className="flex justify-between text-xs font-semibold text-secondaryText mb-1">
                <span>Objective Neutral</span>
                <span>{((neutralCount / totalCount) * 100).toFixed(1)}%</span>
              </div>
              <div className="w-full bg-slate-800 h-3 rounded-full overflow-hidden">
                <div className="bg-success h-full" style={{ width: `${(neutralCount / totalCount) * 100}%` }}></div>
              </div>
            </div>
          </div>
        </div>

        {/* Platform Breakdown */}
        <div className="p-6 rounded-xl bg-card border border-border space-y-6">
          <div className="flex items-center gap-2 border-b border-border pb-4">
            <BarChart2 size={18} className="text-warning" />
            <h2 className="text-base font-semibold text-primaryText">Platform Prevalence Breakdown</h2>
          </div>

          <div className="space-y-4">
            <div>
              <div className="flex justify-between text-xs font-semibold text-secondaryText mb-1">
                <span>Twitter / X</span>
                <span>45% prevalence</span>
              </div>
              <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                <div className="bg-slate-400 h-full" style={{ width: "45%" }}></div>
              </div>
            </div>

            <div>
              <div className="flex justify-between text-xs font-semibold text-secondaryText mb-1">
                <span>Reddit Discussions</span>
                <span>30% prevalence</span>
              </div>
              <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                <div className="bg-slate-400 h-full" style={{ width: "30%" }}></div>
              </div>
            </div>

            <div>
              <div className="flex justify-between text-xs font-semibold text-secondaryText mb-1">
                <span>Broadcast News & Press</span>
                <span>25% prevalence</span>
              </div>
              <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                <div className="bg-slate-400 h-full" style={{ width: "25%" }}></div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
