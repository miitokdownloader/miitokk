"""Pure-Python validation helpers for the photo endpoints.

Extracted from app.py so they can be unit-tested without importing Flask
or any other third-party dependency. app.py imports from this module; the
behavior of /photo-proxy and /download-photo is unchanged.
"""

import re
from urllib.parse import urlparse


# TikTok image-CDN allowlist used by /photo-proxy and /download-photo. Only
# hosts that match one of these suffixes (case-insensitive) are allowed to be
# proxied/streamed back to the client. This keeps the proxy from being abused
# as a generic open relay while still covering TikTok's many image CDNs.
TIKTOK_IMAGE_CDN_SUFFIXES = (
    '.tiktokcdn.com',
    '.tiktokcdn-us.com',
    '.tiktokv.com',
    '.byteoversea.com',
    '.bytecdn.cn',
    '.muscdn.com',
    '.musical.ly',
    '.ibyteimg.com',
    '.ipstatp.com',
)

PHOTO_FILENAME_RE = re.compile(r'^[A-Za-z0-9._-]{1,64}$')
ALLOWED_PHOTO_EXTS = ('.jpg', '.jpeg', '.png', '.webp')


def is_valid_tiktok_image_url(url):
    """Return True if url is http(s) and host ends in a known TikTok image CDN suffix.

    Uses parsed.hostname (which excludes any user:pass@ userinfo) instead of
    parsed.netloc to defeat SSRF tricks like
    'http://aaa.tiktokcdn.com:80@evil.com/x.jpg'. Also explicitly rejects URLs
    that carry userinfo or have an empty host as a defense in depth.
    """
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ('http', 'https'):
            return False
        # Refuse any URL that smuggles userinfo - http(s) basic-auth has no
        # legitimate use against a public CDN and is a classic SSRF carrier.
        if parsed.username or parsed.password:
            return False
        host = (parsed.hostname or '').lower()
        if not host:
            return False
        return any(host.endswith(suffix) for suffix in TIKTOK_IMAGE_CDN_SUFFIXES)
    except Exception:
        return False


def is_valid_photo_filename(filename):
    """Return True if filename is non-empty, matches the safe regex, AND ends
    in an allowed image extension. Used by /download-photo to refuse missing
    or hostile filenames with 400 instead of falling back to a constant
    default (which would collide across photos in the bulk-download flow).
    """
    if not filename:
        return False
    if not PHOTO_FILENAME_RE.match(filename):
        return False
    return filename.lower().endswith(ALLOWED_PHOTO_EXTS)
