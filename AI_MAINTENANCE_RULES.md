# 🚨 [CRITICAL] AI_MAINTENANCE_RULES 🚨
이 문서는 블로그 자동화 파이프라인의 생명줄입니다. 향후 코드를 수정하는 어떤 AI도 아래의 핵심 시스템을 임의로 생략, 최적화, 또는 훼손해서는 안 됩니다.

## 1. 🛡️ API 무적 순환 (Active Failover) 시스템 보존
- generate_with_retry 함수의 API 호출 에러(ResourceExhausted 등) 발생 시 무조건 작동해야 합니다.
- **2중 루프 로직 절대 보존:** 1차로 단일 API 키 내에서 모델(gemini-3.5-flash-lite -> 3.1-flash-lite)을 전환하고, 2차로 다음 GEMINI_API_KEY로 교체하여 재시도하는 로직을 지우지 마세요.

## 2. ✍️ True 3-Pass 글쓰기 파이프라인 (AEO/SEO 최적화)
API 비용을 아끼겠다고 글쓰기 단계를 1~2개로 단축하지 마세요. 반드시 아래 3단계를 독립적으로 호출해야 합니다.
- **Pass 1 (Write):** 검색어 기반의 정보성 초안 생성
- **Pass 2 (Check):** AEO(AI 최적화), SEO, GEO 관점에서 초안의 약점을 날카롭게 비판
- **Pass 3 (Revise):** 비판을 수용하여 AI 특유의 기계적 말투를 제거한 사람다운 전문가 최종 원고 작성

## 3. 🖼️ 썸네일 이미지 기획 (다중 사물 조합 허용 & 심플 프롬프트)
- **대상 제한:** 인물, 동물은 절대 금지합니다.
- **조합 허용:** 반드시 1개의 사물일 필요는 없습니다. 대상은 '상징적인 무생물 사물'이되, 문맥에 맞는 **적절한 사물들의 자연스러운 조합(예: 황금 동전과 계산기)**을 허용합니다.
- **심플 프롬프트 고정:** 찰흙 질감을 방지하기 위해 과도한 수식어(Photorealistic, 8k, ultra 등)를 배제하고 무조건 아래 포맷을 고정 사용하세요.
  A realistic photograph of {obj_name} on a clean desk, bright natural lighting, simple and clear

## 4. 🔗 제휴마케팅(CPA) 필수 규칙
- **캠페인 키워드 강제 주입:** campaigns.json에 정의된 타겟 제품/캠페인 키워드를 직접 사용합니다. 이 블로그는 일상/쇼핑 목적이므로 복잡한 뉴스 API 기반의 씨앗 발굴 로직을 적용하지 마세요.
- **HTML 광고 블록 보존:** 원고 상/중/하단 및 텐핑(Tenping) 제휴 스크립트 블록을 절대 훼손하지 마세요.
