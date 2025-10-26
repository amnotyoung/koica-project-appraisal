#!/usr/bin/env python3
"""
KOICA 관리자 대시보드 - 사용자 데이터 모니터링
개인정보 보호법 준수 - 익명 데이터만 표시
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

# 로깅 설정
from utils.logger import setup_logger
logger = setup_logger(name="admin_dashboard", log_to_file=True)

# 익명 분석 시스템
from utils.analytics import get_analytics
analytics = get_analytics()

# 페이지 설정
st.set_page_config(
    page_title="관리자 대시보드 - KOICA",
    page_icon="📊",
    layout="wide"
)


def render_summary_stats():
    """요약 통계 렌더링"""
    st.markdown("## 📈 전체 요약 통계")

    # 통계 가져오기
    stats = analytics.get_summary_stats()

    if not stats:
        st.warning("⚠️ 통계 데이터가 없습니다.")
        return

    # 메트릭 카드
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="총 세션 수",
            value=stats.get("total_sessions", 0),
            delta=f"오늘: {stats.get('today_sessions', 0)}"
        )

    with col2:
        st.metric(
            label="총 분석 수",
            value=stats.get("pdf_analyses", 0) + stats.get("text_analyses", 0),
            delta=f"오늘: {stats.get('today_actions', 0)}"
        )

    with col3:
        st.metric(
            label="성공률",
            value=f"{stats.get('success_rate', 0)}%",
            delta=f"성공: {stats.get('successful_analyses', 0)}"
        )

    with col4:
        st.metric(
            label="평균 파일 크기",
            value=f"{stats.get('avg_file_size_mb', 0)} MB"
        )

    # 상세 통계
    st.markdown("---")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 📄 분석 유형별")
        st.write(f"- PDF 분석: **{stats.get('pdf_analyses', 0)}**건")
        st.write(f"- 텍스트 분석: **{stats.get('text_analyses', 0)}**건")

    with col2:
        st.markdown("### ✅ 성공/실패")
        st.write(f"- 성공: **{stats.get('successful_analyses', 0)}**건")
        st.write(f"- 실패: **{stats.get('failed_analyses', 0)}**건")


def render_daily_chart():
    """일일 통계 차트 렌더링"""
    st.markdown("---")
    st.markdown("## 📊 일별 사용 추이")

    # 일일 통계 가져오기
    days = st.slider("조회 기간 (일)", min_value=7, max_value=90, value=30)
    daily_stats = analytics.get_daily_stats(days=days)

    if not daily_stats:
        st.info("📭 데이터가 없습니다.")
        return

    # DataFrame 생성
    df = pd.DataFrame(daily_stats)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')

    # 탭으로 차트 구분
    tab1, tab2, tab3 = st.tabs(["📈 세션 & 분석 수", "✅ 성공/실패", "💾 파일 크기"])

    with tab1:
        # 세션 및 분석 수 차트
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df['date'],
            y=df['total_sessions'],
            mode='lines+markers',
            name='세션 수',
            line=dict(color='royalblue', width=2)
        ))
        fig.add_trace(go.Scatter(
            x=df['date'],
            y=df['pdf_analyses'],
            mode='lines+markers',
            name='PDF 분석',
            line=dict(color='green', width=2)
        ))
        fig.add_trace(go.Scatter(
            x=df['date'],
            y=df['text_analyses'],
            mode='lines+markers',
            name='텍스트 분석',
            line=dict(color='orange', width=2)
        ))
        fig.update_layout(
            title="일별 세션 및 분석 수",
            xaxis_title="날짜",
            yaxis_title="개수",
            hovermode='x unified',
            height=400
        )
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        # 성공/실패 차트
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=df['date'],
            y=df['successful'],
            name='성공',
            marker_color='lightgreen'
        ))
        fig.add_trace(go.Bar(
            x=df['date'],
            y=df['failed'],
            name='실패',
            marker_color='lightcoral'
        ))
        fig.update_layout(
            title="일별 성공/실패 분석",
            xaxis_title="날짜",
            yaxis_title="개수",
            barmode='stack',
            hovermode='x unified',
            height=400
        )
        st.plotly_chart(fig, use_container_width=True)

    with tab3:
        # 파일 크기 차트
        fig = px.line(
            df,
            x='date',
            y='total_file_size_mb',
            title='일별 총 파일 크기 (MB)',
            markers=True
        )
        fig.update_layout(
            xaxis_title="날짜",
            yaxis_title="파일 크기 (MB)",
            height=400
        )
        st.plotly_chart(fig, use_container_width=True)

    # 데이터 테이블
    st.markdown("### 📋 상세 데이터")
    st.dataframe(
        df.rename(columns={
            'date': '날짜',
            'total_sessions': '세션 수',
            'pdf_analyses': 'PDF 분석',
            'text_analyses': '텍스트 분석',
            'successful': '성공',
            'failed': '실패',
            'total_file_size_mb': '파일 크기 (MB)'
        }),
        use_container_width=True,
        hide_index=True
    )


def render_recent_activities():
    """최근 활동 로그 렌더링"""
    st.markdown("---")
    st.markdown("## 📝 최근 활동 로그 (익명)")

    limit = st.number_input("표시할 활동 수", min_value=10, max_value=500, value=50)
    activities = analytics.get_recent_activities(limit=limit)

    if not activities:
        st.info("📭 활동 데이터가 없습니다.")
        return

    # DataFrame 생성
    df = pd.DataFrame(activities)
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    # 성공/실패 아이콘 추가
    df['상태'] = df['success'].apply(lambda x: "✅" if x else "❌")

    # 표시할 컬럼 선택
    display_df = df[[
        'timestamp', '상태', 'action_type', 'action_detail',
        'file_size_mb', 'error_type'
    ]].rename(columns={
        'timestamp': '시간',
        'action_type': '활동 유형',
        'action_detail': '상세 정보',
        'file_size_mb': '파일 크기 (MB)',
        'error_type': '에러 타입'
    })

    # 데이터 테이블
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True
    )

    # CSV 다운로드
    csv = df.to_csv(index=False, encoding='utf-8-sig')
    st.download_button(
        label="📥 CSV 다운로드",
        data=csv,
        file_name=f"activity_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv"
    )


def render_privacy_notice():
    """개인정보 보호 안내"""
    st.markdown(
        """
        <div style="background-color: #e8f4f8; padding: 15px; border-radius: 5px; margin-bottom: 20px;">
            <h4 style="color: #0066cc;">🔒 개인정보 보호 정책</h4>
            <p style="font-size: 14px;">
            본 대시보드는 <strong>개인정보 보호법을 준수</strong>하며, 다음 정보만 수집합니다:<br>
            ✅ 익명 세션 ID (무작위 UUID)<br>
            ✅ 타임스탬프 (방문 시간)<br>
            ✅ 사용 기능 (분석 유형)<br>
            ✅ 파일 크기 (내용 제외)<br>
            ✅ 성공/실패 여부<br>
            <br>
            ❌ <strong>수집하지 않는 정보:</strong> IP 주소, 이름, 이메일, 파일 내용, 분석 결과
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )


def main():
    """메인 대시보드"""
    st.title("📊 KOICA 관리자 대시보드")
    st.markdown("### 사용자 데이터 모니터링 (익명)")

    # 개인정보 보호 안내
    render_privacy_notice()

    # 새로고침 버튼
    col1, col2 = st.columns([6, 1])
    with col2:
        if st.button("🔄 새로고침"):
            analytics.update_daily_stats()
            st.rerun()

    # 요약 통계
    render_summary_stats()

    # 일일 차트
    render_daily_chart()

    # 최근 활동
    render_recent_activities()

    # 푸터
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: #666;'>"
        "KOICA 관리자 대시보드 | 개인정보 보호법 준수"
        "</div>",
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()
