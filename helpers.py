import re
import os
import sqlite3
from urllib.parse import urlparse, urljoin
from functools import wraps
from flask import session, redirect, render_template, request

# ==============================================================================
# 1. COMMERCIAL CONTENT ENFORCEMENT CONFIGURATION
# ==============================================================================
COMMERCIAL_KEYWORDS = [
    r"₹",
    r"\brs\.?\b",
    r"\binr\b",
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
    r"\bupi\b",
    r"\bgpay\b",
    r"\bgoogle\s*pay\b",
    r"\bphonepe\b",
    r"\bpaytm\b",
    r"\b\d+\s*/-\b",            # matches '6500/-'
    r"(?:rs\.?|₹|inr)\s*\d+",   # matches 'Rs 6500', '₹6500'
]

COMMERCIAL_REGEX = re.compile("|".join(COMMERCIAL_KEYWORDS), re.IGNORECASE)

def check_commercial_content(*texts):
    """
    Checks if any input text contains commercial, pricing, or payment language.
    Returns: (is_commercial: bool, matched_term: str or None)
    """
    combined = " ".join(t for t in texts if t)
    match = COMMERCIAL_REGEX.search(combined)
    if match:
        return True, match.group(0)
    return False, None


# ==============================================================================
# 2. OPEN REDIRECT DEFENSE
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
# 3. COORDINATE JITTER FOR PRIVACY SHIELDING
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
# 4. VIEW DECORATORS & APOLOGY
# ==============================================================================
def login_required(f):
    """
    Decorate routes to require login, passing the current path as safe 'next'.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            safe_next = request.path if request.method == "GET" and is_safe_url(request.path) else "/"
            return redirect(f"/login?next={safe_next}")
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """
    Decorate routes to require admin privileges.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        if not session.get("is_admin"):
            return apology("Administrator privileges required", 403)
        return f(*args, **kwargs)
    return decorated_function


def apology(message, code=400):
    """Render message as an apology to user."""
    return render_template("apology.html", top=code, bottom=message), code
