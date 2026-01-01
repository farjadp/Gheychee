"""
PATH: HELPERS/pot_helper.py
TIMESTAMP: 2026-01-01 13:45 EST
VERSION: v2.0.0
DESIGN: YouTube PO token management utility.
CONCEPT: "Proof-of-Origin."
"""
# PO Token Helper for YouTube
# Adds PO token provider support for YouTube domains

import requests
import time
import re
from CONFIG.config import Config
from CONFIG.messages import Messages, safe_get_messages
from URL_PARSERS.youtube import is_youtube_url
from HELPERS.logger import logger

# Cache for PO token provider availability
_pot_provider_cache = {
    'available': None,
    'last_check': 0,
    'check_interval': 30  # Check every 30 seconds
}

def check_pot_provider_availability(base_url: str) -> bool:
    """
    Checks PO token provider availability
    
    Args:
        base_url (str): Provider URL
        
    Returns:
        bool: True if provider available, False otherwise
    """
    current_time = time.time()
    
    # Check cache
    if (_pot_provider_cache['available'] is not None and 
        current_time - _pot_provider_cache['last_check'] < _pot_provider_cache['check_interval']):
        return _pot_provider_cache['available']
    
    try:
        # URL validation to prevent SSRF (but allow localhost for local service)
        from urllib.parse import urlparse
        import ipaddress
        parsed_url = urlparse(base_url)
        url_host = (parsed_url.hostname or '').lower()
        # Allow localhost for local PO token provider, but block other internal resources
        if url_host not in ('localhost', '127.0.0.1') and \
           (url_host.endswith('.local') or url_host.endswith('.internal') or 'localhost' in url_host):
            try:
                ip = ipaddress.ip_address(url_host)
                if (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or str(ip) == '169.254.169.254') and \
                   str(ip) not in ('127.0.0.1', '::1'):
                    logger.warning(f"Blocked SSRF attempt: invalid PO token provider URL {base_url}")
                    _pot_provider_cache['available'] = False
                    _pot_provider_cache['last_check'] = current_time
                    return False
            except ValueError:
                pass
        
        # Quick check of provider availability
        # PO token provider might return 404 for root path, but it means service is working
        response = requests.get(base_url, timeout=5)
        is_available = response.status_code in [200, 404]  # 404 means service is working but endpoint not found
        
        # Update cache
        _pot_provider_cache['available'] = is_available
        _pot_provider_cache['last_check'] = current_time
        
        if is_available:
            logger.info(f"PO token provider is available at {base_url} (status: {response.status_code})")
        else:
            logger.warning(f"PO token provider returned status {response.status_code} at {base_url}")
        
        return is_available
        
    except requests.exceptions.RequestException as e:
        logger.warning(f"PO token provider is not available at {base_url}: {e}")
        
        # Update cache
        _pot_provider_cache['available'] = False
        _pot_provider_cache['last_check'] = current_time
        
        return False

def add_pot_to_ytdl_opts(ytdl_opts: dict, url: str) -> dict:
    """
    Adds PO token arguments to yt-dlp options for YouTube domains
    
    Args:
        ytdl_opts (dict): yt-dlp options dictionary
        url (str): URL to check
        
    Returns:
        dict: Updated yt-dlp options dictionary
    """
    # Check if PO token provider is enabled
    if not getattr(Config, 'YOUTUBE_POT_ENABLED', False):
        messages = safe_get_messages()
        logger.info(messages.HELPER_POT_PROVIDER_DISABLED_MSG)
        return ytdl_opts
    
    # Check if URL is a YouTube domain
    if not is_youtube_url(url):
        messages = safe_get_messages()
        logger.info(messages.HELPER_POT_URL_NOT_YOUTUBE_MSG.format(url=url))
        return ytdl_opts
    
    # Get provider base URL
    base_url = getattr(Config, 'YOUTUBE_POT_BASE_URL', 'http://127.0.0.1:4416')
    disable_innertube = getattr(Config, 'YOUTUBE_POT_DISABLE_INNERTUBE', False)
    
    # Check PO token provider availability
    if not check_pot_provider_availability(base_url):
        messages = safe_get_messages()
        logger.warning(messages.HELPER_POT_PROVIDER_NOT_AVAILABLE_MSG.format(base_url=base_url))
        return ytdl_opts

    # Add extractor_args to yt-dlp options
    if 'extractor_args' not in ytdl_opts:
        ytdl_opts['extractor_args'] = {}
    
    # Add arguments for YouTube PO token provider in correct format (nightly ≥ 2025-09-13)
    # Structure:
    # extractor_args: {
    #   'youtubepot': {
    #       'providers': ['bgutilhttp'],
    #       'bgutilhttp': { 'base_url': ['http://...'] },
    #       'disable_innertube': ['1']  # optional
    #   }
    # }
    pot_args = ytdl_opts['extractor_args'].get('youtubepot', {})
    pot_args['providers'] = list(dict.fromkeys((pot_args.get('providers') or []) + ['bgutilhttp']))
    bg_cfg = pot_args.get('bgutilhttp', {})
    bg_cfg['base_url'] = [base_url]
    pot_args['bgutilhttp'] = bg_cfg
    if disable_innertube:
        pot_args['disable_innertube'] = ["1"]
    ytdl_opts['extractor_args']['youtubepot'] = pot_args
    
    # Add verbose mode for detailed PO token logging
    ytdl_opts['verbose'] = True
    
    # Add hook for PO token debugging
    ytdl_opts = add_pot_debug_hook(ytdl_opts)
    
    # Explicit logs to show active providers
    active_providers = ytdl_opts['extractor_args'].get('youtubepot', {}).get('providers', [])
    logger.info(f"🔑 PO TOKEN PROVIDER ENABLED for YouTube URL: {url}")
    logger.info(f"🔗 PO Token Base URL: {base_url}")
    logger.info(f"🧩 PO Token Providers: {active_providers}")
    logger.info(f"⚙️  PO Token Config: disable_innertube={disable_innertube}")
    logger.info(f"📋 extractor_args.youtubepot: {ytdl_opts['extractor_args'].get('youtubepot')}")
    
    return ytdl_opts

def is_pot_enabled() -> bool:
    """
    Checks if PO token provider is enabled in configuration
    
    Returns:
        bool: True if enabled, False otherwise
    """
    return getattr(Config, 'YOUTUBE_POT_ENABLED', False)

def get_pot_base_url() -> str:
    """
    Returns PO token provider base URL
    
    Returns:
        str: Provider base URL
    """
    return getattr(Config, 'YOUTUBE_POT_BASE_URL', 'http://127.0.0.1:4416')

def clear_pot_provider_cache():
    messages = safe_get_messages(None)
    """
    Resets PO token provider availability cache
    Useful for forced re-check after provider recovery
    """
    global _pot_provider_cache
    _pot_provider_cache['available'] = None
    _pot_provider_cache['last_check'] = 0
    messages = safe_get_messages()
    logger.info(messages.HELPER_POT_PROVIDER_CACHE_CLEARED_MSG)

def is_pot_provider_available() -> bool:
    """
    Checks if PO token provider is available (considering cache)
    
    Returns:
        bool: True if provider available, False otherwise
    """
    base_url = getattr(Config, 'YOUTUBE_POT_BASE_URL', 'http://127.0.0.1:4416')
    return check_pot_provider_availability(base_url)

def create_pot_debug_hook():
    messages = safe_get_messages(None)
    """
    Creates hook for yt-dlp that intercepts and logs PO tokens
    
    Returns:
        function: Hook function for yt-dlp
    """
    def pot_debug_hook(d):
        messages = safe_get_messages(None)
        """
        Hook for intercepting PO tokens in yt-dlp
        
        Args:
            d (dict): Dictionary with download info
        """
        if d['status'] == 'downloading':
            # Look for PO tokens in URL or headers
            if 'url' in d:
                url = d['url']
                # Check for PO tokens in URL
                pot_patterns = [
                    r'po_token=([^&]+)',
                    r'popt=([^&]+)',
                    r'pot=([^&]+)',
                    r'proof_of_origin=([^&]+)'
                ]
                
                for pattern in pot_patterns:
                    match = re.search(pattern, url)
                    if match:
                        token = match.group(1)
                        logger.info(f"🎯 PO TOKEN DETECTED in URL: {token[:20]}...")
                        logger.info(f"🔗 Full URL with PO token: {url}")
                        break
                
                # Check headers for PO tokens
                if 'http_headers' in d:
                    headers = d['http_headers']
                    for header_name, header_value in headers.items():
                        if 'po' in header_name.lower() or 'token' in header_name.lower():
                            logger.info(f"🎯 PO TOKEN in header {header_name}: {header_value}")
        
        elif d['status'] == 'finished':
            # Log successful completion with PO tokens
            messages = safe_get_messages()
            logger.info(messages.HELPER_DOWNLOAD_FINISHED_PO_MSG)
            
    return pot_debug_hook

def add_pot_debug_hook(ytdl_opts: dict) -> dict:
    """
    Adds hook for PO token debugging to yt-dlp options
    
    Args:
        ytdl_opts (dict): yt-dlp options dictionary
        
    Returns:
        dict: Updated yt-dlp options dictionary
    """
    if 'progress_hooks' not in ytdl_opts:
        ytdl_opts['progress_hooks'] = []
    
    # Add our hook for PO token debugging
    ytdl_opts['progress_hooks'].append(create_pot_debug_hook())
    
    return ytdl_opts

def build_cli_extractor_args(url: str) -> list[str]:
    """
    Forms CLI arguments for yt-dlp (--extractor-args) with PO token support.
    Returns list like ["--extractor-args", VALUE], or empty list if not needed.
    """
    try:
        # Check enabling and domain
        if not getattr(Config, 'YOUTUBE_POT_ENABLED', False):
            return []
        if not is_youtube_url(url):
            return []
        base_url = getattr(Config, 'YOUTUBE_POT_BASE_URL', 'http://127.0.0.1:4416')
        disable_innertube = getattr(Config, 'YOUTUBE_POT_DISABLE_INNERTUBE', False)

        # CLI syntax for sub-provider: youtubepot-bgutilhttp:base_url=...;disable_innertube=1
        pot_segment = f"youtubepot-bgutilhttp:base_url={base_url}"
        if disable_innertube:
            pot_segment += ";disable_innertube=1"

        # Additional extractor-args (comma separated between namespaces)
        messages = safe_get_messages()
        generic_args = messages.HELPER_POT_GENERIC_ARGS_MSG
        value = ",".join([pot_segment, generic_args])
        logger.info(f"🧱 CLI extractor-args built for POT: {value}")
        return ['--extractor-args', value]
    except Exception as e:
        logger.warning(f"Failed to build CLI extractor-args for POT: {e}")
        return []
