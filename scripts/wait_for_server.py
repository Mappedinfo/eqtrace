"""Bounded readiness check used by the browser CI job."""
import time
import urllib.request
for _ in range(100):
    try:
        with urllib.request.urlopen('http://127.0.0.1:8765', timeout=1) as response:
            if response.status == 200:
                break
    except OSError:
        time.sleep(.2)
else:
    raise SystemExit('EqTrace server did not become ready')
