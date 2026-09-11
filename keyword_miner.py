import sys
sys.stdout.reconfigure(encoding='utf-8')
import os
import json
import time
import hmac
import hashlib
import base64
import requests
import urllib.parse
import random
import google.generativeai as genai

NAVER_CUSTOMER_ID = os.getenv('NAVER_CUSTOMER_ID', '1560667')
NAVER_ACCESS_LICENSE = os.getenv('NAVER_ACCESS_LICENSE', '0100000000275b3c8ab39dd56bad01b6c00904dfb52a7b55ec7176e7e42c48521f51cc0117')
NAVER_SECRET_KEY = os.getenv('NAVER_SECRET_KEY', 'AQAAAAAnWzyKs53Va60BtsAJBN+19kZUXy+tl4BrNzcRhWmIWw==')

api_keys_str = os.getenv("GEMINI_API_KEY", "") or os.getenv("GEMINI_GLOBAL_KEY", "")
if not api_keys_str:
    secrets_path = r"C:\Users\hsm29\Documents\total-system-dashboard\global_secrets.env"
    if os.path.exists(secrets_path):
        with open(secrets_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("GEMINI_GLOBAL_KEY=") or line.startswith("GEMINI_API_KEY="):
                    api_keys_str = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break
API_KEYS = [k.strip() for k in api_keys_str.split(',') if k.strip()]
MODELS = ['gemini-3.5-flash-lite', 'gemini-3.1-flash-lite']

def generate_with_retry(prompt):
    for key in API_KEYS:
        genai.configure(api_key=key)
        for model_name in MODELS:
            try:
                model = genai.GenerativeModel(model_name)
                res = model.generate_content(prompt)
                if res.text and res.text.strip():
                    return res.text.strip()
            except:
                time.sleep(1)
                continue
    return ""

def get_naver_signature(timestamp, method, path):
    message = f"{timestamp}.{method}.{path}"
    sign = hmac.new(NAVER_SECRET_KEY.encode('utf-8'), message.encode('utf-8'), hashlib.sha256)
    return base64.b64encode(sign.digest()).decode()

def mine_naver_ad_keywords(hint_keyword):
    path = '/keywordstool'
    url = 'https://api.naver.com' + path
    timestamp = str(int(round(time.time() * 1000)))
    headers = {
        'X-Timestamp': timestamp,
        'X-API-KEY': NAVER_ACCESS_LICENSE,
        'X-Customer': str(NAVER_CUSTOMER_ID),
        'X-Signature': get_naver_signature(timestamp, 'GET', path)
    }
    try:
        r = requests.get(url, params={'hintKeywords': hint_keyword, 'showDetail': 1}, headers=headers, timeout=10)
        if r.status_code == 200:
            items = r.json().get('keywordList', [])
            return [it.get('relKeyword', '').strip() for it in items if it.get('relKeyword')]
    except: pass
    return []

def mine_autocomplete_keywords(hint_keyword):
    results = set()
    try:
        url = f"https://ac.search.naver.com/nx/ac?q={urllib.parse.quote(hint_keyword)}&con=1&frm=nv&ans=2&r_format=json&r_enc=UTF-8&r_unicode=0&t_koreng=1&run=2&rev=4&q_enc=UTF-8&st=100"
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
        if r.status_code == 200:
            for item in r.json().get('items', [[]])[0]:
                results.add(item[0])
    except: pass
    try:
        url = f"http://suggestqueries.google.com/complete/search?client=firefox&q={urllib.parse.quote(hint_keyword)}"
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
        if r.status_code == 200:
            for item in r.json()[1]:
                results.add(item)
    except: pass
    return list(results)

def get_golden_longtail_keyword(campaigns_file='campaigns.json', history_file='used_keywords.txt'):
    with open(campaigns_file, 'r', encoding='utf-8-sig') as f:
        campaigns = json.load(f)
    campaign = campaigns[0] if isinstance(campaigns, list) else campaigns
    
    used = set()
    if os.path.exists(history_file):
        with open(history_file, 'r', encoding='utf-8') as f:
            used = set([line.strip() for line in f if line.strip()])
            
    seed_keywords = campaign.get('keywords', ['인터배터리 & 미래 테크 엑스포'])
    hint = seed_keywords[0] if seed_keywords else '인터배터리 & 미래 테크 엑스포'
    
    candidates = set()
    candidates.update(mine_naver_ad_keywords(hint))
    candidates.update(mine_autocomplete_keywords(hint))
    candidates.update(seed_keywords)
    
    filtered = [kw.strip() for kw in candidates if kw.strip() and kw.strip() not in used and len(kw.strip()) >= 3]
    
    if not filtered:
        prompt = f"'{campaign["name"]}'에 대해 실제 사용자들이 네이버/구글에 검색할 만한 구체적인 질문형 롱테일 검색어 30개를 줄바꿈으로만 출력하세요."
        res = generate_with_retry(prompt)
        for line in res.splitlines():
            line = line.strip().lstrip('0123456789.- ')
            if line and line not in used:
                filtered.append(line)
                
    golden_keyword = random.choice(filtered) if filtered else f"{hint} 2026 가이드"
    with open(history_file, 'a', encoding='utf-8') as f:
        f.write(golden_keyword + '\n')
    return golden_keyword, campaign
