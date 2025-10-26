# Install: pip install openreview-py pandas

import openreview
import pandas as pd
import json
import time
from typing import List, Dict
import os
import dotenv
from datetime import datetime
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.utils.logger import get_logger, log_crawl_start, log_crawl_progress, log_crawl_complete, log_error_with_context
from src.schemas import Paper, Review, Comment, MetaReview, CrawlResult, create_paper_from_dict, create_crawl_result
from pydantic import ValidationError

dotenv.load_dotenv()

# Get logger for this module
logger = get_logger(__name__)


def get_openreview_client():
    """
    Attempts to create an OpenReview client using API v2, falling back to API v1 if v2 fails.

    This function tries to initialize an OpenReview client with the v2 API endpoint. If that raises an exception,
    it falls back to the v1 API. It uses environment variables OPENREVIEW_USERNAME and OPENREVIEW_PASSWORD for authentication.

    Returns:
        tuple: A tuple containing the OpenReview client object and a string indicating the API version ('v2' or 'v1').
    """
    # Try API v2 first, fall back to v1
    try:
        client = openreview.api.OpenReviewClient(baseurl='https://api2.openreview.net',
                                                 username=os.getenv("OPENREVIEW_USERNAME"),
    password=os.getenv("OPENREVIEW_PASSWORD"))
        logger.info("Using OpenReview API v2")
        return client, 'v2'
    except:
        client = openreview.Client(
    baseurl='https://api.openreview.net',
    username=os.getenv("OPENREVIEW_USERNAME"),
    password=os.getenv("OPENREVIEW_PASSWORD")
)
        logger.info("Using OpenReview API v1")
        return client, 'v1'


def is_accepted_paper(decision):
    """
    Determine if a paper is accepted based on its decision
    
    Args:
        decision: The decision string from the meta review
        
    Returns:
        bool: True if the paper is accepted
    """
    if not decision:
        return False
    
    decision_lower = str(decision).lower()
    
    # Common acceptance indicators for ICLR
    accepted_keywords = [
        'accept', 'oral', 'poster', 'spotlight', 'notable', 'top', 'best'
    ]
    
    # Reject indicators to be sure
    rejected_keywords = [
        'reject', 'desk reject', 'withdraw'
    ]
    
    # Check for rejection first
    for reject_word in rejected_keywords:
        if reject_word in decision_lower:
            return False
    
    # Check for acceptance
    for accept_word in accepted_keywords:
        if accept_word in decision_lower:
            return True
    
    return False


def crawl_iclr_papers_and_reviews(year: int, accepted_only: bool = False, limit: int = None):
    """
    Crawl papers and reviews from ICLR conference
    
    Args:
        year: Conference year (e.g., 2024, 2023, 2022)
        accepted_only: If True, only return accepted papers
        limit: Maximum number of papers to crawl (None for all papers)
    """
    client, api_version = get_openreview_client()
    
    # Try different invitation patterns
    patterns = [
        f'ICLR.cc/{year}/Conference/-/Submission',
        f'ICLR.cc/{year}/Conference/-/Blind_Submission',
    ]
    
    submissions = []
    used_pattern = None
    
    for pattern in patterns:
        logger.debug(f"Trying pattern: {pattern}")
        try:
            if api_version == 'v2':
                submissions = list(client.get_all_notes(invitation=pattern))
            else:
                submissions = client.get_all_notes(invitation=pattern)
            
            if submissions and len(submissions) > 0:
                used_pattern = pattern
                logger.info(f"✓ Found {len(submissions)} papers with pattern: {pattern}")
                break
            else:
                logger.debug(f"No papers found with this pattern")
        except Exception as e:
            logger.warning(f"Error trying pattern {pattern}: {e}")
    
    if not submissions or len(submissions) == 0:
        logger.error("Could not find papers. Possible reasons:")
        logger.error(f"  1. ICLR {year} papers may not be published yet on OpenReview")
        logger.error(f"  2. The venue uses a different invitation format")
        logger.error(f"Try visiting: https://openreview.net/group?id=ICLR.cc/{year}/Conference")
        logger.error(f"Or try a different year like {year-1} or {year-2}")
        return []
    
    logger.info(f"Processing {len(submissions)} papers from {used_pattern}")
    
    valid_papers: List[Paper] = []
    invalid_papers: List[Dict[str, str]] = []
    
    for i, paper in enumerate(submissions, 1):
        title = paper.content.get('title', {})
        if isinstance(title, dict):
            title = title.get('value', 'No title')
        
        log_crawl_progress(i, len(submissions), str(title)[:60])
        
        # Extract paper information (handle both v1 and v2 formats)
        def get_value(content_dict, key):
            val = content_dict.get(key, '')
            if isinstance(val, dict):
                return val.get('value', '')
            return val
        
        paper_data = {
            'paper_id': paper.id,
            'forum_id': paper.forum if hasattr(paper, 'forum') else paper.id,
            'title': str(title),
            'abstract': get_value(paper.content, 'abstract'),
            'authors': get_value(paper.content, 'authors'),
            'keywords': get_value(paper.content, 'keywords'),
            'pdf_url': f"https://openreview.net/pdf?id={paper.forum if hasattr(paper, 'forum') else paper.id}",
            'forum_url': f"https://openreview.net/forum?id={paper.forum if hasattr(paper, 'forum') else paper.id}",
        }
        
        # Get all notes for this paper (reviews, comments, etc.)
        forum_id = paper.forum if hasattr(paper, 'forum') else paper.id
        
        try:
            if api_version == 'v2':
                notes = list(client.get_all_notes(forum=forum_id))
            else:
                notes = client.get_all_notes(forum=forum_id)
            
            reviews = []
            comments = []
            meta_reviews = []
            decision = None
            
            for note in notes:
                # Skip the submission itself
                if note.id == paper.id:
                    continue
                
                invitation = note.invitation if hasattr(note, 'invitation') else ''
                invitation_lower = str(invitation).lower()
                
                # DEBUG: Print invitation patterns we're seeing
                if i <= 3:  # Only for first few papers to avoid spam
                    logger.debug(f"Note content keys: {list(note.content.keys())[:5]}")  # First 5 keys
                
                # Extract content
                def extract_content(note):
                    content = {}
                    for key, val in note.content.items():
                        if isinstance(val, dict) and 'value' in val:
                            content[key] = val['value']
                        else:
                            content[key] = val
                    return content
                
                note_content = extract_content(note)
                
                # Categorize the note based on content rather than invitation
                # Check if this looks like a review
                if any(key in note_content for key in ['rating', 'confidence', 'review', 'recommendation']):
                    review_data = {
                        'review_id': note.id,
                        'invitation': invitation,
                        'rating': note_content.get('rating', note_content.get('recommendation', '')),
                        'confidence': note_content.get('confidence', ''),
                        'summary': note_content.get('summary', ''),
                        'soundness': note_content.get('soundness', ''),
                        'presentation': note_content.get('presentation', ''),
                        'contribution': note_content.get('contribution', ''),
                        'strengths': note_content.get('strengths', ''),
                        'weaknesses': note_content.get('weaknesses', ''),
                        'questions': note_content.get('questions', ''),
                        'limitations': note_content.get('limitations', ''),
                        'review_text': note_content.get('review', ''),
                    }
                    reviews.append(review_data)
                    
                # Check if this looks like a decision/meta-review
                elif any(key in note_content for key in ['decision', 'recommendation']) and 'rating' not in note_content:
                    decision = note_content.get('decision', note_content.get('recommendation', ''))
                    meta_reviews.append({
                        'id': note.id,
                        'decision': decision,
                        'content': note_content
                    })
                    
                # Check if this looks like a comment
                elif any(key in note_content for key in ['comment', 'rebuttal']):
                    comments.append({
                        'note_id': note.id,
                        'invitation': invitation,
                        'comment': note_content.get('comment', note_content.get('rebuttal', '')),
                        'content': note_content
                    })
            
            paper_data['reviews'] = reviews
            paper_data['num_reviews'] = len(reviews)
            paper_data['meta_reviews'] = meta_reviews
            paper_data['decision'] = decision
            paper_data['comments'] = comments
            
            logger.info(f"Found {len(reviews)} reviews, {len(comments)} comments, decision: {decision}")
            
            # Validate and create Paper object using Pydantic schema
            try:
                paper_obj = create_paper_from_dict(paper_data)
                logger.debug(f"✓ Paper validated: {paper_obj.title[:50]}...")
            except (ValidationError, Exception) as e:
                log_error_with_context(e, f"validating paper {paper.id}")
                invalid_papers.append({
                    "paper_id": paper.id,
                    "forum_id": paper_data.get("forum_id"),
                    "title": str(title),
                    "error": str(e)
                })
                continue
            
        except Exception as e:
            log_error_with_context(e, f"fetching notes for paper {paper.id}")
            paper_data['reviews'] = []
            paper_data['num_reviews'] = 0
            paper_data['meta_reviews'] = []
            paper_data['decision'] = None
            paper_data['comments'] = []
            invalid_papers.append({
                "paper_id": paper.id,
                "forum_id": paper_data.get("forum_id"),
                "title": str(title),
                "error": str(e)
            })
            continue
        
        # Filter for accepted papers if requested
        if accepted_only:
            if is_accepted_paper(paper_obj.decision):
                valid_papers.append(paper_obj)
                logger.debug(f"Accepted paper included: {title[:50]}...")
            else:
                logger.debug(f"Rejected/withdrawn paper skipped: {title[:50]}...")
        else:
            valid_papers.append(paper_obj)
        
        # Rate limiting
        time.sleep(0.3)
        
        # Check if we've reached the limit
        if limit and len(valid_papers) >= limit:
            logger.info(f"\n✓ Reached limit of {limit} papers. Stopping crawl.")
            break
    
    if invalid_papers:
        logger.warning(f"Skipped {len(invalid_papers)} papers due to validation errors or fetch issues.")
        logger.debug(f"Skipped paper details: {invalid_papers}")
    
    return valid_papers


def save_data(data: List, year: int, accepted_only: bool = False):
    """Save crawled data to JSON and CSV files
    
    Args:
        data: List of Paper objects or dictionaries
        year: Conference year
        accepted_only: Whether only accepted papers were crawled
    """
    
    if not data:
        logger.warning("No data to save!")
        return None
    
    # Create CrawlResult object for structured data
    try:
        crawl_result = create_crawl_result(
            venue="ICLR",
            year=year,
            accepted_only=accepted_only,
            papers=data
        )
        logger.info("✓ Created validated CrawlResult object")
    except Exception as e:
        log_error_with_context(e, "creating CrawlResult object")
        # Fall back to raw data
        crawl_result = None
    
    # Determine filename suffix
    suffix = "_accepted" if accepted_only else ""
    
    # Save complete data as JSON
    json_filename = f'iclr_{year}_papers_reviews{suffix}.json'
    
    if crawl_result:
        # Save validated CrawlResult
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(crawl_result.model_dump(), f, indent=2, ensure_ascii=False, default=str)
        logger.info(f"Saved validated CrawlResult to {json_filename}")
        papers_data = crawl_result.papers
    else:
        # Fall back to raw data
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        logger.info(f"Saved raw data to {json_filename}")
        papers_data = data
    
    # Create a flattened version for CSV
    csv_data = []
    for paper in papers_data:
        # Handle both Paper objects and dictionaries
        if hasattr(paper, 'model_dump'):
            # It's a Paper object
            paper_dict = paper.model_dump()
        else:
            # It's a raw dictionary
            paper_dict = paper
        
        # Calculate average rating if reviews exist
        ratings = []
        for review in paper_dict.get('reviews', []):
            if hasattr(review, 'model_dump'):
                review_dict = review.model_dump()
            else:
                review_dict = review
            
            rating_str = str(review_dict.get('rating', ''))
            if rating_str:
                # Extract number from rating (various formats)
                try:
                    # Handle formats like "6: Weak Accept", "6", "6.0", etc.
                    rating_clean = rating_str.split(':')[0].strip()
                    rating_num = float(rating_clean)
                    ratings.append(rating_num)
                except:
                    pass
        
        avg_rating = round(sum(ratings) / len(ratings), 2) if ratings else None
        
        authors = paper_dict.get('authors', [])
        if isinstance(authors, list):
            authors_str = ', '.join([str(a) for a in authors])
        else:
            authors_str = str(authors)
        
        keywords = paper_dict.get('keywords', [])
        if isinstance(keywords, list):
            keywords_str = ', '.join([str(k) for k in keywords])
        else:
            keywords_str = str(keywords)
        
        csv_data.append({
            'paper_id': paper_dict['paper_id'],
            'title': paper_dict['title'],
            'authors': authors_str,
            'num_reviews': paper_dict.get('num_reviews', len(paper_dict.get('reviews', []))),
            'avg_rating': avg_rating,
            'decision': paper_dict.get('decision', ''),
            'keywords': keywords_str,
            'forum_url': paper_dict.get('forum_url', '')
        })
    
    # Save as CSV
    df = pd.DataFrame(csv_data)
    csv_filename = f'iclr_{year}_papers_summary{suffix}.csv'
    df.to_csv(csv_filename, index=False, encoding='utf-8')
    logger.info(f"Saved summary to {csv_filename}")

    return df, crawl_result


# Main execution
if __name__ == "__main__":
    # Choose the year you want to crawl
    YEAR = 2024  
    ACCEPTED_ONLY = False  # Set to True to only crawl accepted papers
    LIMIT = 50  # Limit to first 50 papers
    
    print(f"{'='*60}")
    print(f"ICLR {YEAR} Paper & Review Crawler")
    if ACCEPTED_ONLY:
        print("Mode: ACCEPTED PAPERS ONLY")
    else:
        print("Mode: ALL PAPERS")
    if LIMIT:
        print(f"Limit: First {LIMIT} papers")
    # Log the start of crawling
    log_crawl_start("ICLR", YEAR)

    # Crawl the data
    data = crawl_iclr_papers_and_reviews(YEAR, accepted_only=ACCEPTED_ONLY, limit=LIMIT)
    
    if not data:
        print("\nNo data collected. Try a different year.")
        exit(1)
    
    # Save to files
    df, crawl_result = save_data(data, YEAR, accepted_only=ACCEPTED_ONLY)
    
    if df is not None and len(df) > 0:
        # Display summary statistics
        print(f"\n{'='*60}")
        print(f"Summary Statistics for ICLR {YEAR}")
        print(f"{'='*60}")
        
        if crawl_result:
            # Use CrawlResult statistics
            stats = crawl_result.get_statistics()
            print(f"Total papers: {stats['total_papers']}")
            print(f"Papers with reviews: {stats['papers_with_reviews']}")
            print(f"Total reviews: {stats['total_reviews']}")
            print(f"Total comments: {stats['total_comments']}")
            print(f"Average reviews per paper: {stats['average_reviews_per_paper']:.2f}")
            if stats['average_rating'] is not None:
                print(f"Average rating: {stats['average_rating']:.2f}")
                print(f"Rating range: {stats['rating_range']}")
            
            if stats['decision_breakdown']:
                print(f"\nDecision breakdown:")
                for decision, count in stats['decision_breakdown'].items():
                    print(f"  {decision}: {count}")
        else:
            # Fallback to basic statistics
            print(f"Total papers: {len(data)}")
            print(f"Papers with reviews: {df['num_reviews'].gt(0).sum()}")
            print(f"Average reviews per paper: {df['num_reviews'].mean():.2f}")
            if df['avg_rating'].notna().any():
                print(f"Average rating: {df['avg_rating'].mean():.2f}")
            
            # Decision breakdown
            if 'decision' in df.columns and df['decision'].notna().any():
                print(f"\nDecision breakdown:")
                print(df['decision'].value_counts())
        
