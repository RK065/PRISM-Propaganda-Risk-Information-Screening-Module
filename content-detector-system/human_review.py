"""
Human review workflow.
Endpoints:
    POST /review/submit/{analysis_id}   — flag an analysis for human review
    GET  /review/queue                  — list pending reviews (analyst+)
    POST /review/{review_id}/decision   — approve / reject (analyst+)
    GET  /review/{review_id}            — get single review detail
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import get_current_user, require_role
from database import get_review_queue, submit_for_review, update_review

logger = logging.getLogger("human_review")

router = APIRouter(prefix="/review", tags=["review"])


class ReviewDecision(BaseModel):
    verdict: str          # "confirmed", "false_positive", "needs_escalation"
    notes: str = ""


@router.post("/submit/{analysis_id}", status_code=201)
async def submit_review(
    analysis_id: int,
    _user: dict = Depends(get_current_user),
):
    """Flag an analysis for human review."""
    review_id = await submit_for_review(analysis_id)
    logger.info("Review submitted analysis_id=%d review_id=%d by %s",
                analysis_id, review_id, _user["username"])
    return {"review_id": review_id, "status": "pending"}


@router.get("/queue")
async def list_queue(
    status: str = "pending",
    user: dict = Depends(require_role("analyst", "admin")),
):
    """List reviews by status. Requires analyst or admin role."""
    if status not in ("pending", "reviewed"):
        raise HTTPException(status_code=400, detail="status must be 'pending' or 'reviewed'")
    return await get_review_queue(status)


@router.post("/{review_id}/decision")
async def decide_review(
    review_id: int,
    decision: ReviewDecision,
    user: dict = Depends(require_role("analyst", "admin")),
):
    """Submit a verdict on a pending review."""
    valid_verdicts = {"confirmed", "false_positive", "needs_escalation"}
    if decision.verdict not in valid_verdicts:
        raise HTTPException(
            status_code=400,
            detail=f"verdict must be one of: {', '.join(valid_verdicts)}",
        )
    updated = await update_review(
        review_id, user["username"], decision.verdict, decision.notes
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Review not found or already reviewed")
    logger.info("Review %d decided: %s by %s", review_id, decision.verdict, user["username"])
    return {"review_id": review_id, "verdict": decision.verdict, "reviewer": user["username"]}


# ============= ACTIVE LEARNING FEEDBACK LOOP =============

import json
from pathlib import Path

class ActiveLearningQueue:
    """Manages low-confidence predictions and exports human-verified annotations back to dataset."""

    def __init__(self, queue_file: str = "data/active_learning_queue.json"):
        self.queue_path = Path(queue_file)
        self.queue_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.queue_path.exists():
            with open(self.queue_path, "w", encoding="utf-8") as f:
                json.dump([], f)

    def evaluate_and_queue(self, text: str, prediction: dict, threshold: float = 0.65) -> bool:
        """Automatically queue prediction if confidence is below threshold."""
        confidence = prediction.get("confidence", 1.0)
        if confidence < threshold:
            item = {
                "text": text,
                "predicted_label": prediction.get("classification"),
                "confidence": confidence,
                "probabilities": prediction.get("class_probabilities", {}),
                "queued_at": datetime.now(timezone.utc).isoformat(),
                "status": "pending_annotation",
                "verified_label": None,
            }
            with open(self.queue_path, "r+", encoding="utf-8") as f:
                data = json.load(f)
                data.append(item)
                f.seek(0)
                json.dump(data, f, indent=2)
                f.truncate()
            logger.info("Queued low-confidence (%.2f) item for human review", confidence)
            return True
        return False

    def export_reviewed_to_dataset(self, target_dataset_path: str = "datasets/full_3class_dataset.json") -> int:
        """Export human-verified samples into training dataset for continuous retraining."""
        if not self.queue_path.exists():
            return 0

        with open(self.queue_path, "r", encoding="utf-8") as f:
            queue = json.load(f)

        verified_items = [
            {"text": item["text"], "content_type": item["verified_label"], "platform": "human_review"}
            for item in queue
            if item.get("status") == "reviewed" and item.get("verified_label") in {"propaganda", "opinion", "neutral"}
        ]

        if not verified_items:
            return 0

        ds_path = Path(target_dataset_path)
        if ds_path.exists():
            with open(ds_path, "r+", encoding="utf-8") as f:
                dataset = json.load(f)
                dataset.extend(verified_items)
                f.seek(0)
                json.dump(dataset, f, indent=2)
                f.truncate()
        
        logger.info("Exported %d human-verified items to %s", len(verified_items), target_dataset_path)
        return len(verified_items)
