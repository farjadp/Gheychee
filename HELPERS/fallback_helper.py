"""
PATH: HELPERS/fallback_helper.py
TIMESTAMP: 2026-01-01 13:55 EST
VERSION: v2.0.0
DESIGN: Logic for switching between downloaders (yt-dlp, gallery-dl).
CONCEPT: "Smart Fallback."
"""

"""
Helper functions for fallback mechanisms
"""

def should_fallback_to_gallery_dl(error_message: str, url: str) -> bool:
    """
    Determines if we should switch to gallery-dl on yt-dlp error.
    Returns True if error indicates yt-dlp cannot process URL.
    """
    # Check if URL is yt-dlp only domain
    from CONFIG.domains import DomainsConfig
    from urllib.parse import urlparse
    
    try:
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.lower()
        
        # Remove www. prefix for comparison
        if domain.startswith('www.'):
            domain = domain[4:]
            
        # Check if domain is in YTDLP_ONLY_DOMAINS
        for ytdlp_domain in DomainsConfig.YTDLP_ONLY_DOMAINS:
            if domain == ytdlp_domain or domain.endswith('.' + ytdlp_domain):
                return False  # Do not switch to gallery-dl for yt-dlp only domains
    except Exception:
        # If failed to parse URL, continue normal check
        pass
    
    error_lower = error_message.lower()
    
    # Errors indicating yt-dlp cannot process content
    fallback_indicators = [
        # Access and authorization errors
        "http error 429: too many requests",
        "http error 403: forbidden", 
        "http error 401: unauthorized",
        "unable to download webpage",
        "too many requests",
        "rate limit exceeded",
        "quota exceeded",
        
        # Content format errors
        "no videos found in playlist",
        "unsupported url",
        "no video could be found", 
        "no video found",
        "no media found",
        "this tweet does not contain",
        "no video formats found",
        "no video available",
        
        # Extraction errors
        "unable to extract",
        "extraction failed",
        "no suitable formats",
        "requested format is not available",
        
        # Platform errors
        "instagram:user",
        "twitter:user", 
        "tiktok:user",
        "facebook:user",
        "pinterest:user",
        "tumblr:user",
        "flickr:user",
        "deviantart:user",
        "artstation:user",
        "onlyfans:user",
        "patreon:user",
        "fanbox:user",
        "fantia:user",
        
        # Network errors
        "connection refused",
        "connection timeout", 
        "network unreachable",
        "dns resolution failed",
        
        # Block/ban errors
        "blocked by robots.txt",
        "geoblocked",
        "region blocked",
        "country blocked",
        "ip blocked",
        "user agent blocked",
        "captcha required",
        "verification required",
        "age verification required",
        "nsfw verification required",
        
        # Content errors
        "content not available",
        "post deleted",
        "account deleted", 
        "account terminated",
        "account suspended",
        "account banned",
        "account private",
        "profile private",
        "terms of service violation",
        "copyright violation",
        "dmca takedown",
        "content removed"
    ]
    
    # Check for fallback indicators
    for indicator in fallback_indicators:
        if indicator in error_lower:
            return True
    
    # Additional check for Instagram errors
    if "instagram" in error_lower and any(err in error_lower for err in ["429", "403", "401", "unable to download"]):
        return True
    
    # Additional check for Twitter/X errors  
    if any(domain in url.lower() for domain in ["twitter.com", "x.com"]) and any(err in error_lower for err in ["429", "403", "401", "unable to download"]):
        return True
        
    # Additional check for TikTok errors
    # Safe domain check via urlparse
    is_tiktok = False
    try:
        from urllib.parse import urlparse
        parsed_url = urlparse(url)
        tiktok_hostname = (parsed_url.hostname or '').lower()
        is_tiktok = tiktok_hostname in ('tiktok.com', 'www.tiktok.com', 'vm.tiktok.com', 'vt.tiktok.com') or \
                   tiktok_hostname.endswith('.tiktok.com')
    except Exception:
        pass
    
    if is_tiktok and any(err in error_lower for err in ["429", "403", "401", "unable to download"]):
        return True
    
    return False
