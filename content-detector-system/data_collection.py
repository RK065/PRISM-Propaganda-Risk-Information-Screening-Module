"""
Data Collection & Labeling Framework
Tools for gathering, annotating, and managing training datasets
"""

import json
import csv
import os
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Literal
from datetime import datetime, timezone
from pathlib import Path
import uuid

# Hardcoded base — never constructed from user input
_BASE_DIR: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), "datasets")


# ============= DATA STRUCTURES =============

@dataclass
class AnnotatedContent:
    """Single annotated piece of content for training/validation"""
    
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    text: str = ""
    source_url: Optional[str] = None
    platform: Literal["twitter", "instagram", "youtube", "facebook", "reddit", 
                      "whatsapp", "news", "unknown"] = "unknown"
    author: Optional[str] = None
    
    # Labels
    content_type: Literal["propaganda", "opinion", "neutral"] = "neutral"
    
    # Confidence
    annotator_confidence: float = 0.8  # How confident is the annotator (0-1)
    annotations_count: int = 1  # Number of independent annotations
    
    # Metadata
    has_disclosure: bool = False
    has_cta: bool = False
    contains_misinformation: bool = False
    risk_level: Literal["low", "medium", "high"] = "low"
    
    # Tracking
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    notes: str = ""
    tags: List[str] = field(default_factory=list)


@dataclass
class DatasetSplit:
    """Dataset split for train/validation/test"""
    
    name: str
    items: List[AnnotatedContent] = field(default_factory=list)
    split_type: Literal["train", "validation", "test"] = "train"
    
    def size(self) -> int:
        return len(self.items)
    
    def class_distribution(self) -> dict:
        """Get class distribution in this split"""
        distribution = {}
        for item in self.items:
            cls = item.content_type
            distribution[cls] = distribution.get(cls, 0) + 1
        return distribution


class DatasetBuilder:
    """Build and manage datasets for training/validation"""

    # Map of allowed split suffixes to fixed filenames — no user input in path
    _SPLIT_FILES = {
        "train": "train.json",
        "validation": "validation.json",
        "test": "test.json",
    }

    def __init__(self, dataset_name: str = "content_detector"):
        self.dataset_name = dataset_name  # kept for display only
        self._dir_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, dataset_name))
        self._dir = os.path.join(_BASE_DIR, self._dir_id)
        os.makedirs(self._dir, exist_ok=True)
        # Write human-readable name to a metadata file
        with open(os.path.join(self._dir, "name.txt"), "w") as _f:
            _f.write(dataset_name)
        self.items: List[AnnotatedContent] = []

    def add_item(self, item: AnnotatedContent) -> None:
        """Add single annotated item"""
        self.items.append(item)

    def add_items_from_file(self, file_path: str, format: str = "json") -> None:
        """Load items from a file inside the dataset directory (filename only, no paths)"""
        _fname = "data.json" if format == "json" else "data.csv"
        _full = os.path.join(self._dir, _fname)
        if format == "json":
            with open(_full, 'r') as f:
                data = json.load(f)
                if isinstance(data, list):
                    self.items.extend(AnnotatedContent(**d) for d in data)
        elif format == "csv":
            with open(_full, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    for key in ['has_disclosure', 'has_cta', 'contains_misinformation']:
                        if key in row:
                            row[key] = row[key].lower() == 'true'
                    self.items.append(AnnotatedContent(**row))

    def create_splits(self, train_ratio: float = 0.7,
                     val_ratio: float = 0.15,
                     test_ratio: float = 0.15) -> dict:
        """Split dataset into train/validation/test"""
        import random
        random.shuffle(self.items)
        total = len(self.items)
        train_size = int(total * train_ratio)
        val_size = int(total * val_ratio)
        return {
            'train': DatasetSplit('train', self.items[:train_size], 'train'),
            'validation': DatasetSplit('validation',
                                      self.items[train_size:train_size + val_size],
                                      'validation'),
            'test': DatasetSplit('test', self.items[train_size + val_size:], 'test'),
        }

    def save_dataset(self, format: str = "json") -> None:
        """Save dataset to file"""
        _fname = "dataset.json" if format == "json" else "dataset.csv"
        _out = os.path.join(self._dir, _fname)
        if format == "json":
            with open(_out, 'w') as f:
                json.dump([asdict(item) for item in self.items], f, indent=2)
        elif format == "csv":
            if not self.items:
                return
            with open(_out, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=asdict(self.items[0]).keys())
                writer.writeheader()
                for item in self.items:
                    writer.writerow(asdict(item))
        print(f"Dataset saved to {_out}")

    def save_splits(self, splits: dict, format: str = "json") -> None:
        """Save train/val/test splits using fixed filenames"""
        for split_name, split in splits.items():
            _fname = self._SPLIT_FILES.get(split_name, "other.json")
            _out = os.path.join(self._dir, _fname)
            if format == "json":
                with open(_out, 'w') as f:
                    json.dump([asdict(item) for item in split.items], f, indent=2)
            print(f"Saved {split_name} split ({split.size()} items) to {_out}")
    
    def get_statistics(self) -> dict:
        """Get dataset statistics"""
        
        if not self.items:
            return {"total": 0}
        
        stats = {
            "total": len(self.items),
            "class_distribution": {},
            "promotion_types": {},
            "platforms": {},
            "has_disclosure": sum(1 for i in self.items if i.has_disclosure),
            "has_misinformation": sum(1 for i in self.items if i.contains_misinformation),
            "risk_distribution": {}
        }
        
        for item in self.items:
            # Class distribution
            cls = item.content_type
            stats["class_distribution"][cls] = stats["class_distribution"].get(cls, 0) + 1
            
            # Promotion types
            if item.promotion_type:
                ptype = item.promotion_type
                stats["promotion_types"][ptype] = stats["promotion_types"].get(ptype, 0) + 1
            
            # Platforms
            plat = item.platform
            stats["platforms"][plat] = stats["platforms"].get(plat, 0) + 1
            
            # Risk distribution
            risk = item.risk_level
            stats["risk_distribution"][risk] = stats["risk_distribution"].get(risk, 0) + 1
        
        return stats
    
    def print_statistics(self) -> None:
        """Print formatted statistics"""
        stats = self.get_statistics()
        
        print("\n" + "="*60)
        print(f"DATASET STATISTICS: {self.dataset_name}")
        print("="*60)
        print(f"Total Items: {stats.get('total', 0)}")
        
        print("\nClass Distribution:")
        for cls, count in stats.get("class_distribution", {}).items():
            pct = (count / stats['total'] * 100) if stats['total'] > 0 else 0
            print(f"  {cls}: {count} ({pct:.1f}%)")
        
        print("\nPromotion Types:")
        for ptype, count in stats.get("promotion_types", {}).items():
            pct = (count / stats['total'] * 100) if stats['total'] > 0 else 0
            print(f"  {ptype}: {count} ({pct:.1f}%)")
        
        print("\nPlatforms:")
        for plat, count in stats.get("platforms", {}).items():
            pct = (count / stats['total'] * 100) if stats['total'] > 0 else 0
            print(f"  {plat}: {count} ({pct:.1f}%)")
        
        print("\nRisk Levels:")
        for risk, count in stats.get("risk_distribution", {}).items():
            pct = (count / stats['total'] * 100) if stats['total'] > 0 else 0
            print(f"  {risk}: {count} ({pct:.1f}%)")
        
        print(f"\nContent with Disclosures: {stats.get('has_disclosure', 0)}")
        print(f"Content with Misinformation: {stats.get('has_misinformation', 0)}")
        print("="*60 + "\n")


# ============= SAMPLE DATA COLLECTION =============

class SampleDataCollection:
    """Pre-built sample dataset for immediate testing"""
    
    @staticmethod
    def get_propaganda_samples() -> List[AnnotatedContent]:
        """Get labeled propaganda examples"""
        return [
            AnnotatedContent(
                text="WAKE UP!!! They're DESTROYING our country! Everyone must see this TRUTH before they silence us!!!",
                platform="twitter",
                content_type="propaganda",
                has_disclosure=False,
                has_cta=False,
                risk_level="high",
                annotator_confidence=0.95,
                tags=["emotional_language", "all_caps", "fear_mongering"]
            ),
            AnnotatedContent(
                text="The government is hiding this from you. Forward this message to everyone you know NOW!",
                platform="whatsapp",
                content_type="propaganda",
                has_disclosure=False,
                has_cta=True,
                risk_level="high",
                annotator_confidence=0.9,
                tags=["conspiracy", "urgency", "chain_message"]
            ),
            AnnotatedContent(
                text="Mainstream media doesn't want you to know about this. They're all lies! Only we tell the truth.",
                platform="twitter",
                content_type="propaganda",
                has_disclosure=False,
                risk_level="high",
                annotator_confidence=0.85,
                tags=["media_distrust", "us_vs_them"]
            ),
        ]
    
    @staticmethod
    def get_campaign_samples() -> List[AnnotatedContent]:
        """Get labeled paid campaign examples"""
        return [
            AnnotatedContent(
                text="OMG obsessed with this skincare! 🌸 Use code GLOW20 for 20% off! Link in bio #ad #sponsored #gifted",
                platform="instagram",
                content_type="paid_campaign",
                promotion_type="influencer_ad",
                has_disclosure=True,
                has_cta=True,
                risk_level="low",
                annotator_confidence=0.98,
                tags=["influencer_ad", "disclosure_present", "discount_code"]
            ),
            AnnotatedContent(
                text="This video is brought to you by NordVPN. Use code TECH50 for 50% off. Link in the description!",
                platform="youtube",
                content_type="paid_campaign",
                promotion_type="sponsored_content",
                has_disclosure=True,
                has_cta=True,
                risk_level="low",
                annotator_confidence=0.95,
                tags=["youtube_sponsorship", "disclosure_present"]
            ),
            AnnotatedContent(
                text="Just found this amazing deal online! Use my affiliate code REF123 and we both save money!",
                platform="reddit",
                content_type="paid_campaign",
                promotion_type="affiliate",
                has_disclosure=False,
                has_cta=True,
                risk_level="medium",
                annotator_confidence=0.8,
                tags=["affiliate", "undisclosed_benefit"]
            ),
        ]
    
    @staticmethod
    def get_neutral_samples() -> List[AnnotatedContent]:
        """Get labeled neutral examples"""
        return [
            AnnotatedContent(
                text="Just finished reading an interesting article about climate science. The data shows warming trends.",
                platform="twitter",
                content_type="neutral",
                has_disclosure=False,
                has_cta=False,
                risk_level="low",
                annotator_confidence=0.98,
                tags=["informational", "factual"]
            ),
            AnnotatedContent(
                text="Had a great day at the beach with friends. Beautiful weather and good company!",
                platform="instagram",
                content_type="neutral",
                has_disclosure=False,
                has_cta=False,
                risk_level="low",
                annotator_confidence=0.99,
                tags=["personal_post", "casual"]
            ),
            AnnotatedContent(
                text="Our team just released version 2.0 of our open-source project. Check out the new features.",
                platform="twitter",
                content_type="neutral",
                has_disclosure=False,
                has_cta=True,
                risk_level="low",
                annotator_confidence=0.9,
                tags=["product_announcement", "informational"]
            ),
        ]
    
    @staticmethod
    def get_mixed_samples() -> List[AnnotatedContent]:
        """Get labeled mixed examples"""
        return [
            AnnotatedContent(
                text="INCREDIBLE EXCLUSIVE DEAL!!! Don't miss this LIMITED TIME offer! Use code SAVE50! Everyone must see this! #ad #exclusive",
                platform="instagram",
                content_type="mixed",
                promotion_type="brand_campaign",
                has_disclosure=True,
                has_cta=True,
                risk_level="medium",
                annotator_confidence=0.85,
                tags=["emotional_marketing", "urgency", "disclosure"]
            ),
        ]


# ============= DATA COLLECTION GUIDE =============

class DataCollectionGuide:
    """Step-by-step guide for collecting labeled data"""
    
    @staticmethod
    def print_guide():
        guide = """
╔════════════════════════════════════════════════════════════════════╗
║         DATA COLLECTION & LABELING GUIDE                          ║
╚════════════════════════════════════════════════════════════════════╝

1. COLLECT SOURCES
   ├─ Twitter/X: Use API or web scraping
   ├─ Instagram: Manual collection from public accounts
   ├─ YouTube: Comments and video descriptions
   ├─ Reddit: Subreddit API or web scraping
   ├─ WhatsApp: Forward chains collected from users
   └─ News Sites: Articles and comments

2. INITIAL LABELING
   
   PROPAGANDA (High Risk)
   └─ Labels: "propaganda"
     └─ Characteristics:
        ├─ Emotional/fear-based language
        ├─ Polarizing (us vs. them)
        ├─ Exaggerated claims
        ├─ Calls for action ("SHARE NOW", "SPREAD THIS")
        └─ Lack of sources or credibility
   
   PAID CAMPAIGNS (Medium Risk)
   └─ Labels: "paid_campaign"
     └─ Sub-types:
        ├─ "influencer_ad": Gifted/sponsored influencer posts
        ├─ "brand_campaign": Official brand promotions
        ├─ "affiliate": Referral/commission-based
        ├─ "sponsored_content": Labeled partnerships
        └─ "undisclosed_ad": Paid without disclosure
   
   NEUTRAL (Low Risk)
   └─ Labels: "neutral"
     └─ Characteristics:
        ├─ Factual information
        ├─ Balanced perspective
        ├─ Clear sources
        ├─ Personal/casual posts
        └─ No promotional intent
   
   MIXED (Variable Risk)
   └─ Labels: "mixed"
     └─ Contains elements of both propaganda + paid campaign

3. ANNOTATION FIELDS
   
   Required:
   ├─ text: The content to classify
   ├─ platform: Where it came from
   ├─ content_type: Primary classification
   └─ risk_level: low/medium/high
   
   Optional but Recommended:
   ├─ promotion_type: For paid campaigns
   ├─ has_disclosure: Advertising labels present?
   ├─ has_cta: Call-to-action present?
   ├─ contains_misinformation: False claims?
   ├─ annotator_confidence: Your confidence (0-1)
   └─ tags: Keywords describing content

4. QUALITY CONTROL
   
   Single Annotation:
   ├─ Use if: Limited resources, trusted annotator
   └─ Risk: Single perspective bias
   
   Multi-Annotation (Recommended):
   ├─ Use if: High accuracy needed
   ├─ Process:
   │  ├─ Have 2-3 people label same content
   │  ├─ Calculate inter-annotator agreement (Cohen's Kappa)
   │  ├─ Resolve disagreements through discussion
   │  └─ Update labels with consensus
   └─ Target: >0.8 agreement score
   
   Validation Against System:
   ├─ Run system on labeled data
   ├─ Compare predictions vs. labels
   └─ Calculate accuracy metrics

5. ANNOTATION TIPS
   
   ✓ DO:
   ├─ Label the primary purpose of content
   ├─ Consider context and platform norms
   ├─ Note when you're uncertain (confidence < 0.8)
   ├─ Add tags for specific features you notice
   └─ Review confusing cases as a team
   
   ✗ DON'T:
   ├─ Confuse personal opinion with classification
   ├─ Miss subtle indicators (influencer hashtags, links)
   ├─ Ignore platform-specific conventions
   ├─ Over-label as propaganda (strong opinions ≠ propaganda)
   └─ Force labels when uncertain

6. DATASET TARGETS
   
   Minimum for Validation:
   ├─ Propaganda: 50 examples
   ├─ Paid Campaigns: 50 examples
   ├─ Neutral: 50 examples
   └─ Mixed: 20 examples
   └─ TOTAL: ~170 items
   
   Good Dataset:
   ├─ Propaganda: 200+ examples
   ├─ Paid Campaigns: 200+ examples
   ├─ Neutral: 200+ examples
   ├─ Mixed: 100+ examples
   └─ TOTAL: ~700 items
   
   Excellent Dataset:
   ├─ Each class: 500+ examples
   ├─ Multi-platform distribution
   ├─ Multiple annotators
   └─ TOTAL: 2000+ items

7. DATASET SPLIT STRATEGY
   
   Standard 70-15-15:
   ├─ Training: 70% (for model improvement)
   ├─ Validation: 15% (for hyperparameter tuning)
   └─ Test: 15% (for final accuracy measurement)
   
   Balanced Splits:
   └─ Each split should have same class distribution
      ├─ ~35% Propaganda
      ├─ ~35% Paid Campaigns
      ├─ ~25% Neutral
      └─ ~5% Mixed
"""
        print(guide)


# ============= EXAMPLE USAGE =============

if __name__ == "__main__":
    print("="*60)
    print("SETTING UP SAMPLE DATASET")
    print("="*60)
    
    # Create dataset builder
    builder = DatasetBuilder("content_detector_v1")
    
    # Add sample data
    samples = SampleDataCollection()
    for item in samples.get_propaganda_samples():
        builder.add_item(item)
    for item in samples.get_campaign_samples():
        builder.add_item(item)
    for item in samples.get_neutral_samples():
        builder.add_item(item)
    for item in samples.get_mixed_samples():
        builder.add_item(item)
    
    # Print statistics
    builder.print_statistics()
    
    # Create splits
    splits = builder.create_splits(train_ratio=0.7, val_ratio=0.15, test_ratio=0.15)
    
    # Save dataset
    builder.save_dataset(format="json")
    builder.save_dataset(format="csv")
    builder.save_splits(splits, format="json")
    
    # Print guide
    print("\n")
    DataCollectionGuide.print_guide()
    
    print("\nDataset files created in: datasets/content_detector_v1/")
