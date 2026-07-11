import requests
import re

url = 'https://www.taiwanlottery.com/_nuxt/entry.1_0_8_0.js'
resp = requests.get(url, timeout=20, verify=False)
print('status', resp.status_code)
text = resp.text
print('len', len(text))
for pat in ['TLCAPIWeB', 'TLC_WEB', 'lotto', 'result', 'traditional', 'fetch', 'axios', 'XMLHttpRequest', 'https://api.taiwanlottery.com']:
    print(pat, text.count(pat))

for m in re.finditer(r'https?://[^"\']*', text):
    u = m.group(0)
    if 'TLCAPI' in u or 'lotto' in u.lower() or 'api.taiwanlottery.com' in u:
        print('url', u)
        if len(u) > 200: break

for m in re.finditer(r'"([^"]*TLC[^"]*)"', text):
    print('str', m.group(1))
    break

for m in re.finditer(r"['\"](/[^'\"]*lotto[^'\"]*)['\"]", text, re.I):
    print('path', m.group(1))
    break
