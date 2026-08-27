# 🚨 [CRITICAL] AI_MAINTENANCE_RULES 🚨
이 문서는 블로그 자동화 파이프라인의 생명줄입니다. 향후 코드를 수정하는 어떤 AI도 아래의 핵심 시스템을 임의로 생략, 최적화, 또는 훼손해서는 안 됩니다.

## 1. 🛡️ API 무적 순환 (Active Failover) 시스템 보존
- `generate_with_retry` 함수는 API 호출 에러(ResourceExhausted 등) 발생 시 무조건 작동해야 합니다.
- **2중 루프 로직 절대 보존:** 1차로 동일한 API 키 내에서 모델(`gemini-3.5-flash-lite` -> `3.1-flash-lite`)을 순환하고, 2차로 다음 `GEMINI_API_KEY`로 교체하여 재시도하는 로직을 지우지 마세요.

## 2. 📝 True 3-Pass 글쓰기 파이프라인 (AEO/SEO 최적화)
API 비용을 아끼겠다고 글쓰기 단계를 1~2개로 압축하지 마세요. 반드시 아래 3단계를 독립적으로 호출해야 합니다.
- **Pass 1 (Write):** 검색어 기반의 정보성 초안 작성
- **Pass 2 (Check):** AEO(답변 최적화), SEO, GEO 관점에서 초안의 약점을 날카롭게 비판
- **Pass 3 (Revise):** 비판을 수용하여 AI 특유의 기계적 어투("결론적으로")를 제거한 사람다운(인플루언서/전문가) 최종 원고 윤문

## 3. 💰 수동 애드센스 (AdSense) 및 레이아웃 보호
- 블로그 글 상단(`ad_top`), 중단(`ad_middle`), 하단(`ad_bottom`)에 하드코딩된 구글 애드센스 HTML 블록을 어떠한 경우에도 삭제하거나 로직에서 제외하지 마세요. 수익과 직결됩니다.

## 4. 🎨 덜어냄의 미학: 심플 & 클리어 실사 이미지 생성 (Pollinations)
- **Over-prompting 금지:** 3D 렌더링, 8k, 복잡한 질감 등 화려한 수식어를 떡칠하면 오히려 이미지가 뭉개지는 CG 현상이 발생합니다. 절대 과시형 프롬프트를 쓰지 마세요.
- **상징물 1개 추출:** 글 주제를 상징하는 **무생물 사물 또는 자연스러운 사물들의 조합(e.g., 동전과 계산기, 분무기와 스펀지)**을 영어로 추출하세요.
- **심플 프롬프트 고정:** Pollinations URL에 넘기는 프롬프트는 무조건 다음 형식을 고정으로 사용하세요:
  `A realistic photograph of {obj_name} on a clean desk, bright natural lighting, simple and clear`
- 다운로드 받은 이미지(WebP 변환 800x800)를 `assets/images/`에 저장하는 로직을 보존하세요.
