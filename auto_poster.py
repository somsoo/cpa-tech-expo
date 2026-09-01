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
# 3. Keyword Extraction
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
best_keyword = real_keywords[0]

# =================================================================
# 4. Image Generation (Thumbnail + Vibe)
# =================================================================
def create_text_thumbnail(text, filename_prefix):
    os.makedirs('assets/images', exist_ok=True)
    img_path = f'assets/images/{filename_prefix}.webp'
    
    img = Image.new('RGB', (800, 800), color=(245, 245, 245))
    draw = ImageDraw.Draw(img)
    
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf", 60)
    except:
        font = ImageFont.load_default()

    lines = text.split('\n')
    y_text = 300
    for line in lines:
        try:
            bbox = draw.textbbox((0, 0), line, font=font)
            width = bbox[2] - bbox[0]
            height = bbox[3] - bbox[1]
        except:
            width, height = 400, 60
        draw.text(((800 - width) / 2, y_text), line, font=font, fill=(50, 50, 50))
        y_text += height + 20
        
    img.save(img_path, 'WEBP', quality=90)
    return img_path

def download_vibe_image(prompt, filename_prefix):
    os.makedirs('assets/images', exist_ok=True)
    img_path = f'assets/images/{filename_prefix}.webp'
    
    encoded_prompt = urllib.parse.quote(f"A minimalistic aesthetic interior photo related to {prompt}, bright lighting, high quality, soft colors, unsplash style")
    img_url = f'https://image.pollinations.ai/prompt/{encoded_prompt}?width=800&height=500&nologo=true&private=true&model=flux'
    try:
        r = requests.get(img_url, timeout=120)
        if r.status_code == 200:
            img = Image.open(io.BytesIO(r.content)).convert('RGB')
            img.save(img_path, 'WEBP', quality=80)
            return img_path
    except Exception as e:
        print(f"Vibe image failed: {e}")
    return None

def generate_post():
    # [Pass 4: Thumbnail Catchphrase]
    thumb_prompt = f"""
Create a catchy 2-line hook for a blog thumbnail about: {best_keyword}.
Rule: No fear-mongering, no extreme words (like bugs, stench). Informational and clean.
Example format:
First Line
Second Line
"""
    try:
        thumb_text = generate_with_retry(thumb_prompt).strip().replace('"', '').replace("'", '')
    except:
        thumb_text = f"[{best_keyword}]\n꼭 알아야 할 필수 정보!"

    thumb_filename = f"thumb_{int(time.time())}"
    thumb_rel_path = create_text_thumbnail(thumb_text, thumb_filename)
    image_markdown = f"![{best_keyword}]({{{{ '/' | append: '{thumb_rel_path}' | relative_url }}}})\n\n"

    # [Vibe Image Generation]
    vibe_prompt = f"""
Translate the following topic into 2 English keywords that represent a clean, aesthetic lifestyle or interior mood. Output ONLY the keywords separated by comma.
Topic: {best_keyword}
"""
    try:
        vibe_keywords = generate_with_retry(vibe_prompt).strip()
    except:
        vibe_keywords = "interior,clean"
        
    vibe_rel_path = download_vibe_image(vibe_keywords, f"vibe_{int(time.time())}")
    vibe_markdown = f"![감성사진]({{{{ '/' | append: '{vibe_rel_path}' | relative_url }}}})" if vibe_rel_path else ""

    # [Pass 1: Draft]
    draft_prompt = f"""
당신은 생활 정보와 팁을 제공하는 전문 에디터입니다.
다음 캠페인 정보와 타겟 키워드를 바탕으로 정보성 블로그 초안(1500자)을 작성하세요.

[캠페인 정보]
- 이름: {campaign['name']}
- 혜택: {campaign['benefits']}
- 타겟 키워드: {keyword_str}

지침:
- 너무 자극적이거나 공포감을 주는 단어(벌레, 악취 등)는 절대 금지.
- 소제목은 반드시 마크다운(##, ###) 사용.
"""
    draft_content = generate_with_retry(draft_prompt).strip()

    # [Pass 2: Check]
    check_prompt = f"""
다음 작성된 초안을 SEO/AEO 관점에서 비판적으로 검토하고 개선사항 5가지를 작성하세요.
[초안]
{draft_content}
"""
    feedback_content = generate_with_retry(check_prompt).strip()

    # [Pass 3: Rewrite]
    button_html = f'<div style="text-align: center; margin: 20px 0;"><a href="{campaign["link"]}" style="background-color: #ff5722; color: white; padding: 15px 25px; text-decoration: none; border-radius: 5px; font-weight: bold; font-size: 18px;" target="_blank">[DYNAMIC_BUTTON_TEXT]</a></div>'

    rewrite_prompt = f"""
당신은 상위 1% 정보 매거진 에디터입니다.
[초안]에 [전문가 피드백]을 100% 반영하여 2000자 내외의 최종 텍스트를 작성하세요.
자극적인 단어 없이 깔끔한 정보성 톤앤매너를 유지하세요.

[전문가 피드백]
{feedback_content}

[초안]
{draft_content}

[필수 구조 규칙]
글 서론과 결론 부근에 다음 버튼 HTML 태그를 그대로 2회 삽입하세요.
단, [DYNAMIC_BUTTON_TEXT] 부분을 문맥에 맞게 매력적인 문구(예: 무료 상담 신청하기, 혜택 확인하기 등)로 수정해서 넣으세요.
{button_html}

[시각적 강조 규칙 - 반드시 적용]
1. 본문 중간에 딱 1번 아래의 감성 사진 마크다운을 본문과 가장 자연스러운 위치에 줄바꿈하여 삽입하세요.
{vibe_markdown}
"""
    final_text = generate_with_retry(rewrite_prompt).strip()
    final_text = re.sub(r'^---.*?---\s*', '', final_text, flags=re.DOTALL)
    final_text = re.sub(r'^\s*layout:.*?\n\s*', '', final_text, flags=re.DOTALL)

    title_prompt = f"""이 글의 검색 상위 노출을 위한 매력적인 제목 1줄만 출력하세요.
핵심 키워드 [{best_keyword}] 포함. 큰따옴표 제외."""
    title = generate_with_retry(title_prompt).strip().replace('"', '').replace("'", '')

    # AdSense Setup (CPA Common Codes)
    ad_top = '''
<div class="manual-ad-container" style="margin: 25px 0; text-align: center;">
    <ins class="adsbygoogle"
         style="display:block"
         data-ad-client="ca-pub-2228289204702106"
         data-ad-slot="2231432699"
         data-ad-format="auto"
         data-full-width-responsive="true"></ins>
    <script>(adsbygoogle = window.adsbygoogle || []).push({});</script>
</div>'''
    ad_middle = '''
<div class="manual-ad-container" style="margin: 25px 0; text-align: center;">
    <ins class="adsbygoogle"
         style="display:block"
         data-ad-client="ca-pub-2228289204702106"
         data-ad-slot="5979106011"
         data-ad-format="auto"
         data-full-width-responsive="true"></ins>
    <script>(adsbygoogle = window.adsbygoogle || []).push({});</script>
</div>'''
    ad_bottom = '''
<div class="manual-ad-container" style="margin: 35px 0 10px 0; text-align: center;">
    <ins class="adsbygoogle"
         style="display:block"
         data-ad-client="ca-pub-2228289204702106"
         data-ad-slot="2249895363"
         data-ad-format="auto"
         data-full-width-responsive="true"></ins>
    <script>(adsbygoogle = window.adsbygoogle || []).push({});</script>
</div>'''

    lines = final_text.split('\n')
    if len(lines) > 10:
        mid_idx = len(lines) // 2
        body_content = "\n".join(lines[:mid_idx]) + "\n\n" + ad_middle + "\n\n" + "\n".join(lines[mid_idx:])
    else:
        body_content = final_text
        
    final_body = image_markdown + ad_top + "\n\n" + body_content + "\n\n" + ad_bottom
    return title, final_body

def save_post(title, body):
    now = datetime.utcnow()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%Y-%m-%d %H:%M:%S")
    slug = "".join(c if c.isalnum() else "-" for c in title.lower())
    slug = "-".join(filter(None, slug.split("-")))[:50]
    if not slug:
        slug = str(int(time.time()))
    filename = f"{date_str}-{slug}.md"
    filepath = os.path.join('_posts', filename)
    os.makedirs('_posts', exist_ok=True)
    
    frontmatter = f"---\nlayout: post\ntitle: \"{title}\"\ndate: {time_str}\ncategories: [Info]\n---\n\n{body}\n"
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(frontmatter)

if __name__ == "__main__":
    title, body = generate_post()
    save_post(title, body)
