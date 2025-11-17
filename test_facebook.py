"""
Test Facebook reel scraper functionality
"""

from facebook_scraper import FacebookScraper

def test_facebook_url_validation():
    """Test Facebook URL validation"""
    scraper = FacebookScraper(None)

    # Test valid URLs
    valid_urls = [
        "https://www.facebook.com/share/r/1D6Vi3iEhk/",
        "https://facebook.com/reel/123456789",
        "https://www.facebook.com/watch/?v=123456789",
        "https://fb.watch/abc123",
    ]

    print("Testing valid Facebook URLs:")
    for url in valid_urls:
        is_valid, error = scraper.validate_facebook_url(url)
        print(f"  {url}")
        print(f"    Valid: {is_valid}, Error: {error}")

    # Test invalid URLs
    invalid_urls = [
        "https://youtube.com/watch?v=123",
        "https://instagram.com/p/123",
        "https://facebook.com/profile/username",
        "",
    ]

    print("\nTesting invalid URLs:")
    for url in invalid_urls:
        is_valid, error = scraper.validate_facebook_url(url)
        print(f"  {url if url else '(empty)'}")
        print(f"    Valid: {is_valid}, Error: {error}")

def test_platform_detection():
    """Test platform detection"""
    scraper = FacebookScraper(None)

    test_urls = [
        ("https://www.facebook.com/share/r/1D6Vi3iEhk/", "facebook"),
        ("https://youtube.com/watch?v=123", "youtube"),
        ("https://instagram.com/reel/123", "instagram"),
        ("https://example.com", None),
    ]

    print("\nTesting platform detection:")
    for url, expected in test_urls:
        detected = scraper.detect_url_platform(url)
        status = "PASS" if detected == expected else "FAIL"
        print(f"  {status} {url}")
        print(f"    Expected: {expected}, Got: {detected}")

def test_reel_info():
    """Test getting Facebook reel info (requires valid public reel URL)"""
    scraper = FacebookScraper(None)

    # Note: This will only work with a valid, public Facebook reel URL
    test_url = "https://www.facebook.com/share/r/1D6Vi3iEhk/"

    print("\nTesting reel info retrieval:")
    print(f"  URL: {test_url}")

    try:
        info = scraper.get_reel_info(test_url)
        print(f"  SUCCESS: Retrieved reel info:")
        print(f"    Title: {info['title']}")
        print(f"    Duration: {info['duration']:.2f}s")
        print(f"    Has audio: {info['has_audio']}")
        print(f"    Uploader: {info['uploader']}")
    except Exception as e:
        print(f"  FAILED: Could not get reel info: {e}")
        print(f"    Note: This may be expected if the URL is private or requires login")

if __name__ == "__main__":
    print("=" * 60)
    print("Facebook Scraper Test Suite")
    print("=" * 60)

    test_facebook_url_validation()
    test_platform_detection()
    test_reel_info()

    print("\n" + "=" * 60)
    print("Test suite complete!")
    print("=" * 60)
