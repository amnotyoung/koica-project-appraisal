"""
KOICA 사업 예비조사 심사 시스템 - 익명 사용자 분석
개인정보 보호법 준수 - 개인정보를 수집하지 않습니다

환경 자동 감지:
- 로컬 개발: SQLite (analytics/usage_data.db)
- Streamlit Cloud: PostgreSQL (DATABASE_URL 환경변수 사용)
"""

import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
import logging

from config import LogConfig
from utils.logger import setup_logger

logger = setup_logger(name="koica_analytics", log_to_file=True)


class AnonymousAnalytics:
    """
    익명 사용자 활동 추적 시스템
    개인정보 보호법 준수 - IP, 이름, 이메일, 파일 내용 등 개인정보 수집 안 함

    환경에 따라 자동으로 SQLite 또는 PostgreSQL 사용
    """

    def __init__(self, db_path: str = "analytics/usage_data.db"):
        """
        Args:
            db_path: SQLite 데이터베이스 파일 경로 (로컬 개발용)
        """
        # 환경 감지: DATABASE_URL이 있으면 PostgreSQL, 없으면 SQLite
        self.database_url = os.getenv("DATABASE_URL")
        self.use_postgres = self.database_url is not None

        if self.use_postgres:
            # PostgreSQL 사용 (Streamlit Cloud 배포)
            import psycopg2
            from urllib.parse import urlparse

            self.db_type = "postgresql"
            logger.info("PostgreSQL 모드로 실행 중 (배포 환경)")

            # DATABASE_URL 파싱
            result = urlparse(self.database_url)
            self.db_config = {
                'host': result.hostname,
                'port': result.port,
                'database': result.path[1:],
                'user': result.username,
                'password': result.password
            }
        else:
            # SQLite 사용 (로컬 개발)
            import sqlite3

            self.db_type = "sqlite"
            self.db_path = Path(db_path)
            self.db_path.parent.mkdir(exist_ok=True)
            logger.info(f"SQLite 모드로 실행 중 (로컬 개발): {self.db_path}")

        self._init_database()

    def _get_connection(self):
        """데이터베이스 연결 가져오기"""
        if self.use_postgres:
            import psycopg2
            return psycopg2.connect(**self.db_config)
        else:
            import sqlite3
            return sqlite3.connect(self.db_path)

    def _init_database(self):
        """데이터베이스 및 테이블 초기화"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            if self.use_postgres:
                # PostgreSQL용 테이블 생성
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS sessions (
                        session_id VARCHAR(36) PRIMARY KEY,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS activity_logs (
                        id SERIAL PRIMARY KEY,
                        session_id VARCHAR(36) NOT NULL,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        action_type VARCHAR(50) NOT NULL,
                        action_detail TEXT,
                        file_size_bytes BIGINT,
                        success BOOLEAN,
                        error_type VARCHAR(100),
                        FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                    )
                """)

                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS daily_stats (
                        date DATE PRIMARY KEY,
                        total_sessions INTEGER DEFAULT 0,
                        total_pdf_analyses INTEGER DEFAULT 0,
                        total_text_analyses INTEGER DEFAULT 0,
                        successful_analyses INTEGER DEFAULT 0,
                        failed_analyses INTEGER DEFAULT 0,
                        total_file_size_mb REAL DEFAULT 0,
                        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
            else:
                # SQLite용 테이블 생성
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS sessions (
                        session_id TEXT PRIMARY KEY,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS activity_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NOT NULL,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        action_type TEXT NOT NULL,
                        action_detail TEXT,
                        file_size_bytes INTEGER,
                        success BOOLEAN,
                        error_type TEXT,
                        FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                    )
                """)

                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS daily_stats (
                        date DATE PRIMARY KEY,
                        total_sessions INTEGER DEFAULT 0,
                        total_pdf_analyses INTEGER DEFAULT 0,
                        total_text_analyses INTEGER DEFAULT 0,
                        successful_analyses INTEGER DEFAULT 0,
                        failed_analyses INTEGER DEFAULT 0,
                        total_file_size_mb REAL DEFAULT 0,
                        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

            conn.commit()
            conn.close()
            logger.info(f"데이터베이스 초기화 완료 ({self.db_type})")

        except Exception as e:
            logger.error(f"데이터베이스 초기화 실패: {e}", exc_info=True)

    def get_or_create_session(self, session_id: Optional[str] = None) -> str:
        """
        세션 ID 가져오기 또는 생성

        Args:
            session_id: 기존 세션 ID (없으면 새로 생성)

        Returns:
            세션 ID (익명 UUID)
        """
        if not session_id:
            session_id = str(uuid.uuid4())

        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            if self.use_postgres:
                # PostgreSQL용 쿼리
                cursor.execute("""
                    INSERT INTO sessions (session_id)
                    VALUES (%s)
                    ON CONFLICT (session_id) DO NOTHING
                """, (session_id,))

                cursor.execute("""
                    UPDATE sessions
                    SET last_active = CURRENT_TIMESTAMP
                    WHERE session_id = %s
                """, (session_id,))
            else:
                # SQLite용 쿼리
                cursor.execute("""
                    INSERT OR IGNORE INTO sessions (session_id)
                    VALUES (?)
                """, (session_id,))

                cursor.execute("""
                    UPDATE sessions
                    SET last_active = CURRENT_TIMESTAMP
                    WHERE session_id = ?
                """, (session_id,))

            conn.commit()
            conn.close()

        except Exception as e:
            logger.error(f"세션 생성/업데이트 실패: {e}", exc_info=True)

        return session_id

    def log_activity(
        self,
        session_id: str,
        action_type: str,
        action_detail: Optional[str] = None,
        file_size_bytes: Optional[int] = None,
        success: bool = True,
        error_type: Optional[str] = None
    ):
        """
        사용자 활동 로깅 (익명)

        Args:
            session_id: 익명 세션 ID
            action_type: 활동 유형 (page_view, pdf_analysis, text_analysis 등)
            action_detail: 활동 상세 정보 (개인정보 제외)
            file_size_bytes: 파일 크기 (바이트, 실제 내용은 저장 안 함)
            success: 성공 여부
            error_type: 에러 타입 (상세 내용 제외)
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            if self.use_postgres:
                cursor.execute("""
                    INSERT INTO activity_logs
                    (session_id, action_type, action_detail, file_size_bytes, success, error_type)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (session_id, action_type, action_detail, file_size_bytes, success, error_type))
            else:
                cursor.execute("""
                    INSERT INTO activity_logs
                    (session_id, action_type, action_detail, file_size_bytes, success, error_type)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (session_id, action_type, action_detail, file_size_bytes, success, error_type))

            conn.commit()
            conn.close()

            logger.debug(f"활동 로그 기록: {action_type} (세션: {session_id[:8]}...)")

        except Exception as e:
            logger.error(f"활동 로그 기록 실패: {e}", exc_info=True)

    def update_daily_stats(self):
        """일일 통계 업데이트"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            today = datetime.now().date()

            if self.use_postgres:
                # PostgreSQL용 쿼리
                cursor.execute("""
                    SELECT
                        COUNT(DISTINCT session_id) as total_sessions,
                        SUM(CASE WHEN action_type = 'pdf_analysis' THEN 1 ELSE 0 END) as pdf_analyses,
                        SUM(CASE WHEN action_type = 'text_analysis' THEN 1 ELSE 0 END) as text_analyses,
                        SUM(CASE WHEN success = true THEN 1 ELSE 0 END) as successful,
                        SUM(CASE WHEN success = false THEN 1 ELSE 0 END) as failed,
                        COALESCE(SUM(file_size_bytes), 0) / 1024.0 / 1024.0 as total_mb
                    FROM activity_logs
                    WHERE DATE(timestamp) = %s
                """, (today,))

                stats = cursor.fetchone()

                cursor.execute("""
                    INSERT INTO daily_stats
                    (date, total_sessions, total_pdf_analyses, total_text_analyses,
                     successful_analyses, failed_analyses, total_file_size_mb, last_updated)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT (date) DO UPDATE SET
                        total_sessions = EXCLUDED.total_sessions,
                        total_pdf_analyses = EXCLUDED.total_pdf_analyses,
                        total_text_analyses = EXCLUDED.total_text_analyses,
                        successful_analyses = EXCLUDED.successful_analyses,
                        failed_analyses = EXCLUDED.failed_analyses,
                        total_file_size_mb = EXCLUDED.total_file_size_mb,
                        last_updated = CURRENT_TIMESTAMP
                """, (today, stats[0], stats[1], stats[2], stats[3], stats[4], stats[5]))
            else:
                # SQLite용 쿼리
                cursor.execute("""
                    SELECT
                        COUNT(DISTINCT session_id) as total_sessions,
                        SUM(CASE WHEN action_type = 'pdf_analysis' THEN 1 ELSE 0 END) as pdf_analyses,
                        SUM(CASE WHEN action_type = 'text_analysis' THEN 1 ELSE 0 END) as text_analyses,
                        SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful,
                        SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failed,
                        COALESCE(SUM(file_size_bytes), 0) / 1024.0 / 1024.0 as total_mb
                    FROM activity_logs
                    WHERE DATE(timestamp) = ?
                """, (today,))

                stats = cursor.fetchone()

                cursor.execute("""
                    INSERT OR REPLACE INTO daily_stats
                    (date, total_sessions, total_pdf_analyses, total_text_analyses,
                     successful_analyses, failed_analyses, total_file_size_mb, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (today, stats[0], stats[1], stats[2], stats[3], stats[4], stats[5]))

            conn.commit()
            conn.close()
            logger.debug(f"일일 통계 업데이트 완료: {today}")

        except Exception as e:
            logger.error(f"일일 통계 업데이트 실패: {e}", exc_info=True)

    def get_daily_stats(self, days: int = 30) -> List[Dict[str, Any]]:
        """
        일일 통계 조회

        Args:
            days: 조회할 일수

        Returns:
            일일 통계 리스트
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            if self.use_postgres:
                cursor.execute("""
                    SELECT
                        date,
                        total_sessions,
                        total_pdf_analyses,
                        total_text_analyses,
                        successful_analyses,
                        failed_analyses,
                        total_file_size_mb
                    FROM daily_stats
                    ORDER BY date DESC
                    LIMIT %s
                """, (days,))
            else:
                cursor.execute("""
                    SELECT
                        date,
                        total_sessions,
                        total_pdf_analyses,
                        total_text_analyses,
                        successful_analyses,
                        failed_analyses,
                        total_file_size_mb
                    FROM daily_stats
                    ORDER BY date DESC
                    LIMIT ?
                """, (days,))

            rows = cursor.fetchall()
            conn.close()

            return [
                {
                    "date": row[0],
                    "total_sessions": row[1],
                    "pdf_analyses": row[2],
                    "text_analyses": row[3],
                    "successful": row[4],
                    "failed": row[5],
                    "total_file_size_mb": round(row[6], 2) if row[6] else 0
                }
                for row in rows
            ]

        except Exception as e:
            logger.error(f"통계 조회 실패: {e}", exc_info=True)
            return []

    def get_summary_stats(self) -> Dict[str, Any]:
        """
        전체 요약 통계 조회

        Returns:
            요약 통계 딕셔너리
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            if self.use_postgres:
                # PostgreSQL용 쿼리
                cursor.execute("""
                    SELECT
                        COUNT(DISTINCT session_id) as total_sessions,
                        COUNT(*) as total_actions,
                        SUM(CASE WHEN action_type = 'pdf_analysis' THEN 1 ELSE 0 END) as pdf_analyses,
                        SUM(CASE WHEN action_type = 'text_analysis' THEN 1 ELSE 0 END) as text_analyses,
                        SUM(CASE WHEN success = true THEN 1 ELSE 0 END) as successful,
                        SUM(CASE WHEN success = false THEN 1 ELSE 0 END) as failed,
                        COALESCE(AVG(file_size_bytes), 0) / 1024.0 / 1024.0 as avg_file_size_mb
                    FROM activity_logs
                """)

                stats = cursor.fetchone()

                cursor.execute("""
                    SELECT
                        COUNT(DISTINCT session_id) as today_sessions,
                        COUNT(*) as today_actions
                    FROM activity_logs
                    WHERE DATE(timestamp) = CURRENT_DATE
                """)
            else:
                # SQLite용 쿼리
                cursor.execute("""
                    SELECT
                        COUNT(DISTINCT session_id) as total_sessions,
                        COUNT(*) as total_actions,
                        SUM(CASE WHEN action_type = 'pdf_analysis' THEN 1 ELSE 0 END) as pdf_analyses,
                        SUM(CASE WHEN action_type = 'text_analysis' THEN 1 ELSE 0 END) as text_analyses,
                        SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful,
                        SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failed,
                        COALESCE(AVG(file_size_bytes), 0) / 1024.0 / 1024.0 as avg_file_size_mb
                    FROM activity_logs
                """)

                stats = cursor.fetchone()

                cursor.execute("""
                    SELECT
                        COUNT(DISTINCT session_id) as today_sessions,
                        COUNT(*) as today_actions
                    FROM activity_logs
                    WHERE DATE(timestamp) = DATE('now')
                """)

            today_stats = cursor.fetchone()
            conn.close()

            # None 값을 0으로 변환
            total_sessions = stats[0] or 0
            total_actions = stats[1] or 0
            pdf_analyses = stats[2] or 0
            text_analyses = stats[3] or 0
            successful = stats[4] or 0
            failed = stats[5] or 0
            avg_file_size_mb = stats[6] or 0
            today_sessions = today_stats[0] or 0
            today_actions = today_stats[1] or 0

            # 성공률 계산 (0으로 나누기 방지)
            total_analyses = successful + failed
            success_rate = round((successful / total_analyses * 100) if total_analyses > 0 else 0, 2)

            return {
                "total_sessions": total_sessions,
                "total_actions": total_actions,
                "pdf_analyses": pdf_analyses,
                "text_analyses": text_analyses,
                "successful_analyses": successful,
                "failed_analyses": failed,
                "avg_file_size_mb": round(avg_file_size_mb, 2),
                "today_sessions": today_sessions,
                "today_actions": today_actions,
                "success_rate": success_rate
            }

        except Exception as e:
            logger.error(f"요약 통계 조회 실패: {e}", exc_info=True)
            return {}

    def get_recent_activities(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        최근 활동 조회 (익명)

        Args:
            limit: 조회할 활동 수

        Returns:
            최근 활동 리스트
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            if self.use_postgres:
                cursor.execute("""
                    SELECT
                        timestamp,
                        action_type,
                        action_detail,
                        file_size_bytes,
                        success,
                        error_type
                    FROM activity_logs
                    ORDER BY timestamp DESC
                    LIMIT %s
                """, (limit,))
            else:
                cursor.execute("""
                    SELECT
                        timestamp,
                        action_type,
                        action_detail,
                        file_size_bytes,
                        success,
                        error_type
                    FROM activity_logs
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (limit,))

            rows = cursor.fetchall()
            conn.close()

            return [
                {
                    "timestamp": row[0],
                    "action_type": row[1],
                    "action_detail": row[2],
                    "file_size_mb": round(row[3] / 1024 / 1024, 2) if row[3] else None,
                    "success": bool(row[4]),
                    "error_type": row[5]
                }
                for row in rows
            ]

        except Exception as e:
            logger.error(f"최근 활동 조회 실패: {e}", exc_info=True)
            return []


# 전역 인스턴스
_analytics_instance: Optional[AnonymousAnalytics] = None


def get_analytics() -> AnonymousAnalytics:
    """
    전역 Analytics 인스턴스 가져오기

    Returns:
        AnonymousAnalytics 인스턴스
    """
    global _analytics_instance
    if _analytics_instance is None:
        _analytics_instance = AnonymousAnalytics()
    return _analytics_instance
