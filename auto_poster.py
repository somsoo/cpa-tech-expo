import os
import json
import random
from datetime import datetime
import google.generativeai as genai

# Setup Gemini API
api_key = os.environ.get('GEMINI_API_KEY')
if not api_key:
    print('GEMINI_API_KEY is not set!')
    exit(1)

genai.configure(api_key=api_key)
models = ['gemini-3.5-flash-lite', 'gemini-3.1-flash-lite']

def generate_post(campaign, keyword):
    # --- 1차 작성 (Draft) ---
    draft_prompt = f'''
    당신은 20대~60대 중장년층 및 구직자를 위한 유망 자격증 및 취업 정보를 전문으로 다루는 프로 블로거입니다.
    다음 캠페인 정보를 바탕으로 정보성 블로그 포스팅 초안을 작성해주세요.

    [캠페인 정보]
    - 주제: {keyword} (메인 키워드로 글 전체에 자연스럽게 반복)
    - 혜택: {campaign['benefits']}
    
    [🚨 절대 지켜야 할 엄격한 금지 규정 (위반 시 계정 정지)]
    {campaign['rules']}

    [작성 가이드]
    1. 글 길이는 1500자 이상.
    2. 무료 고화질 이미지를 삽입하세요. 마크다운 형식: ![이미지 설명](https://loremflickr.com/800/600/english_keyword) (english_keyword는 문맥에 맞게 변경, 최소 2장 이상).
    3. 글 내용 중에 절대 "제가 직접 해봤는데", "이 자격증을 따면 월 300만원을 법니다", "한 달 만에 무조건 땁니다", "무조건 취업시켜 줍니다" 같은 멘트를 쓰지 마세요.
    4. 독자가 안심하고 공식 홈페이지에 들어가서 무료 상담을 신청하도록 유도하세요.
    5. 글 맨 마지막에 아래 HTML 제휴 링크 코드를 그대로 삽입하세요.

    <div style="margin-top: 30px; padding: 20px; text-align: center; border: 2px solid #5c46b6; border-radius: 10px; background-color: #f8f9fa;">
        <h3 style="color: #5c46b6; margin-bottom: 15px;">🎁 간병사 자격증 전액 지원 & 취업지원금 무료 상담</h3>
        <p style="font-size: 16px; margin-bottom: 20px;">수강료 전액 지원 및 미취업시 최대 50만원 지원 혜택 자격을 지금 바로 확인해보세요!</p>
        <a href="{campaign['link']}" target="_blank" style="display: inline-block; padding: 15px 30px; background-color: #5c46b6; color: white; font-size: 18px; font-weight: bold; text-decoration: none; border-radius: 5px;">👉 내 지원 자격 무료 조회하기</a>
    </div>

    최상단에 YAML Frontmatter를 포함하세요 (layout: post, title: "클릭을 유도하는 매력적인 제목", date: YYYY-MM-DD HH:MM:SS +0900, categories: [자격증]).
    '''
    
    draft_text = None
    for model_name in models:
        try:
            print(f'1차 작성 시도 중 (Draft): {model_name}')
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(draft_prompt)
            if response.text:
                draft_text = response.text
                break
        except Exception as e:
            print(f'Draft Model {model_name} failed: {e}')
            
    if not draft_text:
        return None

    # --- 2차 검증 및 수정 (Review & Revise: SEO, GEO, AEO) ---
    eval_prompt = f'''
    당신은 세계 최고의 편집장이자 SEO/AEO/GEO 최적화 전문가입니다.
    아래 작성된 블로그 포스팅 초안을 평가하고 수정하세요.

    [초안 원본]
    {draft_text}

    [평가 기준 (총점 300점)]
    1. SEO (Search Engine Optimization): 키워드({keyword})의 자연스러운 배치, 헤딩(H2, H3) 구조, 가독성 (100점 만점)
    2. GEO (Generative Engine Optimization): AI 검색 엔진이 긁어가기 좋도록 명확한 구조화 데이터, 불릿 포인트 목록, 간결한 사실 전달 (100점 만점)
    3. AEO (Answer Engine Optimization): 독자가 궁금해하는 질문에 대한 명쾌한 '직접적인 답변' 포함 여부 (100점 만점)

    총점이 285/300점 미만이라고 판단된다면, 점수를 극대화할 수 있도록 글을 논리적으로 수정하고 발전시키세요. 
    가독성을 높이고, 전문적인 어휘를 사용하며, H2/H3 태그와 불릿 포인트를 적극 활용하세요.
    단, 초안에 있던 제휴 링크 HTML 코드와 이미지 삽입 코드, YAML Frontmatter 구조는 절대로 삭제하거나 훼손하지 마세요.
    텐핑 금지 규정(과장된 후기, 월급 명시, 취업 100% 보장 등)도 절대 위반하지 않도록 주의하세요.

    수정이 완료된 최종 마크다운 블로그 포스트 본문만 출력하세요. (평가 과정이나 점수는 출력하지 마세요.)
    '''

    final_text = draft_text
    for model_name in models:
        try:
            print(f'2차 검증 및 수정 시도 중 (Review & Revise): {model_name}')
            model = genai.GenerativeModel(model_name)
            revised_response = model.generate_content(eval_prompt)
            if revised_response.text and len(revised_response.text) > 500:
                final_text = revised_response.text
                break
        except Exception as e:
            print(f'Revise Model {model_name} failed: {e}')

    # --- 애드센스 벤치마킹 (CPA 전용 공통 코드) ---
    ad_top = '''
<div class="manual-ad-container" style="margin: 25px 0; text-align: center;">
    <ins class="adsbygoogle" style="display:block" data-ad-client="ca-pub-2228289204702106" data-ad-slot="2231432699" data-ad-format="auto" data-full-width-responsive="true"></ins>
    <script>(adsbygoogle = window.adsbygoogle || []).push({});</script>
</div>'''
    ad_middle = '''
<div class="manual-ad-container" style="margin: 25px 0; text-align: center;">
    <ins class="adsbygoogle" style="display:block" data-ad-client="ca-pub-2228289204702106" data-ad-slot="5979106011" data-ad-format="auto" data-full-width-responsive="true"></ins>
    <script>(adsbygoogle = window.adsbygoogle || []).push({});</script>
</div>'''

    cpa_button_mid = f'''
<div style="margin: 30px 0; padding: 20px; text-align: center; border: 2px dashed #ff5722; border-radius: 8px; background-color: #fff9f7;">
    <h3 style="color: #ff5722; margin-bottom: 10px;">⚡ {campaign['name']} - 기간 한정 혜택 안내</h3>
    <p style="font-size: 16px; margin-bottom: 15px; color: #333;">{campaign['benefits']}</p>
    <a href="{campaign['link']}" target="_blank" style="display: inline-block; padding: 12px 25px; background-color: #ff5722; color: white; font-size: 18px; font-weight: bold; text-decoration: none; border-radius: 5px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">👉 내 지원자격 1초만에 확인하기</a>
</div>
'''

    lines = final_text.split('\n')
    if len(lines) > 10:
        mid_idx = len(lines) // 3  # Place it roughly after the introduction (1/3rd of the way down)
        final_text = "\n".join(lines[:mid_idx]) + "\n" + cpa_button_mid + "\n" + ad_middle + "\n" + "\n".join(lines[mid_idx:])
        
    final_text = ad_top + "\n" + final_text

    return final_text

def main():
    with open('campaigns.json', 'r', encoding='utf-8-sig') as f:
        campaigns = json.load(f)
    
    campaign = random.choice(campaigns)
    keyword = random.choice(campaign['keywords'])
    print(f'Selected Campaign: {campaign["name"]} | Keyword: {keyword}')
    
    post_content = generate_post(campaign, keyword)
    
    if post_content:
        date_str = datetime.now().strftime('%Y-%m-%d')
        safe_title = keyword.replace(' ', '-')
        filename = f'_posts/{date_str}-{safe_title}.md'
        
        os.makedirs('_posts', exist_ok=True)
        
        frontmatter = f"""---
layout: post
title: "{keyword}"
date: {date_str}
---

"""
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(frontmatter + post_content)
        print(f'Successfully generated {filename}')
    else:
        print('Failed to generate post.')

if __name__ == '__main__':
    main()
