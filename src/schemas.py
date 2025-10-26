"""
Pydantic schemas for OpenReview Academic Paper Crawler.

This module defines data validation models using Pydantic for:
- Paper metadata and content
- Review data with ratings and feedback
- Comments and rebuttals
- Meta-reviews and decisions
- Complete paper records with all associated data

All models include proper type hints, validation, and JSON schema generation.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator


class Review(BaseModel):
    """Schema for individual paper reviews from OpenReview."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        json_schema_extra={
            "description": "A peer review containing ratings and detailed feedback"
        }
    )

    review_id: str = Field(..., description="Unique identifier for the review")
    invitation: Optional[str] = Field(None, description="OpenReview invitation string")
    rating: Optional[Union[str, float]] = Field(None, description="Review rating (e.g., '8: Accept', '6', 7.5)")
    confidence: Optional[Union[str, int]] = Field(None, description="Reviewer confidence level")
    summary: Optional[str] = Field(None, description="Brief summary of the review")
    soundness: Optional[str] = Field(None, description="Soundness evaluation")
    presentation: Optional[str] = Field(None, description="Presentation quality assessment")
    contribution: Optional[str] = Field(None, description="Contribution significance")
    strengths: Optional[str] = Field(None, description="Key strengths identified")
    weaknesses: Optional[str] = Field(None, description="Main weaknesses identified")
    questions: Optional[str] = Field(None, description="Questions for authors")
    limitations: Optional[str] = Field(None, description="Limitations noted")
    review_text: Optional[str] = Field(None, description="Full review content")

    @field_validator('rating')
    @classmethod
    def validate_rating(cls, v):
        """Validate and normalize rating values."""
        if v is None:
            return None

        # Convert to string for processing
        rating_str = str(v).strip()

        # Handle empty strings
        if not rating_str:
            return None

        # Try to extract numeric rating from formats like "8: Accept", "6", "7.5"
        if ':' in rating_str:
            # Extract the number before the colon
            try:
                numeric_part = rating_str.split(':')[0].strip()
                return float(numeric_part)
            except (ValueError, IndexError):
                return rating_str

        # Try to convert to float if it's a pure number
        try:
            return float(rating_str)
        except ValueError:
            # Keep as string if it contains non-numeric content
            return rating_str

    @field_validator('confidence')
    @classmethod
    def validate_confidence(cls, v):
        """Validate confidence values."""
        if v is None:
            return None

        confidence_str = str(v).strip()
        if not confidence_str:
            return None

        # Try to extract numeric confidence from formats like "4: High", "3"
        if ':' in confidence_str:
            try:
                numeric_part = confidence_str.split(':')[0].strip()
                return int(numeric_part)
            except (ValueError, IndexError):
                return confidence_str

        try:
            return int(float(confidence_str))
        except (ValueError, TypeError):
            return confidence_str


class Comment(BaseModel):
    """Schema for comments and rebuttals on papers."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        json_schema_extra={
            "description": "Comments, rebuttals, and discussions on papers"
        }
    )

    note_id: str = Field(..., description="Unique identifier for the comment")
    invitation: Optional[str] = Field(None, description="OpenReview invitation string")
    comment: Optional[str] = Field(None, description="Comment or rebuttal text")
    content: Dict[str, Any] = Field(default_factory=dict, description="Full content dictionary")

    @field_validator('comment')
    @classmethod
    def validate_comment(cls, v):
        """Ensure comment is a valid string or None."""
        if v is None:
            return None
        return str(v).strip() or None


class MetaReview(BaseModel):
    """Schema for meta-reviews and final decisions."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        json_schema_extra={
            "description": "Meta-reviews containing final decisions and justifications"
        }
    )

    id: str = Field(..., description="Unique identifier for the meta-review")
    decision: Optional[str] = Field(None, description="Final decision (Accept/Reject/etc.)")
    content: Dict[str, Any] = Field(default_factory=dict, description="Full content dictionary")

    @field_validator('decision')
    @classmethod
    def validate_decision(cls, v):
        """Validate and normalize decision values."""
        if v is None:
            return None

        decision_str = str(v).strip()
        if not decision_str:
            return None

        # Normalize common decision formats
        decision_lower = decision_str.lower()

        # Map common variations to standardized forms
        decision_mapping = {
            'accept': 'Accept',
            'accepted': 'Accept',
            'reject': 'Reject',
            'rejected': 'Reject',
            'oral': 'Accept (Oral)',
            'poster': 'Accept (Poster)',
            'spotlight': 'Accept (Spotlight)',
            'notable': 'Accept (Notable)',
            'top': 'Accept (Top)',
            'best': 'Accept (Best)',
            'desk reject': 'Desk Reject',
            'withdraw': 'Withdrawn',
            'withdrawn': 'Withdrawn'
        }

        # Check for exact matches first
        if decision_str in decision_mapping:
            return decision_mapping[decision_str]

        # Check for substring matches
        for key, value in decision_mapping.items():
            if key in decision_lower:
                return value

        # Return original if no mapping found
        return decision_str


class Paper(BaseModel):
    """Schema for complete paper records with all associated data."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        json_schema_extra={
            "description": "Complete paper record with metadata, reviews, and discussions"
        }
    )

    # Core paper identifiers
    paper_id: str = Field(..., description="Unique paper identifier")
    forum_id: str = Field(..., description="OpenReview forum identifier")

    # Basic metadata
    title: str = Field(..., description="Paper title")
    abstract: Optional[str] = Field(None, description="Paper abstract")
    authors: Optional[Union[str, List[str]]] = Field(None, description="Paper authors")
    keywords: Optional[Union[str, List[str]]] = Field(None, description="Paper keywords")

    # URLs
    pdf_url: Optional[str] = Field(None, description="Direct link to PDF")
    forum_url: Optional[str] = Field(None, description="OpenReview forum URL")

    # Review data
    reviews: List[Review] = Field(default_factory=list, description="List of peer reviews")
    num_reviews: int = Field(default=0, description="Number of reviews received")

    # Discussion data
    comments: List[Comment] = Field(default_factory=list, description="List of comments and rebuttals")
    meta_reviews: List[MetaReview] = Field(default_factory=list, description="List of meta-reviews")

    # Decision data
    decision: Optional[str] = Field(None, description="Final decision on the paper")

    @field_validator('authors')
    @classmethod
    def validate_authors(cls, v):
        """Validate and normalize authors field."""
        if v is None:
            return None
        elif isinstance(v, list):
            # Ensure all authors are strings
            return [str(author).strip() for author in v if author]
        else:
            # Convert string to list if comma-separated
            authors_str = str(v).strip()
            if ',' in authors_str:
                return [author.strip() for author in authors_str.split(',') if author.strip()]
            else:
                return [authors_str]

    @field_validator('paper_id')
    @classmethod
    def validate_paper_id(cls, v):
        """Validate that paper_id is not empty."""
        if not v or not v.strip():
            raise ValueError("paper_id cannot be empty")
        return v.strip()

    @field_validator('keywords')
    @classmethod
    def validate_keywords(cls, v):
        """Validate and normalize keywords field."""
        if v is None:
            return None
        elif isinstance(v, list):
            # Ensure all keywords are strings
            return [str(keyword).strip() for keyword in v if keyword]
        else:
            # Convert string to list if comma-separated
            keywords_str = str(v).strip()
            if ',' in keywords_str:
                return [kw.strip() for kw in keywords_str.split(',') if kw.strip()]
            else:
                return [keywords_str]

    @model_validator(mode='after')
    def validate_consistency(self):
        """Validate internal consistency of the paper data."""
        # Ensure num_reviews matches actual reviews count
        if len(self.reviews) != self.num_reviews:
            self.num_reviews = len(self.reviews)

        # If we have meta-reviews, try to extract decision if not set
        if not self.decision and self.meta_reviews:
            for meta_review in self.meta_reviews:
                if meta_review.decision:
                    self.decision = meta_review.decision
                    break

        return self

    @property
    def average_rating(self) -> Optional[float]:
        """Calculate average rating from all reviews."""
        ratings = []
        for review in self.reviews:
            if review.rating is not None:
                try:
                    # Convert to float if possible
                    rating_val = float(review.rating)
                    ratings.append(rating_val)
                except (ValueError, TypeError):
                    continue

        return round(sum(ratings) / len(ratings), 2) if ratings else None

    @property
    def has_reviews(self) -> bool:
        """Check if paper has any reviews."""
        return len(self.reviews) > 0

    @property
    def has_comments(self) -> bool:
        """Check if paper has any comments."""
        return len(self.comments) > 0

    def get_reviews_summary(self) -> Dict[str, Any]:
        """Get a summary of review statistics."""
        if not self.reviews:
            return {"total_reviews": 0, "average_rating": None}

        ratings = []
        confidences = []

        for review in self.reviews:
            if review.rating is not None:
                try:
                    ratings.append(float(review.rating))
                except (ValueError, TypeError):
                    pass

            if review.confidence is not None:
                try:
                    confidences.append(float(review.confidence))
                except (ValueError, TypeError):
                    pass

        return {
            "total_reviews": len(self.reviews),
            "average_rating": round(sum(ratings) / len(ratings), 2) if ratings else None,
            "average_confidence": round(sum(confidences) / len(confidences), 2) if confidences else None,
            "rating_range": (min(ratings), max(ratings)) if ratings else None
        }


class CrawlResult(BaseModel):
    """Schema for the complete result of a crawling operation."""

    model_config = ConfigDict(
        json_schema_extra={
            "description": "Complete crawling result with metadata and paper data"
        }
    )

    venue: str = Field(..., description="Conference venue (e.g., 'ICLR', 'NeurIPS')")
    year: int = Field(..., description="Conference year")
    accepted_only: bool = Field(..., description="Whether only accepted papers were crawled")
    total_papers: int = Field(..., description="Total number of papers crawled")
    crawled_at: datetime = Field(default_factory=datetime.now, description="When the crawl was performed")
    api_version: Optional[str] = Field(None, description="OpenReview API version used")
    papers: List[Paper] = Field(default_factory=list, description="List of crawled papers")

    @property
    def papers_with_reviews(self) -> int:
        """Count papers that have at least one review."""
        return sum(1 for paper in self.papers if paper.has_reviews)

    @property
    def total_reviews(self) -> int:
        """Total number of reviews across all papers."""
        return sum(len(paper.reviews) for paper in self.papers)

    @property
    def total_comments(self) -> int:
        """Total number of comments across all papers."""
        return sum(len(paper.comments) for paper in self.papers)

    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics about the crawl result."""
        if not self.papers:
            return {"error": "No papers in result"}

        # Calculate rating statistics
        all_ratings = []
        for paper in self.papers:
            for review in paper.reviews:
                if review.rating is not None:
                    try:
                        all_ratings.append(float(review.rating))
                    except (ValueError, TypeError):
                        continue

        # Decision breakdown
        decisions = {}
        for paper in self.papers:
            decision = paper.decision or "Unknown"
            decisions[decision] = decisions.get(decision, 0) + 1

        return {
            "venue": self.venue,
            "year": self.year,
            "accepted_only": self.accepted_only,
            "total_papers": self.total_papers,
            "papers_with_reviews": self.papers_with_reviews,
            "total_reviews": self.total_reviews,
            "total_comments": self.total_comments,
            "average_reviews_per_paper": round(self.total_reviews / self.total_papers, 2) if self.total_papers > 0 else 0,
            "average_rating": round(sum(all_ratings) / len(all_ratings), 2) if all_ratings else None,
            "rating_range": (min(all_ratings), max(all_ratings)) if all_ratings else None,
            "decision_breakdown": decisions,
            "crawled_at": self.crawled_at.isoformat()
        }


# Convenience functions for creating validated instances
def create_paper_from_dict(data: Dict[str, Any]) -> Paper:
    """Create a validated Paper instance from a dictionary."""
    return Paper.model_validate(data)


def create_review_from_dict(data: Dict[str, Any]) -> Review:
    """Create a validated Review instance from a dictionary."""
    return Review.model_validate(data)


def create_comment_from_dict(data: Dict[str, Any]) -> Comment:
    """Create a validated Comment instance from a dictionary."""
    return Comment.model_validate(data)


def create_crawl_result(venue: str, year: int, papers: List[Dict[str, Any]],
                       accepted_only: bool = False, api_version: Optional[str] = None) -> CrawlResult:
    """Create a validated CrawlResult instance."""
    # Convert paper dictionaries to Paper objects
    paper_objects = [create_paper_from_dict(paper) for paper in papers]

    return CrawlResult(
        venue=venue,
        year=year,
        accepted_only=accepted_only,
        total_papers=len(paper_objects),
        api_version=api_version,
        papers=paper_objects
    )