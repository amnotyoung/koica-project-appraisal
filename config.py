"""
KOICA 사업 예비조사 심사 시스템 - 설정 파일
모든 설정 상수와 기본값 관리
"""

from typing import Dict, Any


class AppConfig:
    """애플리케이션 전역 설정"""

    # 앱 정보
    APP_TITLE = "KOICA 심사 분석 도구 v3 (RAG)"
    APP_VERSION = "3.1.0"
    APP_ICON = "🚀"

    # 페이지 레이아웃
    PAGE_LAYOUT = "wide"
    SIDEBAR_STATE = "expanded"


class FileConfig:
    """파일 업로드 및 처리 설정"""

    # 파일 크기 제한 (바이트)
    MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB
    MAX_FILE_SIZE_MB = 100

    # 지원 파일 형식
    SUPPORTED_FILE_TYPES = ['pdf']


class RAGConfig:
    """RAG (Retrieval-Augmented Generation) 설정"""

    # 텍스트 청킹
    CHUNK_SIZE = 1500
    CHUNK_OVERLAP = 200

    # 벡터 검색
    TOP_K_DOCUMENTS = 15  # 검색할 상위 문서 수
    DEFAULT_K_SEARCH = 10  # 기본 검색 수

    # 임베딩
    EMBEDDING_MODEL = "models/text-embedding-004"
    EMBEDDING_DIMENSION = 768
    EMBEDDING_TASK_TYPE_DOC = "retrieval_document"
    EMBEDDING_TASK_TYPE_QUERY = "retrieval_query"

    # 컨텍스트 길이
    MAX_CONTEXT_LENGTH = 35000  # API에 전송할 최대 컨텍스트 길이


class APIConfig:
    """API 설정"""

    # 모델
    GENERATIVE_MODEL = "gemini-2.5-pro"

    # Rate Limiting
    RATE_LIMIT_DELAY = 0.3  # 일반 요청 간 대기 시간 (초)
    RATE_LIMIT_BATCH_DELAY = 1.0  # 배치 요청 후 대기 시간 (초)
    RATE_LIMIT_BATCH_SIZE = 10  # 배치 크기

    # 재시도
    MAX_RETRIES = 3
    RETRY_DELAY = 1.0  # 재시도 간 대기 시간 (초)


class AuditConfig:
    """심사 기준 설정"""

    # 심사 항목별 배점
    POLICY_ALIGNMENT_MAX_SCORE = 30
    IMPLEMENTATION_READINESS_MAX_SCORE = 70
    TOTAL_MAX_SCORE = 100

    # 세부 평가 항목
    AUDIT_CRITERIA: Dict[str, Dict[str, Any]] = {
        "정책부합성": {
            "만점": 30,
            "항목": [
                {"name": "SDGs 연관성", "score": 10},
                {"name": "수원국 정책", "score": 5},
                {"name": "CPS/국정과제", "score": 5},
                {"name": "코이카 전략", "score": 5},
                {"name": "타 공여기관", "score": 5}
            ]
        },
        "추진여건": {
            "만점": 70,
            "항목": [
                {"name": "수원국 추진체계", "score": 20},
                {"name": "국내 추진체계", "score": 15},
                {"name": "사업 추진전략", "score": 15},
                {"name": "리스크 관리", "score": 10},
                {"name": "성과관리", "score": 10}
            ]
        }
    }

    # 점수 등급 기준
    SCORE_EXCELLENT_THRESHOLD = 80  # 우수
    SCORE_GOOD_THRESHOLD = 60  # 양호
    # 60 미만은 미흡


class UIConfig:
    """UI 스타일 및 메시지 설정"""

    # CSS 클래스
    CSS_GOOD_SCORE = "good-score"
    CSS_AVERAGE_SCORE = "average-score"
    CSS_POOR_SCORE = "poor-score"

    # 메시지
    MSG_FILE_TOO_LARGE = "파일 크기가 너무 큽니다. 최대 {}MB까지 업로드 가능합니다."
    MSG_NO_API_KEY = "Gemini API 키가 설정되지 않았습니다."
    MSG_API_KEY_GUIDE = "`.streamlit/secrets.toml` 또는 환경변수에 `GEMINI_API_KEY`를 설정하세요."
    MSG_ANALYSIS_STARTED = "분석을 시작합니다..."
    MSG_ANALYSIS_COMPLETE = "분석이 완료되었습니다."
    MSG_ANALYSIS_FAILED = "분석 중 오류가 발생했습니다."

    # 진행 상황 메시지
    PROGRESS_PDF_EXTRACT = "PDF 텍스트 추출 중..."
    PROGRESS_EMBEDDING = "임베딩 생성 중: {current}/{total}"
    PROGRESS_POLICY_ANALYSIS = "정책 부합성 분석 중..."
    PROGRESS_IMPL_ANALYSIS = "사업 추진 여건 분석 중..."


class LogConfig:
    """로깅 설정"""

    # 로그 레벨
    LOG_LEVEL = "INFO"

    # 로그 파일
    LOG_DIR = "logs"
    LOG_FILE = "koica_auditor.log"
    LOG_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
    LOG_BACKUP_COUNT = 5

    # 로그 포맷
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


class CacheConfig:
    """캐싱 설정"""

    # 세션 상태 키
    SESSION_PDF_RESULTS = "pdf_results"
    SESSION_TEXT_RESULTS = "text_results"
    SESSION_PDF_TEXT = "pdf_full_text"
    SESSION_VECTOR_STORE = "vector_store_cache"
    SESSION_DOC_HASH = "document_hash"

    # 캐시 활성화
    ENABLE_EMBEDDING_CACHE = True
    ENABLE_RESULT_CACHE = True


# 전역 설정 인스턴스 (필요시 사용)
APP_CONFIG = AppConfig()
FILE_CONFIG = FileConfig()
RAG_CONFIG = RAGConfig()
API_CONFIG = APIConfig()
AUDIT_CONFIG = AuditConfig()
UI_CONFIG = UIConfig()
LOG_CONFIG = LogConfig()
CACHE_CONFIG = CacheConfig()
