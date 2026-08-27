import os
import json
import random
import requests
import time
import urllib.parse
import re
from datetime import datetime
import google.generativeai as genai
import pytz
import io
try:
    from PIL import Image
except ImportError:
    pass

# =================================================================
# 1. API & Failover Setup (Dynamic Rotation)
# =================================================================
api_keys_str = os.environ.get('GEMINI_API_KEY', '')
if not api_keys_str:
    print('GEMINI_API_KEY is not set.')
    exit(1)

API_KEYS = [k.strip() for k in api_keys_str.split(',') if k.strip()]
MODELS = ['gemini-3.5-flash-lite', 'gemini-3.1-flash-lite']

def generate_with_retry(prompt, is_json=False):
    generation_config = {"response_mime_type": "application/json"} if is_json else None
    
    for key in API_KEYS:
        genai.configure(api_key=key)
        for model_name in MODELS:
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(prompt, generation_config=generation_config)
                return response.text
            except Exception as e:
                print(f"Fallback triggered: Failed on {model_name} with key ...{key[-4:]} -> {e}")
                time.sleep(2)
                continue
                
    raise Exception("Critical: All API keys and models are exhausted!")

# =================================================================
# 2. Load Campaigns
# =================================================================
campaigns_file = 'campaigns.json'
if not os.path.exists(campaigns_file):
    print('No campaigns.json found.')
    exit(1)

with open(campaigns_file, 'r', encoding='utf-8') as f:
    campaigns = json.load(f)

if not campaigns:
    print('No campaigns available.')
    exit(1)

campaign = random.choice(campaigns)

# =================================================================
# 3. Real-time SEO Trend Extraction
# =================================================================
main_keyword = campaign.get('keywords', [campaign['name']])[0]
real_keywords = [main_keyword]
try:
    url = f'https://mac.search.naver.com/mobile/ac?q={main_keyword}&st=1&r_format=json&q_enc=UTF-8'
    res = requests.get(url, timeout=5)
    data = res.json()
    if 'items' in data and len(data['items']) > 0 and len(data['items'][0]) > 0:
        real_keywords = [item[0] for item in data['items'][0][:4]]
except Exception as e:
    print('Trend API fetch failed, using fallback:', e)

keyword_str = ', '.join(real_keywords)
print(f'Extracted Keywords: {keyword_str}')

# =================================================================
# 4. Text Generation (3-Pass: Write -> Check -> Revise)
# =================================================================
# [Pass 1: 글쓰기 (Write)]
draft_prompt = f"""
당신은 제휴마케팅(CPA) 전문가입니다. 다음 캠페인 정보를 바탕으로 블로그 포스팅 뼈대(초안)를 1500자 분량으로 작성하세요.

[캠페인 정보]
- 이름: {campaign['name']}
- 혜택: {campaign['benefits']}
- 주의규칙: {campaign['rules']}
- 링크: {campaign['link']}
- 타겟 키워드: {keyword_str}
"""
draft_content = generate_with_retry(draft_prompt).strip()

# [Pass 2: 검사 (Check for AEO/SEO/GEO)]
check_prompt = f"""
다음은 작성된 블로그 포스팅 초안입니다. 이 초안을 최고 수준의 SEO, AEO(답변 엔진 최적화), GEO(생성형 엔진 최적화) 전문가 관점에서 꼼꼼하게 검사(Check)하고 비판하세요.

[초안]
{draft_content}

[검사 지침]
1. SEO: 롱테일 키워드({keyword_str})가 제목, 서론, 본문에 자연스럽게 배치되었는가?
2. AEO: 사용자의 직접적인 질문에 명확하게 답변하는 '요약형 문단'이나 'FAQ 구조'가 있는가?
3. GEO: 지역 정보나 타겟 유저의 구체적 의도에 부합하는가?
위 세 가지 관점에서 무엇을 어떻게 수정해야 완벽해질지 5가지 피드백을 작성하세요.
"""
feedback_content = generate_with_retry(check_prompt).strip()

# [Pass 3: 수정 (Revise & Tone Polish)]
rewrite_prompt = f"""
당신은 수익형 블로그 상위 1% 인플루언서입니다. 
다음 [초안]에 [전문가 피드백]을 100% 반영하여, AEO/SEO/GEO가 완벽하게 충족된 최종 포스팅을 2000자 내외로 작성하세요(수정).
주의: AI 특유의 번역투 문장('결론적으로', '안녕하세요 여러분')을 완벽히 삭제하고, 실제 사람이 친한 지인에게 꿀팁을 주듯 매우 자연스럽고 공감 가는 말투로 윤문하세요.

[전문가 피드백 (반드시 반영할 것)]
{feedback_content}

[초안]
{draft_content}

[필수 구조 규칙]
글 중간중간에 자연스럽게 아래 버튼 태그를 2개 이상 삽입하세요. 
<div style="text-align: center; margin: 20px 0;"><a href="{campaign['link']}" style="background-color: #ff5722; color: white; padding: 15px 25px; text-decoration: none; border-radius: 5px; font-weight: bold; font-size: 18px;" target="_blank">👉 무료 상담 신청하기</a></div>
"""
body_content = generate_with_retry(rewrite_prompt).strip()

body_content = re.sub(r'^---.*?---\s*', '', body_content, flags=re.DOTALL)
body_content = re.sub(r'^\s*layout:.*?\n\s*', '', body_content, flags=re.DOTALL)

# =================================================================
# 5. Image Generation (Optimized for SEO - WebP Compression)
# =================================================================
# [Pass 4: 심플 프롬프트 기반 실사 상징물 이미지 기획]
image_prompt_gen = f"""
Based on the topic "{main_keyword}", choose ONE symbolic inanimate object (e.g. golden coin, spray bottle, dog toy) that visually represents the core topic.
Do NOT include humans or complex landscapes. 
Output JSON only:
{{
    "object": "specific object name in English (e.g., golden coin, red rubber dog toy)"
}}
"""
try:
    img_response_text = generate_with_retry(image_prompt_gen, is_json=True)
    import json
    img_data = json.loads(img_response_text)
    obj_name = img_data.get('object', 'abstract object')
except Exception as e:
    obj_name = 'simple object'

final_img_prompt = f'A realistic photograph of a {obj_name} on a clean desk, bright natural lighting, simple and clear'
encoded_prompt = urllib.parse.quote(final_img_prompt)

kst = pytz.timezone('Asia/Seoul')
now = datetime.now(kst)
file_date_str = now.strftime('%Y-%m-%d')
file_time_str = now.strftime('%H-%M-%S')

os.makedirs('assets/images', exist_ok=True)
image_filename = f'{file_date_str}-{file_time_str}.webp'
image_path = f'assets/images/{image_filename}'

print('Requesting Pollinations Image...')
time.sleep(5)
img_url = f'https://image.pollinations.ai/prompt/{encoded_prompt}?width=800&height=800&nologo=true&private=true&model=flux'
try:
    r = requests.get(img_url, timeout=120)
    if r.status_code == 200:
        img_raw = Image.open(io.BytesIO(r.content))
        if img_raw.mode in ("RGBA", "P"):
            img_raw = img_raw.convert("RGB")
        img_raw.thumbnail((800, 800), Image.Resampling.LANCZOS)
        img_raw.save(image_path, "WEBP", quality=80)
        
        markdown_image = f'\n\n![{keyword_str} 관련 실사 3D 아이콘](/{image_path})\n\n'
        insert_pos = body_content.find('\n', 150)
        if insert_pos == -1:
            insert_pos = 150
        body_content = body_content[:insert_pos] + markdown_image + body_content[insert_pos:]
    else:
        print(f'Failed to fetch image: {r.status_code}')
except Exception as e:
    print(f'Image processing skipped due to error: {e}')

# =================================================================
# 6. Generate Title & Save Post
# =================================================================
title_prompt = f"""이 글의 검색 상위 노출을 위해 클릭 유도하는 제목을 작성하세요.
타겟 롱테일 키워드: [{keyword_str}]
키워드를 포함하여 40~60자 길이의 매력적인 제목을 한 줄만 출력하세요. (특수문자 제외)"""
title = generate_with_retry(title_prompt).strip().replace('"', '').replace("'", "")

category = '정보'
if campaign.get('keywords'):
    category = campaign['keywords'][0]

date_str = now.strftime('%Y-%m-%d %H:%M:%S +0900')
frontmatter = f"""---
layout: post
title: "{title}"
date: {date_str}
categories: [{category}]
---
"""
final_post = frontmatter + '\n\n' + body_content
os.makedirs('_posts', exist_ok=True)
filename = f'_posts/{file_date_str}-{file_time_str}.md'
with open(filename, 'w', encoding='utf-8') as f:
    f.write(final_post)

print(f'Generated {filename}')
