#!/usr/bin/env python3
"""
Analytics 시스템 테스트 - 샘플 데이터 생성
"""

import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from utils.analytics import get_analytics
import random
from datetime import datetime, timedelta

analytics = get_analytics()

print("📊 Analytics 테스트 데이터 생성 중...")

# 세션 5개 생성
sessions = []
for i in range(5):
    session_id = analytics.get_or_create_session()
    sessions.append(session_id)
    print(f"✓ 세션 {i+1} 생성: {session_id[:8]}...")

# 각 세션에서 여러 활동 로깅
activities = [
    ("pdf_analysis", "PDF 파일 분석 성공", True),
    ("text_analysis", "텍스트 분석 성공", True),
    ("pdf_analysis", "PDF 업로드 실패", False),
    ("text_analysis", "텍스트 입력 분석", True),
]

print("\n📝 활동 로그 생성 중...")
for session in sessions:
    for action_type, detail, success in random.sample(activities, k=random.randint(1, 3)):
        file_size = random.randint(100000, 5000000) if "pdf" in action_type else None
        analytics.log_activity(
            session_id=session,
            action_type=action_type,
            action_detail=detail,
            file_size_bytes=file_size,
            success=success,
            error_type=None if success else "ValidationError"
        )
        print(f"  ✓ {action_type}: {detail}")

# 일일 통계 업데이트
print("\n📈 일일 통계 업데이트 중...")
analytics.update_daily_stats()

# 결과 확인
print("\n" + "="*50)
print("📊 생성된 데이터 요약:")
print("="*50)

stats = analytics.get_summary_stats()
print(f"총 세션 수: {stats.get('total_sessions', 0)}")
print(f"총 활동 수: {stats.get('total_actions', 0)}")
print(f"PDF 분석: {stats.get('pdf_analyses', 0)}")
print(f"텍스트 분석: {stats.get('text_analyses', 0)}")
print(f"성공: {stats.get('successful_analyses', 0)}")
print(f"실패: {stats.get('failed_analyses', 0)}")
print(f"성공률: {stats.get('success_rate', 0)}%")

print("\n✅ 테스트 데이터 생성 완료!")
print("이제 대시보드를 새로고침하면 데이터가 보입니다.")
