"""
Test script for Instagram scraping functionality
"""
import sys
from instagram_scraper import InstagramScraper

def test_url_detection():
    """Test URL platform detection"""
    print("Testing URL detection...")

    scraper = InstagramScraper(None)

    # Test Instagram URLs
    test_urls = [
        ("https://www.instagram.com/p/ABC123/", "instagram"),
        ("https://instagram.com/reel/XYZ789/", "instagram"),
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "youtube"),
        ("https://youtu.be/dQw4w9WgXcQ", "youtube"),
        ("https://example.com/video", None),
    ]

    for url, expected in test_urls:
        result = scraper.detect_url_platform(url)
        status = "[PASS]" if result == expected else "[FAIL]"
        print(f"  {status} {url} -> {result} (expected: {expected})")

def test_instagram_validation():
    """Test Instagram URL validation"""
    print("\nTesting Instagram URL validation...")

    scraper = InstagramScraper(None)

    test_cases = [
        ("https://www.instagram.com/p/ABC123/", True),
        ("https://instagram.com/reel/XYZ789/", True),
        ("https://www.youtube.com/watch?v=test", False),
        ("not a url", False),
        ("", False),
    ]

    for url, should_be_valid in test_cases:
        is_valid, error = scraper.validate_instagram_url(url)
        status = "[PASS]" if is_valid == should_be_valid else "[FAIL]"
        print(f"  {status} {url[:50]} -> Valid: {is_valid}")
        if error:
            print(f"      Error: {error}")

def test_real_instagram_post(url):
    """Test with a real Instagram post (requires public post URL)"""
    print(f"\nTesting real Instagram post: {url}")

    try:
        scraper = InstagramScraper(None)

        # Validate URL
        is_valid, error = scraper.validate_instagram_url(url)
        if not is_valid:
            print(f"  [FAIL] Invalid URL: {error}")
            return

        print("  [PASS] URL is valid")

        # Get post info
        print("  Fetching post info...")
        post_info = scraper.get_post_info(url)

        print(f"  [PASS] Post loaded successfully")
        print(f"    Title: {post_info['title']}")
        print(f"    Is carousel: {post_info['is_carousel']}")
        print(f"    Items with audio: {len(post_info['items'])}")

        for idx, item in enumerate(post_info['items']):
            print(f"    Item {idx + 1}:")
            print(f"      Type: {item['type']}")
            print(f"      Has audio: {item['has_audio']}")
            print(f"      Duration: {item['duration']:.1f}s")
            print(f"      Has thumbnail: {'Yes' if item['thumbnail'] else 'No'}")

        print("\n  [PASS] All tests passed!")

    except Exception as e:
        print(f"  [FAIL] Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("Instagram Scraper Test Suite")
    print("=" * 50)

    # Run basic tests
    test_url_detection()
    test_instagram_validation()

    # Test with real URL if provided
    if len(sys.argv) > 1:
        test_url = sys.argv[1]
        test_real_instagram_post(test_url)
    else:
        print("\n" + "=" * 50)
        print("To test with a real Instagram post, run:")
        print("  python test_instagram.py <instagram_url>")
        print("\nExample:")
        print("  python test_instagram.py https://www.instagram.com/reel/ABC123/")

    print("\n" + "=" * 50)
    print("Basic tests completed!")
