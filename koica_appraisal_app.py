#!/usr/bin/env python3
"""
KOICA 사업 예비조사 심사 시스템 - Streamlit Web App
(RAG v3.1 - 개선 및 리팩토링 버전)
"""

import os
import logging
from datetime import datetime
from typing import Optional
import streamlit as st

# 로깅 설정 (다른 import보다 먼저)
from utils.logger import setup_logger
logger = setup_logger(name="koica_main", log_to_file=True)

# 익명 분석 설정
from utils.analytics import get_analytics
analytics = get_analytics()

# 내부 모듈 import
from core.auditor import KOICAAuditorStreamlit
from ui.components import (
    display_results,
    generate_report_text,
    generate_report_json,
    generate_report_csv,
    get_custom_css
)
from config import (
    AppConfig, FileConfig, UIConfig, CacheConfig
)

# 페이지 설정 (최상위에서 한 번만 호출)
st.set_page_config(
    page_title=AppConfig.APP_TITLE,
    page_icon=AppConfig.APP_ICON,
    layout=AppConfig.PAGE_LAYOUT,
    initial_sidebar_state=AppConfig.SIDEBAR_STATE
)


def load_api_key() -> Optional[str]:
    """API 키 로드

    Returns:
        API 키 또는 None
    """
    api_key = None

    # 1. Streamlit secrets에서 로드 시도 (우선순위 1)
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
        logger.info("API 키를 Streamlit secrets에서 로드했습니다.")
        return api_key
    except KeyError:
        logger.debug("Streamlit secrets에 API 키가 없습니다.")

    # 2. 환경변수에서 로드 시도 (우선순위 2)
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            logger.info("API 키를 환경변수에서 로드했습니다.")
            return api_key
    except Exception as e:
        logger.error(f"환경변수 로드 중 오류: {e}")

    return None


def validate_file_size(uploaded_file) -> bool:
    """파일 크기 검증

    Args:
        uploaded_file: Streamlit UploadedFile 객체

    Returns:
        검증 통과 여부
    """
    if not uploaded_file:
        return False

    file_size = uploaded_file.size
    logger.info(f"업로드 파일 크기: {file_size / (1024*1024):.2f} MB")

    if file_size > FileConfig.MAX_FILE_SIZE:
        error_msg = UIConfig.MSG_FILE_TOO_LARGE.format(FileConfig.MAX_FILE_SIZE_MB)
        st.error(f"❌ {error_msg}")
        logger.warning(f"파일 크기 초과: {file_size} bytes (최대: {FileConfig.MAX_FILE_SIZE})")
        return False

    return True


def render_sidebar():
    """사이드바 렌더링"""
    with st.sidebar:
        st.markdown(f"## 📊 도구 정보 (v{AppConfig.APP_VERSION})")
        st.warning("**비공식 개인 프로젝트**")
        st.markdown("---")

        st.markdown("### ℹ️ v3.1 개선 사항")
        st.info("""
        - ✅ **모듈화된 코드 구조**
        - ✅ **파일 크기 제한 (100MB)**
        - ✅ **개선된 예외 처리**
        - ✅ **로깅 시스템 추가**
        - ✅ **API 응답 검증**
        - ✅ **중앙화된 설정 관리**
        """)

        st.markdown("### 📝 이전 버전 개선사항")
        st.success("""
        - **안정적인 임베딩**: Gemini API 직접 사용
        - **배치 문제 해결**: 단일 텍스트씩 처리
        - **오류 복구**: 실패 시 자동 대체
        - **진행 상황 표시**: 실시간 프로그레스바
        """)


def render_disclaimer():
    """면책 조항 렌더링"""
    st.markdown(
        """
        <div class="disclaimer">
            <strong>⚠️ 주의사항</strong><br>
            본 도구는 <strong>KOICA 공식 서비스가 아닙니다</strong>.
            개인이 KOICA 심사 기준을 참고하여 독자적으로 개발한 분석 도구입니다.
            분석 결과는 참고용이며, 공식적인 심사 결과와 다를 수 있습니다.
        </div>
        """,
        unsafe_allow_html=True
    )


def render_pdf_tab(auditor: KOICAAuditorStreamlit):
    """PDF 분석 탭 렌더링

    Args:
        auditor: 심사 시스템 인스턴스
    """
    st.markdown("### 📄 PDF 보고서 업로드")

    uploaded_file = st.file_uploader(
        "KOICA 예비조사 보고서 (PDF)",
        type=FileConfig.SUPPORTED_FILE_TYPES,
        key="pdf_uploader"
    )

    if uploaded_file:
        st.success(f"✅ 파일 업로드 완료: {uploaded_file.name}")

        # 파일 크기 검증
        if not validate_file_size(uploaded_file):
            return

        if st.button("🚀 분석 시작 (RAG v3.1)", type="primary", key="analyze_pdf"):
            logger.info(f"PDF 분석 시작: {uploaded_file.name}")

            # 익명 분석 활동 로깅 (파일 이름은 저장하지 않음)
            analytics.log_activity(
                st.session_state.analytics_session_id,
                action_type="pdf_analysis_started",
                file_size_bytes=uploaded_file.size
            )

            try:
                # 1. 텍스트 추출
                full_text = auditor.extract_text_from_pdf(uploaded_file)
                st.session_state[CacheConfig.SESSION_PDF_TEXT] = full_text

                if not full_text:
                    st.error("❌ PDF에서 텍스트를 추출하지 못했습니다.")
                    logger.error("PDF 텍스트 추출 실패")
                    # 실패 로깅
                    analytics.log_activity(
                        st.session_state.analytics_session_id,
                        action_type="pdf_analysis",
                        file_size_bytes=uploaded_file.size,
                        success=False,
                        error_type="text_extraction_failed"
                    )
                    return

                logger.info(f"PDF 텍스트 추출 완료: {len(full_text)} 문자")

                # 2. 분석 수행
                results = auditor.conduct_audit(full_text=full_text)

                if results:
                    st.session_state[CacheConfig.SESSION_PDF_RESULTS] = results
                    logger.info("PDF 분석 완료")
                    # 성공 로깅
                    analytics.log_activity(
                        st.session_state.analytics_session_id,
                        action_type="pdf_analysis",
                        file_size_bytes=uploaded_file.size,
                        success=True
                    )
                else:
                    st.error("❌ 분석에 실패했습니다.")
                    logger.error("PDF 분석 실패")
                    # 실패 로깅
                    analytics.log_activity(
                        st.session_state.analytics_session_id,
                        action_type="pdf_analysis",
                        file_size_bytes=uploaded_file.size,
                        success=False,
                        error_type="analysis_failed"
                    )

            except Exception as e:
                logger.error(f"PDF 분석 오류: {e}", exc_info=True)
                st.error(f"❌ PDF 분석 중 오류가 발생했습니다.")
                # 예외 로깅
                analytics.log_activity(
                    st.session_state.analytics_session_id,
                    action_type="pdf_analysis",
                    file_size_bytes=uploaded_file.size,
                    success=False,
                    error_type=type(e).__name__
                )
                # 프로덕션에서는 상세 에러를 숨김 (로그에만 기록)

    # 결과 표시
    if CacheConfig.SESSION_PDF_RESULTS in st.session_state:
        results = st.session_state[CacheConfig.SESSION_PDF_RESULTS]
        display_results(results)

        # 다운로드 버튼 3개 (TXT, JSON, CSV)
        st.markdown("### 📥 심사 결과 다운로드")
        col1, col2, col3 = st.columns(3)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        with col1:
            report_text = generate_report_text(results)
            st.download_button(
                label="📄 텍스트 (TXT)",
                data=report_text,
                file_name=f"KOICA_심사결과_{timestamp}.txt",
                mime="text/plain",
                key="download_pdf_txt",
                help="사람이 읽기 쉬운 텍스트 형식"
            )

        with col2:
            report_json = generate_report_json(results)
            st.download_button(
                label="💾 JSON",
                data=report_json,
                file_name=f"KOICA_심사결과_{timestamp}.json",
                mime="application/json",
                key="download_pdf_json",
                help="데이터베이스 저장에 적합한 JSON 형식"
            )

        with col3:
            report_csv = generate_report_csv(results)
            st.download_button(
                label="📊 CSV",
                data=report_csv,
                file_name=f"KOICA_심사결과_{timestamp}.csv",
                mime="text/csv",
                key="download_pdf_csv",
                help="엑셀/스프레드시트에서 열어볼 수 있는 CSV 형식"
            )


def render_text_tab(auditor: KOICAAuditorStreamlit):
    """텍스트 분석 탭 렌더링

    Args:
        auditor: 심사 시스템 인스턴스
    """
    st.markdown("### 📝 텍스트 직접 입력")

    text_input = st.text_area(
        "보고서 내용을 입력하세요",
        height=300,
        key="text_input"
    )

    if st.button("🚀 분석 시작 (RAG v3.1)", key="text_analyze", type="primary"):
        if not text_input.strip():
            st.warning("⚠️ 분석할 텍스트를 입력하세요")
            return

        logger.info(f"텍스트 분석 시작: {len(text_input)} 문자")

        # 익명 분석 활동 로깅 (텍스트 내용은 저장하지 않음)
        analytics.log_activity(
            st.session_state.analytics_session_id,
            action_type="text_analysis_started",
            action_detail=f"text_length:{len(text_input)}"
        )

        try:
            results = auditor.conduct_audit(full_text=text_input)

            if results:
                st.session_state[CacheConfig.SESSION_TEXT_RESULTS] = results
                logger.info("텍스트 분석 완료")
                # 성공 로깅
                analytics.log_activity(
                    st.session_state.analytics_session_id,
                    action_type="text_analysis",
                    action_detail=f"text_length:{len(text_input)}",
                    success=True
                )
            else:
                st.error("❌ 분석에 실패했습니다.")
                logger.error("텍스트 분석 실패")
                # 실패 로깅
                analytics.log_activity(
                    st.session_state.analytics_session_id,
                    action_type="text_analysis",
                    action_detail=f"text_length:{len(text_input)}",
                    success=False,
                    error_type="analysis_failed"
                )

        except Exception as e:
            logger.error(f"텍스트 분석 오류: {e}", exc_info=True)
            st.error(f"❌ 텍스트 분석 중 오류가 발생했습니다.")
            # 예외 로깅
            analytics.log_activity(
                st.session_state.analytics_session_id,
                action_type="text_analysis",
                action_detail=f"text_length:{len(text_input)}",
                success=False,
                error_type=type(e).__name__
            )

    # 결과 표시
    if CacheConfig.SESSION_TEXT_RESULTS in st.session_state:
        results = st.session_state[CacheConfig.SESSION_TEXT_RESULTS]
        display_results(results)

        # 다운로드 버튼 3개 (TXT, JSON, CSV)
        st.markdown("### 📥 심사 결과 다운로드")
        col1, col2, col3 = st.columns(3)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        with col1:
            report_text = generate_report_text(results)
            st.download_button(
                label="📄 텍스트 (TXT)",
                data=report_text,
                file_name=f"KOICA_심사결과_{timestamp}.txt",
                mime="text/plain",
                key="download_text_txt",
                help="사람이 읽기 쉬운 텍스트 형식"
            )

        with col2:
            report_json = generate_report_json(results)
            st.download_button(
                label="💾 JSON",
                data=report_json,
                file_name=f"KOICA_심사결과_{timestamp}.json",
                mime="application/json",
                key="download_text_json",
                help="데이터베이스 저장에 적합한 JSON 형식"
            )

        with col3:
            report_csv = generate_report_csv(results)
            st.download_button(
                label="📊 CSV",
                data=report_csv,
                file_name=f"KOICA_심사결과_{timestamp}.csv",
                mime="text/csv",
                key="download_text_csv",
                help="엑셀/스프레드시트에서 열어볼 수 있는 CSV 형식"
            )


def render_guide_tab():
    """사용 가이드 탭 렌더링"""
    st.markdown("### 📖 사용 가이드 (v3.1 - 개선 및 리팩토링)")

    st.markdown("#### 🔧 v3.1 주요 개선사항")
    st.markdown("""
    **코드 품질 개선:**
    - ✅ **모듈화된 아키텍처**: 코드를 논리적 모듈로 분리
    - ✅ **파일 크기 검증**: 100MB 제한으로 안정성 확보
    - ✅ **개선된 예외 처리**: 구체적인 예외 타입 처리
    - ✅ **로깅 시스템**: 파일 기반 로깅으로 디버깅 용이
    - ✅ **API 응답 검증**: JSON 파싱 전 필수 키 검증
    - ✅ **중앙화된 설정**: config.py로 모든 상수 관리
    - ✅ **타입 힌트 완성**: 모든 함수에 타입 어노테이션
    """)

    st.markdown("#### 🚀 RAG 작동 방식")
    st.markdown("""
    1. **문서 분할**: 전체 PDF를 1,500자 단위 청크로 분할
    2. **벡터화**: 각 청크를 768차원 벡터로 변환 (단일 텍스트씩 처리)
    3. **검색**: 질문과 관련된 상위 15개 청크 검색
    4. **분석**: 검색된 핵심 내용만으로 AI 분석 수행
    """)

    st.markdown("#### 📋 KOICA 심사 기준")
    st.markdown("""
    **1. 국내외 정책 부합성 (30점)**
    - SDGs와의 연관성 (10점)
    - 수원국 정책 부합성 (5점)
    - 한국 정부 CPS 및 국정과제 연계 (5점)
    - 코이카 중기전략 부합성 (5점)
    - 타 공여기관 중복 분석 (5점)

    **2. 사업 추진 여건 (70점)**
    - 수원국 추진체계 (20점)
    - 국내 추진체계 (15점)
    - 사업 추진전략 (15점)
    - 리스크 관리 (10점)
    - 성과관리 (10점)
    """)

    st.markdown("#### 🏗️ 코드 구조")
    st.code("""
    koica-project-appraisal/
    ├── main.py              # 메인 애플리케이션
    ├── config.py            # 설정 관리
    ├── core/                # 핵심 로직
    │   ├── models.py        # 데이터 모델
    │   ├── vector_store.py  # RAG 벡터 스토어
    │   └── auditor.py       # 심사 엔진
    ├── ui/                  # UI 컴포넌트
    │   └── components.py    # 결과 표시 함수
    └── utils/               # 유틸리티
        └── logger.py        # 로깅 시스템
    """, language="text")


def main():
    """메인 애플리케이션"""
    logger.info("애플리케이션 시작")

    # 익명 세션 ID 초기화 (개인정보 수집 안 함)
    if "analytics_session_id" not in st.session_state:
        st.session_state.analytics_session_id = analytics.get_or_create_session()
        analytics.log_activity(
            st.session_state.analytics_session_id,
            action_type="app_start",
            action_detail="Application started"
        )

    # CSS 적용
    st.markdown(get_custom_css(), unsafe_allow_html=True)

    # 헤더
    st.markdown(
        f'<h1 class="main-header">{AppConfig.APP_ICON} {AppConfig.APP_TITLE}</h1>',
        unsafe_allow_html=True
    )
    st.markdown(
        '<p class="sub-header">개선된 RAG · 비공식 개인 프로젝트</p>',
        unsafe_allow_html=True
    )

    # 면책 조항
    render_disclaimer()

    # API 키 로드
    api_key = load_api_key()

    if not api_key:
        st.error(f"⚠️ {UIConfig.MSG_NO_API_KEY}")
        st.info(UIConfig.MSG_API_KEY_GUIDE)
        logger.error("API 키를 찾을 수 없습니다")
        st.stop()

    logger.info("API 키 로드 완료")

    # 사이드바
    render_sidebar()

    # 심사 시스템 초기화
    try:
        auditor = KOICAAuditorStreamlit(api_key=api_key)
        logger.info("심사 시스템 초기화 완료")
    except Exception as e:
        st.error(f"❌ 초기화 실패: 시스템을 시작할 수 없습니다.")
        logger.error(f"초기화 실패: {e}", exc_info=True)
        st.stop()

    # 메인 탭
    tab1, tab2, tab3 = st.tabs([
        "📄 PDF 분석 (권장)",
        "📝 텍스트 분석",
        "ℹ️ 사용 가이드"
    ])

    with tab1:
        render_pdf_tab(auditor)

    with tab2:
        render_text_tab(auditor)

    with tab3:
        render_guide_tab()

    # 푸터
    st.markdown("---")
    st.markdown(
        f"<div style='text-align: center; color: #666;'>"
        f"KOICA 사업 심사 분석 도구 v{AppConfig.APP_VERSION} (개선 및 리팩토링) | 비공식 개인 프로젝트"
        f"</div>",
        unsafe_allow_html=True
    )

    logger.info("애플리케이션 렌더링 완료")


if __name__ == "__main__":
    main()
