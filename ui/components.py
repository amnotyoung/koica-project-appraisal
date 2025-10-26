"""
KOICA 사업 예비조사 심사 시스템 - UI 컴포넌트
결과 표시 및 리포트 생성 함수
"""

import logging
from typing import Dict, Any
from datetime import datetime
import streamlit as st

from config import UIConfig, AuditConfig

logger = logging.getLogger(__name__)


def display_results(results: Dict[str, Any]) -> None:
    """분석 결과 표시

    Args:
        results: 심사 결과 딕셔너리
    """
    # RAG 사용 여부 표시
    if not results.get('RAG_사용', False):
        st.warning("⚠️ 이 분석은 RAG 없이 수행되었습니다. 전체 문서가 아닌 앞부분만 분석되었을 수 있습니다.")
    else:
        st.success("✅ RAG 기반 전체 문서 분석 완료")

    # 총점 표시
    total_score = results['총점']
    score_class = _get_score_class(total_score)

    st.markdown(
        f"""
        <div class="score-box {score_class}">
            <h2>총점: {total_score} / 100</h2>
            <p>분석 시간: {results['분석시간']}</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown("### 📋 항목별 평가")
    col1, col2 = st.columns(2)

    with col1:
        _display_policy_alignment(results['정책부합성'])

    with col2:
        _display_implementation_readiness(results['추진여건'])


def _get_score_class(score: int) -> str:
    """점수에 따른 CSS 클래스 반환

    Args:
        score: 점수

    Returns:
        CSS 클래스명
    """
    if score >= AuditConfig.SCORE_EXCELLENT_THRESHOLD:
        return UIConfig.CSS_GOOD_SCORE
    elif score >= AuditConfig.SCORE_GOOD_THRESHOLD:
        return UIConfig.CSS_AVERAGE_SCORE
    else:
        return UIConfig.CSS_POOR_SCORE


def _display_policy_alignment(policy: Dict[str, Any]) -> None:
    """정책 부합성 결과 표시

    Args:
        policy: 정책 부합성 데이터
    """
    st.markdown("#### 🌍 국내외 정책 부합성")
    st.metric(
        "점수",
        f"{policy['점수']}/{policy['만점']}",
        f"{policy['백분율']:.1f}%"
    )

    with st.expander("상세 분석 보기", expanded=True):
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


def _display_implementation_readiness(impl: Dict[str, Any]) -> None:
    """추진 여건 결과 표시

    Args:
        impl: 추진 여건 데이터
    """
    st.markdown("#### 🏗️ 사업 추진 여건")
    st.metric(
        "점수",
        f"{impl['점수']}/{impl['만점']}",
        f"{impl['백분율']:.1f}%"
    )

    with st.expander("상세 분석 보기", expanded=True):
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
    """텍스트 보고서 생성

    Args:
        results: 심사 결과 딕셔너리

    Returns:
        텍스트 형식의 보고서
    """
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


def get_custom_css() -> str:
    """커스텀 CSS 반환

    Returns:
        CSS 스타일 문자열
    """
    return """
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
        .disclaimer {
            background-color: #fff3cd;
            border-left: 5px solid #ffc107;
            padding: 15px;
            margin: 20px 0;
            border-radius: 5px;
        }
    </style>
    """
