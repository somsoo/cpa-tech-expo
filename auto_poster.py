import sys
sys.stdout.reconfigure(encoding='utf-8')
import os
import json
import random
import re
import time
import datetime
import requests
import urllib.parse
from PIL import Image, ImageDraw, ImageFont
import google.generativeai as genai
import keyword_miner

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

def generate_with_retry(prompt, is_json=False):
    for key in API_KEYS:
        genai.configure(api_key=key)
        for model_name in MODELS:
            try:
                model = genai.GenerativeModel(model_name)
                config = genai.GenerationConfig(response_mime_type="application/json") if is_json else None
                res = model.generate_content(prompt, generation_config=config)
                if res.text and res.text.strip():
                    text = res.text.strip()
                    if is_json:
                        text = text.replace('```json', '').replace('```', '').strip()
                    return text
            except Exception as e:
                time.sleep(1)
                continue
    raise Exception("Critical: All Gemini models failed!")

def create_text_thumbnail(text, filename_prefix):
    try:
        img_width, img_height = 1200, 675
        img = Image.new('RGB', (img_width, img_height), color=(15, 23, 42))
        draw = ImageDraw.Draw(img)
        
        for y in range(img_height):
            r = int(15 + (y / img_height) * 20)
            g = int(23 + (y / img_height) * 35)
            b = int(42 + (y / img_height) * 60)
            draw.line([(0, y), (img_width, y)], fill=(r, g, b))
            
        lines = [l.strip() for l in text.split('\n') if l.strip()][:2]
        if not lines: lines = ["2026 데이터센터코리아 사전등록", "핵심 실무 가이드"]
        
        font = None
        for font_path in [
            "C:/Windows/Fonts/malgunbd.ttf",
            "C:/Windows/Fonts/malgun.ttf",
            "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
            "/usr/share/fonts/truetype/nanum/NanumSquareB.ttf"
        ]:
            if os.path.exists(font_path):
                try:
                    font = ImageFont.truetype(font_path, 64)
                    break
                except: pass
        if not font: font = ImageFont.load_default()
            
        draw.rectangle([40, 40, img_width-40, img_height-40], outline=(59, 130, 246), width=3)
        
        y_text = (img_height // 2) - (len(lines) * 45)
        for line in lines:
            try:
                bbox = draw.textbbox((0, 0), line, font=font)
                width = bbox[2] - bbox[0]
                height = bbox[3] - bbox[1]
            except:
                width = len(line) * 25
                height = 50
            draw.text(((img_width - width) / 2, y_text), line, font=font, fill=(255, 255, 255))
            y_text += height + 30
            
        os.makedirs('assets/images', exist_ok=True)
        img_path = f'assets/images/{filename_prefix}.webp'
        img.save(img_path, 'WEBP', quality=85)
        return img_path
    except Exception as e:
        print(f"Thumbnail error: {e}")
        return ""

def download_vibe_image(img_url, filename_prefix):
    if not img_url: return ""
    try:
        import io
        os.makedirs('assets/images', exist_ok=True)
        img_r = requests.get(img_url, timeout=10)
        image = Image.open(io.BytesIO(img_r.content))
        clean_img = Image.new(image.mode, image.size)
        try:
            clean_img.putdata(list(image.getdata()))
        except:
            clean_img = image.copy()
        base_width = 800
        if clean_img.size[0] > base_width:
            wpercent = (base_width / float(clean_img.size[0]))
            hsize = int((float(clean_img.size[1]) * float(wpercent)))
            clean_img = clean_img.resize((base_width, hsize), Image.Resampling.LANCZOS)
        img_path = f'assets/images/{filename_prefix}.webp'
        clean_img.save(img_path, 'WEBP', quality=85)
        return img_path
    except:
        return ""

def generate_post(campaign, keyword):
    print(f"Pass 1/3: Generating Grounded Draft on '{keyword}'...")
    
    draft_prompt = f"""당신은 글로벌 배터리·테크 산업 전문 테크니컬 리서처입니다.
'{keyword}'에 대해 독자가 가장 궁금해하는 핵심 실무/정보를 담은 1800자 분량의 전문 블로그 초안을 작성하세요.

[초안 작성 필수 조건]
1. 4개의 H2(## ) 소제목 구조로 구성하세요. 최상위 제목(# H1)은 절대 쓰지 마세요.
2. 각 H2 소제목 바로 다음 줄에 정확히 '[VIBE_IMAGE_HERE]'를 단독 줄로 1회씩 배치하세요.
3. 구체적인 통계 수치와 마크다운 비교 표(Table), 실천 체크리스트를 포함하세요.
4. "완전 무료", "공짜", "수익 보장", "100% 당첨" 같은 과장 광고성 단어는 엄격히 금지합니다.
5. 어색한 챗봇 인사말(안녕하세요 등)이나 결언(결론적으로 등)은 일체 배제하고, 독자의 결핍과 문제의식으로 곧바로 시작하세요."""

    draft = generate_with_retry(draft_prompt)

    print("Pass 2/3: Running Incisive Critic Audit (AI Smell & Ad Cliches)...")
    critic_prompt = f"""당신은 엄격한 수석 편집장입니다.
다음 초안을 읽고 개선해야 할 핵심 단점 3가지를 신랄하게 지적하세요:
1. AI 특유의 번역투, 기계적인 말투, 작위적 추임새(하하, 자 그럼, 현대 사회에서, 알아보겠습니다, 살펴보겠습니다 등) 여부
2. 과장되거나 상투적인 광고/홍보성 냄새(약장수 같은 문체) 여부
3. 뻔한 교과서 설명에 그치지 않고 실제 독자에게 피가 되고 살이 되는 현실적 팁과 통찰이 있는지 여부

[초안]:
{draft}"""

    critique = generate_with_retry(critic_prompt)

    print("Pass 3/3: Executing Final Humanized Rewrite & Meta Generation...")
    rewrite_prompt = f"""당신은 상위 1% 전문 저널리스트이자 수석 에디터입니다.
아래 [초안]에 [수석 편집장 비판]을 100% 수용하여 결함을 완벽히 뜯어고친 최종 2,000자 내외의 고품질 블로그 원고를 완성하세요.

[핵심 서술 및 클린업 규칙]
1. 인공지능 특유의 기계적 말투와 번역투를 완전히 제거하고, 실제 사람이 직접 취재해 쓴 것처럼 유려하고 자연스러운 호흡으로 작성하세요.
2. 소제목은 반드시 '## '(H2) 또는 '### '(H3)만 사용하세요. 최상위 제목(# H1)은 절대 쓰지 마세요.
3. 각 H2 소제목 바로 다음 줄에 정확히 '[VIBE_IMAGE_HERE]'를 유지하세요.
4. 대괄호 지시어(예: [3단계 ...])를 소제목으로 노출하지 말고 자연스러운 명사형 소제목으로 다듬으세요.
5. 마크다운 코드 블록(```)으로 전체 본문을 감싸지 마세요.
6. 외부 제휴 링크는 본문에 절대 넣지 마세요 (순수 정보글).

[전문가 비판]:
{critique}

[초안]:
{draft}

반드시 본문 작성이 끝난 후, 맨 마지막 줄에 아래 구분자 사이에 메타데이터 JSON을 정확히 첨부하세요:
---METADATA_START---
{{
  "title": "{keyword} 관련 매력적인 1줄 제목 (광고 냄새 없는)",
  "thumb_hook": "{keyword}\\n핵심 실무 가이드 (줄바꿈 \\n)",
  "vibe_keywords": "technology battery future",
  "meta_description": "150자 이내의 검색 최적화 요약문"
}}
---METADATA_END---"""

    rewrite_output = generate_with_retry(rewrite_prompt)

    meta = {}
    if '---METADATA_START---' in rewrite_output and '---METADATA_END---' in rewrite_output:
        parts = rewrite_output.split('---METADATA_START---')
        final_draft = parts[0].strip()
        meta_json_str = parts[1].split('---METADATA_END---')[0].strip()
        try:
            meta = json.loads(meta_json_str)
        except: pass
    else:
        final_draft = rewrite_output.strip()

    title = meta.get('title', f"{keyword} 핵심 가이드")
    thumb_hook = meta.get('thumb_hook', f"{keyword}\\n완벽 분석")
    vibe_keywords = meta.get('vibe_keywords', 'technology battery future')
    meta_desc = meta.get('meta_description', '')

    # AI 클리셰 정제 필터
    final_draft = re.sub(r'^#\s+(.+)$', r'## \1', final_draft, flags=re.MULTILINE)
    final_draft = re.sub(r'^(?:하하[!,~]?\s*|자,\s*그럼\s*|현대\s*사회[는에서]?\s*)', '', final_draft, flags=re.MULTILINE)
    final_draft = re.sub(r'\[(?:\d+단계|[가-힣\s]+체크리스트|[가-힣\s]+절차)\]', r'### 핵심 실천 및 준비 절차', final_draft)
    final_draft = re.sub(r'(?i)^(?:#+\s*)?H[23]:\s*', '', final_draft, flags=re.MULTILINE)
    final_draft = re.sub(r'^---.*?---\s*', '', final_draft, flags=re.DOTALL)
    final_draft = re.sub(r'\[([^\]]+)\]\((?:https?:\/\/)[^\)]*\)', r'\1', final_draft)

    # Pixabay 이미지 처리
    image_urls = []
    try:
        url = f"https://pixabay.com/api/?key=57366919-c2774ae5199cc6a6cdb9a301d&q={urllib.parse.quote(vibe_keywords)}&image_type=photo&orientation=horizontal&per_page=5"
        r = requests.get(url, timeout=10)
        data = r.json()
        if data.get('hits'):
            image_urls = [hit.get('largeImageURL', hit.get('webformatURL')) for hit in data['hits']]
    except: pass

    parts = final_draft.split('[VIBE_IMAGE_HERE]')
    processed_text = parts[0]
    img_idx = 0
    for part in parts[1:]:
        v_path = ""
        if img_idx < len(image_urls):
            v_path = download_vibe_image(image_urls[img_idx], f"vibe_{int(time.time())}_{img_idx}")
            img_idx += 1
        if v_path:
            alt_text = f"{keyword} 핵심 안내 인포그래픽 {img_idx}"
            processed_text += f"\n\n![{alt_text}]({{ '/' | append: '{v_path}' | relative_url }})\n\n"
        processed_text += part

    thumb_filename = f"thumb_{int(time.time())}"
    thumb_rel_path = create_text_thumbnail(thumb_hook, thumb_filename)

    # 허브 앤 스포크 핵심: 외부 링크 0개! 내 사이트 대표 가이드북(/guide/) 내부 링크 박스
    cpa_guide_box = f"""
<div style="margin: 35px 0; padding: 22px 24px; text-align: center; border: 2px solid #3b82f6; border-radius: 14px; background-color: #f0f7ff; box-shadow: 0 4px 6px rgba(59,130,246,0.08);">
    <h3 style="color: #1d4ed8; margin-bottom: 8px; font-weight: bold; font-size: 19px; word-break: keep-all;">💡 {campaign['name']} 상세 일정 및 공식 가이드</h3>
    <p style="font-size: 15px; margin-bottom: 18px; color: #475569; word-break: keep-all; line-height: 1.6;">
        2026년 최신 개정 혜택, 신청 절차 및 공식 지원 요건에 관한 종합 안내는 대표 가이드북에서 확인하실 수 있습니다.
    </p>
    <a href="{{ '/guide/' | relative_url }}" style="display: block; width: 100%; max-width: 360px; margin: 0 auto; padding: 15px 20px; box-sizing: border-box; background-color: #2563eb; color: #ffffff; font-size: 16px; font-weight: bold; text-decoration: none; border-radius: 8px; box-shadow: 0 4px 6px rgba(37,99,235,0.25); word-break: keep-all;">
        👉 공식 종합 가이드북 바로가기 ▶
    </a>
</div>
"""
    attribution_notice = """
<div style="margin: 35px 0; padding: 16px 20px; border-left: 4px solid #3b82f6; background-color: #f8fafc; font-size: 13px; color: #475569; line-height: 1.6;">
    <strong>공공 정보 및 가이드라인 공시:</strong> 본 안내문은 한국전지산업협회 및 코엑스 인터배터리 공식 사무국 공시를 기준으로 작성되었습니다.
</div>
"""
    final_text = processed_text + cpa_guide_box + attribution_notice
    return title, final_text, thumb_rel_path, meta_desc

def main():
    print("=== Starting 3-Pass Long-tail CPA Spoke Post Generation ===")
    keyword, campaign = keyword_miner.get_golden_longtail_keyword()
    print(f"Target Long-tail Keyword: {keyword}")
    print(f"Campaign: {campaign.get('name')}")
    
    title, post_content, thumb_path, meta_desc = generate_post(campaign, keyword)
    
    if post_content:
        date_str = datetime.datetime.now().strftime('%Y-%m-%d')
        clean_kw = re.sub(r'[^a-zA-Z0-9가-힣\s\-]', '', keyword).strip()
        safe_title = re.sub(r'[\s\-]+', '-', clean_kw).strip('-').lower()
        if not safe_title or safe_title == '-':
            safe_title = f"post-{int(time.time())}"
        filename = f'_posts/{date_str}-{safe_title}.md'
        os.makedirs('_posts', exist_ok=True)
        
        front_matter = f"""---
layout: post
title: "{title}"
date: {date_str}
image: {thumb_path}
description: "{meta_desc}"
---

"""
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(front_matter + post_content)
        print(f"Successfully generated post: {filename}")
        
        log_line = f"- [{date_str}] | [Tenping] {campaign.get('name')} | {title} -> `{filename}`\n"
        with open('POST_LOG.md', 'a', encoding='utf-8') as f:
            f.write(log_line)
        print("Logged to POST_LOG.md")

if __name__ == "__main__":
    main()
