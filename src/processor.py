import json
from typing import List, Optional
from pydantic import BaseModel, Field, ValidationError
from google.genai import types

from config import config

# ==========================================
# [Pydantic 스키마 — AI 전용]
#
# AI의 역할: 이미지에서 정보를 추출하고, 그 정보를 바탕으로
# 검색엔진 최적화(SEO)에 강력한 콘텐츠를 "생성"합니다.
# (단순 복사-붙여넣기가 아닌 풍부하고 설득력 있는 문장으로 재창조)
#
# 위치/날짜: 전처리 모듈 담당 → AI 스키마에서 제외 (토큰 절약)
# ==========================================

class SeoMetadata(BaseModel):
    """
    검색엔진 최적화를 위한 메타데이터.
    단순 정보 나열이 아닌, 검색 의도를 정확히 반영한 문구여야 합니다.
    """
    # 클릭률을 높이는 제목: 행사명 + 지역 + 핵심 혜택 포함 (50~60자 이내)
    title: str = Field(
        ...,
        description="검색 노출 최적화 제목. '브랜드명 + [지역] + 핵심혜택' 구조. 예: '이니웨딩 박람회 | 서울 상담 시 100만원 상품권 증정'"
    )
    # 클릭을 유도하는 설명: 구체적인 혜택과 희소성 어필 (120~160자)
    meta_description: str = Field(
        ...,
        description="클릭률을 높이는 검색 결과 설명문. 구체적 혜택(수치), 일시, 희소성(선착순/한정)을 포함한 120~160자 설득 문구."
    )
    # 롱테일 키워드 10개 이상: 지역+행사, 혜택 중심 검색어
    keywords: List[str] = Field(
        default_factory=list,
        description="검색 유입을 위한 롱테일 키워드 목록 10개 이상. 예: ['서울 웨딩박람회', '신혼부부 웨딩 혜택', '2026 결혼 준비 박람회']"
    )

class MarketingHooks(BaseModel):
    """
    방문자의 즉각적인 관심을 사로잡는 마케팅 문구.
    감성과 혜택을 동시에 자극해야 합니다.
    """
    # 핵심 가치 제안을 담은 강렬한 한 문장
    primary_headline: str = Field(
        ...,
        description="단 1초 만에 관심을 끄는 주 헤드라인. 숫자나 강력한 혜택 포함. 예: '지금 등록하면 최대 현금 100만원 환급'"
    )
    # 주 헤드라인을 보완하는 구체적 설명
    secondary_headline: str = Field(
        ...,
        description="주 헤드라인을 뒷받침하는 보조 문구. 대상(신혼부부), 특징, 차별점 중심."
    )
    urgency_text: str = Field(
        "",
        description="행동을 즉시 유도하는 희소성/긴박감 문구. 예: '선착순 100쌍 한정', '이번 주말까지만'"
    )
    call_to_action_text: str = Field(
        ...,
        description="클릭을 유발하는 CTA 버튼 문구. 구체적이고 행동 지향적으로. 예: '지금 무료 상담 신청하기'"
    )

class Benefits(BaseModel):
    """
    방문/계약 혜택 목록. 구체적인 수치와 조건을 포함해야 합니다.
    """
    # 방문만 해도 받는 혜택
    visit_gifts: List[str] = Field(
        default_factory=list,
        description="방문 시 증정 혜택 목록. 수치 포함. 예: ['현장 방문 시 스타벅스 쿠폰', '선착순 50쌍 경품 추첨']"
    )
    # 계약 체결 시 혜택
    contract_benefits: List[str] = Field(
        default_factory=list,
        description="계약/상담 체결 시 혜택 목록. 예: ['계약 축하금 최대 50만원', '허니문 여행권 증정']"
    )
    # 특별 이벤트
    special_events: List[str] = Field(
        default_factory=list,
        description="현장 특별 이벤트 목록. 예: ['포토존 운영', '웨딩 드레스 피팅 체험']"
    )

class ConversionAndTrust(BaseModel):
    """
    신뢰도를 높이고 전환율을 극대화하는 요소들.
    """
    required_form_fields: List[str] = Field(
        default_factory=list,
        description="신청 폼에 필요한 정보 목록. 예: ['이름', '연락처', '예식 예정일']"
    )
    gift_conditions: str = Field(
        "",
        description="경품/혜택 수령 조건 전문. 예: '현장 상담 완료 후 QR코드 스캔 시 증정'"
    )
    trust_indicators: List[str] = Field(
        default_factory=list,
        description="신뢰도를 높이는 요소 목록. 예: ['업체 30개 이상 입점', '누적 방문객 10만 명', '1:1 전문 상담']"
    )

class DetailedContent(BaseModel):
    """
    페이지 내 상세 콘텐츠. SEO를 위해 검색 의도를 반영하여 풍부하게 작성합니다.
    """
    intro_text: str = Field(
        ...,
        description=(
            "페이지 상단 인트로 문단. 2~3문장, 150자 이상. "
            "행사의 가치, 대상, 핵심 혜택을 녹여 '왜 이 박람회여야 하는가'를 설득하세요. "
            "예: '결혼을 앞둔 커플이라면 놓칠 수 없는 기회입니다. "
            "2026년 봄 웨딩 시즌을 맞아 서울 최대 규모의 웨딩 박람회가 열립니다...'"
        )
    )
    benefits_description: str = Field(
        ...,
        description=(
            "혜택 상세 설명 문단. 3~5문장, 200자 이상. "
            "방문 시 받을 수 있는 혜택을 구체적 수치와 함께 풍부하게 설명하세요. "
            "단순 나열이 아닌, 신혼부부의 감정에 공감하는 문체로 작성하세요."
        )
    )
    summary_for_search: str = Field(
        ...,
        description=(
            "검색 결과 스니펫으로 활용될 요약문. 200자 이내. "
            "행사명, 일시, 장소, 핵심 혜택이 자연스럽게 포함된 문장. "
            "검색어 '웨딩박람회 서울', '결혼 준비 박람회' 등에 노출되도록 최적화하세요."
        )
    )


class StructuredData(BaseModel):
    """
    Google 리치 스니펫(Rich Snippet) 적격 조건을 충족하는 Schema.org 구조화 데이터.
    검색 결과에 날짜·장소·가격 정보가 직접 노출되어 클릭률 20~30% 향상 효과.
    """
    event_schema: dict = Field(
        ...,
        description=(
            "Schema.org Event 형식의 JSON-LD 객체. "
            "name, startDate(ISO8601), endDate(ISO8601), "
            "location(name+address.streetAddress+addressLocality+addressCountry), "
            "organizer(name), offers(price/priceCurrency/availability), "
            "eventStatus('https://schema.org/EventScheduled') 포함. "
            "Google 리치 결과 적격 조건 완전 충족 필수."
        )
    )
    faq_schema: List[dict] = Field(
        default_factory=list,
        description=(
            "FAQ 리치 스니펫용 Q&A 목록 5개 이상. "
            "형식: [{'question': '주차 가능한가요?', 'answer': '...'}] "
            "실제 방문자 궁금증(교통/주차/혜택조건/참여업체/복장) 중심. "
            "검색 결과 FAQ 영역 점유 목적."
        )
    )


class ContentDepth(BaseModel):
    """
    Google E-E-A-T(경험·전문성·권위·신뢰성) 기준 대응 콘텐츠 깊이 강화.
    정보성 쿼리 유입과 토픽 권위도 향상에 기여합니다.
    """
    target_audience_description: str = Field(
        ...,
        description=(
            "방문 대상자 상세 설명. 200자 이상. "
            "'예비부부', '결혼 6개월 이내 준비 커플', '스드메 비용 비교 중인 신혼부부' 등 "
            "구체적 페르소나 묘사. '결혼 준비 어떻게 시작하나요' 등 정보성 쿼리 대응."
        )
    )
    exhibitor_highlights: List[str] = Field(
        default_factory=list,
        description=(
            "주요 입점 업체 카테고리 또는 브랜드 목록. "
            "예: ['드레스샵 15개', '스드메 패키지 업체', '허니문 여행사', '예물·예복 브랜드'] "
            "'웨딩홀 추천', '스드메 박람회' 등 카테고리 검색 유입 목적."
        )
    )
    comparison_hooks: List[str] = Field(
        default_factory=list,
        description=(
            "타 박람회 대비 차별점 문구 3개 이상. "
            "예: '현장 즉시 계약 할인 제공', '국내 최다 50개 업체 입점', '1:1 전문 상담 보장' "
            "'웨딩박람회 비교', '어떤 박람회 가야 하나' 쿼리 대응."
        )
    )


class SearchCluster(BaseModel):
    """
    단일 페이지 SEO를 넘어 사이트 전체 토픽 권위도와 내부 링크 구조를 강화합니다.
    """
    related_queries: List[str] = Field(
        default_factory=list,
        description=(
            "연관 검색어 클러스터 10개 이상. People Also Ask·자동완성 기반 예상 쿼리. "
            "예: ['웨딩박람회 준비물', '웨딩박람회 뭐 받나요', '결혼 박람회 사기 주의', "
            "'웨딩박람회 예약 방법', '스드메 박람회 차이'] "
            "하단 콘텐츠 섹션 또는 FAQ 생성에 활용."
        )
    )
    internal_link_anchors: List[dict] = Field(
        default_factory=list,
        description=(
            "내부 링크용 앵커 텍스트 + 연결 카테고리 목록. "
            "형식: [{'anchor': '서울 웨딩박람회 전체 일정', 'category': 'seoul_events'}] "
            "사이트 내 관련 페이지로 링크 주스 전달 목적."
        )
    )
    semantic_keywords: List[str] = Field(
        default_factory=list,
        description=(
            "LSI(잠재 의미 색인) 키워드 목록. 주 키워드와 의미적으로 연관된 단어들. "
            "예: ['스드메', '혼수', '예식장', '웨딩홀', '부케', '혼수가전', '신혼여행'] "
            "본문에 자연스럽게 배치하여 토픽 권위도 향상."
        )
    )


class SocialMeta(BaseModel):
    """
    카카오·인스타그램 등 SNS 공유 시 노출되는 메타 정보.
    소셜 공유 → 백링크 증가 → 도메인 권위도 상승으로 이어지는 간접 SEO 효과.
    """
    og_title: str = Field(
        ...,
        description="Open Graph 제목. 카카오/인스타 공유 시 노출. 40자 이내 임팩트 문구. 핵심 혜택 포함."
    )
    og_description: str = Field(
        ...,
        description="OG 설명문. 2~3줄 분량. 공유 시 클릭을 유도하는 혜택·희소성 중심 문구."
    )
    hashtags: List[str] = Field(
        default_factory=list,
        description=(
            "SNS 해시태그 10개 이상. 인스타/카카오 검색 유입용. "
            "예: ['#웨딩박람회', '#결혼준비', '#신혼부부혜택', '#서울웨딩', '#스드메'] "
            "# 기호 포함하여 작성."
        )
    )


class AiAnalysisOutput(BaseModel):
    """
    AI가 생성해야 하는 최종 출력 스키마.

    [AI 역할 정의]
    단순 데이터 추출이 아닌 SEO 콘텐츠 생성자:
    - 이미지에서 정보를 정확히 추출
    - 추출한 정보를 검색엔진 최적화(SEO)에 유리한 풍부한 문장으로 재창조
    - 검색 의도(신혼부부, 웨딩 준비, 결혼 박람회)를 반영한 자연스러운 키워드 배치
    - 위치/날짜는 별도 처리됨 → 포함 불필요
    """
    seo_metadata: SeoMetadata
    detailed_content: DetailedContent
    marketing_hooks: MarketingHooks
    benefits: Benefits
    venue: str = Field("", description="개최 장소명 (이미지에서 확인)")
    parking_info: Optional[str] = Field(None, description="주차 정보 (이미지에서 확인)")
    conversion_and_trust: ConversionAndTrust
    # ==== 503 에러로 인한 토큰 최적화 (임시 주석 처리) ====
    structured_data: StructuredData
    content_depth: ContentDepth
    search_cluster: SearchCluster
    social_meta: SocialMeta


# ==========================================
# [페르소나 정의 — 데이터셋별 AI 역할/어조 설정]
#
# DATA_DIR 환경변수 기준으로 자동 선택됩니다.
# 새 데이터셋 추가 시 PERSONAS에 항목만 더하면 됨.
# ==========================================

_COMMON_TASKS = (
    "\n"
    "[임무 3 - 구조화 데이터 (structured_data)]:\n"
    "  - Schema.org Event JSON-LD 객체 생성 (event_schema). "
    "startDate/endDate ISO8601, location name+address, "
    "eventStatus 'https://schema.org/EventScheduled', "
    "offers.price 무료 입장이면 '0', priceCurrency 'KRW'\n"
    "  - 실제 방문자 궁금증 기반 FAQ 5개 이상 (faq_schema)\n"
    "\n"
    "[임무 4 - E-E-A-T 콘텐츠 (content_depth)]:\n"
    "  - 구체적 페르소나 기반 방문 대상자 설명 200자 이상\n"
    "  - 이미지에서 확인되는 입점 업체 카테고리 목록 추출\n"
    "  - 타 박람회 대비 차별점 문구 3개 이상\n"
    "\n"
    "[임무 5 - 검색 클러스터 (search_cluster)]:\n"
    "  - People Also Ask 기반 연관 쿼리 10개 이상\n"
    "  - 내부 링크용 앵커 텍스트 + 카테고리 목록\n"
    "  - LSI 키워드(스드메·혼수·예식장 등) 목록\n"
    "\n"
    "[임무 6 - 소셜 메타 (social_meta)]:\n"
    "  - 카카오/인스타 공유 최적화 OG 제목(40자 이내)과 설명\n"
    "  - SNS 해시태그 10개 이상 (# 기호 포함)\n"
    "\n"
    "위치(시도/시군구)와 날짜 정보는 이미 별도로 확보되었으므로 분석에서 제외합니다. "
    "값이 이미지에서 확인되지 않으면 null 또는 빈 문자열로 처리합니다."
)

PERSONAS = {
    # ===== 기본 페르소나 (weddinggo 및 기타 데이터셋) =====
    "default": (
        "당신은 웨딩 박람회 전문 SEO 콘텐츠 라이터입니다. "
        "웨딩 박람회 랜딩페이지 이미지를 분석하여 다음 임무를 수행합니다.\n"
        "\n"
        "[임무 1 - 정보 추출] 이미지에서 다음을 정확히 파악합니다:\n"
        "  - 제공하는 방문 혜택, 계약 혜택, 특별 이벤트\n"
        "  - 개최 장소명, 주차 정보\n"
        "  - 신뢰를 높이는 요소(참여 업체 수, 방문객 수 등)\n"
        "  - CTA 버튼 문구, 마케팅 헤드라인\n"
        "\n"
        "[임무 2 - SEO 콘텐츠 생성] 추출한 정보를 바탕으로:\n"
        "  - 검색엔진 상위 노출에 유리한 제목(50~60자)과 메타 디스크립션(120~160자)을 작성합니다\n"
        "  - '웨딩박람회', '결혼준비', '신혼부부 혜택' 등 검색 의도를 반영한 키워드를 자연스럽게 포함시킵니다\n"
        "  - 단순 정보 나열이 아닌, 방문자의 공감을 얻고 클릭/방문을 유도하는 설득력 있는 문장을 작성합니다\n"
        "  - 구체적인 수치(금액, 인원, 업체 수)가 있으면 반드시 포함합니다\n"
    ) + _COMMON_TASKS,

    # ===== weddingExpo 페르소나 =====
    # 20대 후반~30대 초반 결혼적령기 여성이
    # 콴미니티(ex. 네이버 웨딩 카페, 마망른노될령)에
    # 경어체로 후기/정보 글을 쓰는 스타일
    "weddingExpo": (
        "당신은 웨딩박람회 정보를 전문적으로 큐레이션하는 웨딩 콘텐츠 에디터입니다. "
        "직접 방문한 것처럼 꾸미지 않고, 예비부부에게 실질적으로 도움이 되는 "
        "박람회 정보를 정확하고 친절하게 정리해 전달합니다.\n"
        "\n"
        "[글쓰기 특징]\n"
        "  - 정보 안내 중심의 자연스러운 도입: '이번 OO 웨딩박람회, 참가를 고민 중이시라면 아래 정보를 참고해보세요.'\n"
        "  - 객관적 사실 전달: '이번 박람회에서는 드레스 업체가 예년 대비 다양하게 참가합니다.'\n"
        "  - 실용 정보 안내: 'OO 부스는 명함 등록 시 사은품을 제공하는 것으로 확인됩니다. 참가 전 참고하시면 좋습니다.'\n"
        "  - 참여 유도는 정보성으로: '박람회 일정과 사전등록 방법은 아래에서 확인하실 수 있어요.'\n"
        "  - 어조는 딱딱하지 않게, 그러나 '제가 가봤는데' 식 개인 경험담은 사용하지 않음\n"
        "  - 문장은 정중한 존댓말을 기본으로 하되, 지나치게 사무적이지 않도록 자연스러운 연결어를 사용\n"
        "\n"
        "[임무 1 - 정보 추출] 이미지에서 다음을 정확히 파악합니다:\n"
        "  - 예비부부에게 실질적으로 도움이 되는 주요 혜택\n"
        "  - 참가 전 알아두면 좋은 유의사항 (주차, 시간, 사전등록 등)\n"
        "  - 참가 업체 중 눈에 띄는 부스/구성\n"
        "  - 검색 유입에 도움이 될 만한 실용 정보 포인트\n"
        "\n"
        "[임무 2 - 콘텐츠 작성] 정보 중심 콘텐츠로 작성합니다:\n"
        "  - 서론은 박람회를 소개하는 안내글처럼 자연스럽게 (경어체 유지, 과장된 감탄사 지양)\n"
        "  - 혜택은 '~로 확인됩니다', '~을 제공합니다' 등 사실 전달형으로 서술\n"
        "  - 메타 디스크립션은 박람회 소개 요약문처럼, 130~160자\n"
        "  - 수치는 출처가 확인되는 범위 내에서 정확히 포함\n"
        "  - '웨딩박람회 정보', '결혼 준비' 키워드를 자연스럽게 배치\n"
    ) + _COMMON_TASKS,
}


# ==========================================
# [데이터 처리 클래스]
# ==========================================

class WeddingDataProcessor:
    def __init__(self, api_client):
        self.client = api_client

        # 현재 데이터셋에 맞는 페르소나를 자동 선택
        # config.dataset_name → PERSONAS dict 키 매치 → 없으면 'default' 폴백
        dataset = config.dataset_name
        self.system_instruction = PERSONAS.get(dataset, PERSONAS["default"])
        print(f"[-] [Processor] 페르소나 로드: '{dataset if dataset in PERSONAS else 'default ('+dataset+')'}'")

    def get_ai_schema(self):
        """AI 전용 스키마 반환"""
        return AiAnalysisOutput.model_json_schema()

    def analyze_image(self, image_path: str, api_basic_data: dict, preprocessed: dict = None):
        """
        Gemini API로 이미지를 분석하고 SEO 최적화 콘텐츠를 생성합니다.

        [전략]
        - 광고명 + 전처리된 위치/날짜를 컨텍스트로 제공 → AI가 더 정확한 SEO 문구 생성 가능
        - 추출 정보를 SEO 콘텐츠로 재창조하도록 명시적 지시
        """
        print(f"[*] [Processor] Gemini API 이미지 분석 + SEO 콘텐츠 생성...")
        uploaded_file = self.client.files.upload(file=image_path)

        ad_name = api_basic_data.get("gather_name", "")
        schema = self.get_ai_schema()

        # 전처리된 위치/날짜/장소명을 컨텍스트로 제공 (AI가 더 정확한 SEO 문구 작성 가능)
        context_parts = [f"광고명: {ad_name}"]
        if preprocessed:
            loc = preprocessed.get("location", {})
            dates = preprocessed.get("dates", {})
            if loc.get("sido"):
                context_parts.append(f"지역: {loc.get('sido')} {loc.get('sigungu', '')}")
            if loc.get("venue"):
                context_parts.append(f"추정 장소명: {loc.get('venue')}")
            if dates.get("display_date"):
                context_parts.append(f"행사 일시: {dates.get('display_date')}")

        context_str = "\n".join(context_parts)

        prompt = (
            f"[행사 기본 정보] (SEO 콘텐츠 작성 시 참고)\n"
            f"{context_str}\n\n"
            f"위 이미지는 웨딩 박람회 랜딩페이지입니다.\n"
            f"이미지에서 혜택, 마케팅 문구, 장소, 신뢰 요소 등을 추출하고, "
            f"검색엔진 상위 노출에 유리한 SEO 콘텐츠를 생성하여 아래 JSON 형식으로 반환하세요.\n"
            f"Schema: {json.dumps(schema, ensure_ascii=False)}"
        )

        try:
            # 설정된 AI 모델 사용 (config.json 또는 환경변수)
            model_name = config.ai_model
            response = self.client.models.generate_content(
                model=model_name,
                contents=[prompt, uploaded_file],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    system_instruction=self.system_instruction,
                ),
            )

            if response.text is None:
                # 텍스트가 None인 경우는 보통 안전 정책(Safety Filter)에 걸렸거나 응답 생성이 차단된 경우입니다.
                raise ValueError(f"AI 응답이 비어 있습니다. (안전 정책 차단 등) - {response.model_dump()}")
                
            raw_json = json.loads(response.text)

            validated = AiAnalysisOutput(**raw_json)
            print(f"[✔] [Processor] AI 데이터 검증 통과")
            return validated.model_dump(mode="json")

        except ValidationError as ve:
            print(f"[!] [Processor] 데이터 검증 실패: {ve}")
            raise ValueError(f"AI 생성 데이터 유효성 검증 실패: {ve.errors()}")
        except Exception as e:
            print(f"[✘] [Processor] analyze_image 도중 오류: {e}")
            raise e
        finally:
            try:
                self.client.files.delete(name=uploaded_file.name)
            except:
                pass

    def smart_merge(self, ai_data: dict, api_basic_data: dict, campaign_id: str, preprocessed: dict, organizer_name: str = ""):
        """
        전처리 데이터(위치/날짜) + AI 생성 데이터(SEO/마케팅) + API 원본(에셋)을 결합합니다.

        데이터 출처별 역할:
        - preprocessed: 위치(sido/sigungu/영문), 날짜(start/end_date) — 정확도 보장
        - ai_data: SEO 메타, 상세 콘텐츠, 마케팅 문구, 혜택, 신뢰 요소 — AI 창작
        - api_basic_data: gather_name, 에셋(메인비주얼/썸네일 URL) — API 원본
        - organizer_name: lib/organizerMapping.json에서 조회된 주관사 명칭
        """
        loc_pre = preprocessed["location"]
        dates_pre = preprocessed["dates"]

        # 구조화 데이터 — Schema.org JSON-LD + FAQ 리치 스니펫 (AI 생성)
        structured_data = ai_data.get("structured_data", {})
        
        # [추가] event_schema 내부에 organizer 정보 주입 (mapping 기반)
        if organizer_name and "event_schema" in structured_data:
            if isinstance(structured_data["event_schema"], dict):
                structured_data["event_schema"]["organizer"] = {
                    "@type": "Organization",
                    "name": organizer_name,
                    "url": api_basic_data.get("ad_url", "")
                }

        result = {
            "campaign_id": campaign_id,
            "gather_name": api_basic_data.get("gather_name", ""),
            "organizer_name": organizer_name, # 최상위에도 추가 (편의성)

            # SEO 메타데이터 (AI 생성)
            "seo_metadata": ai_data.get("seo_metadata", {}),

            # 풍부한 상세 콘텐츠 (AI 생성 — SEO 최적화 문단)
            "detailed_content": ai_data.get("detailed_content", {}),

            # 마케팅 문구 (AI 생성)
            "marketing_hooks": ai_data.get("marketing_hooks", {}),

            # 혜택 정보 (AI 추출)
            "benefits": ai_data.get("benefits", {}),

            # 행사 상세 (위치: 전처리, 날짜: 전처리, 장소/주차: AI 추출)
            "event_details": {
                "event": {
                    "start_date": dates_pre.get("start_date"),
                    "end_date": dates_pre.get("end_date"),
                    "display_date": dates_pre.get("display_date", ""),
                    "original_display_date": api_basic_data.get("ad_date", ""),
                },
                "location": {
                    "sido": loc_pre.get("sido", ""),
                    "sido_en": loc_pre.get("sido_en", "etc"),
                    "sigungu": loc_pre.get("sigungu", ""),
                    "sigungu_en": loc_pre.get("sigungu_en", ""),
                    "address": loc_pre.get("address", ""),  # 전처리된 주소 추가
                    "venue": loc_pre.get("venue") if loc_pre.get("venue") else ai_data.get("venue", ""),
                    "parking_info": ai_data.get("parking_info") or "대중교통 이용 권장 또는 현장 문의",
                    "region_code": api_basic_data.get("region", ""),
                },
            },

            # 전환/신뢰 요소 (AI 생성)
            "conversion_and_trust": ai_data.get("conversion_and_trust", {}),

            # 구조화 데이터 — Schema.org JSON-LD + FAQ 리치 스니펫 (AI 생성)
            "structured_data": structured_data,

            # E-E-A-T 콘텐츠 깊이 — 대상자/입점업체/차별점 (AI 생성)
            "content_depth": ai_data.get("content_depth", {}),

            # 검색 클러스터 — 연관쿼리/내부링크/LSI 키워드 (AI 생성)
            "search_cluster": ai_data.get("search_cluster", {}),

            # 소셜 메타 — OG 태그/해시태그 (AI 생성)
            "social_meta": ai_data.get("social_meta", {}),

            # 에셋 (API 원본)
            "campaign_assets": {
                "target_url": api_basic_data.get("ad_url"),
                "mainvisual": api_basic_data.get("ad_mainvisual"),
                "thumbnail": api_basic_data.get("ad_thumbnail"),
                "thumbnail2": api_basic_data.get("ad_thumbnail2"),
            },
        }

        return result

        return result
