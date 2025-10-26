"""
Simple script to crawl first 50 ICLR papers with all information
"""

import openreview
import json
import time
from datetime import datetime
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def get_client():
    """Get OpenReview client"""
    try:
        # Try API v2
        client = openreview.api.OpenReviewClient(
            baseurl='https://api2.openreview.net'
        )
        print("✓ Connected to OpenReview API v2")
        return client, 'v2'
    except:
        # Fallback to API v1
        client = openreview.Client(
            baseurl='https://api.openreview.net'
        )
        print("✓ Connected to OpenReview API v1")
        return client, 'v1'


def extract_value(content, key):
    """Extract value from content dict (handles both v1 and v2 formats)"""
    val = content.get(key, '')
    if isinstance(val, dict):
        return val.get('value', '')
    return val


def crawl_first_50_papers(year=2024, limit=500):
    """
    Crawl first 50 papers from ICLR with all information

    Args:
        year: ICLR year (default: 2024)
        limit: Number of papers to crawl (default: 50)
    """
    print(f"\n{'='*70}")
    print(f"Crawling first {limit} papers from ICLR {year}")
    print(f"{'='*70}\n")

    client, api_version = get_client()

    venue_id = f"ICLR.cc/{year}/Conference"

    # Try different submission patterns
    submission_names = ['Submission', 'Blind_Submission']

    submissions = []
    for submission_name in submission_names:
        print(f"Trying submission name: {submission_name}")
        try:
            invitation = f"{venue_id}/-/{submission_name}"
            if api_version == 'v2':
                # Use details='replies' to get all replies (reviews, comments, decisions, rebuttals) in one call
                submissions = list(client.get_all_notes(invitation=invitation, details='replies'))
            else:
                submissions = client.get_all_notes(invitation=invitation)

            if submissions and len(submissions) > 0:
                print(f"✓ Found {len(submissions)} papers\n")
                break
        except Exception as e:
            print(f"  Error: {e}")
            continue

    if not submissions:
        print(f"\n✗ No papers found for ICLR {year}")
        print(f"Try visiting: https://openreview.net/group?id={venue_id}")
        return []

    # Limit to first N papers
    submissions = submissions[:limit]
    print(f"Processing {len(submissions)} papers...\n")

    papers = []

    for i, paper in enumerate(submissions, 1):
        try:
            # Extract basic paper info
            title = paper.content.get('title', {})
            if isinstance(title, dict):
                title = title.get('value', 'No title')

            print(f"[{i}/{len(submissions)}] {title[:60]}...")

            forum_id = paper.forum if hasattr(paper, 'forum') else paper.id

            paper_info = {
                'paper_id': paper.id,
                'forum_id': forum_id,
                'number': paper.number if hasattr(paper, 'number') else i,
                'title': str(title),
                'abstract': extract_value(paper.content, 'abstract'),
                'authors': extract_value(paper.content, 'authors'),
                'keywords': extract_value(paper.content, 'keywords'),
                'pdf_url': f"https://openreview.net/pdf?id={forum_id}",
                'forum_url': f"https://openreview.net/forum?id={forum_id}",
                'reviews': [],
                'comments': [],
                'meta_reviews': [],
                'decision': None
            }

            # Process replies if available (for API v2 with details='replies')
            if hasattr(paper, 'details') and 'replies' in paper.details:
                replies = paper.details['replies']
                for reply in replies:
                    # Extract content
                    content = {}
                    for key, val in reply.get('content', {}).items():
                        if isinstance(val, dict) and 'value' in val:
                            content[key] = val['value']
                        else:
                            content[key] = val

                    invitation = reply.get('invitation', '')
                    reply_type = invitation.split('/')[-1] if '/' in invitation else ''

                    note_data = {
                        'id': reply.get('id'),
                        'invitation': invitation,
                        'replyto': reply.get('replyto'),
                        'content': content,
                        'created': reply.get('cdate'),
                        'modified': reply.get('mdate'),
                    }

                    # Categorize by invitation type or content
                    if reply_type.endswith('Official_Review') or any(key in content for key in ['rating', 'confidence', 'review']):
                        # This is a review
                        review_data = {
                            'review_id': reply.get('id'),
                            'invitation': invitation,
                            'rating': content.get('rating', content.get('recommendation', '')),
                            'confidence': content.get('confidence', ''),
                            'summary': content.get('summary', ''),
                            'soundness': content.get('soundness', ''),
                            'presentation': content.get('presentation', ''),
                            'contribution': content.get('contribution', ''),
                            'strengths': content.get('strengths', ''),
                            'weaknesses': content.get('weaknesses', ''),
                            'questions': content.get('questions', ''),
                            'limitations': content.get('limitations', ''),
                            'review_text': content.get('review', ''),
                            'full_content': content,
                            'created': note_data['created'],
                            'modified': note_data['modified']
                        }
                        paper_info['reviews'].append(review_data)

                    elif reply_type.endswith('Decision') or reply_type.endswith('Meta_Review') or (any(key in content for key in ['decision']) and 'rating' not in content):
                        # This is a decision/meta-review
                        decision = content.get('decision', content.get('recommendation', ''))
                        if decision:
                            paper_info['decision'] = decision
                        paper_info['meta_reviews'].append({
                            'id': reply.get('id'),
                            'invitation': invitation,
                            'decision': decision,
                            'content': content,
                            'created': note_data['created'],
                            'modified': note_data['modified']
                        })

                    elif reply_type.endswith('Official_Comment') or reply_type.endswith('Rebuttal') or any(key in content for key in ['comment', 'rebuttal']):
                        # This is a comment
                        paper_info['comments'].append({
                            'comment_id': reply.get('id'),
                            'invitation': invitation,
                            'comment': content.get('comment', content.get('rebuttal', '')),
                            'title': content.get('title', ''),
                            'full_content': content,
                            'created': note_data['created'],
                            'modified': note_data['modified']
                        })
                    else:
                        # Other replies - add to comments
                        paper_info['comments'].append(note_data)

            else:
                # Fallback: get notes separately (for API v1 or if details not available)
                try:
                    if api_version == 'v2':
                        notes = list(client.get_all_notes(forum=forum_id))
                    else:
                        notes = client.get_all_notes(forum=forum_id)

                    for note in notes:
                        # Skip the submission itself
                        if note.id == paper.id:
                            continue

                        # Extract all content
                        content = {}
                        for key, val in note.content.items():
                            if isinstance(val, dict) and 'value' in val:
                                content[key] = val['value']
                            else:
                                content[key] = val

                        invitation = note.invitation if hasattr(note, 'invitation') else ''
                        reply_type = invitation.split('/')[-1] if '/' in invitation else ''

                        note_data = {
                            'id': note.id,
                            'invitation': invitation,
                            'replyto': note.replyto if hasattr(note, 'replyto') else None,
                            'content': content,
                            'created': note.cdate if hasattr(note, 'cdate') else None,
                            'modified': note.mdate if hasattr(note, 'mdate') else None,
                        }

                        # Categorize similar to above
                        if reply_type.endswith('Official_Review') or any(key in content for key in ['rating', 'confidence', 'review']):
                            review_data = {
                                'review_id': note.id,
                                'invitation': invitation,
                                'rating': content.get('rating', content.get('recommendation', '')),
                                'confidence': content.get('confidence', ''),
                                'summary': content.get('summary', ''),
                                'soundness': content.get('soundness', ''),
                                'presentation': content.get('presentation', ''),
                                'contribution': content.get('contribution', ''),
                                'strengths': content.get('strengths', ''),
                                'weaknesses': content.get('weaknesses', ''),
                                'questions': content.get('questions', ''),
                                'limitations': content.get('limitations', ''),
                                'review_text': content.get('review', ''),
                                'full_content': content,
                                'created': note_data['created'],
                                'modified': note_data['modified']
                            }
                            paper_info['reviews'].append(review_data)

                        elif reply_type.endswith('Decision') or reply_type.endswith('Meta_Review') or (any(key in content for key in ['decision']) and 'rating' not in content):
                            decision = content.get('decision', content.get('recommendation', ''))
                            if decision:
                                paper_info['decision'] = decision
                            paper_info['meta_reviews'].append({
                                'id': note.id,
                                'invitation': invitation,
                                'decision': decision,
                                'content': content,
                                'created': note_data['created'],
                                'modified': note_data['modified']
                            })

                        elif reply_type.endswith('Official_Comment') or reply_type.endswith('Rebuttal') or any(key in content for key in ['comment', 'rebuttal']):
                            paper_info['comments'].append({
                                'comment_id': note.id,
                                'invitation': invitation,
                                'comment': content.get('comment', content.get('rebuttal', '')),
                                'title': content.get('title', ''),
                                'full_content': content,
                                'created': note_data['created'],
                                'modified': note_data['modified']
                            })
                        else:
                            paper_info['comments'].append(note_data)

                except Exception as e:
                    print(f"  ✗ Error fetching notes: {e}")

            print(f"  → {len(paper_info['reviews'])} reviews, "
                  f"{len(paper_info['comments'])} comments, "
                  f"decision: {paper_info['decision']}")

            papers.append(paper_info)

            # Rate limiting
            time.sleep(0.3)

        except Exception as e:
            print(f"  ✗ Error processing paper: {e}")
            continue

    return papers


def save_to_json(papers, filename=None):
    """Save papers to JSON file"""
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"iclr_first_50_papers_{timestamp}.json"
    
    # Create output structure
    output = {
        'metadata': {
            'crawled_at': datetime.now().isoformat(),
            'total_papers': len(papers),
            'total_reviews': sum(len(p['reviews']) for p in papers),
            'total_comments': sum(len(p['comments']) for p in papers),
        },
        'papers': papers
    }
    
    # Save to file
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"\n{'='*70}")
    print(f"✓ Saved to: {filename}")
    print(f"{'='*70}")
    print(f"Total papers: {output['metadata']['total_papers']}")
    print(f"Total reviews: {output['metadata']['total_reviews']}")
    print(f"Total comments: {output['metadata']['total_comments']}")
    print(f"Average reviews per paper: {output['metadata']['total_reviews'] / len(papers):.2f}")
    print(f"{'='*70}\n")
    
    return filename


if __name__ == "__main__":
    # Configuration
    YEAR = 2024
    LIMIT = 50
    OUTPUT_FILE = "iclr_2024_first_50_papers.json"
    
    # Crawl papers
    papers = crawl_first_50_papers(year=YEAR, limit=LIMIT)
    
    if papers:
        # Save to JSON
        save_to_json(papers, OUTPUT_FILE)
        print("✓ Done!")
    else:
        print("✗ No papers crawled")
