"""
extractor.py
Turns raw PDF notes into structured "smart notes":
  - detects headings
  - groups text into sections
  - pulls out important keywords/topics (frequency + heuristics, no AI needed)
  - builds a short extractive summary per section
"""

import re
import string
from collections import Counter

import pdfplumber

STOPWORDS = set("""
a about above after again against all am an and any are aren't as at be because
been before being below between both but by can't cannot could couldn't did
didn't do does doesn't doing don't down during each few for from further had
hadn't has hasn't have haven't having he he'd he'll he's her here here's hers
herself him himself his how how's i i'd i'll i'm i've if in into is isn't it
it's its itself let's me more most mustn't my myself no nor not of off on once
only or other ought our ours ourselves out over own same shan't she she'd
she'll she's should shouldn't so some such than that that's the their theirs
them themselves then there there's these they they'd they'll they're they've
this those through to too under until up very was wasn't we we'd we'll we're
we've were weren't what what's when when's where where's which while who
who's whom why why's with won't would wouldn't you you'd you'll you're you've
your yours yourself yourselves also thus hence etc using use used via one two
three four five example examples given note notes chapter unit section page
""".split())

HEADING_PATTERNS = [
    re.compile(r"^\s*(chapter|unit|section|module|lesson|topic)\s+\d+", re.I),
    re.compile(r"^\s*\d+(\.\d+)*[\.\)]\s+\S"),          # 1.  /  1.2)  numbered
    re.compile(r"^\s*[A-Z][A-Z\s\-&/]{3,60}$"),          # ALL CAPS LINE
    re.compile(r"^\s*(#{1,3})\s+\S"),                    # markdown-style
]


def clean_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def is_heading(line: str) -> bool:
    line = line.strip()
    if not line or len(line) > 80:
        return False
    if line.endswith((".", ",", ";")) and not line.endswith(("etc.", "...")):
        return False
    for pat in HEADING_PATTERNS:
        if pat.match(line):
            return True
    words = line.split()
    if 1 <= len(words) <= 9:
        cap_words = [w for w in words if w[:1].isupper()]
        if words and len(cap_words) / len(words) >= 0.7:
            return True
    return False


def split_sentences(paragraph: str):
    sentences = re.split(r"(?<=[.!?])\s+", paragraph.strip())
    return [s.strip() for s in sentences if s.strip()]


def tokenize(text: str):
    text = text.lower()
    text = text.translate(str.maketrans("", "", string.punctuation.replace("-", "")))
    return [w for w in text.split() if w and w not in STOPWORDS and len(w) > 2 and not w.isdigit()]


def extract_pages_text(pdf_path: str):
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            pages.append(clean_text(text))
    return pages


def build_sections(pages_text):
    """Walk through all lines and group them into (heading, [body_lines]) sections."""
    sections = []
    current_heading = "Introduction"
    current_lines = []

    for page_text in pages_text:
        for raw_line in page_text.split("\n"):
            line = raw_line.strip()
            if not line:
                continue
            if is_heading(line):
                if current_lines:
                    sections.append((current_heading, current_lines))
                current_heading = line.rstrip(":")
                current_lines = []
            else:
                current_lines.append(line)

    if current_lines:
        sections.append((current_heading, current_lines))

    # Drop a leading empty "Introduction" section if it never got any content
    sections = [s for s in sections if s[1]]
    return sections


def find_capitalized_terms(lines):
    """Words capitalized mid-sentence are often technical terms / proper nouns."""
    terms = Counter()
    for line in lines:
        words = line.split()
        for i, w in enumerate(words):
            clean = w.strip(string.punctuation)
            if i > 0 and clean[:1].isupper() and clean.lower() not in STOPWORDS and len(clean) > 2:
                terms[clean] += 1
    return terms


def summarize_section(lines, max_points=4):
    paragraph = " ".join(lines)
    sentences = split_sentences(paragraph)
    if not sentences:
        return []
    # Prefer earlier sentences (typical for definitions/topic sentences) but
    # also fold in the longest (usually most information-dense) sentence.
    chosen = sentences[:max_points]
    if len(sentences) > max_points:
        longest = max(sentences, key=len)
        if longest not in chosen:
            chosen[-1] = longest
    return chosen


def process_pdf(pdf_path: str, top_n_keywords: int = 15):
    pages_text = extract_pages_text(pdf_path)
    full_text = "\n".join(pages_text)
    sections_raw = build_sections(pages_text)

    all_words = tokenize(full_text)
    freq = Counter(all_words)
    cap_terms = find_capitalized_terms([l for _, lines in sections_raw for l in lines])

    # Combine frequency + "looks like a proper noun / technical term" boost
    combined_score = Counter()
    for word, count in freq.items():
        combined_score[word] += count
    for term, count in cap_terms.items():
        combined_score[term.lower()] += count * 1.5

    top_keywords = [w for w, _ in combined_score.most_common(top_n_keywords)]

    sections = []
    for heading, lines in sections_raw:
        section_words = tokenize(" ".join(lines))
        section_freq = Counter(section_words)
        section_keywords = [w for w, _ in section_freq.most_common(6)]
        summary_points = summarize_section(lines)
        sections.append({
            "heading": heading,
            "keywords": section_keywords,
            "summary_points": summary_points,
        })

    important_topics = []
    seen = set()
    for heading, _ in sections_raw:
        h = heading.strip()
        if h.lower() not in seen and h.lower() != "introduction":
            important_topics.append(h)
            seen.add(h.lower())
    for kw in top_keywords:
        if kw not in seen:
            important_topics.append(kw)
            seen.add(kw)

    return {
        "page_count": len(pages_text),
        "sections": sections,
        "important_topics": important_topics[:20],
        "keywords": top_keywords,
    }
