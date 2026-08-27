import os
import requests
import json
import random
import time
import base64
import hmac
import hashlib
import google.generativeai as genai
import xml.etree.ElementTree as ET

def generate_with_retry(prompt, is_json=False):
    api_keys_str = os.environ.get('GEMINI_API_KEY', '')
    if not api_keys_str:
        raise ValueError('GEMINI_API_KEY is not set.')
    API_KEYS = [k.strip() for k in api_keys_str.split(',') if k.strip()]
    MODELS = ['gemini-3.5-flash-lite', 'gemini-3.1-flash-lite']
    
    generation_config = {"response_mime_type": "application/json"} if is_json else None
    
    for key in API_KEYS:
        genai.configure(api_key=key)
        for model_name in MODELS:
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(prompt, generation_config=generation_config)
                return response.text
            except Exception as e:
                time.sleep(2)
                continue
    raise Exception("Critical: All API keys and models exhausted in keyword_miner!")

def get_naver_news_seeds(query):
    # Uses NCP Naver Search API
    client_id = os.environ.get("NAVER_CLIENT_ID", "yfjf88u5j9") # Defaulting to known
    client_secret = os.environ.get("NAVER_CLIENT_SECRET", "caO9XsoqsjFbsZv60ruCAFx41diF7vA8aOyoMI8a")
    
    url = f"https://openapi.naver.com/v1/search/news.json?query={query}&display=15"
    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret
    }
    
    try:
        res = requests.get(url, headers=headers, timeout=5)
        data = res.json()
        headlines = [item['title'] for item in data.get('items', [])]
        return headlines
    except Exception as e:
        print(f"Naver News API error: {e}")
        return []

def get_searchad_data(keywords):
    # Naver Search Ad API (keywordstool)
    api_key = os.environ.get("NAVER_SEARCH_AD_API_KEY", "")
    secret_key = os.environ.get("NAVER_SEARCH_AD_SECRET_KEY", "")
    customer_id = os.environ.get("NAVER_SEARCH_AD_CUSTOMER_ID", "")
    
    if not api_key:
        return None
        
    timestamp = str(int(time.time() * 1000))
    method = "GET"
    uri = "/keywordstool"
    message = f"{timestamp}.{method}.{uri}"
    signature = base64.b64encode(hmac.new(secret_key.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).digest()).decode("utf-8")
    
    headers = {
        "X-Timestamp": timestamp,
        "X-API-KEY": api_key,
        "X-Customer": str(customer_id),
        "X-Signature": signature
    }
    
    kwd_str = ",".join([k.replace(" ", "") for k in keywords])
    url = f"https://api.naver.com/keywordstool?hintKeywords={kwd_str}&showDetail=1"
    try:
        res = requests.get(url, headers=headers, timeout=10)
        return res.json().get('keywordList', [])
    except Exception as e:
        print(f"SearchAd API error: {e}")
        return None

def get_golden_keyword_kr(seed_category):
    history_file = 'posted_history.txt'
    history = []
    if os.path.exists(history_file):
        with open(history_file, 'r', encoding='utf-8') as f:
            history = [line.strip().lower() for line in f if line.strip()]

    # STEP 1: Get News Headlines based on category
    headlines = get_naver_news_seeds(seed_category)
    if not headlines:
        headlines = [seed_category]

    # STEP 2: Extract Noun Seeds using AI
    prompt = f"""
    아래 네이버 뉴스 헤드라인들을 분석해서, 오늘 한국 사람들이 당장 검색해 볼 만한 핵심 씨앗 명사를 5개만 추출해 줘. (예: 금투세, 주택담보대출, 특정 상품명 등)
    출력은 반드시 JSON 형식으로만 해.
    {{
        "seeds": ["명사1", "명사2", "명사3", "명사4", "명사5"]
    }}
    
    [Headlines]:
    {chr(10).join(headlines)}
    """
    try:
        res = generate_with_retry(prompt, is_json=True)
        seeds = json.loads(res).get('seeds', [])
    except:
        seeds = [seed_category]
        
    # STEP 3 & 4: SearchAd API Evaluation & History filtering
    searchad_results = get_searchad_data(seeds)
    if searchad_results:
        valid_keywords = []
        for item in searchad_results:
            kw = item['relKeyword'].lower()
            if kw in history: continue
            
            # monthlyPcQcCnt can be string "< 10"
            pc = item.get('monthlyPcQcCnt', 0)
            mobile = item.get('monthlyMobileQcCnt', 0)
            try:
                pc_val = int(pc) if isinstance(pc, (int, float)) else int(str(pc).replace('< ', ''))
                mob_val = int(mobile) if isinstance(mobile, (int, float)) else int(str(mobile).replace('< ', ''))
                total_vol = pc_val + mob_val
            except:
                total_vol = 0
                
            doc_cnt = item.get('monthlyBlogQcCnt', 0)
            
            if total_vol >= 1000:
                competition = doc_cnt / total_vol if total_vol > 0 else 999
                if competition <= 0.5:
                    valid_keywords.append((kw, total_vol, competition))
                    
        if valid_keywords:
            # Sort by search volume descending
            valid_keywords.sort(key=lambda x: x[1], reverse=True)
            best_kw = valid_keywords[0][0]
            with open(history_file, 'a', encoding='utf-8') as f:
                f.write(best_kw + '\n')
            return best_kw

    # FALLBACK if Naver SearchAd API fails or keys aren't set
    # Using Naver Autocomplete API
    for seed in seeds:
        try:
            url = f'https://mac.search.naver.com/mobile/ac?q={seed}&st=1&r_format=json&q_enc=UTF-8'
            res = requests.get(url, timeout=5)
            data = res.json()
            if 'items' in data and len(data['items']) > 0 and len(data['items'][0]) > 0:
                for item in data['items'][0]:
                    kw = item[0].lower()
                    if kw not in history:
                        with open(history_file, 'a', encoding='utf-8') as f:
                            f.write(kw + '\n')
                        return kw
        except: pass
        
    fallback = seeds[0]
    with open(history_file, 'a', encoding='utf-8') as f:
        f.write(fallback + '\n')
    return fallback
