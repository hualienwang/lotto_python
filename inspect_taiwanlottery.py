import requests
import re

url = 'https://www.taiwanlottery.com/lotto/result/traditional'
resp = requests.get(url, timeout=20, verify=False)
print('status', resp.status_code)
text = resp.text
print('contains window.__NUXT__', 'window.__NUXT__' in text)
print('api.taiwanlottery.com count', text.count('api.taiwanlottery.com'))
print('TLCAPIWeB count', text.count('TLCAPIWeB'))
print('TLCAPI count', text.count('TLCAPI'))

scripts = re.findall(r'src=["\']([^"\']*_nuxt/[^"\']*)["\']', text)
print('scripts', len(scripts))
for s in scripts[:20]:
    print('  ', s)

for m in re.finditer(r'window\.__NUXT__\s*=\s*(\{.*?\});', text, re.S):
    snippet = m.group(1)
    print('NUXT payload length', len(snippet))
    print(snippet[:500])
    break

for m in re.finditer(r'https?://[^"\']*TLC[^"\']*', text):
    print('match', m.group(0))

for m in re.finditer(r'"([^"\']*lotto[^"\']*)"', text, re.I):
    print('lotto string', m.group(1))
    break
