"""
Test script to verify YouTube to Sound conversion works
"""
import os
from pathlib import Path

# Simulate the fix by adding ffmpeg to PATH before importing
local_ffmpeg_dir_abs = Path(__file__).parent / "ffmpeg"
if local_ffmpeg_dir_abs.exists():
    os.environ['PATH'] = str(local_ffmpeg_dir_abs.absolute()) + os.pathsep + os.environ.get('PATH', '')
    print(f"[OK] Added ffmpeg to PATH: {local_ffmpeg_dir_abs.absolute()}")

from pydub import AudioSegment

def test_audio_loading():
    """Test if we can load the existing audio file"""
    test_file = Path("sounds/rick_roll_full.mp3")

    if not test_file.exists():
        print(f"[FAIL] Test file not found: {test_file}")
        return False

    try:
        audio = AudioSegment.from_file(str(test_file))
        duration_sec = len(audio) / 1000
        print(f"[OK] Successfully loaded audio file!")
        print(f"  - File: {test_file}")
        print(f"  - Duration: {duration_sec:.2f} seconds")
        print(f"  - Channels: {audio.channels}")
        print(f"  - Sample rate: {audio.frame_rate} Hz")
        return True
    except Exception as e:
        print(f"[FAIL] Failed to load audio: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_audio_clipping():
    """Test if we can clip audio"""
    test_file = Path("sounds/rick_roll_full.mp3")

    if not test_file.exists():
        print(f"[FAIL] Test file not found: {test_file}")
        return False

    try:
        print("\nTesting audio clipping...")
        audio = AudioSegment.from_file(str(test_file))

        # Clip first 3 seconds
        clipped = audio[0:3000]

        # Export to temp file
        output_path = Path("sounds/test_clip.mp3")
        clipped.export(str(output_path), format='mp3', bitrate='128k')

        if output_path.exists():
            file_size_kb = output_path.stat().st_size / 1024
            print(f"[OK] Successfully clipped audio!")
            print(f"  - Output: {output_path}")
            print(f"  - Duration: {len(clipped)/1000:.2f} seconds")
            print(f"  - File size: {file_size_kb:.2f} KB")

            # Cleanup
            output_path.unlink()
            print(f"[OK] Cleaned up test file")
            return True
        else:
            print(f"[FAIL] Output file not created")
            return False

    except Exception as e:
        print(f"[FAIL] Failed to clip audio: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("YouTube to Sound - Fix Verification Test")
    print("=" * 60)
    print()

    # Test 1: Load audio
    test1_passed = test_audio_loading()
    print()

    # Test 2: Clip audio
    test2_passed = test_audio_clipping()
    print()

    # Summary
    print("=" * 60)
    print("Test Results:")
    print(f"  - Audio Loading: {'PASS' if test1_passed else 'FAIL'}")
    print(f"  - Audio Clipping: {'PASS' if test2_passed else 'FAIL'}")
    print("=" * 60)

    if test1_passed and test2_passed:
        print("\n[OK] All tests passed! The fix is working correctly.")
    else:
        print("\n[FAIL] Some tests failed. Please check the errors above.")
