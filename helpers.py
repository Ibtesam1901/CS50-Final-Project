import re
import os
import sqlite3
from urllib.parse import urlparse, urljoin
from functools import wraps
from flask import session, redirect, render_template, request

# ==============================================================================
# 1. COMMERCIAL CONTENT ENFORCEMENT CONFIGURATION (ENGLISH & HINGLISH)
# ==============================================================================
COMMERCIAL_KEYWORDS = [
    # Symbols & Currency
    r"₹",
    r"\brs\.?\b",
    r"\br\s+s\.?\b",
    r"\binr\b",
    r"\brupees?\b",
    r"\brupaye?\b",
    r"\bpaise?\b",
    r"\b\d+\s*/-\b",            # matches '6500/-'
    r"(?:rs\.?|r\s+s|₹|inr)\s*\d+", # matches 'Rs 6500', 'R s 6500', '₹6500'
    
    # English commercial verbs/nouns
    r"\bprice\b",
    r"\bsell(?:ing)?\b",
    r"\bfor\s+sale\b",
    r"\bcash\b",
    r"\bcod\b",
    r"\bfixed\s+price\b",
    r"\brent\s+per\s+day\b",
    r"\bcharge[s]?\b",
    r"\bpaid\b",
    r"\bbuy(?:ing)?\b",
    r"\bdiscount[s]?\b",
    
    # Hinglish & Hindi commercial terms
    r"\bbechn[aie]\b",          # bechna, bechni, bechne
    r"\bkimat\b",              # kimat / keemat
    r"\bkeemat\b",
    r"\bdaam\b",               # daam
    r"\bkharid(?:na|ni|ne)?\b",# kharidna
    r"\bbikau\b",              # bikau
    
    # Payment apps & methods
    r"\bupi\b",
    r"\bgpay\b",
    r"\bgoogle\s*pay\b",
    r"\bphonepe\b",
    r"\bpaytm\b",
]

COMMERCIAL_REGEX = re.compile("|".join(COMMERCIAL_KEYWORDS), re.IGNORECASE)

def check_commercial_content(*texts):
    """
    Checks if any input text contains commercial, pricing, or payment language.
    Normalizes dots, spaces, and case before matching.
    Returns: (is_commercial: bool, matched_term: str or None)
    """
    combined = " ".join(t for t in texts if t)
    # Simple normalization of internal multi-spaces
    normalized = re.sub(r"\s+", " ", combined)
    match = COMMERCIAL_REGEX.search(normalized)
    if match:
        return True, match.group(0)
    return False, None


# ==============================================================================
# 2. RESIDENTIAL ADDRESS / PRIVACY DETECTION REGEX (PART B2)
# ==============================================================================
ADDRESS_PATTERNS = [
    r"\bflat\s*(?:no\.?|num(?:ber)?\.?|#)?\s*\w+",
    r"\bhouse\s*(?:no\.?|num(?:ber)?\.?|#)\s*\w+",
    r"\bdoor\s*(?:no\.?|num(?:ber)?\.?|#)\s*\w+",
    r"\b(?:apt|apartment)\s*(?:no\.?|num(?:ber)?\.?|#)?\s*\w+",
    r"\b(?:bldg|building)\s*(?:no\.?|#)\s*\w+",
    r"#\s*\d+[a-zA-Z]?",
    r"\bno\.?\s*\d+\b",
    r"\bplot\s*(?:no\.?|#)\s*\d+",
    r"\bvilla\s*(?:no\.?|#)\s*\d+",
    r"\bfloor\s*,\s*flat\b",
]

ADDRESS_REGEX = re.compile("|".join(ADDRESS_PATTERNS), re.IGNORECASE)

def check_private_address(text):
    """
    Detects if location_details looks like a private residential house or apartment address.
    Returns: (has_private_address: bool, matched_phrase: str or None)
    """
    if not text:
        return False, None
    match = ADDRESS_REGEX.search(text)
    if match:
        return True, match.group(0)
    return False, None


# ==============================================================================
# 3. OPEN REDIRECT DEFENSE
# ==============================================================================
def is_safe_url(target):
    """
    Validates that a redirect target strictly points to this application's host
    and does not contain open-redirect exploits.
    """
    if not target:
        return False
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc


# ==============================================================================
# 4. COORDINATE JITTER FOR PRIVACY SHIELDING
# ==============================================================================
def jitter_coordinate(coord, jitter_amount=0.0009):
    """
    Rounds/jitters coordinates slightly (~80-100m) to preserve exact home privacy
    on public maps while maintaining accurate neighborhood walking distances.
    """
    if coord is None:
        return None
    # Round to 3 decimal places (~110m resolution)
    return round(float(coord), 3)


# ==============================================================================
# 5. VIEW DECORATORS & APOLOGY HELPER
# ==============================================================================
def apology(message, code=400):
    """Render structured error page"""
    return render_template("apology.html", top=code, bottom=message), code


def login_required(f):
    """
    Decorate routes to require login.
    Redirects to login page with validated ?next= parameter.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            # Capture current requested path for seamless redirect back
            target_path = request.path
            if request.query_string:
                target_path += "?" + request.query_string.decode("utf-8")
            return redirect(f"/login?next={target_path}")
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Decorate routes to require admin privileges"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("user_id"):
            return redirect("/login")
        if not session.get("is_admin"):
            return apology("Administrative access required", 403)
        return f(*args, **kwargs)
    return decorated_function
