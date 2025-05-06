import re
from typing import List


def _detect_emails(text: str) -> List[str]:
    """
    Detects email addresses in a string.
    Email patterns are usually distinct enough that keyword aiding is less critical,
    but a good regex is important.
    """

    email_regex = r"[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+"
    found_emails = re.findall(email_regex, text)
    return list(set(found_emails))

def _detect_phones(text: str) -> List[str]:
    """
    Detects phone numbers, prioritizing those mentioned with keywords.
    For robust international phone number parsing, use the 'phonenumbers' library.
    (pip install phonenumbers)
    Example with phonenumbers:
    import phonenumbers
    detected_numbers = []
    for match in phonenumbers.PhoneNumberMatcher(text, "US"): # Specify default region or None
        detected_numbers.append(phonenumbers.format_number(match.number, phonenumbers.PhoneNumberFormat.E164))
    if detected_numbers: return list(set(detected_numbers))
    """
    
    # Regex for phone numbers, somewhat generic. Focus on North American for this example.
    # \(? \b\d{3}\b \)?      # Optional parens around area code (3 digits)
    # [-.\s]?                # Optional separator
    # \b\d{3}\b              # Exchange code (3 digits)
    # [-.\s]?                # Optional separator
    # \b\d{4}\b              # Subscriber number (4 digits)

    phone_pattern_str = r"\(?\b\d{3}\b\)?[-.\s]?\b\d{3}\b[-.\s]?\b\d{4}\b"
    
    # Keywords that might precede a phone number
    keyword_phone_patterns = [
        re.compile(r"(?:my\s+phone(?:\s+number)?\s+is|call\s+me\s+at|my\s+number\s+is|contact\s+no\.?\s*(?:is)?)\s*:?\s*(" + phone_pattern_str + r")", re.IGNORECASE),
        re.compile(r"(\bphone(?:\s+number)?\b|\bcell\b|\bmobile\b)\s*:?\s*(" + phone_pattern_str + r")", re.IGNORECASE), # e.g. "Phone: (123) 456-7890"
    ]

    found_phones = []

    for pattern in keyword_phone_patterns:
        matches = pattern.findall(text)
        for match_group in matches:
            phone_number = match_group if isinstance(match_group, str) else match_group[-1]
            found_phones.append(phone_number.strip())

    # If no keyworded phones found, try a general search (higher chance of false positives)
    if not found_phones:
        general_matches = re.findall(phone_pattern_str, text)
        for match in general_matches:
            found_phones.append(match.strip())
            
    # Basic cleanup (remove common separators for consistent storage, though not full normalization)
    cleaned_phones = [re.sub(r"[-.\s\(\)]", "", phone) for phone in found_phones]
    return list(set(cleaned_phones)) # Return unique, somewhat cleaned phones

def _detect_names(text: str) -> List[str]:
    """
    Detects potential names, prioritizing those mentioned with keywords.
    This is heuristic and NOT a replacement for proper NER (e.g., spaCy).
    (pip install spacy; python -m spacy download en_core_web_sm)
    Example with spaCy:
    import spacy
    nlp = spacy.load("en_core_web_sm")
    doc = nlp(text)
    names = [ent.text for ent in doc.ents if ent.label_ == "PERSON"]
    if names: return list(set(names))
    """
    
    # Pattern for a potential name: 1 to 3 capitalized words
    # \b[A-Z][a-z']+      # First capitalized word (e.g., John, O'Malley)
    # (?:\s+[A-Z][a-z']+){0,2} # 0 to 2 additional capitalized words
    name_structure_pattern = r"\b[A-Z][a-z']+(?:\s+[A-Z][a-z']+){0,2}\b"

    keyword_name_patterns = [
        # "My name is John Doe", "I am John Doe", "I'm John Doe"
        re.compile(r"(?:my\s+name\s+is|i\s*am|i'm)\s+(" + name_structure_pattern + r")", re.IGNORECASE),
        # "You can call me John", "Call me John Doe"
        re.compile(r"(?:call\s+me)\s+(" + name_structure_pattern + r")", re.IGNORECASE),
        # "The user's name is John" (less likely for self-reporting but an example)
        # re.compile(r"(?:user(?:\s*name)?\s+is)\s+(" + name_structure_pattern + r")", re.IGNORECASE),
    ]

    found_names = []
    # First, try to find names mentioned with keywords
    for pattern in keyword_name_patterns:
        matches = pattern.findall(text)
        for match_group in matches:
            name_candidate = match_group if isinstance(match_group, str) else match_group[-1]
            # Basic filter: avoid single-letter "names" unless it's like "A. B. Smith" (which this regex doesn't handle well)
            if len(name_candidate.replace(" ", "")) > 1: 
                found_names.append(name_candidate.strip())

    # Fallback: If no keyworded names, try to find any sequence of 2-3 capitalized words
    # This is very prone to false positives (e.g., "New York City", "Customer Support Team")
    # Use with caution or add more sophisticated filtering if this fallback is enabled.
    
    if not found_names:
        general_name_candidates = re.findall(r"(\b[A-Z][a-z']+\s+[A-Z][a-z']+(?:\s+[A-Z][a-z']+)?)", text)
        for candidate in general_name_candidates:
            if len(candidate.replace(" ", "")) > 2:
                found_names.append(candidate.strip())

    return list(set(found_names))