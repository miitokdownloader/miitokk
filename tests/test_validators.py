"""Regression tests for the photo-endpoint validators.

Pin the SSRF closure on _is_valid_tiktok_image_url and the safety bounds on
_PHOTO_FILENAME_RE / _is_valid_photo_filename so a future "simplification"
that re-introduces a netloc-split or a permissive filename fallback trips
CI instead of shipping silently.

Runnable with stdlib only:

    python3 -m unittest tests.test_validators -v
    python3 -m unittest discover tests -v
    python3 tests/test_validators.py

No third-party dependencies. The validators live in app_validators.py
specifically so this test file does not need flask, yt_dlp or requests on
PYTHONPATH.
"""

import os
import sys
import unittest

# Allow `python3 tests/test_validators.py` from the repo root by putting
# the project root on sys.path. Harmless when invoked via unittest discover.
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from app_validators import (  # noqa: E402
    PHOTO_FILENAME_RE,
    is_valid_photo_filename,
    is_valid_tiktok_image_url,
)


class IsValidTiktokImageUrlTests(unittest.TestCase):
    """Behavioral pin for the SSRF fix shipped in commit 6b6aa42."""

    def test_userinfo_bypass_is_rejected(self):
        # The original v1 bypass: parsed.netloc.split(':')[0] returned the
        # userinfo prefix and let the request through; parsed.hostname is
        # 'evil.com' and the userinfo guard catches it first.
        self.assertFalse(
            is_valid_tiktok_image_url(
                'http://aaa.tiktokcdn.com:80@evil.com/x.jpg'
            )
        )

    def test_userinfo_password_only_is_rejected(self):
        self.assertFalse(
            is_valid_tiktok_image_url(
                'https://:secret@p16.tiktokcdn.com/x.jpg'
            )
        )

    def test_sibling_domain_is_rejected(self):
        # 'tiktokcdn.com.attacker.com' must NOT match the .tiktokcdn.com
        # suffix because suffix matching has to compare against a leading dot.
        self.assertFalse(
            is_valid_tiktok_image_url(
                'https://tiktokcdn.com.attacker.com/x.jpg'
            )
        )

    def test_naked_domain_is_rejected(self):
        # The allowlist only covers subdomains of TikTok CDNs, never the
        # apex of a public suffix.
        self.assertFalse(
            is_valid_tiktok_image_url('https://tiktokcdn.com/x.jpg')
        )

    def test_non_http_scheme_is_rejected(self):
        self.assertFalse(
            is_valid_tiktok_image_url('file:///etc/passwd')
        )
        self.assertFalse(
            is_valid_tiktok_image_url('ftp://p16.tiktokcdn.com/x.jpg')
        )

    def test_empty_or_garbage_url_is_rejected(self):
        self.assertFalse(is_valid_tiktok_image_url(''))
        self.assertFalse(is_valid_tiktok_image_url('not a url'))
        self.assertFalse(is_valid_tiktok_image_url(None))

    def test_rfc1918_host_is_rejected(self):
        self.assertFalse(
            is_valid_tiktok_image_url('http://10.0.0.1/x.jpg')
        )
        self.assertFalse(
            is_valid_tiktok_image_url('http://169.254.169.254/latest/meta-data')
        )

    def test_happy_path_p16_subdomain(self):
        self.assertTrue(
            is_valid_tiktok_image_url('https://p16.tiktokcdn.com/img/abc.jpg')
        )

    def test_happy_path_other_cdn_suffixes(self):
        self.assertTrue(
            is_valid_tiktok_image_url('https://p77.tiktokcdn-us.com/img/x.jpg')
        )
        self.assertTrue(
            is_valid_tiktok_image_url('https://v16.tiktokv.com/img/x.jpg')
        )
        self.assertTrue(
            is_valid_tiktok_image_url('https://sf16.muscdn.com/img/x.jpg')
        )

    def test_host_match_is_case_insensitive(self):
        self.assertTrue(
            is_valid_tiktok_image_url('https://P16.TikTokCdn.com/x.jpg')
        )


class PhotoFilenameRegexTests(unittest.TestCase):
    """Bounds on _PHOTO_FILENAME_RE plus the high-level helper."""

    def test_path_traversal_is_rejected(self):
        self.assertIsNone(PHOTO_FILENAME_RE.match('../foo.jpg'))
        self.assertFalse(is_valid_photo_filename('../foo.jpg'))

    def test_slashes_are_rejected(self):
        self.assertIsNone(PHOTO_FILENAME_RE.match('a/b.jpg'))
        self.assertIsNone(PHOTO_FILENAME_RE.match('a\\b.jpg'))
        self.assertFalse(is_valid_photo_filename('a/b.jpg'))

    def test_nul_byte_is_rejected(self):
        self.assertIsNone(PHOTO_FILENAME_RE.match('foo\x00.jpg'))
        self.assertFalse(is_valid_photo_filename('foo\x00.jpg'))

    def test_oversize_is_rejected(self):
        # 65 chars total: 61 'a' + '.jpg' is just past the 64-char cap.
        oversize = ('a' * 61) + '.jpg'
        self.assertEqual(len(oversize), 65)
        self.assertIsNone(PHOTO_FILENAME_RE.match(oversize))
        self.assertFalse(is_valid_photo_filename(oversize))

    def test_double_extension_is_rejected_by_helper(self):
        # The regex on its own is permissive about the suffix; the helper
        # is the layer that enforces an allowed image extension.
        self.assertIsNotNone(PHOTO_FILENAME_RE.match('foo.jpg.exe'))
        self.assertFalse(is_valid_photo_filename('foo.jpg.exe'))

    def test_empty_filename_is_rejected(self):
        self.assertFalse(is_valid_photo_filename(''))
        self.assertFalse(is_valid_photo_filename(None))

    def test_non_image_extension_is_rejected(self):
        self.assertFalse(is_valid_photo_filename('foo.txt'))
        self.assertFalse(is_valid_photo_filename('foo'))

    def test_happy_path(self):
        # The frontend pattern 'miitok_photo_<n>.jpg' must keep working.
        self.assertTrue(is_valid_photo_filename('miitok_photo_1.jpg'))
        self.assertTrue(is_valid_photo_filename('miitok_photo_42.jpg'))
        self.assertTrue(is_valid_photo_filename('a.png'))
        self.assertTrue(is_valid_photo_filename('a.jpeg'))
        self.assertTrue(is_valid_photo_filename('a.webp'))
        self.assertTrue(is_valid_photo_filename('a.JPG'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
