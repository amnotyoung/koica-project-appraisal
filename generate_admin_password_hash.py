#!/usr/bin/env python3
"""
관리자 비밀번호 해시 생성 도구
사용법: python generate_admin_password_hash.py
"""

import hashlib
import getpass


def generate_password_hash(password: str) -> str:
    """비밀번호 해시 생성 (SHA-256)

    Args:
        password: 원본 비밀번호

    Returns:
        SHA-256 해시 문자열
    """
    return hashlib.sha256(password.encode()).hexdigest()


def main():
    """메인 함수"""
    print("=" * 60)
    print("🔐 KOICA 관리자 대시보드 비밀번호 해시 생성 도구")
    print("=" * 60)
    print()

    # 비밀번호 입력 (화면에 표시되지 않음)
    password = getpass.getpass("관리자 비밀번호를 입력하세요: ")

    if not password:
        print("❌ 비밀번호를 입력해야 합니다.")
        return

    # 확인을 위해 다시 입력
    password_confirm = getpass.getpass("비밀번호를 다시 입력하세요: ")

    if password != password_confirm:
        print("❌ 비밀번호가 일치하지 않습니다.")
        return

    # 해시 생성
    password_hash = generate_password_hash(password)

    # 결과 출력
    print()
    print("=" * 60)
    print("✅ 비밀번호 해시 생성 완료!")
    print("=" * 60)
    print()
    print("다음 내용을 .streamlit/secrets.toml 파일에 추가하세요:")
    print()
    print("-" * 60)
    print(f'ADMIN_PASSWORD_HASH = "{password_hash}"')
    print("-" * 60)
    print()
    print("⚠️ 주의사항:")
    print("1. 이 해시 값을 안전하게 보관하세요")
    print("2. secrets.toml 파일을 Git에 커밋하지 마세요")
    print("3. 비밀번호는 다른 사람과 공유하지 마세요")
    print()


if __name__ == "__main__":
    main()
