"""
KOICA 사업 예비조사 심사 시스템 - 심사 엔진
AI 기반 사업 심사 로직 구현
"""

import json
import logging
import traceback
from datetime import datetime
from typing import Dict, Any, Optional, List
import streamlit as st
import PyPDF2
import google.generativeai as genai
from google.generativeai.types import GenerationConfig

from core.models import AuditEvidence
from core.vector_store import SimpleVectorStore
from config import (
    RAGConfig, APIConfig, AuditConfig, UIConfig
)

logger = logging.getLogger(__name__)


class KOICAAuditorStreamlit:
    """KOICA 심사 시스템 - RAG v3 (개선)

    Retrieval-Augmented Generation을 활용한 사업 심사 엔진
    """

    def __init__(self, api_key: Optional[str] = None):
        """시스템 초기화

        Args:
            api_key: Gemini API 키

        Raises:
            ValueError: API 키가 없는 경우
            Exception: API 연결 실패
        """
        if not api_key:
            raise ValueError("Gemini API 키가 필요합니다")

        try:
            genai.configure(api_key=api_key)

            # JSON 모드 설정
            self.json_config = GenerationConfig(
                response_mime_type="application/json"
            )

            # Gemini 모델 초기화
            self.model = genai.GenerativeModel(
                APIConfig.GENERATIVE_MODEL,
                generation_config=self.json_config
            )

            self.api_key = api_key
            logger.info("KOICAAuditorStreamlit 초기화 완료")

        except Exception as e:
            logger.error(f"Gemini API 연결 실패: {e}")
            raise Exception(f"Gemini API 연결 실패: {e}")

    def extract_text_from_pdf(self, pdf_file) -> str:
        """PDF에서 전체 텍스트 추출

        Args:
            pdf_file: PDF 파일 객체 (Streamlit UploadedFile)

        Returns:
            추출된 텍스트

        Raises:
            Exception: PDF 처리 실패
        """
        try:
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            full_text = ""
            total_pages = len(pdf_reader.pages)

            logger.info(f"PDF 텍스트 추출 시작 (총 {total_pages} 페이지)")
            progress_bar = st.progress(0, text="📄 PDF 텍스트 추출 중...")

            for page_num, page in enumerate(pdf_reader.pages, 1):
                try:
                    full_text += page.extract_text() + "\n"
                    progress = page_num / total_pages
                    progress_bar.progress(
                        progress,
                        text=f"페이지 추출 중: {page_num}/{total_pages}"
                    )
                except Exception as e:
                    logger.warning(f"페이지 {page_num} 처리 오류: {e}")
                    st.warning(f"페이지 {page_num} 처리 오류 (건너뜀)")

            progress_bar.empty()
            logger.info(f"PDF 텍스트 추출 완료 ({len(full_text)} 문자)")
            return full_text

        except Exception as e:
            logger.error(f"PDF 처리 오류: {e}")
            raise Exception(f"PDF 처리 오류: {e}")

    def create_vector_store(self, full_text: str) -> Optional[SimpleVectorStore]:
        """텍스트를 청크로 나누고 벡터 스토어 생성

        Args:
            full_text: 전체 텍스트

        Returns:
            생성된 벡터 스토어 또는 None
        """
        if not full_text:
            logger.error("추출된 텍스트가 없습니다")
            st.error("추출된 텍스트가 없습니다.")
            return None

        # 텍스트를 청크로 분할
        chunks = self._split_text(
            full_text,
            chunk_size=RAGConfig.CHUNK_SIZE,
            overlap=RAGConfig.CHUNK_OVERLAP
        )

        if not chunks:
            logger.error("텍스트를 청크로 나눌 수 없습니다")
            st.error("텍스트를 청크로 나눌 수 없습니다.")
            return None

        st.info(f"📦 총 {len(chunks)}개 청크 생성됨")
        logger.info(f"텍스트를 {len(chunks)}개 청크로 분할")

        try:
            vector_store = SimpleVectorStore(self.api_key)
            vector_store.add_texts(chunks)
            logger.info("벡터 스토어 생성 완료")
            return vector_store

        except Exception as e:
            logger.error(f"벡터 스토어 생성 실패: {e}")
            st.error(f"벡터 스토어 생성 실패: {e}")
            st.code(traceback.format_exc())
            return None

    def _split_text(
        self,
        text: str,
        chunk_size: int = RAGConfig.CHUNK_SIZE,
        overlap: int = RAGConfig.CHUNK_OVERLAP
    ) -> List[str]:
        """텍스트를 청크로 분할

        Args:
            text: 분할할 텍스트
            chunk_size: 청크 크기
            overlap: 중첩 크기

        Returns:
            청크 리스트
        """
        chunks = []
        start = 0
        text_length = len(text)

        while start < text_length:
            end = start + chunk_size
            chunk = text[start:end]
            chunks.append(chunk)
            start = end - overlap

        logger.debug(f"텍스트 분할 완료: {len(chunks)}개 청크")
        return chunks

    def get_relevant_context(
        self,
        vector_store: SimpleVectorStore,
        query: str,
        k: int = RAGConfig.DEFAULT_K_SEARCH
    ) -> str:
        """벡터 스토어에서 쿼리와 관련된 K개의 청크 검색

        Args:
            vector_store: 벡터 스토어
            query: 검색 쿼리
            k: 검색할 문서 수

        Returns:
            검색된 청크들을 연결한 컨텍스트
        """
        if vector_store is None:
            logger.warning("벡터 스토어가 없어 빈 컨텍스트 반환")
            return ""

        try:
            docs = vector_store.similarity_search(query, k=k)
            context = "\n---\n".join(docs)
            logger.debug(f"컨텍스트 검색 완료: {len(docs)}개 청크, {len(context)} 문자")
            return context

        except Exception as e:
            logger.error(f"관련 컨텍스트 검색 오류: {e}")
            st.warning(f"관련 컨텍스트 검색 오류: {e}")
            return ""

    def analyze_policy_alignment(
        self,
        vector_store: Optional[SimpleVectorStore] = None,
        full_text: str = ""
    ) -> AuditEvidence:
        """[RAG 적용] 국내외 정책 부합성 AI 분석

        Args:
            vector_store: RAG용 벡터 스토어 (선택)
            full_text: 전체 텍스트 (fallback)

        Returns:
            정책 부합성 심사 결과
        """
        # RAG: 관련성 높은 컨텍스트 검색
        if vector_store:
            query = "국내외 정책 부합성, SDGs, 수원국 개발 정책, 한국 정부 CPS, 코이카 중기 전략, 타 공여기관 지원 현황, ODA"
            context = self.get_relevant_context(
                vector_store,
                query,
                k=RAGConfig.TOP_K_DOCUMENTS
            )
        else:
            context = full_text[:RAGConfig.MAX_CONTEXT_LENGTH] if full_text else ""

        if not context:
            context = "보고서에서 관련 내용을 찾을 수 없습니다."
            logger.warning("정책부합성 분석용 컨텍스트 없음")

        prompt = self._build_policy_alignment_prompt(context)

        try:
            response = self.model.generate_content(prompt)
            result = self._parse_and_validate_response(
                response.text,
                required_keys=['total_score', 'detailed_scores']
            )

            logger.info(f"정책부합성 분석 완료: {result.get('total_score', 0)}점")
            return self._create_audit_evidence(
                result,
                max_score=AuditConfig.POLICY_ALIGNMENT_MAX_SCORE
            )

        except json.JSONDecodeError as e:
            logger.error(f"정책부합성 분석 JSON 파싱 실패: {e}")
            st.error(f"정책부합성 분석 결과 파싱 실패: {e}")
            return AuditEvidence.create_failed(
                AuditConfig.POLICY_ALIGNMENT_MAX_SCORE,
                f"JSON 파싱 실패: {e}"
            )
        except Exception as e:
            logger.error(f"정책부합성 분석 오류: {e}")
            st.error(f"정책부합성 분석 오류: {e}")
            return AuditEvidence.create_failed(
                AuditConfig.POLICY_ALIGNMENT_MAX_SCORE,
                str(e)
            )

    def analyze_implementation_readiness(
        self,
        vector_store: Optional[SimpleVectorStore] = None,
        full_text: str = ""
    ) -> AuditEvidence:
        """[RAG 적용] 사업 추진 여건 AI 분석

        Args:
            vector_store: RAG용 벡터 스토어 (선택)
            full_text: 전체 텍스트 (fallback)

        Returns:
            추진 여건 심사 결과
        """
        if vector_store:
            query = "사업 추진 여건, 수원국 추진체계, 국내 추진체계, 사업 추진전략, 리스크 관리, 성과관리, 예산, 일정"
            context = self.get_relevant_context(
                vector_store,
                query,
                k=RAGConfig.TOP_K_DOCUMENTS
            )
        else:
            context = full_text[:RAGConfig.MAX_CONTEXT_LENGTH] if full_text else ""

        if not context:
            context = "보고서에서 관련 내용을 찾을 수 없습니다."
            logger.warning("추진여건 분석용 컨텍스트 없음")

        prompt = self._build_implementation_readiness_prompt(context)

        try:
            response = self.model.generate_content(prompt)
            result = self._parse_and_validate_response(
                response.text,
                required_keys=['total_score', 'detailed_scores']
            )

            logger.info(f"추진여건 분석 완료: {result.get('total_score', 0)}점")
            return self._create_audit_evidence(
                result,
                max_score=AuditConfig.IMPLEMENTATION_READINESS_MAX_SCORE
            )

        except json.JSONDecodeError as e:
            logger.error(f"추진여건 분석 JSON 파싱 실패: {e}")
            st.error(f"추진여건 분석 결과 파싱 실패: {e}")
            return AuditEvidence.create_failed(
                AuditConfig.IMPLEMENTATION_READINESS_MAX_SCORE,
                f"JSON 파싱 실패: {e}"
            )
        except Exception as e:
            logger.error(f"추진여건 분석 오류: {e}")
            st.error(f"추진여건 분석 오류: {e}")
            return AuditEvidence.create_failed(
                AuditConfig.IMPLEMENTATION_READINESS_MAX_SCORE,
                str(e)
            )

    def _build_policy_alignment_prompt(self, context: str) -> str:
        """정책 부합성 분석 프롬프트 생성"""
        return f"""당신은 KOICA 사업 심사 전문가입니다. 다음 보고서 발췌 내용을 '국내외 정책 부합성' 기준으로 평가하세요.

=== 평가 기준 (30점 만점) ===
1. SDGs와의 연관성 (10점)
2. 수원국 정책 부합성 (5점)
3. 한국 정부 CPS 및 국정과제 연계 (5점)
4. 코이카 중기전략 부합성 (5점)
5. 타 공여기관 중복 분석 (5점)

=== 보고서 발췌 내용 ===
{context[:RAGConfig.MAX_CONTEXT_LENGTH]}

=== 출력 형식 (JSON) ===
{{
  "total_score": 0-30 사이 정수,
  "detailed_scores": [
    {{"item": "SDGs", "score": 0-10, "max_score": 10, "reason": "SDGs 연관성에 대한 평가 근거"}},
    {{"item": "수원국 정책", "score": 0-5, "max_score": 5, "reason": "수원국 정책 부합성에 대한 평가 근거"}},
    {{"item": "CPS/국정과제", "score": 0-5, "max_score": 5, "reason": "CPS/국정과제 연계성에 대한 평가 근거"}},
    {{"item": "코이카 전략", "score": 0-5, "max_score": 5, "reason": "코이카 중기전략 부합성에 대한 평가 근거"}},
    {{"item": "타 공여기관", "score": 0-5, "max_score": 5, "reason": "타 공여기관 중복 분석에 대한 평가 근거"}}
  ],
  "reasoning": "점수 산정 논리 상세 설명",
  "strengths": ["발견된 모든 강점을 나열"],
  "weaknesses": ["발견된 모든 약점을 나열"],
  "recommendations": ["필요한 모든 개선안을 나열"]
}}

**주의**: strengths, weaknesses, recommendations는 각각 발견된 모든 내용을 빠짐없이 나열해주세요.
JSON만 출력하세요."""

    def _build_implementation_readiness_prompt(self, context: str) -> str:
        """추진 여건 분석 프롬프트 생성"""
        return f"""당신은 KOICA 사업 심사 전문가입니다. 다음 보고서 발췌 내용을 '사업 추진 여건' 기준으로 평가하세요.

=== 평가 기준 (70점 만점) ===
1. 수원국 추진체계 (20점)
2. 국내 추진체계 (15점)
3. 사업 추진전략 (15점)
4. 리스크 관리 (10점)
5. 성과관리 (10점)

=== 보고서 발췌 내용 ===
{context[:RAGConfig.MAX_CONTEXT_LENGTH]}

=== 출력 형식 (JSON) ===
{{
  "total_score": 0-70 사이 정수,
  "detailed_scores": [
    {{"item": "수원국 추진체계", "score": 0-20, "max_score": 20, "reason": "평가 근거"}},
    {{"item": "국내 추진체계", "score": 0-15, "max_score": 15, "reason": "평가 근거"}},
    {{"item": "사업 추진전략", "score": 0-15, "max_score": 15, "reason": "평가 근거"}},
    {{"item": "리스크 관리", "score": 0-10, "max_score": 10, "reason": "평가 근거"}},
    {{"item": "성과관리", "score": 0-10, "max_score": 10, "reason": "평가 근거"}}
  ],
  "reasoning": "점수 산정 논리 상세 설명",
  "strengths": ["발견된 모든 강점을 나열"],
  "weaknesses": ["발견된 모든 약점을 나열"],
  "recommendations": ["필요한 모든 개선안을 나열"]
}}

**주의**: strengths, weaknesses, recommendations는 각각 발견된 모든 내용을 빠짐없이 나열해주세요.
JSON만 출력하세요."""

    @staticmethod
    def _parse_and_validate_response(
        response_text: str,
        required_keys: List[str]
    ) -> Dict[str, Any]:
        """API 응답 파싱 및 검증

        Args:
            response_text: JSON 응답 텍스트
            required_keys: 필수 키 리스트

        Returns:
            파싱된 딕셔너리

        Raises:
            json.JSONDecodeError: JSON 파싱 실패
            KeyError: 필수 키 누락
        """
        result = json.loads(response_text)

        # 필수 키 검증
        for key in required_keys:
            if key not in result:
                raise KeyError(f"필수 키 '{key}'가 응답에 없습니다")

        return result

    @staticmethod
    def _create_audit_evidence(result: Dict[str, Any], max_score: int) -> AuditEvidence:
        """API 응답에서 AuditEvidence 객체 생성

        Args:
            result: 파싱된 API 응답
            max_score: 만점

        Returns:
            AuditEvidence 객체
        """
        score = result.get('total_score', 0)
        return AuditEvidence(
            score=score,
            max_score=max_score,
            percentage=round(score / max_score * 100, 1) if max_score > 0 else 0.0,
            detailed_scores=result.get('detailed_scores', []),
            reasoning=result.get('reasoning', ''),
            strengths=result.get('strengths', []),
            weaknesses=result.get('weaknesses', []),
            recommendations=result.get('recommendations', [])
        )

    def conduct_audit(self, full_text: str) -> Optional[Dict[str, Any]]:
        """전체 심사 수행 (RAG 기반)

        Args:
            full_text: 심사할 전체 텍스트

        Returns:
            심사 결과 딕셔너리 또는 None
        """
        start_time = datetime.now()
        logger.info("심사 시작")

        try:
            # 1. 벡터 스토어 생성 시도
            vector_store = self.create_vector_store(full_text)

            if not vector_store:
                st.warning("⚠️ RAG 모드 실패. 전체 텍스트 앞부분으로 분석합니다.")
                logger.warning("RAG 모드 실패, fallback으로 진행")

            # 2. 정책 부합성 분석
            with st.spinner("🌍 정책 부합성 분석 중..."):
                policy_result = self.analyze_policy_alignment(vector_store, full_text)

            # 3. 추진 여건 분석
            with st.spinner("🏗️ 사업 추진 여건 분석 중..."):
                impl_result = self.analyze_implementation_readiness(vector_store, full_text)

            # 4. 결과 종합
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            results = {
                "총점": policy_result.score + impl_result.score,
                "정책부합성": {
                    "점수": policy_result.score,
                    "만점": policy_result.max_score,
                    "백분율": policy_result.percentage,
                    "세부점수": policy_result.detailed_scores,
                    "강점": policy_result.strengths,
                    "약점": policy_result.weaknesses,
                    "제안": policy_result.recommendations
                },
                "추진여건": {
                    "점수": impl_result.score,
                    "만점": impl_result.max_score,
                    "백분율": impl_result.percentage,
                    "세부점수": impl_result.detailed_scores,
                    "강점": impl_result.strengths,
                    "약점": impl_result.weaknesses,
                    "제안": impl_result.recommendations
                },
                "분석시간": f"{duration:.1f}초",
                "RAG_사용": vector_store is not None
            }

            logger.info(f"심사 완료: 총점 {results['총점']}/100, 소요시간 {duration:.1f}초")
            return results

        except Exception as e:
            logger.error(f"심사 수행 중 오류: {e}")
            logger.error(traceback.format_exc())
            st.error(f"❌ 심사 수행 중 오류가 발생했습니다.")
            # 프로덕션에서는 상세 스택트레이스를 숨김
            # st.code(traceback.format_exc())
            return None
