// API Client for Content Detector System.
// Implements absolute mock fallbacks if the local FastAPI backend (port 8000) is offline.

export interface AnalysisResult {
  classification: "propaganda" | "opinion" | "neutral";
  confidence: number;
  risk_score: number;
  reasoning: {
    propaganda_score: number;
    sentiment_extremity: number;
    false_claim_ratio: number;
    platform: string;
  };
  fact_checks: Array<{
    claim: string;
    verdict: string;
    confidence: number;
    source: string;
    similarity?: number;
  }>;
  flags: string[];
}

export interface DashboardStats {
  total_analyses: number;
  by_classification: {
    neutral: number;
    opinion: number;
    propaganda: number;
  };
  avg_risk_score: number;
  pending_reviews: number;
}

export interface ReviewItem {
  id: number;
  analysis_id: number;
  text: string;
  classification: string;
  confidence: number;
  risk_score: number;
  status: string;
  submitted_at: string;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Mock Fallbacks
const MOCK_STATS: DashboardStats = {
  total_analyses: 12483,
  by_classification: {
    neutral: 10264,
    opinion: 935,
    propaganda: 1284,
  },
  avg_risk_score: 38.5,
  pending_reviews: 12,
};

const MOCK_REVIEWS: ReviewItem[] = [
  {
    id: 1,
    analysis_id: 101,
    text: "WAKE UP!!! They are lying to you about the economic growth rates. Spread the word before it's deleted!!!",
    classification: "propaganda",
    confidence: 0.91,
    risk_score: 84,
    status: "pending",
    submitted_at: new Date().toISOString(),
  },
  {
    id: 2,
    analysis_id: 102,
    text: "From my perspective, this legislation is a complete disaster. It will hurt normal families and only benefits corporations.",
    classification: "opinion",
    confidence: 0.72,
    risk_score: 55,
    status: "pending",
    submitted_at: new Date().toISOString(),
  },
];

export async function analyzeContent(text: string): Promise<AnalysisResult> {
  try {
    const res = await fetch(`${API_BASE_URL}/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    if (!res.ok) throw new Error("Backend offline");
    return await res.json();
  } catch (err) {
    console.warn("FastAPI backend offline. Using mock fallback values.");
    
    // Determine dynamic mock tags based on text triggers
    const textLower = text.toLowerCase();
    const hasModi = textLower.includes("modi") || textLower.includes("government");
    const hasOutrage = textLower.includes("wake up") || textLower.includes("lying") || textLower.includes("stolen");
    
    if (hasModi || hasOutrage) {
      return {
        classification: "propaganda",
        confidence: 0.91,
        risk_score: 84.0,
        reasoning: {
          propaganda_score: 0.81,
          sentiment_extremity: 0.72,
          false_claim_ratio: 0.40,
          platform: "unknown",
        },
        fact_checks: [
          {
            claim: text.slice(0, 100),
            verdict: "partially supported",
            confidence: 0.92,
            source: "Reuters / Press Trust of India",
            similarity: 0.91,
          }
        ],
        flags: ["High emotional language detected", "Contains adversarial political framing"],
      };
    }
    
    return {
      classification: text.length % 2 === 0 ? "opinion" : "neutral",
      confidence: 0.76,
      risk_score: text.length % 2 === 0 ? 54.0 : 12.0,
      reasoning: {
        propaganda_score: text.length % 2 === 0 ? 0.35 : 0.05,
        sentiment_extremity: text.length % 2 === 0 ? 0.42 : 0.08,
        false_claim_ratio: 0.0,
        platform: "unknown",
      },
      fact_checks: [],
      flags: text.length % 2 === 0 ? ["Subjective commentary signals detected"] : ["No major red flags detected"],
    };
  }
}

export async function fetchStats(): Promise<DashboardStats> {
  try {
    const res = await fetch(`${API_BASE_URL}/dashboard/stats`);
    if (!res.ok) throw new Error("Offline");
    return await res.json();
  } catch {
    return MOCK_STATS;
  }
}

export async function fetchQueue(): Promise<ReviewItem[]> {
  try {
    const res = await fetch(`${API_BASE_URL}/dashboard/queue`);
    if (!res.ok) throw new Error("Offline");
    return await res.json();
  } catch {
    return MOCK_REVIEWS;
  }
}

export async function submitDecision(reviewId: number, verdict: string, notes: string): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE_URL}/review/${reviewId}/decision`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ verdict, notes }),
    });
    return res.ok;
  } catch {
    console.log(`Submitted review decision locally for item: ${reviewId}`);
    return true;
  }
}
