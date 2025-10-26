#!/usr/bin/env python3
"""
KOICA 사업 예비조사 심사 시스템 - Streamlit Web App
(RAG v3 - 임베딩 방식 개선 버전 - 수정됨)
"""

import streamlit as st
import os
import json
import traceback
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

# --- 필수 패키지 임포트 ---
import PyPDF2
import google.generativeai as genai
from google.generativeai.types import GenerationConfig
import numpy as np

# --- 페이지 설정 ---
st.set_page_config(
    page_title="KOICA 심사 분석 도구 v3 (RAG)",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS 스타일 ---
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        text-align: center;
        color: #666;
        margin-bottom: 2rem;
    }
    .score-box {
        padding: 20px;
        border-radius: 10px;
        margin: 20px 0;
        text-align: center;
    }
    .good-score { background-color: #d4edda; border: 2px solid #28a745; }
    .average-score { background-color: #fff3cd; border: 2px solid #ffc107; }
    .poor-score { background-color: #f8d7da; border: 2px solid #dc3545; }
    .disclaimer {
        background-color: #fff3cd;
        border-left: 5px solid #ffc107;
        padding: 15px;
        margin: 20px 0;
        border-radius: 5px;
    }
</style>
""", unsafe_allow_html=True)


# --- 데이터 클래스 ---
@dataclass
class AuditEvidence:
    """심사 근거 데이터 클래스"""
    score: int
    max_score: int
    percentage: float
    detailed_scores: List[Dict[str, Any]]
    reasoning: str
    strengths: List[str]
    weaknesses: List[str]
    recommendations: List[str]


class SimpleVectorStore:
    """간단한 벡터 스토어 (Gemini API 직접 사용)"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        genai.configure(api_key=api_key)
        self.chunks = []
        self.embeddings = []
    
    def add_texts(self, texts: List[str], batch_size: int = 1):
        """텍스트를 임베딩하여 저장 - 단일 텍스트씩 처리로 변경"""
        self.chunks = texts
        total = len(texts)
        
        progress_bar = st.progress(0)
        
        for i, text in enumerate(texts, 1):
            try:
                # 단일 텍스트씩 임베딩 생성 (배치 문제 회피)
                result = genai.embed_content(
                    model="models/text-embedding-004",
                    content=text,
                    task_type="retrieval_document"
                )
                
                # 단일 텍스트 응답 처리
                if isinstance(result, dict) and 'embedding' in result:
                    self.embeddings.append(result['embedding'])
                elif isinstance(result, list):
                    self.embeddings.append(result)
                else:
                    st.warning(f"청크 {i}: 예상치 못한 응답 구조")
                    self.embeddings.append([0.0] * 768)
                
                progress = i / total
                progress_bar.progress(progress, text=f"임베딩 생성 중: {i}/{total}")
                
                # API Rate Limit 방지
                if i % 10 == 0:
                    time.sleep(1)
                else:
                    time.sleep(0.3)
                
            except Exception as e:
                st.error(f"청크 {i} 임베딩 실패: {e}")
                # 실패한 청크는 빈 임베딩으로 채움
                self.embeddings.append([0.0] * 768)
        
        progress_bar.empty()
        st.success(f"✅ {len(self.embeddings)}개 청크 임베딩 완료!")
    
    def similarity_search(self, query: str, k: int = 10) -> List[str]:
        """쿼리와 유사한 청크 검색"""
        if not self.embeddings:
            return []
        
        try:
            # 쿼리 임베딩
            result = genai.embed_content(
                model="models/text-embedding-004",
                content=query,
                task_type="retrieval_query"
            )
            
            # 쿼리 임베딩 응답 처리
            if isinstance(result, dict) and 'embedding' in result:
                query_embedding = result['embedding']
            elif isinstance(result, list):
                query_embedding = result
            else:
                st.warning(f"예상치 못한 쿼리 응답 구조: {type(result)}")
                return self.chunks[:k]
            
            # 코사인 유사도 계산
            similarities = []
            for idx, doc_embedding in enumerate(self.embeddings):
                similarity = self._cosine_similarity(query_embedding, doc_embedding)
                similarities.append((idx, similarity))
            
            # 상위 k개 선택
            similarities.sort(key=lambda x: x[1], reverse=True)
            top_k = similarities[:k]
            
            return [self.chunks[idx] for idx, _ in top_k]
            
        except Exception as e:
            st.warning(f"검색 중 오류: {e}")
            return self.chunks[:k]  # 실패 시 앞부분 반환
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """코사인 유사도 계산"""
        try:
            vec1 = np.array(vec1)
            vec2 = np.array(vec2)
            
            # Zero division 방지
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            return np.dot(vec1, vec2) / (norm1 * norm2)
        except Exception:
            return 0.0


class KOICAAuditorStreamlit:
    """KOICA 심사 시스템 - RAG v3"""
    
    def __init__(self, api_key: Optional[str] = None):
        """시스템 초기화"""
        self.audit_criteria = {
            "정책부합성": {
                "만점": 30,
                "항목": ["SDGs 연관성", "수원국 정책", "CPS/국정과제", "코이카 전략", "타 공여기관"]
            },
            "추진여건": {
                "만점": 70,
                "항목": ["수원국 추진체계", "국내 추진체계", "사업 추진전략", "리스크 관리", "성과관리"]
            }
        }
        
        if not api_key:
            raise ValueError("Gemini API 키가 필요합니다")
        
        try:
            genai.configure(api_key=api_key)
            
            # JSON 모드 설정
            self.json_config = GenerationConfig(response_mime_type="application/json")
            
            # Gemini 모델 초기화
            self.model = genai.GenerativeModel(
                'gemini-2.5-pro',
                generation_config=self.json_config
            )
            
            self.api_key = api_key
            
        except Exception as e:
            raise Exception(f"Gemini API 연결 실패: {e}")
    
    def extract_text_from_pdf(self, pdf_file) -> str:
        """PDF에서 전체 텍스트 추출"""
        try:
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            full_text = ""
            total_pages = len(pdf_reader.pages)
            
            progress_bar = st.progress(0, text="📄 PDF 텍스트 추출 중...")
            
            for page_num, page in enumerate(pdf_reader.pages, 1):
                try:
                    full_text += page.extract_text() + "\n"
                    progress = page_num / total_pages
                    progress_bar.progress(progress, text=f"페이지 추출 중: {page_num}/{total_pages}")
                except Exception:
                    st.warning(f"페이지 {page_num} 처리 오류 (건너뜀)")
            
            progress_bar.empty()
            return full_text
            
        except Exception as e:
            raise Exception(f"PDF 처리 오류: {e}")

    def create_vector_store(self, full_text: str) -> Optional[SimpleVectorStore]:
        """텍스트를 청크로 나누고 벡터 스토어 생성"""
        if not full_text:
            st.error("추출된 텍스트가 없습니다.")
            return None
        
        # 텍스트를 청크로 분할
        chunks = self._split_text(full_text, chunk_size=1500, overlap=200)
        
        if not chunks:
            st.error("텍스트를 청크로 나눌 수 없습니다.")
            return None
        
        st.info(f"📦 총 {len(chunks)}개 청크 생성됨")
        
        try:
            vector_store = SimpleVectorStore(self.api_key)
            vector_store.add_texts(chunks)
            return vector_store
            
        except Exception as e:
            st.error(f"벡터 스토어 생성 실패: {e}")
            st.code(traceback.format_exc())
            return None
    
    def _split_text(self, text: str, chunk_size: int = 1500, overlap: int = 200) -> List[str]:
        """텍스트를 청크로 분할"""
        chunks = []
        start = 0
        text_length = len(text)
        
        while start < text_length:
            end = start + chunk_size
            chunk = text[start:end]
            chunks.append(chunk)
            start = end - overlap
        
        return chunks

    def get_relevant_context(self, vector_store: SimpleVectorStore, query: str, k: int = 10) -> str:
        """벡터 스토어에서 쿼리와 관련된 K개의 청크 검색"""
        if vector_store is None:
            return ""
        try:
            docs = vector_store.similarity_search(query, k=k)
            context = "\n---\n".join(docs)
            return context
        except Exception as e:
            st.warning(f"관련 컨텍스트 검색 오류: {e}")
            return ""

    def analyze_policy_alignment(self, vector_store: SimpleVectorStore = None, full_text: str = "") -> AuditEvidence:
        """[RAG 적용] 국내외 정책 부합성 AI 분석"""
        
        # RAG: 관련성 높은 컨텍스트 검색
        if vector_store:
            query = "국내외 정책 부합성, SDGs, 수원국 개발 정책, 한국 정부 CPS, 코이카 중기 전략, 타 공여기관 지원 현황, ODA"
            context = self.get_relevant_context(vector_store, query, k=15)
        else:
            context = full_text[:30000] if full_text else ""
        
        if not context:
            context = "보고서에서 관련 내용을 찾을 수 없습니다."
        
        prompt = f"""당신은 KOICA 사업 심사 전문가입니다. 다음 보고서 발췌 내용을 '국내외 정책 부합성' 기준으로 평가하세요.

=== 평가 기준 (30점 만점) ===
1. SDGs와의 연관성 (10점)
2. 수원국 정책 부합성 (5점)
3. 한국 정부 CPS 및 국정과제 연계 (5점)
4. 코이카 중기전략 부합성 (5점)
5. 타 공여기관 중복 분석 (5점)

=== 보고서 발췌 내용 ===
{context[:35000]}

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
  "strengths": ["강점1", "강점2"],
  "weaknesses": ["약점1", "약점2"],
  "recommendations": ["개선안1", "개선안2"]
}}

JSON만 출력하세요."""

        try:
            response = self.model.generate_content(prompt)
            result = json.loads(response.text)
            
            return AuditEvidence(
                score=result['total_score'],
                max_score=30,
                percentage=round(result['total_score'] / 30 * 100, 1),
                detailed_scores=result.get('detailed_scores', []),
                reasoning=result.get('reasoning', ''),
                strengths=result.get('strengths', []),
                weaknesses=result.get('weaknesses', []),
                recommendations=result.get('recommendations', [])
            )
        except Exception as e:
            st.error(f"정책부합성 분석 오류: {e}")
            return AuditEvidence(0, 30, 0.0, [], f"분석 실패: {e}", [], [], [])

    def analyze_implementation_readiness(self, vector_store: SimpleVectorStore = None, full_text: str = "") -> AuditEvidence:
        """[RAG 적용] 사업 추진 여건 AI 분석"""
        
        if vector_store:
            query = "사업 추진 여건, 수원국 추진체계, 국내 추진체계, 사업 추진전략, 리스크 관리, 성과관리, 예산, 일정"
            context = self.get_relevant_context(vector_store, query, k=15)
        else:
            context = full_text[:30000] if full_text else ""
        
        if not context:
            context = "보고서에서 관련 내용을 찾을 수 없습니다."
        
        prompt = f"""당신은 KOICA 사업 심사 전문가입니다. 다음 보고서 발췌 내용을 '사업 추진 여건' 기준으로 평가하세요.

=== 평가 기준 (70점 만점) ===
1. 수원국 추진체계 (20점)
2. 국내 추진체계 (15점)
3. 사업 추진전략 (15점)
4. 리스크 관리 (10점)
5. 성과관리 (10점)

=== 보고서 발췌 내용 ===
{context[:35000]}

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
  "strengths": ["강점1", "강점2"],
  "weaknesses": ["약점1", "약점2"],
  "recommendations": ["개선안1", "개선안2"]
}}

JSON만 출력하세요."""

        try:
            response = self.model.generate_content(prompt)
            result = json.loads(response.text)
            
            return AuditEvidence(
                score=result['total_score'],
                max_score=70,
                percentage=round(result['total_score'] / 70 * 100, 1),
                detailed_scores=result.get('detailed_scores', []),
                reasoning=result.get('reasoning', ''),
                strengths=result.get('strengths', []),
                weaknesses=result.get('weaknesses', []),
                recommendations=result.get('recommendations', [])
            )
        except Exception as e:
            st.error(f"추진여건 분석 오류: {e}")
            return AuditEvidence(0, 70, 0.0, [], f"분석 실패: {e}", [], [], [])

    def conduct_audit(self, full_text: str) -> Optional[Dict[str, Any]]:
        """전체 심사 수행 (RAG 기반)"""
        start_time = datetime.now()
        
        try:
            # 1. 벡터 스토어 생성 시도
            vector_store = self.create_vector_store(full_text)
            
            if not vector_store:
                st.warning("⚠️ RAG 모드 실패. 전체 텍스트 앞부분으로 분석합니다.")
            
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
            
            return results
            
        except Exception as e:
            st.error(f"❌ 심사 수행 중 오류: {e}")
            st.code(traceback.format_exc())
            return None


def display_results(results: Dict[str, Any]):
    """분석 결과 표시"""
    # RAG 사용 여부 표시
    if not results.get('RAG_사용', False):
        st.warning("⚠️ 이 분석은 RAG 없이 수행되었습니다. 전체 문서가 아닌 앞부분만 분석되었을 수 있습니다.")
    else:
        st.success("✅ RAG 기반 전체 문서 분석 완료")
    
    # 총점 표시
    total_score = results['총점']
    score_class = "good-score" if total_score >= 80 else "average-score" if total_score >= 60 else "poor-score"
    st.markdown(f"""
    <div class="score-box {score_class}">
        <h2>총점: {total_score} / 100</h2>
        <p>분석 시간: {results['분석시간']}</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("### 📋 항목별 평가")
    col1, col2 = st.columns(2)
    
    with col1:
        policy = results['정책부합성']
        st.markdown("#### 🌍 국내외 정책 부합성")
        st.metric("점수", f"{policy['점수']}/{policy['만점']}", f"{policy['백분율']:.1f}%")
        
        with st.expander("상세 분석 보기"):
            st.markdown("**📌 세부 항목 평가**")
            for item in policy['세부점수']:
                st.markdown(f"**{item['item']} ({item['score']}/{item['max_score']})**")
                st.caption(f"_{item['reason']}_")
            
            st.markdown("---")
            st.markdown("**✅ 강점**")
            for s in policy['강점']:
                st.markdown(f"- {s}")
            st.markdown("**⚠️ 약점**")
            for w in policy['약점']:
                st.markdown(f"- {w}")
            st.markdown("**💡 개선 제안**")
            for r in policy['제안']:
                st.markdown(f"- {r}")
    
    with col2:
        impl = results['추진여건']
        st.markdown("#### 🏗️ 사업 추진 여건")
        st.metric("점수", f"{impl['점수']}/{impl['만점']}", f"{impl['백분율']:.1f}%")
        
        with st.expander("상세 분석 보기"):
            st.markdown("**📌 세부 항목 평가**")
            for item in impl['세부점수']:
                st.markdown(f"**{item['item']} ({item['score']}/{item['max_score']})**")
                st.caption(f"_{item['reason']}_")

            st.markdown("---")
            st.markdown("**✅ 강점**")
            for s in impl['강점']:
                st.markdown(f"- {s}")
            st.markdown("**⚠️ 약점**")
            for w in impl['약점']:
                st.markdown(f"- {w}")
            st.markdown("**💡 개선 제안**")
            for r in impl['제안']:
                st.markdown(f"- {r}")


def generate_report_text(results: Dict[str, Any]) -> str:
    """텍스트 보고서 생성"""
    lines = []
    lines.append("=" * 80)
    lines.append("KOICA 사업 심사 분석 결과 (AI-RAG v3)")
    lines.append("=" * 80)
    lines.append(f"분석 일시: {datetime.now().strftime('%Y년 %m월 %d일 %H:%M:%S')}")
    lines.append(f"분석 시간: {results['분석시간']}")
    lines.append(f"RAG 사용: {'예' if results.get('RAG_사용', False) else '아니오'}")
    lines.append(f"총점: {results['총점']} / 100\n")
    
    # 정책 부합성
    policy = results['정책부합성']
    lines.append(f"\n[1] 국내외 정책 부합성 ({policy['점수']}/{policy['만점']})")
    lines.append("-" * 80)
    lines.append("\n세부 평가:")
    for item in policy['세부점수']:
        lines.append(f"  • {item['item']} ({item['score']}/{item['max_score']})")
        lines.append(f"    └ 근거: {item['reason']}")
    lines.append("\n강점:")
    for s in policy['강점']:
        lines.append(f"  ✓ {s}")
    lines.append("\n약점:")
    for w in policy['약점']:
        lines.append(f"  ✗ {w}")
    lines.append("\n개선 제안:")
    for r in policy['제안']:
        lines.append(f"  → {r}")
    
    # 추진 여건
    impl = results['추진여건']
    lines.append(f"\n\n[2] 사업 추진 여건 ({impl['점수']}/{impl['만점']})")
    lines.append("-" * 80)
    lines.append("\n세부 평가:")
    for item in impl['세부점수']:
        lines.append(f"  • {item['item']} ({item['score']}/{item['max_score']})")
        lines.append(f"    └ 근거: {item['reason']}")
    lines.append("\n강점:")
    for s in impl['강점']:
        lines.append(f"  ✓ {s}")
    lines.append("\n약점:")
    for w in impl['약점']:
        lines.append(f"  ✗ {w}")
    lines.append("\n개선 제안:")
    for r in impl['제안']:
        lines.append(f"  → {r}")
    
    lines.append("\n\n" + "=" * 80)
    lines.append("면책 조항")
    lines.append("=" * 80)
    lines.append("본 분석 결과는 AI 기반 참고용이며, KOICA 공식 심사 결과가 아닙니다.")
    lines.append("실제 심사는 전문가의 종합적 판단으로 이루어집니다.")
    
    return "\n".join(lines)


# ========== 메인 앱 ==========

def main():
    st.markdown('<h1 class="main-header">🚀 KOICA 사업 심사 분석 도구 (RAG v3)</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">개선된 RAG · 비공식 개인 프로젝트</p>', unsafe_allow_html=True)
    
    # Disclaimer
    st.markdown("""
    <div class="disclaimer">
        <strong>⚠️ 주의사항</strong><br>
        본 도구는 <strong>KOICA 공식 서비스가 아닙니다</strong>. 개인이 KOICA 심사 기준을 참고하여 독자적으로 개발한 분석 도구입니다. 분석 결과는 참고용이며, 공식적인 심사 결과와 다를 수 있습니다.
    </div>
    """, unsafe_allow_html=True)
    
    # API 키 로드
    api_key = None
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
    except:
        api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        st.error("⚠️ Gemini API 키가 설정되지 않았습니다.")
        st.info("`.streamlit/secrets.toml` 또는 환경변수에 `GEMINI_API_KEY`를 설정하세요.")
        st.stop()

    # 사이드바
    with st.sidebar:
        st.markdown("## 📊 도구 정보 (v3 - 수정됨)")
        st.warning("**비공식 개인 프로젝트**")
        st.markdown("---")
        st.markdown("### ℹ️ v3 개선 사항")
        st.info("""
        - ✅ **임베딩 API 단일 처리로 변경**
        - **안정적인 임베딩**: Gemini API 직접 사용
        - **배치 문제 해결**: 단일 텍스트씩 처리
        - **오류 복구**: 실패 시 자동 대체
        - **진행 상황 표시**: 실시간 프로그레스바
        """)
        st.success("✅ API 연결됨")
    
    # 메인 영역
    tab1, tab2, tab3 = st.tabs(["📄 PDF 분석 (권장)", "📝 텍스트 분석", "ℹ️ 사용 가이드"])
    
    try:
        auditor = KOICAAuditorStreamlit(api_key=api_key)
    except Exception as e:
        st.error(f"초기화 실패: {e}")
        st.stop()

    with tab1:
        st.markdown("### PDF 보고서 업로드")
        uploaded_file = st.file_uploader("KOICA 예비조사 보고서 (PDF)", type=['pdf'], key="pdf_uploader")
        
        if uploaded_file:
            st.success(f"✅ 파일 업로드 완료: {uploaded_file.name}")
            
            if st.button("🚀 분석 시작 (RAG v3)", type="primary", key="analyze_pdf"):
                try:
                    # 1. 텍스트 추출
                    full_text = auditor.extract_text_from_pdf(uploaded_file)
                    st.session_state['pdf_full_text'] = full_text
                    
                    if not full_text:
                        st.error("PDF에서 텍스트를 추출하지 못했습니다.")
                    else:
                        # 2. 분석 수행
                        results = auditor.conduct_audit(full_text=full_text)
                        if results:
                            st.session_state['pdf_results'] = results
                    
                except Exception as e:
                    st.error(f"❌ PDF 분석 오류: {e}")
                    st.exception(e)
        
        # 결과 표시
        if 'pdf_results' in st.session_state:
            results = st.session_state['pdf_results']
            display_results(results)
            
            report_text = generate_report_text(results)
            st.download_button(
                label="📥 심사 결과 다운로드",
                data=report_text,
                file_name=f"KOICA_RAG_심사결과_{datetime.now().strftime('%Y%m%d')}.txt",
                mime="text/plain",
                key="download_pdf"
            )
    
    with tab2:
        st.markdown("### 텍스트 직접 입력")
        text_input = st.text_area("보고서 내용을 입력하세요", height=300, key="text_input")
        
        if st.button("🚀 분석 시작 (RAG v3)", key="text_analyze", type="primary"):
            if text_input.strip():
                try:
                    results = auditor.conduct_audit(full_text=text_input)
                    if results:
                        st.session_state['text_results'] = results
                    
                except Exception as e:
                    st.error(f"❌ 텍스트 분석 오류: {e}")
            else:
                st.warning("⚠️ 분석할 텍스트를 입력하세요")
        
        if 'text_results' in st.session_state:
            results = st.session_state['text_results']
            display_results(results)
            
            report_text = generate_report_text(results)
            st.download_button(
                label="📥 심사 결과 다운로드",
                data=report_text,
                file_name=f"KOICA_RAG_심사결과_{datetime.now().strftime('%Y%m%d')}.txt",
                mime="text/plain",
                key="download_text"
            )
    
    with tab3:
        st.markdown("### 📖 사용 가이드 (v3 - 개선된 RAG)")
        st.markdown("#### 🔧 v3의 주요 개선사항")
        st.markdown("""
        **문제 해결:**
        - ✅ **임베딩 배치 처리 문제 해결 (단일 처리로 변경)**
        - v2에서 발생했던 "Illegal metadata" 오류 해결
        - Langchain 의존성 제거, Gemini API 직접 사용
        - 더 안정적이고 빠른 임베딩 처리
        
        **성능 향상:**
        - 단일 텍스트씩 처리로 안정성 확보
        - 실시간 진행 상황 표시
        - 오류 발생 시 자동 복구
        - 향상된 오류 처리 및 디버깅 메시지
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

    # 푸터
    st.markdown("---")
    st.markdown("<div style='text-align: center; color: #666;'>KOICA 사업 심사 분석 도구 v3 (개선된 RAG) | 비공식 개인 프로젝트</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
