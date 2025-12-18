import json

TAG_RULES = {
    "AI": ["ai", "artificial intelligence", "llm", "gpt", "generative", "neural", "machine learning", "ml "],
    "Biotech": ["biotech", "pharma", "life science", "biology", "genomics", "medtech", "nucleate"],
    "Startup": ["startup", "founder", "entrepreneur", "pitch", "incubator", "accelerator", "venture"],
    "Fintech": ["fintech", "finance", "crypto", "blockchain", "bitcoin", "web3", "defi"],
    "Robotics": ["robot", "drone", "autonomous", "hardware"],
    "Engineering": ["engineering", "developer", "coding", "software", "devops", "cloud", "api"],
    "Networking": ["networking", "mixer", "meetup", "social", "gathering", "coffee"],
    "Hackathon": ["hackathon", "jam", "challenge", "competition"],
    "Workshop": ["workshop", "tutorial", "bootcamp", "class", "course", "training"],
    "Conference": ["conference", "summit", "symposium", "expo", "forum"],
    "Academic": ["mit ", "harvard", "tufts", "bu ", "northeastern", "university", "research"],
    "VC": ["venture capital", "angel", "investor", "fundraising"]
}

def generate_tags(title: str, description: str = "") -> str:
    """
    Analyzes title and description to generate a list of tags.
    Returns a JSON string of tags.
    """
    text = (title + " " + (description or "")).lower()
    tags = set()
    
    for category, keywords in TAG_RULES.items():
        for keyword in keywords:
            # Simple check for now. Can be improved with regex \bword\b
            if keyword in text:
                tags.add(category)
                break
    
    return json.dumps(list(tags))
