#!/usr/bin/env python3
"""
KOICA 사업 예비조사 심사 시스템 - Streamlit Web App
"""

import streamlit as st
import os
import io
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

# 필수 패키지
try:
    import PyPDF2
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

# 페이지 설정
st.set_page_config(
    page_title="KOICA 심사 분석 도구 (비공식)",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS 스타일
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: bold;
        color: #2c3e50;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #7f8c8d;
        text-align: center;
        margin-bottom: 2rem;
        font-style: italic;
    }
    .disclaimer {
        background-color: #fff3cd;
        border-left: 4px solid #ffc107;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 5px;
    }
    .score-box {
        padding: 1.5rem;
        border-radius: 10px;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .good-score {
        background-color: #d4edda;
        border: 2px solid #28a745;
    }
    .average-score {
        background-color: #fff3cd;
        border: 2px solid #ffc107;
    }
    .poor-score {
        background-color: #f8d7da;
        border: 2px solid #dc3545;
    }
</style>
""", unsafe_allow_html=True)


@dataclass
class AuditEvidence:
    """심사 근거 데이터 클래스"""
    score: int
    max_score: int
    percentage: float
    evidence_text: List[str]
    reasoning: str
    strengths: List[str]
    weaknesses: List[str]
    recommendations: List[str]


class KOICAAuditorStreamlit:
    """KOICA 심사 시스템 - Streamlit 버전"""
    
    def __init__(self, api_key: Optional[str] = None):
        """시스템 초기화"""
        self.audit_criteria = {
            '국내외정책부합성': {
                'max_score': 30,
                'description': '사업이 국내외 상위 정책 및 전략과의 일치성',
                'detailed_items': [
                    '지속가능개발목표(SDGs)와의 연관성 및 기여도',
                    '수원국의 국가 개발 정책 및 전략과의 부합성',
                    '우리 정부의 국별 협력 전략(CPS) 및 주요 국정과제와의 연계성',
                    '코이카의 분야별 중기 전략 및 취약국 전략과의 부합성',
                    '다른 공여기관들의 유사 사업 지원 현황 분석'
                ]
            },
            '사업추진여건': {
                'max_score': 70,
                'description': '사업을 실제로 추진할 수 있는 현실적인 환경과 여건',
                'detailed_items': [
                    '문제 및 수요 분석의 체계성 (문제나무, 목표나무)',
                    '법/제도적 여건',
                    '사업 대상지 분석',
                    '이해관계자 분석',
                    '중복 여부 및 협업 가능성',
                    '파트너 재원 가능성',
                    '경제적 타당성 분석 (1,500만불 이상: B/C, NPV, IRR 필수)',
                    '지속가능성 및 출구전략',
                    '리스크 관리'
                ]
            }
        }
        
        if not GEMINI_AVAILABLE:
            raise ImportError("google-generativeai 패키지가 필요합니다")
        
        if not api_key:
            raise ValueError("Gemini API 키가 필요합니다")
        
        try:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-2.5-pro')
        except Exception as e:
            raise Exception(f"Gemini API 연결 실패: {e}")
    
    def extract_text_from_pdf(self, pdf_file) -> Dict[str, str]:
        """PDF 텍스트 추출"""
        if not PDF_AVAILABLE:
            raise ImportError("PyPDF2 필요")
        
        sections = {
            '사업개요': '', '정책부합성': '', '문제분석': '',
            '여건분석': '', '이해관계자분석': '', '리스크분석': '',
            '지속가능성': '', '전체내용': ''
        }
        
        try:
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            full_text = ""
            total_pages = len(pdf_reader.pages)
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for page_num, page in enumerate(pdf_reader.pages, 1):
                try:
                    full_text += page.extract_text() + "\n"
                    progress = page_num / total_pages
                    progress_bar.progress(progress)
                    status_text.text(f"페이지 추출 중: {page_num}/{total_pages}")
                except Exception as e:
                    st.warning(f"페이지 {page_num} 처리 오류 (건너뜀)")
            
            progress_bar.empty()
            status_text.empty()
            
            sections['전체내용'] = full_text
            sections['사업개요'] = self._extract_section(full_text, ['사업개요', '개요', '배경', '목적'], 10)
            sections['정책부합성'] = self._extract_section(full_text, ['정책', '부합성', 'SDG', 'CPS', '국정과제'], 8)
            sections['문제분석'] = self._extract_section(full_text, ['문제', '수요', '현황', '문제나무', '목표나무'], 8)
            sections['여건분석'] = self._extract_section(full_text, ['여건', '법', '제도', '환경', '대상지'], 8)
            sections['이해관계자분석'] = self._extract_section(full_text, ['이해관계자', '수혜자', '파트너', '협력기관'], 6)
            sections['리스크분석'] = self._extract_section(full_text, ['리스크', '위험', '관리', '대응'], 6)
            sections['지속가능성'] = self._extract_section(full_text, ['지속가능', '출구전략', '유지', '운영'], 6)
            
            return sections
            
        except Exception as e:
            raise Exception(f"PDF 처리 오류: {e}")
    
    def _extract_section(self, text: str, keywords: List[str], context_lines: int = 5) -> str:
        """키워드 기반 섹션 추출"""
        lines = text.split('\n')
        section_indices = set()
        
        for i, line in enumerate(lines):
            if any(kw.lower() in line.lower() for kw in keywords):
                start = max(0, i - context_lines)
                end = min(len(lines), i + context_lines + 1)
                section_indices.update(range(start, end))
        
        if not section_indices:
            return ""
        
        sorted_indices = sorted(section_indices)
        return '\n'.join(lines[i] for i in sorted_indices)
    
    def analyze_policy_alignment(self, content: str) -> AuditEvidence:
        """국내외 정책 부합성 AI 분석"""
        
        prompt = f"""당신은 KOICA 사업 심사 전문가입니다. 다음 보고서를 '국내외 정책 부합성' 기준으로 평가하세요.

=== 평가 기준 (30점 만점) ===
1. SDGs와의 연관성 및 기여도
2. 수원국 정책 부합성
3. 한국 정부 CPS 및 국정과제 연계
4. 코이카 중기전략 부합성
5. 타 공여기관 중복 분석

=== 보고서 내용 ===
{content[:4000]}

=== 출력 형식 (JSON) ===
{{
  "score": 0-30 사이 정수,
  "evidence": ["근거1", "근거2", "근거3"],
  "reasoning": "점수 산정 논리 상세 설명",
  "strengths": ["강점1", "강점2"],
  "weaknesses": ["약점1", "약점2"],
  "recommendations": ["개선안1", "개선안2"]
}}

JSON만 출력하세요."""

        try:
            response = self.model.generate_content(prompt)
            import json
            result = json.loads(response.text.strip().replace('```json', '').replace('```', ''))
            
            return AuditEvidence(
                score=result['score'],
                max_score=30,
                percentage=round(result['score'] / 30 * 100, 1),
                evidence_text=result.get('evidence', []),
                reasoning=result.get('reasoning', ''),
                strengths=result.get('strengths', []),
                weaknesses=result.get('weaknesses', []),
                recommendations=result.get('recommendations', [])
            )
        except Exception as e:
            st.error(f"AI 정책부합성 분석 오류: {e}")
            raise
    
    def analyze_implementation_readiness(self, content: str) -> AuditEvidence:
        """사업 추진 여건 AI 분석"""
        
        prompt = f"""당신은 KOICA 사업 심사 전문가입니다. 다음 보고서를 '사업 추진 여건' 기준으로 평가하세요.

=== 평가 기준 (70점 만점) ===
1. 문제/수요 분석 체계성
2. 법제도적 여건
3. 사업 대상지 분석
4. 이해관계자 분석
5. 중복성 및 협업
6. 경제성 분석
7. 지속가능성
8. 리스크 관리

=== 보고서 내용 ===
{content[:4000]}

=== 출력 형식 (JSON) ===
{{
  "score": 0-70 사이 정수,
  "evidence": ["근거1", "근거2", "근거3"],
  "reasoning": "점수 산정 논리",
  "strengths": ["강점1", "강점2"],
  "weaknesses": ["약점1", "약점2"],
  "recommendations": ["개선안1", "개선안2"]
}}

JSON만 출력하세요."""

        try:
            response = self.model.generate_content(prompt)
            import json
            result = json.loads(response.text.strip().replace('```json', '').replace('```', ''))
            
            return AuditEvidence(
                score=result['score'],
                max_score=70,
                percentage=round(result['score'] / 70 * 100, 1),
                evidence_text=result.get('evidence', []),
                reasoning=result.get('reasoning', ''),
                strengths=result.get('strengths', []),
                weaknesses=result.get('weaknesses', []),
                recommendations=result.get('recommendations', [])
            )
        except Exception as e:
            st.error(f"AI 추진여건 분석 오류: {e}")
            raise
    
    
    def conduct_audit(self, pdf_file=None, text_content=None) -> Dict[str, Any]:
        """심사 수행"""
        if pdf_file:
            sections = self.extract_text_from_pdf(pdf_file)
        else:
            sections = {'전체내용': text_content}
        
        content = sections.get('전체내용', '')
        
        with st.spinner('🤖 AI 정책부합성 분석 중...'):
            policy_result = self.analyze_policy_alignment(content)
        
        with st.spinner('🤖 AI 사업추진여건 분석 중...'):
            implementation_result = self.analyze_implementation_readiness(content)
        
        total_score = policy_result.score + implementation_result.score
        
        return {
            '정책부합성': {
                '점수': policy_result.score,
                '만점': policy_result.max_score,
                '백분율': policy_result.percentage,
                '근거': policy_result.evidence_text,
                '분석': policy_result.reasoning,
                '강점': policy_result.strengths,
                '약점': policy_result.weaknesses,
                '제안': policy_result.recommendations
            },
            '추진여건': {
                '점수': implementation_result.score,
                '만점': implementation_result.max_score,
                '백분율': implementation_result.percentage,
                '근거': implementation_result.evidence_text,
                '분석': implementation_result.reasoning,
                '강점': implementation_result.strengths,
                '약점': implementation_result.weaknesses,
                '제안': implementation_result.recommendations
            },
            '총점': total_score,
            '분석시간': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }


def display_results(results: Dict[str, Any]):
    """결과 시각화"""
    
    st.markdown("---")
    st.markdown("## 📊 심사 결과")
    
    # 총점 표시
    total_score = results['총점']
    score_class = "good-score" if total_score >= 80 else "average-score" if total_score >= 60 else "poor-score"
    
    st.markdown(f"""
    <div class="score-box {score_class}">
        <h2>총점: {total_score} / 100</h2>
        <p>분석 시간: {results['분석시간']}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 항목별 점수
    st.markdown("### 📋 항목별 평가")
    
    col1, col2 = st.columns(2)
    
    with col1:
        policy = results['정책부합성']
        st.markdown("#### 🌍 국내외 정책 부합성")
        st.metric("점수", f"{policy['점수']}/{policy['만점']}", f"{policy['백분율']:.1f}%")
        
        with st.expander("상세 분석 보기"):
            st.markdown("**📌 평가 근거**")
            for evidence in policy['근거']:
                st.markdown(f"- {evidence}")
            
            st.markdown("**✅ 강점**")
            for strength in policy['강점']:
                st.markdown(f"- {strength}")
            
            st.markdown("**⚠️ 약점**")
            for weakness in policy['약점']:
                st.markdown(f"- {weakness}")
            
            st.markdown("**💡 개선 제안**")
            for rec in policy['제안']:
                st.markdown(f"- {rec}")
    
    with col2:
        impl = results['추진여건']
        st.markdown("#### 🏗️ 사업 추진 여건")
        st.metric("점수", f"{impl['점수']}/{impl['만점']}", f"{impl['백분율']:.1f}%")
        
        with st.expander("상세 분석 보기"):
            st.markdown("**📌 평가 근거**")
            for evidence in impl['근거']:
                st.markdown(f"- {evidence}")
            
            st.markdown("**✅ 강점**")
            for strength in impl['강점']:
                st.markdown(f"- {strength}")
            
            st.markdown("**⚠️ 약점**")
            for weakness in impl['약점']:
                st.markdown(f"- {weakness}")
            
            st.markdown("**💡 개선 제안**")
            for rec in impl['제안']:
                st.markdown(f"- {rec}")


def generate_report_text(results: Dict[str, Any]) -> str:
    """텍스트 보고서 생성"""
    lines = []
    lines.append("=" * 80)
    lines.append("KOICA 사업 심사 분석 결과 (비공식)")
    lines.append("=" * 80)
    lines.append("\n⚠️  본 보고서는 KOICA 공식 심사 결과가 아닙니다.")
    lines.append("    개인이 개발한 AI 분석 도구의 참고 자료입니다.\n")
    lines.append(f"분석 일시: {results['분석시간']}")
    lines.append(f"총점: {results['총점']} / 100\n")
    
    lines.append("\n[1] 국내외 정책 부합성 ({}/30)".format(results['정책부합성']['점수']))
    lines.append("-" * 80)
    lines.append("\n평가 근거:")
    for e in results['정책부합성']['근거']:
        lines.append(f"  • {e}")
    lines.append("\n강점:")
    for s in results['정책부합성']['강점']:
        lines.append(f"  ✓ {s}")
    lines.append("\n약점:")
    for w in results['정책부합성']['약점']:
        lines.append(f"  ✗ {w}")
    lines.append("\n개선 제안:")
    for r in results['정책부합성']['제안']:
        lines.append(f"  → {r}")
    
    lines.append("\n\n[2] 사업 추진 여건 ({}/70)".format(results['추진여건']['점수']))
    lines.append("-" * 80)
    lines.append("\n평가 근거:")
    for e in results['추진여건']['근거']:
        lines.append(f"  • {e}")
    lines.append("\n강점:")
    for s in results['추진여건']['강점']:
        lines.append(f"  ✓ {s}")
    lines.append("\n약점:")
    for w in results['추진여건']['약점']:
        lines.append(f"  ✗ {w}")
    lines.append("\n개선 제안:")
    for r in results['추진여건']['제안']:
        lines.append(f"  → {r}")
    
    lines.append("\n\n" + "=" * 80)
    lines.append("면책 조항")
    lines.append("=" * 80)
    lines.append("\n본 분석 결과는 AI 기반 참고 자료이며, KOICA 공식 심사 결과가 아닙니다.")
    lines.append("실제 심사는 KOICA 전문 심사위원회에서 진행됩니다.")
    lines.append("본 도구는 KOICA와 무관한 개인 프로젝트입니다.\n")
    lines.append("=" * 80)
    
    return "\n".join(lines)


# ========== 메인 앱 ==========

def main():
    st.markdown('<h1 class="main-header">📊 KOICA 사업 심사 분석 도구</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">비공식 개인 프로젝트 · KOICA 심사 기준 참고</p>', unsafe_allow_html=True)
    
    # Disclaimer
    st.markdown("""
    <div class="disclaimer">
        <strong>⚠️ 주의사항</strong><br>
        본 도구는 <strong>KOICA 공식 서비스가 아닙니다</strong>. 개인이 KOICA 심사 기준을 참고하여 독자적으로 개발한 분석 도구입니다. 
        분석 결과는 참고용이며, 공식적인 심사 결과와 다를 수 있습니다.
    </div>
    """, unsafe_allow_html=True)
    
    # API 키 로드 (secrets 또는 환경변수)
    api_key = None
    api_status = "❌ API 키 없음"
    
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
        api_status = "✅ API 연결됨"
    except:
        try:
            api_key = os.getenv("GEMINI_API_KEY")
            if api_key:
                api_status = "✅ API 연결됨 (환경변수)"
        except:
            pass
    
    if not api_key:
        st.error("⚠️ Gemini API 키가 설정되지 않았습니다.")
        st.info("""
        **API 키 설정 방법:**
        
        1. 프로젝트 폴더에서 `.streamlit/secrets.toml` 파일 생성
        2. 다음 내용 추가:
        ```
        GEMINI_API_KEY = "your-api-key-here"
        ```
        3. 앱 재시작
        
        또는 환경변수로 설정:
        ```bash
        export GEMINI_API_KEY="your-api-key-here"
        ```
        """)
        st.stop()
    
    # 사이드바
    with st.sidebar:
        st.markdown("## 📊 도구 정보")
        st.warning("**비공식 개인 프로젝트**")
        st.markdown("---")
        
        st.markdown("### ℹ️ 주요 기능")
        st.info("""
        - PDF 문서 자동 분석
        - AI 기반 심사 평가
        - 상세 개선 제안
        
        **참고 평가 기준**
        - 정책부합성: 30점
        - 추진여건: 70점
        
        *KOICA 공식 심사 기준 참고*
        """)
        
        # API 상태 표시
        st.markdown("### 🔑 API 상태")
        st.success(api_status)
        
        st.markdown("---")
        st.caption("본 도구는 개인이 개발한 비공식 분석 도구입니다.")
    
    # 메인 영역
    tab1, tab2, tab3 = st.tabs(["📄 PDF 분석", "📝 텍스트 분석", "ℹ️ 사용 가이드"])
    
    with tab1:
        st.markdown("### PDF 보고서 업로드")
        uploaded_file = st.file_uploader("KOICA 예비조사 보고서 (PDF)", type=['pdf'])
        
        if uploaded_file:
            st.success(f"✅ 파일 업로드 완료: {uploaded_file.name} ({uploaded_file.size/1024:.1f} KB)")
            
            if st.button("🚀 분석 시작", type="primary", key="analyze_pdf"):
                try:
                    auditor = KOICAAuditorStreamlit(api_key=api_key)
                    
                    with st.spinner("📄 PDF 처리 중..."):
                        results = auditor.conduct_audit(pdf_file=uploaded_file)
                    
                    # 결과를 session_state에 저장
                    st.session_state['pdf_results'] = results
                    
                except Exception as e:
                    st.error(f"❌ 오류 발생: {e}")
                    st.exception(e)
        
        # session_state에 결과가 있으면 항상 표시
        if 'pdf_results' in st.session_state:
            results = st.session_state['pdf_results']
            display_results(results)
            
            # 보고서 다운로드 버튼
            report_text = generate_report_text(results)
            st.download_button(
                label="📥 심사 결과 다운로드",
                data=report_text,
                file_name=f"KOICA_심사결과_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain",
                key="download_pdf"
            )
    
    with tab2:
        st.markdown("### 텍스트 직접 입력")
        text_input = st.text_area("보고서 내용을 입력하세요", height=300,
                                  placeholder="사업 개요, 정책 부합성, 추진 여건 등을 입력...")
        
        if st.button("🚀 분석 시작", key="text_analyze", type="primary"):
            if text_input.strip():
                try:
                    auditor = KOICAAuditorStreamlit(api_key=api_key)
                    
                    with st.spinner("🤖 AI 분석 중..."):
                        results = auditor.conduct_audit(text_content=text_input)
                    
                    # 결과를 session_state에 저장
                    st.session_state['text_results'] = results
                    
                except Exception as e:
                    st.error(f"❌ 오류 발생: {e}")
            else:
                st.warning("⚠️ 분석할 텍스트를 입력하세요")
        
        # session_state에 결과가 있으면 항상 표시
        if 'text_results' in st.session_state:
            results = st.session_state['text_results']
            display_results(results)
            
            # 보고서 다운로드 버튼
            report_text = generate_report_text(results)
            st.download_button(
                label="📥 심사 결과 다운로드",
                data=report_text,
                file_name=f"KOICA_심사결과_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain",
                key="download_text"
            )
    
    with tab3:
        st.markdown("""
        ### 📖 사용 가이드
        
        #### ⚠️ 중요 공지
        
        **본 도구는 KOICA 공식 서비스가 아닙니다.**
        - 개인이 KOICA 심사 기준을 참고하여 독자적으로 개발
        - 분석 결과는 참고용이며 공식 심사 결과와 다를 수 있음
        - KOICA와 법적/업무적 관계 없음
        
        #### 1️⃣ PDF 분석 방법
        1. 'PDF 분석' 탭에서 파일 업로드
        2. '분석 시작' 버튼 클릭
        3. 30-60초 대기 (AI 분석 중)
        4. 결과 확인 및 다운로드
        
        #### 2️⃣ 참고 평가 기준
        
        본 도구는 KOICA 공식 심사 기준을 참고합니다:
        
        **국내외 정책 부합성 (30점)**
        - SDGs 연관성
        - 수원국 정책 부합성
        - 한국 CPS 연계성
        - 코이카 전략 부합성
        - 타 공여기관 중복 분석
        
        **사업 추진 여건 (70점)**
        - 문제/수요 분석
        - 법제도적 여건
        - 대상지 분석
        - 이해관계자 분석
        - 경제성 분석
        - 지속가능성
        - 리스크 관리
        
        #### 3️⃣ API 키 설정
        
        **Gemini API 키 발급 방법:**
        1. [Google AI Studio](https://aistudio.google.com/app/apikey) 접속
        2. "Create API Key" 클릭
        3. `.streamlit/secrets.toml` 파일에 저장
        
        #### 4️⃣ 면책 조항
        
        - 본 도구의 분석은 AI 기반 참고 자료일 뿐입니다
        - 실제 KOICA 심사는 전문 심사위원회가 진행합니다
        - 본 도구 사용으로 인한 결과에 대해 개발자는 책임지지 않습니다
        - KOICA 공식 가이드라인을 반드시 참조하시기 바랍니다
        """)
    
    
    # 푸터
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; font-size: 0.9rem;">
        <p>📊 KOICA 심사 분석 도구 v1.0</p>
        <p><strong>비공식 개인 프로젝트</strong> · KOICA와 무관한 독립적 분석 도구</p>
        <p>본 도구의 분석 결과는 참고용이며, KOICA 공식 심사 결과와 다를 수 있습니다.</p>
        <p style="font-size: 0.8rem; margin-top: 1rem;">KOICA 심사 기준을 참고하여 개발됨</p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
