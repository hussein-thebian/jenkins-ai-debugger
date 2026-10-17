import os
import time

WAIT_SECONDS = int(os.environ.get("SMOKE_WAIT_SECONDS", "3"))

print(f"Waiting {WAIT_SECONDS}s for the service to become healthy...", flush=True)
for second in range(1, WAIT_SECONDS + 1):
    time.sleep(1)
    print(f"  still waiting... {second}s", flush=True)
print("Service is healthy")