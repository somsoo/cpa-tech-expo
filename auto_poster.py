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
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    pass

# =================================================================
# 1. API Setup
# =================================================================
api_keys_str = os.environ.get('GEMINI_API_KEY', '')
if not api_keys_str:
    print('GEMINI_API_KEY is not set.')
    exit(1)

API_KEYS = [k.strip() for k in api_keys_str.split(',') if k.strip()]

# [DYNAMIC_MODELS_PLACEHOLDER] - Replaced by mass patcher based on blog type
# CPA/Economy 블로그는 한도 관리를 위해 100% Lite 모델만 사용합니다 (6단계 분업)
THINK_MODELS = ['gemini-3.5-flash-lite', 'gemini-3.1-flash-lite']
WRITE_MODELS = ['gemini-3.5-flash-lite', 'gemini-3.1-flash-lite']

def generate_with_retry(prompt, is_json=False, step_type="write"):
    generation_config = {"response_mime_type": "application/json"} if is_json else None
    models_to_use = THINK_MODELS if step_type == "think" else WRITE_MODELS
    
    for key in API_KEYS:
        genai.configure(api_key=key)
        for model_name in models_to_use:
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(prompt, generation_config=generation_config)
                return response.text
            except Exception as e:
                print(f"Fallback triggered: Failed on {model_name} with key ...{key[-4:]} -> {e}")
                time.sleep(2)
                continue
    raise Exception(f"Critical: All API keys and {step_type} models exhausted!")

# =================================================================
# 2. Image Generation & Processing
# =================================================================
def create_text_thumbnail(text, filename_prefix="thumb"):
    lines = text.strip().split('\n')
    lines = [line for line in lines if line.strip()][:2]
    
    img_width = 800
    img_height = 800
    background_color = (92, 70, 182)
    text_color = (255, 255, 255)
    
    try:
        img = Image.new('RGB', (img_width, img_height), color=background_color)
        draw = ImageDraw.Draw(img)
        font_path = "/usr/share/fonts/truetype/nanum/NanumSquareB.ttf"
        
        try:
            font = ImageFont.truetype(font_path, 60)
        except:
            font = ImageFont.load_default()
            
        y_text = img_height // 3
        for line in lines:
            line = line.strip()
            if not line: continue
            try:
                bbox = draw.textbbox((0, 0), line, font=font)
                width = bbox[2] - bbox[0]
                height = bbox[3] - bbox[1]
            except:
                width = 400
                height = 60
            draw.text(((img_width - width) / 2, y_text), line, font=font, fill=text_color)
            y_text += height + 30
            
        os.makedirs('assets/images', exist_ok=True)
        img_path = f'assets/images/{filename_prefix}.webp'
        img.save(img_path, 'WEBP', quality=85)
        return img_path
    except Exception as e:
        print(f"Thumbnail error: {e}")
        return ""

def download_vibe_image(vibe_keywords, filename_prefix):
    try:
        url = f"https://pixabay.com/api/?key=25916942-02c31e217bbcfcf7e089d81d2&q={urllib.parse.quote(vibe_keywords)}&image_type=photo&orientation=horizontal&per_page=3"
        r = requests.get(url, timeout=10)
        data = r.json()
        if not data.get('hits'):
            return ""
        
        hit = data['hits'][0]
        img_url = hit.get('largeImageURL', hit.get('webformatURL'))
        if not img_url:
            return ""
            
        os.makedirs('assets/images', exist_ok=True)
        img_r = requests.get(img_url, timeout=10)
        try:
            image = Image.open(io.BytesIO(img_r.content))
            base_width = 800
            if image.size[0] > base_width:
                wpercent = (base_width / float(image.size[0]))
                hsize = int((float(image.size[1]) * float(wpercent)))
                image = image.resize((base_width, hsize), Image.Resampling.LANCZOS)
            img_path = f'assets/images/{filename_prefix}.webp'
            image.save(img_path, 'WEBP', quality=85)
            return img_path
        except:
            img_path = f'assets/images/{filename_prefix}.jpg'
            with open(img_path, 'wb') as f:
                f.write(img_r.content)
            return img_path
    except Exception as e:
        print(f"Pixabay failed: {e}")
        return ""

# =================================================================
# 3. 6-Step Dynamic Pipeline Core
# =================================================================
def generate_post(campaign, keyword):
    print(f"Starting 6-Step Pipeline for keyword: {keyword}")
    
    # [Step 1: Profiling]
    profile_prompt = f"""
당신은 최고 수준의 마케터입니다. 아래 캠페인과 키워드를 검색하는 '타겟 독자'를 3문장으로 분석하세요.
[키워드]: {keyword}
[캠페인 혜택]: {campaign['benefits']}
분석 내용: 독자의 성별/연령대, 가장 절실한 결핍(Pain point), 그리고 이 글의 적합한 톤앤매너(위로, 팩트폭격, 희망 등).
"""
    profiling = generate_with_retry(profile_prompt, step_type="think").strip()
    print("Step 1 (Profiling) Done.")

    # [Step 2: Outline]
    outline_prompt = f"""
당신은 블로그 기획자입니다. 다음 타겟 분석을 바탕으로 블로그 본문 목차(H2 3~4개, 각각 하위 H3 포함)를 설계하세요.
[분석]: {profiling}
출력: 마크다운 목차 형식으로만 출력.
"""
    outline = generate_with_retry(outline_prompt, step_type="think").strip()
    print("Step 2 (Outline) Done.")

    # [Step 3: Draft (Zero-shot Rule Framework)]
    draft_prompt = f"""
당신은 전문 카피라이터입니다. 아래 설계된 [목차]에 맞추어 1500자 분량의 블로그 초안을 작성하세요.

[캠페인 정보]: {campaign['name']}
[혜택]: {campaign['benefits']}
[타겟 분석]: {profiling}
[목차]:
{outline}

[CPA 절대 규칙]
1. 첫 문장은 독자의 결핍에 공감하며 시작.
2. 혜택은 반드시 글머리기호(-)를 써서 가독성을 높일 것.
3. 한 문단은 3줄을 넘지 않도록 짧게 끊어 칠 것.
4. "제가 해봤는데" 같은 가짜 후기 절대 금지.
5. 자연스러운 정보 전달 후, 마지막에 혜택을 강조할 것.
"""
    draft = generate_with_retry(draft_prompt, step_type="write").strip()
    print("Step 3 (Draft) Done.")

    # [Step 4: Critique]
    critique_prompt = f"""
당신은 냉혹한 SEO/AEO 전문가입니다. 다음 초안을 읽고 개선해야 할 약점 3가지를 신랄하게 지적하세요.
기준: 가독성, 기계적인 말투(AI 티가 나는지), 타겟 독자(결핍) 후킹 여부.
[초안]:
{draft}
"""
    critique = generate_with_retry(critique_prompt, step_type="think").strip()
    print("Step 4 (Critique) Done.")

    # [Step 5: Rewrite (Final Content)]
    button_html = f'<div style="text-align: center; margin: 20px 0;"><a href="{campaign["link"]}" style="background-color: #ff5722; color: white; padding: 15px 25px; text-decoration: none; border-radius: 5px; font-weight: bold; font-size: 18px;" target="_blank">👉 내 지원 자격 무료로 확인하기</a></div>'
    
    rewrite_prompt = f"""
당신은 상위 1% 원고 편집자입니다. [초안]에 [전문가 비판]을 100% 수용하여 최종 본문(2000자 내외)으로 윤문하세요.
인공지능 특유의 기계적인 말투를 완전히 제거하고 사람처럼 자연스럽게 작성하세요.

[전문가 비판]:
{critique}

[초안]:
{draft}

[시각적 강조 규칙]
1. 본문의 서론이 끝나는 지점과 글의 맨 마지막(결론) 지점에 아래 버튼 HTML 코드를 각각 1번씩(총 2번) 삽입하세요. 버튼 위에는 클릭을 유도하는 강력한 문장을 쓰세요.
{button_html}
2. 본문 중간(약 1/3 지점)에 [VIBE_IMAGE_HERE] 라는 텍스트를 정확히 1번 삽입하세요.
"""
    final_text = generate_with_retry(rewrite_prompt, step_type="write").strip()
    # Remove any stray frontmatter hallucinated by AI
    final_text = re.sub(r'^---.*?---\s*', '', final_text, flags=re.DOTALL)
    print("Step 5 (Rewrite) Done.")

    # [Step 6: Metadata (JSON)]
    meta_prompt = f"""
이 글에 대한 메타데이터를 JSON 형식으로만 출력하세요.
{{
    "title": "검색 상위노출을 위한 1줄짜리 후킹 제목 (키워드 '{keyword}' 포함)",
    "thumb_hook": "썸네일에 들어갈 2줄짜리 강력한 카피 (줄바꿈은 \\n 사용, 특수문자 최소화)",
    "vibe_keywords": "이 글의 분위기를 나타내는 영문 인테리어/라이프스타일 픽사베이 검색어 2개 (예: office,desk)"
}}
"""
    meta_json_str = generate_with_retry(meta_prompt, is_json=True, step_type="write").strip()
    try:
        meta = json.loads(meta_json_str)
        title = meta.get('title', f"{keyword} 핵심 정보").replace('"', '').replace("'", '')
        thumb_hook = meta.get('thumb_hook', f"[{keyword}]\n핵심 정보 확인하기")
        vibe_keywords = meta.get('vibe_keywords', 'office,desk')
    except:
        title = f"{keyword} 필수 정보 총정리"
        thumb_hook = f"[{keyword}]\n반드시 확인하세요"
        vibe_keywords = 'interior,clean'
    print("Step 6 (Metadata) Done.")

    # Asset Generation
    thumb_filename = f"thumb_{int(time.time())}"
    thumb_rel_path = create_text_thumbnail(thumb_hook, thumb_filename)
    image_markdown = f"![{keyword}]({{{{ '/' | append: '{thumb_rel_path}' | relative_url }}}})\n\n"

    safe_keyword = "".join(c if c.isalnum() else "-" for c in keyword).strip("-")
    vibe_rel_path = download_vibe_image(vibe_keywords, f"{safe_keyword}-vibe-{int(time.time())}")
    vibe_markdown = f"![{keyword} 관련 이미지 (출처: 픽사베이)]({{{{ '/' | append: '{vibe_rel_path}' | relative_url }}}})" if vibe_rel_path else ""

    # Replace Vibe Image Placeholder
    final_text = final_text.replace('[VIBE_IMAGE_HERE]', vibe_markdown)

    # AdSense Setup
    ad_top = '''<div class="manual-ad-container" style="margin: 25px 0; text-align: center;">\n    <ins class="adsbygoogle" style="display:block" data-ad-client="ca-pub-2228289204702106" data-ad-slot="2231432699" data-ad-format="auto" data-full-width-responsive="true"></ins>\n    <script>(adsbygoogle = window.adsbygoogle || []).push({});</script>\n</div>'''
    ad_middle = '''<div class="manual-ad-container" style="margin: 25px 0; text-align: center;">\n    <ins class="adsbygoogle" style="display:block" data-ad-client="ca-pub-2228289204702106" data-ad-slot="5979106011" data-ad-format="auto" data-full-width-responsive="true"></ins>\n    <script>(adsbygoogle = window.adsbygoogle || []).push({});</script>\n</div>'''
    ad_bottom = '''<div class="manual-ad-container" style="margin: 35px 0 10px 0; text-align: center;">\n    <ins class="adsbygoogle" style="display:block" data-ad-client="ca-pub-2228289204702106" data-ad-slot="2249895363" data-ad-format="auto" data-full-width-responsive="true"></ins>\n    <script>(adsbygoogle = window.adsbygoogle || []).push({});</script>\n</div>'''

    lines = final_text.split('\n')
    if len(lines) > 10:
        mid_idx = len(lines) // 2
        body_content = "\n".join(lines[:mid_idx]) + "\n\n" + ad_middle + "\n\n" + "\n".join(lines[mid_idx:])
    else:
        body_content = final_text
        
    final_body = image_markdown + ad_top + "\n\n" + body_content + "\n\n" + ad_bottom
    return title, final_body, thumb_rel_path

def main():
    if not os.path.exists('campaigns.json'):
        print("campaigns.json not found!")
        return
        
    with open('campaigns.json', 'r', encoding='utf-8') as f:
        campaigns = json.load(f)
    
    campaign = random.choice(campaigns)
    
    keyword_str = campaign.get('keywords', ['정보'])
    if isinstance(keyword_str, list):
        best_keyword = random.choice(keyword_str)
    else:
        best_keyword = keyword_str
        
    print(f'Selected Campaign: {campaign["name"]} | Keyword: {best_keyword}')
    
    title, body, thumb = generate_post(campaign, best_keyword)
    
    now = datetime.utcnow()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%Y-%m-%d %H:%M:%S")
    slug = "".join(c if c.isalnum() else "-" for c in title.lower())
    slug = "-".join(filter(None, slug.split("-")))[:50]
    if not slug:
        slug = str(int(time.time()))
        
    category = campaign['keywords'][0] if isinstance(campaign.get('keywords'), list) and campaign['keywords'] else "정보"
    
    filename = f"{date_str}-{slug}.md"
    filepath = os.path.join('_posts', filename)
    os.makedirs('_posts', exist_ok=True)
    
    frontmatter = f"---\nlayout: post\ntitle: \"{title}\"\ndate: {time_str} +0000\ncategories: [{category}]\n---\n\n{body}\n"
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(frontmatter)
        
    print(f'Successfully generated {filepath}')

if __name__ == "__main__":
    main()
