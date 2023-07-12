"""
This file implements the signature check that verifies that incoming webhook 
requests come from WHOOP.
"""

import os
import hmac
import hashlib
import base64

timestamp = '1689034518795'
signature = 'Wq89oDxFHaUJnMV5gHNNMvo6bLwzcrPvgkFSRz7G1Kc='
client_secret = os.getenv("WHOOP_CLIENT_SECRET")
body = b'{"user_id":10199261,"id":715846661,"type":"sleep.updated","trace_id":"bfe46c1e-1173-4df6-bdc0-986d2a3074fb"}'

print("Signature: ", signature)

# compute signature
computed_signature = base64.b64encode(
    hmac.new(
        (client_secret).encode('utf-8'), 
        f"{timestamp}".encode('utf-8') + body,
        hashlib.sha256
    ).digest()
).decode('utf-8')
print("Computed signature: ", computed_signature)
