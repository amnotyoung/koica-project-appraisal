"""
KOICA 사업 예비조사 심사 시스템 - 로깅 유틸리티
중앙화된 로깅 설정 및 관리
"""

import os
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from config import LogConfig


def setup_logger(
    name: str = "koica_auditor",
    level: str = LogConfig.LOG_LEVEL,
    log_to_file: bool = True
) -> logging.Logger:
    """로거 설정 및 반환

    Args:
        name: 로거 이름
        level: 로그 레벨 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_file: 파일 로깅 활성화 여부

    Returns:
        설정된 Logger 인스턴스
    """
    logger = logging.getLogger(name)

    # 이미 핸들러가 설정되어 있으면 반환
    if logger.handlers:
        return logger

    # 로그 레벨 설정
    log_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(log_level)

    # 포맷터 생성
    formatter = logging.Formatter(
        fmt=LogConfig.LOG_FORMAT,
        datefmt=LogConfig.LOG_DATE_FORMAT
    )

    # 콘솔 핸들러
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 파일 핸들러 (선택적)
    if log_to_file:
        try:
            # 로그 디렉토리 생성
            log_dir = Path(LogConfig.LOG_DIR)
            log_dir.mkdir(exist_ok=True)

            # 로그 파일 경로
            log_file = log_dir / LogConfig.LOG_FILE

            # 회전 파일 핸들러 (최대 크기 초과 시 새 파일 생성)
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=LogConfig.LOG_MAX_BYTES,
                backupCount=LogConfig.LOG_BACKUP_COUNT,
                encoding='utf-8'
            )
            file_handler.setLevel(log_level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

            logger.info(f"로그 파일: {log_file}")

        except Exception as e:
            logger.warning(f"파일 로깅 설정 실패: {e}")

    # 상위 로거로 전파 방지 (중복 로깅 방지)
    logger.propagate = False

    logger.info(f"로거 '{name}' 초기화 완료 (레벨: {level})")
    return logger


def get_logger(name: str = "koica_auditor") -> logging.Logger:
    """로거 인스턴스 가져오기

    Args:
        name: 로거 이름

    Returns:
        Logger 인스턴스
    """
    return logging.getLogger(name)


# 기본 로거 초기화 (모듈 임포트 시 자동 설정)
default_logger = setup_logger()
