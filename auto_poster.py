
import os
import json
import random
from datetime import datetime
import google.generativeai as genai
import pytz

# Setup Gemini
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("GEMINI_API_KEY is not set.")
    exit(1)

genai.configure(api_key=api_key)
# Using flash model, but structure prevents formatting errors
model = genai.GenerativeModel('gemini-1.5-flash')

# Load campaigns
campaigns_file = 'campaigns.json'
if not os.path.exists(campaigns_file):
    print("No campaigns.json found.")
    exit(1)

with open(campaigns_file, 'r', encoding='utf-8') as f:
    campaigns = json.load(f)

if not campaigns:
    print("No campaigns available.")
    exit(1)

# Select random campaign
campaign = random.choice(campaigns)

# System Prompt for 2-Pass Generation (Content ONLY, NO Frontmatter)
prompt = f"""
당신은 최고의 제휴마케팅(CPA) 카피라이터입니다.
다음 캠페인 정보를 바탕으로 블로그 포스팅 '본문'만 작성하세요. 
절대 YAML Frontmatter(--- layout: post ... ---)를 작성하지 마세요. 오직 마크다운 본문 텍스트만 출력하세요.

[캠페인 정보]
- 이름: {campaign['name']}
- 혜택: {campaign['benefits']}
- 타겟 및 규칙: {campaign['rules']}
- 링크: {campaign['link']}
- 키워드: {', '.join(campaign.get('keywords', []))}

[2-Pass 작성 로직]
1. (Pass 1) 창의적인 스토리텔링 초안을 작성합니다. 타겟의 고충을 자극하고 혜택을 강조하세요.
2. (Pass 2) 초안을 검토하며 금지어나 규칙 위반이 없는지 확인하고, 최종적으로 가장 자연스럽고 설득력 있는 완벽한 본문을 생성하세요.

[필수 구조]
1. 글 중간중간에 자연스럽게 버튼 형태의 CPA 링크를 2회 이상 삽입하세요.
(버튼 HTML 예시: <div style="text-align: center; margin: 20px 0;"><a href="{campaign['link']}" style="background-color: #ff5722; color: white; padding: 15px 25px; text-decoration: none; border-radius: 5px; font-weight: bold; font-size: 18px;" target="_blank">👉 무료 상담 신청하기</a></div>)
2. 글의 내용과 어울리는 고화질 언스플래쉬 이미지 URL(https://source.unsplash.com/800x600/?키워드)을 마크다운 형태로 2장 이상 삽입하세요.

출력은 2-Pass를 거친 최종 '본문 내용'만 해주세요.
"""

response = model.generate_content(prompt)
body_content = response.text.strip()

# Strip any rogue frontmatter if AI hallucinates it
import re
body_content = re.sub(r'^---.*?---\s*', '', body_content, flags=re.DOTALL)
body_content = re.sub(r'—\s*layout:.*?—\s*', '', body_content, flags=re.DOTALL)

# Python handles the exact Frontmatter
kst = pytz.timezone('Asia/Seoul')
now = datetime.now(kst)
date_str = now.strftime('%Y-%m-%d %H:%M:%S +0900')
file_date_str = now.strftime('%Y-%m-%d')
file_time_str = now.strftime('%H-%M-%S')

# Generate a creative title
title_prompt = f"이 글은 구글 검색 유입(SEO)을 극대화해야 합니다. 타겟 고객이 검색할 만한 '롱테일 키워드(세부 질문, 고민거리)'를 자연스럽게 포함하여 40~60자 길이의 제목을 작성하세요. 단순 광고처럼 보이지 않고, 유용한 '꿀팁 정보글'처럼 보여서 클릭하지 않고는 못 배기게 만드세요. ('{campaign['name']}' 캠페인 관련, 특수문자 제외, 본문 없이 제목만 출력)"
title_response = model.generate_content(title_prompt)
title = title_response.text.strip().replace('"', '').replace("'", "")

category = "정보"
if campaign.get('keywords'):
    category = campaign['keywords'][0]

frontmatter = f"""---
layout: post
title: "{title}"
date: {date_str}
categories: [{category}]
---
"""

final_post = frontmatter + "\n\n" + body_content

os.makedirs('_posts', exist_ok=True)
filename = f"_posts/{file_date_str}-{file_time_str}.md"
with open(filename, 'w', encoding='utf-8') as f:
    f.write(final_post)

print(f"Generated {filename}")
