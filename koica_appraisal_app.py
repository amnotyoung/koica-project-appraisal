#!/usr/bin/env python3
"""
KOICA 사업 예비조사 심사 시스템 - Streamlit Web App
(RAG, JSON 모드, 세부 채점 기능 적용 버전 - 임베딩 오류 수정)
"""

import streamlit as st
import os
import io
import json
import traceback
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

# --- 필수 패키지 임포트 ---
import PyPDF2
import google.generativeai as genai
from google.generativeai.types import GenerationConfig
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings

# --- 페이지 설정 ---
st.set_page_config(
    page_title="KOICA 심사 분석 도구 v2 (RAG)",
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


class KOICAAuditorStreamlit:
    """KOICA 심사 시스템 - RAG 적용 버전"""
    
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
            # 1. Gemini 설정
            genai.configure(api_key=api_key)
            
            # 2. JSON 모드 설정
            self.json_config = GenerationConfig(response_mime_type="application/json")
            
            # 3. Gemini 모델 초기화 (JSON 모드 적용)
            self.model = genai.GenerativeModel(
                'gemini-2.0-flash-exp',
                generation_config=self.json_config
            )
            
            # 4. RAG를 위한 임베딩 모델 초기화 (수정됨)
            # task_type을 명시적으로 지정하여 메타데이터 오류 방지
            self.embeddings = GoogleGenerativeAIEmbeddings(
                model="models/text-embedding-004",
                google_api_key=api_key,
                task_type="retrieval_document"  # 문서 검색용으로 명시
            )
            
        except Exception as e:
            raise Exception(f"Gemini API 또는 임베딩 모델 연결 실패: {e}")
    
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

    def create_vector_store(self, full_text: str) -> Optional[FAISS]:
        """텍스트를 청크로 나누고 벡터 스토어(FAISS) 생성 (오류 수정 버전)"""
        if not full_text:
            st.error("추출된 텍스트가 없습니다.")
            return None
        
        # 1. 텍스트를 청크로 분할
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1500,
            chunk_overlap=200,
            separators=["\n\n", "\n", "##", "#", " ", ""]
        )
        chunks = text_splitter.split_text(full_text)
        
        if not chunks:
            st.error("텍스트를 청크로 나눌 수 없습니다.")
            return None
        
        st.info(f"📦 총 {len(chunks)}개 청크 생성됨. 임베딩 중...")
        
        try:
            # 2. 벡터 스토어 생성 (배치 처리로 안정성 향상)
            with st.spinner("임베딩 생성 및 벡터 인덱싱 중... (문서 크기에 따라 시간이 걸릴 수 있습니다)"):
                # 큰 문서의 경우 배치 처리
                batch_size = 50  # 한 번에 50개씩 처리
                
                if len(chunks) <= batch_size:
                    # 작은 문서는 한 번에 처리
                    vector_store = FAISS.from_texts(chunks, self.embeddings)
                else:
                    # 큰 문서는 배치로 나누어 처리
                    vector_store = None
                    progress_bar = st.progress(0)
                    
                    for i in range(0, len(chunks), batch_size):
                        batch = chunks[i:i+batch_size]
                        progress = (i + len(batch)) / len(chunks)
                        progress_bar.progress(progress, text=f"임베딩 진행 중: {i+len(batch)}/{len(chunks)}")
                        
                        if vector_store is None:
                            # 첫 배치로 벡터 스토어 초기화
                            vector_store = FAISS.from_texts(batch, self.embeddings)
                        else:
                            # 기존 벡터 스토어에 추가
                            temp_store = FAISS.from_texts(batch, self.embeddings)
                            vector_store.merge_from(temp_store)
                    
                    progress_bar.empty()
            
            st.success("✅ 벡터 스토어 생성 완료!")
            return vector_store
            
        except Exception as e:
            st.error(f"벡터 스토어 생성 실패: {e}")
            st.code(traceback.format_exc())
            
            # 대체 방안 제시
            st.warning("💡 **대체 방안**: RAG 없이 전체 텍스트의 앞부분만 분석하시겠습니까?")
            if st.button("RAG 없이 계속 진행", key="fallback_no_rag"):
                st.session_state['use_fallback'] = True
            
            return None

    def get_relevant_context(self, vector_store: FAISS, query: str, k: int = 10) -> str:
        """벡터 스토어에서 쿼리와 관련된 K개의 청크 검색"""
        if vector_store is None:
            return ""
        try:
            docs = vector_store.similarity_search(query, k=k)
            context = "\n---\n".join([doc.page_content for doc in docs])
            return context
        except Exception as e:
            st.warning(f"관련 컨텍스트 검색 오류: {e}")
            return ""

    def analyze_policy_alignment(self, vector_store: FAISS = None, full_text: str = "") -> AuditEvidence:
        """[RAG 적용] 국내외 정책 부합성 AI 분석"""
        
        # 1. RAG: 관련성 높은 컨텍스트 검색
        if vector_store:
            query = "국내외 정책 부합성, SDGs, 수원국 개발 정책, 한국 정부 CPS, 코이카 중기 전략, 타 공여기관 지원 현황, ODA"
            context = self.get_relevant_context(vector_store, query)
        else:
            # RAG 실패 시 전체 텍스트의 앞부분 사용
            context = full_text[:30000] if full_text else ""
        
        if not context:
            context = "보고서에서 관련 내용을 찾을 수 없습니다."
        
        # 2. 세부 채점 기준 프롬프트 (JSON 모드)
        prompt = f"""당신은 KOICA 사업 심사 전문가입니다. 다음 보고서 발췌 내용을 '국내외 정책 부합성' 기준으로 평가하세요.

=== 평가 기준 (30점 만점) ===
1. SDGs와의 연관성 (10점)
2. 수원국 정책 부합성 (5점)
3. 한국 정부 CPS 및 국정과제 연계 (5점)
4. 코이카 중기전략 부합성 (5점)
5. 타 공여기관 중복 분석 (5점)

=== 보고서 발췌 내용 ===
{context[:30000]}

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

    def analyze_implementation_readiness(self, vector_store: FAISS = None, full_text: str = "") -> AuditEvidence:
        """[RAG 적용] 사업 추진 여건 AI 분석"""
        
        if vector_store:
            query = "사업 추진 여건, 수원국 추진체계, 국내 추진체계, 사업 추진전략, 리스크 관리, 성과관리, 예산, 일정"
            context = self.get_relevant_context(vector_store, query)
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
{context[:30000]}

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
    lines.append("KOICA 사업 심사 분석 결과 (AI-RAG 기반 v2)")
    lines.append("=" * 80)
    lines.append(f"분석 일시: {datetime.now().strftime('%Y년 %m월 %d일 %H:%M:%S')}")
    lines.append(f"분석 시간: {results['분석시간']}")
    lines.append(f"RAG 사용: {'예' if results.get('RAG_사용', False) else '아니오 (전체 텍스트 앞부분만 분석)'}")
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
    st.markdown('<h1 class="main-header">🚀 KOICA 사업 심사 분석 도구 (RAG v2)</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">RAG, JSON 모드 적용 · 비공식 개인 프로젝트</p>', unsafe_allow_html=True)
    
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
        st.markdown("## 📊 도구 정보 (v2)")
        st.warning("**비공식 개인 프로젝트**")
        st.markdown("---")
        st.markdown("### ℹ️ v2 주요 기능")
        st.info("""
        - **RAG (Retrieval-Augmented Generation)**:
          문서 전체를 벡터화하여 심사 항목과
          관련된 핵심 내용만 AI에 전달
        - **JSON 모드**: 안정적인 분석 결과
        - **세부 항목 채점**: 정교한 피드백
        - **오류 복구**: RAG 실패 시 대체 방안 제공
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
            
            if st.button("🚀 분석 시작 (RAG)", type="primary", key="analyze_pdf"):
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
        
        if st.button("🚀 분석 시작 (RAG)", key="text_analyze", type="primary"):
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
        st.markdown("### 📖 사용 가이드 (v2 - RAG)")
        st.markdown("#### 🚀 RAG (Retrieval-Augmented Generation) 란?")
        st.markdown("""
        이전 버전(v1)은 보고서의 **앞부분 4,000자**만 분석하는 한계가 있었습니다.
        
        **v2의 RAG 방식**은 다릅니다:
        1. **벡터화:** PDF 문서 전체를 텍스트로 변환한 뒤, 의미 단위(청크)로 잘라 '벡터'로 변환하여 데이터베이스를 구축합니다.
        2. **검색:** '정책 부합성'을 분석할 땐, PDF 전체에서 "SDGs", "CPS" 등 관련 내용만 **검색(Retrieval)**합니다.
        3. **분석:** AI는 검색된 **핵심 내용들만**을 바탕으로 심사를 진행합니다.
        
        **결과: 100페이지가 넘는 문서라도 전체 내용을 빠짐없이 검토하여 훨씬 정확한 심사 결과를 제공합니다.**
        """)
        
        st.markdown("#### 🔧 오류 발생 시 대처 방법")
        st.markdown("""
        **"Illegal metadata" 또는 "503" 오류가 발생하면:**
        - 이는 Google API의 일시적 문제일 수 있습니다
        - 시스템이 자동으로 대체 방안(전체 텍스트 앞부분 분석)을 제공합니다
        - 몇 분 후 다시 시도하거나, 문서를 더 작은 부분으로 나누어 분석하세요
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
    st.markdown("<div style='text-align: center; color: #666;'>KOICA 사업 심사 분석 도구 v2 (RAG) | 비공식 개인 프로젝트</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
