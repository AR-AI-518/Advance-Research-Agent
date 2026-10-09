import re
from langsmith import traceable


INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"ignore\s+(the\s+)?system\s+prompt",
    r"ignore\s+(the\s+)?developer\s+instructions",
    r"forget\s+(all\s+)?previous\s+instructions",
    r"reveal\s+(your\s+)?system\s+prompt",
    r"show\s+(me\s+)?your\s+(hidden\s+)?instructions",
    r"reveal\s+(your\s+)?hidden\s+prompt",
    r"you\s+are\s+now\s+an?\s+unrestricted",
    r"bypass\s+(your\s+)?restrictions",
    r"disregard\s+(all\s+)?previous\s+rules",
]


class InputSanitizer:

    def check_input(self, text: str) -> bool:
        for pattern in INJECTION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return True

        return False

    def clean_text(self, text: str) -> str:
        text = text.strip()

        text = re.sub(r"<[^>]*>", "", text)

        text = re.sub(
            r"https?://\S+|www\.\S+",
            "",
            text
        )

        text = re.sub(r"-{3,}", "", text)
        text = re.sub(r"={3,}", "", text)

        text = re.sub(r"\s+", " ", text)

        return text


PII_PATTERNS = {
    "email": re.compile(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
    ),

    "phone": re.compile(
        r"\b(?:\+92|0092|0)?3\d{2}[- ]?\d{7}\b"
    ),

    "cnic": re.compile(
        r"\b\d{5}-\d{7}-\d\b"
    ),

    "credit_card": re.compile(
        r"\b(?:\d[ -]?){13,19}\b"
    ),

    "ip_address": re.compile(
        r"\b(?:\d{1,3}\.){3}\d{1,3}\b"
    ),

    "date_of_birth": re.compile(
        r"\b(?:\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\b"
    ),

    "url": re.compile(
        r"\bhttps?://[^\s]+\b"
    ),
}


MASK_MAP = {
    "email": "[EMAIL]",
    "phone": "[PHONE NUMBER]",
    "cnic": "[CNIC]",
    "credit_card": "[CREDIT CARD]",
    "ip_address": "[IP ADDRESS]",
    "date_of_birth": "[DATE OF BIRTH]",
    "url": "[URL]",
}


HARMFUL_PATTERNS = {
    "violence": r"\b(kill|murder|assassinate|attack|hurt|stab|shoot)\b",

    "weapons": r"\b(make|build|create)\b.{0,30}\b(bomb|explosive|weapon)\b",

    "self_harm": r"\b(suicide|self[- ]harm|kill myself|hurt myself)\b",

    "malware": r"\b(create|write|build|make)\b.{0,30}\b(malware|ransomware|keylogger|trojan)\b",

    "credential_theft": r"\b(steal|capture|harvest)\b.{0,30}\b(password|credential|login|token)\b",

    "fraud": r"\b(phishing|scam|fraud|credit card theft|identity theft)\b",
}


class PIIDetector:

    def detected(self, text: str):
        found = {}

        for pii_type, pattern in PII_PATTERNS.items():
            matches = pattern.findall(text)
            if matches:
                found[pii_type] = matches

        return found

    def mask(self, text: str):
        for pii_type, pattern in PII_PATTERNS.items():
            replacement = MASK_MAP[pii_type]
            text = pattern.sub(replacement, text)

        return text


class Validator:

    def __init__(self):
        self.pii_detector = PIIDetector()

    @traceable
    def harmful_response(self, output: str) -> str:
        pii_detect = self.pii_detector.detected(output)
        if pii_detect:
            output = self.pii_detector.mask(output)

        for harmful_type, pattern in HARMFUL_PATTERNS.items():
            if re.search(pattern, output, re.IGNORECASE):
                return "The output is blocked due to harmful content"

        return output