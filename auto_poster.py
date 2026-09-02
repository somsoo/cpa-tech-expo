import os
import json
import random
import time
import re
from datetime import datetime
import google.generativeai as genai

api_keys_str = os.environ.get('GEMINI_API_KEY', '')
if not api_keys_str:
    print('GEMINI_API_KEY is not set.')
    exit(1)
API_KEYS = [k.strip() for k in api_keys_str.split(',') if k.strip()]
models_to_use = ['gemini-3.5-flash-lite', 'gemini-3.1-flash-lite']
genai.configure(api_key=API_KEYS[0])

def generate_with_retry(prompt, is_json=False):
    for model_name in models_to_use:
        try:
            model = genai.GenerativeModel(model_name)
            config = genai.GenerationConfig(response_mime_type="application/json") if is_json else None
            response = model.generate_content(prompt, generation_config=config)
            if response.text:
                return response.text
        except Exception as e:
            pass
    raise Exception("Critical: All API models exhausted!")

def create_text_thumbnail(text, filename_prefix="thumb"):
    lines = text.strip().split('\n')
    lines = [line for line in lines if line.strip()][:3]
    img_width, img_height = 1200, 500
    background_color = (40, 50, 70)
    text_color = (255, 255, 255)
    try:
        from PIL import Image, ImageDraw, ImageFont
        img = Image.new('RGB', (img_width, img_height), color=background_color)
        draw = ImageDraw.Draw(img)
        font_path = "malgun.ttf"
        try:
            font = ImageFont.truetype(font_path, 80)
        except:
            font = ImageFont.load_default()
            
        draw.rectangle([30, 30, img_width-30, img_height-30], outline=(100, 150, 200), width=3)
        y_text = (img_height // 2) - (len(lines) * 50)
        for line in lines:
            line = line.strip()
            if not line: continue
            try:
                bbox = draw.textbbox((0, 0), line, font=font)
                width = bbox[2] - bbox[0]
                height = bbox[3] - bbox[1]
            except:
                width = len(line) * 20; height = 80
            draw.text(((img_width - width) / 2, y_text), line, font=font, fill=text_color)
            y_text += height + 40
            
        os.makedirs('assets/images', exist_ok=True)
        img_path = f'assets/images/{filename_prefix}.webp'
        img.save(img_path, 'WEBP', quality=90)
        return img_path
    except:
        return ""

def download_vibe_image(img_url, filename_prefix):
    if not img_url: return ""
    try:
        import requests, io
        from PIL import Image
        os.makedirs('assets/images', exist_ok=True)
        img_r = requests.get(img_url, timeout=10)
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
        return ""

def generate_post(campaign, keyword):
    profile_prompt = f"당신은 30~50대를 타겟으로 하는 최상급 한국어 마케팅 카피라이터입니다. '{keyword}'의 타겟 유저가 가장 갈망하는 혜택이 무엇인지 3문장으로 분석하세요."
    profiling = generate_with_retry(profile_prompt)
    
    outline_prompt = f"'{profiling}'을 바탕으로 '{keyword}'에 대한 정보성 블로그 포스팅 목차(H2 3개)를 마크다운으로 작성하세요."
    outline = generate_with_retry(outline_prompt)

    draft_prompt = f"""
    아래 목차를 바탕으로 '{keyword}'에 대한 1500자 분량의 전문적인 정보성 블로그 포스팅 초안을 작성하세요.
    [목차]
    {outline}
    [캠페인 혜택]
    {campaign['benefits']}
    [절대 규칙]
    {campaign['rules']}
    """
    draft = generate_with_retry(draft_prompt)

    critique_prompt = f"마케팅 전문가로서 위 초안({draft})의 전환율(CPA 신청)과 구글 상위 노출을 높이기 위한 개선점 3가지를 제시하세요."
    critique = generate_with_retry(critique_prompt)

    rewrite_prompt = f"""
    개선점({critique})을 반영하여 최종 2000자 블로그 본문(한국어)을 완성하세요.
    CRITICAL RULES:
    1. 본문의 딱 중간 지점(대략 절반)에 정확히 '[VIBE_IMAGE_HERE]' 라는 텍스트를 1회만 삽입하세요. (이미지는 많이 넣지 마세요)
    2. 마크다운 코드 블록(`)은 절대 사용하지 마세요. 구조화 데이터(JSON-LD)가 필요하다면 반드시 <script type="application/ld+json"> 태그 안에 넣어서 유저 눈에 보이지 않게 하세요.
    3. 글 내용 중에 "무조건 합격", "월 500 보장" 같은 과장 광고는 절대 쓰지 마세요.
    
    [초안]
    {draft}
    """
    final_text = generate_with_retry(rewrite_prompt)
    
    final_text = re.sub(r'(?i)^(?:#+\s*)?H[23]:\s*', '', final_text, flags=re.MULTILINE)
    final_text = re.sub(r'^---.*?---\s*', '', final_text, flags=re.DOTALL)


    meta_prompt = f"""
    이 글을 위한 JSON 데이터를 반환하세요:
    {{ 
      'title': '{keyword}를 포함한 후킹되는 블로그 제목', 
      'thumb_hook': '{keyword} 관련 썸네일에 들어갈 짧은 두 줄짜리 텍스트', 
      'vibe_keywords': '픽사베이 영문 검색용 키워드 1개 (예: study, exam)',
      'cta_text': '이 캠페인에 딱 맞는 가장 매혹적인 버튼 문구 1개 (예: 나의 예상 혜택 1분만에 확인하기, 올해 합격 가능성 진단받기)'
    }}
    """
    meta_json_str = generate_with_retry(meta_prompt, is_json=True)
    try:
        meta = json.loads(meta_json_str)
        title, thumb_hook, vibe_keywords, cta_text = meta['title'], meta['thumb_hook'], meta['vibe_keywords'], meta.get('cta_text', '정보 알아보기')
    except:
        title, thumb_hook, vibe_keywords, cta_text = f"{keyword} 핵심 가이드", f"{keyword}\n총정리", "study", "알아보기"

    image_urls = []
    try:
        import urllib.parse, requests
        url = f"https://pixabay.com/api/?key=57366919-c2774ae5199cc6a6cdb9a301d&q={urllib.parse.quote(vibe_keywords)}&image_type=photo&orientation=horizontal&per_page=5"
        r = requests.get(url, timeout=10)
        data = r.json()
        if data.get('hits'):
            image_urls = [hit.get('largeImageURL', hit.get('webformatURL')) for hit in data['hits']]
    except:
        pass

    parts = final_text.split('[VIBE_IMAGE_HERE]')
    processed_text = parts[0]
    if len(parts) > 1:
        v_path = ""
        if len(image_urls) > 0:
            v_path = download_vibe_image(image_urls[0], f"vibe_{int(time.time())}")
        if v_path:
            processed_text += f"\n<br>\n![관련 이미지]({{{{ '/' | append: '{v_path}' | relative_url }}}})\n<br>\n"
        processed_text += parts[1]

    thumb_filename = f"thumb_{int(time.time())}"
    thumb_rel_path = create_text_thumbnail(thumb_hook, thumb_filename)
    
    cpa_button = f"""
<div style="margin: 40px 0; padding: 25px; text-align: center; border: 2px solid #3b82f6; border-radius: 12px; background-color: #eff6ff; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
    <h3 style="color: #1d4ed8; margin-bottom: 12px; font-weight: bold; font-size: 20px;">💡 {campaign['name']}</h3>
    <p style="font-size: 16px; margin-bottom: 20px; color: #374151; word-break: keep-all;">{campaign['benefits']}</p>
    <a href="{campaign['link']}" target="_blank" style="display: inline-block; padding: 14px 28px; background-color: #2563eb; color: white; font-size: 18px; font-weight: bold; text-decoration: none; border-radius: 8px; transition: background-color 0.3s; box-shadow: 0 2px 4px rgba(37,99,235,0.3);">👉 {cta_text}</a>
</div>
"""
    ad_bottom = '\n<div class="manual-ad-container" style="margin: 30px 0; text-align: center;">\n<ins class="adsbygoogle" style="display:block" data-ad-client="ca-pub-2228289204702106" data-ad-slot="2231432699" data-ad-format="auto" data-full-width-responsive="true"></ins>\n<script>(adsbygoogle = window.adsbygoogle || []).push({});</script>\n</div>\n'
    
    final_text = processed_text + cpa_button + ad_bottom
    return title, final_text, thumb_rel_path

def main():
    with open('campaigns.json', 'r', encoding='utf-8-sig') as f:
        campaigns = json.load(f)
    
    campaign = random.choice(campaigns)
    keyword = random.choice(campaign['keywords'])
    print(f'Campaign: {campaign["name"]} | Keyword: {keyword}')
    
    title, post_content, thumb_path = generate_post(campaign, keyword)
    if post_content:
        date_str = datetime.now().strftime('%Y-%m-%d')
        safe_title = keyword.replace(' ', '-').lower()
        filename = f'_posts/{date_str}-{safe_title}.md'
        os.makedirs('_posts', exist_ok=True)
        frontmatter = f"---\nlayout: post\ntitle: \"{title}\"\ndate: {date_str}\nimage: {thumb_path}\n---\n\n"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(frontmatter + post_content)
        print(f'Successfully generated {filename}')

if __name__ == '__main__':
    main()
