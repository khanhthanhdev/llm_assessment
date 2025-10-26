# read the json in iclr_2024_first_50_papers.json. I want to get the overall json structure.
import json

# Load the JSON file
with open('iclr_2024_first_50_papers.json', 'r') as f:
    data = json.load(f)

# Print the top-level keys
print("Top-level keys:", list(data.keys()))

# Print metadata structure
print("\nMetadata structure:")
print(json.dumps(data['metadata'], indent=2))

# Print structure of the first paper
print("\nFirst paper structure (keys):")
if data['papers']:
    first_paper = data['papers'][1]
    print("Paper keys:", list(first_paper.keys()))
    print("\nFirst review structure (keys):")
    if first_paper['reviews']:
        first_review = first_paper['reviews'][0]
        print("Review keys:", list(first_review.keys()))
        
    if first_paper['comments']:
        first_comment = first_paper['comments'][0]
        print("Comment keys:", list(first_comment.keys()))
