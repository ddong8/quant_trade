# backend/test_tqsdk_import.py
import sys
print("--- TQSDK IMPORT TEST: SCRIPT STARTED ---", file=sys.stderr)
try:
    from tqsdk import TqApi, TqAuth
    print("--- TQSDK IMPORT TEST: IMPORT SUCCEEDED ---", file=sys.stderr)
except Exception as e:
    import traceback
    print(f"--- TQSDK IMPORT TEST: IMPORT FAILED WITH PYTHON EXCEPTION ---", file=sys.stderr)
    traceback.print_exc()

# Keep the script running for a moment to ensure output is flushed
import time
time.sleep(1)
