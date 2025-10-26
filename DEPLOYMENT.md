# 🚀 KOICA 심사 시스템 배포 가이드

이 가이드는 **메인 웹앱**과 **관리자 대시보드**를 Streamlit Cloud에 배포하는 방법을 설명합니다.

---

## 📋 목차

1. [준비 사항](#준비-사항)
2. [PostgreSQL 데이터베이스 설정 (Neon.tech)](#postgresql-데이터베이스-설정)
3. [Streamlit Cloud 배포](#streamlit-cloud-배포)
4. [환경 변수 설정](#환경-변수-설정)
5. [배포 후 확인](#배포-후-확인)

---

## 1️⃣ 준비 사항

### 필요한 계정

- ✅ **GitHub 계정** (코드 저장소)
- ✅ **Streamlit Cloud 계정** (무료) - https://share.streamlit.io
- ✅ **Neon.tech 계정** (무료 PostgreSQL) - https://neon.tech
- ✅ **Google Gemini API 키** - https://aistudio.google.com/app/apikey

### GitHub 저장소 준비

```bash
# main 브랜치에 최신 코드 merge
git checkout main
git merge claude/fix-dashboard-functionality-011CUVwDy77PmPrYWiTF4uD5
git push origin main
```

---

## 2️⃣ PostgreSQL 데이터베이스 설정

### Neon.tech에서 무료 PostgreSQL 만들기

1. **Neon.tech 가입**
   - https://neon.tech 접속
   - GitHub 계정으로 로그인

2. **새 프로젝트 생성**
   - "Create Project" 클릭
   - Project name: `koica-analytics`
   - Region: **Asia Pacific (Singapore)** 선택 (한국과 가장 가까움)
   - PostgreSQL version: 최신 버전 선택

3. **연결 문자열 복사**
   - 프로젝트 생성 후 **Connection String** 복사
   - 형식: `postgresql://user:password@host/database`
   - 예시:
     ```
     postgresql://koica_owner:AbC123...@ep-cool-cloud-123.ap-southeast-1.aws.neon.tech/koica_analytics
     ```

4. **연결 테스트 (선택사항)**
   ```bash
   # 로컬에서 테스트 (psycopg2-binary 설치 필요)
   pip install psycopg2-binary

   python3 -c "
   import psycopg2
   conn = psycopg2.connect('YOUR_CONNECTION_STRING')
   print('✅ PostgreSQL 연결 성공!')
   conn.close()
   "
   ```

---

## 3️⃣ Streamlit Cloud 배포

### A. 메인 웹앱 배포

1. **Streamlit Cloud 접속**
   - https://share.streamlit.io 로그인
   - GitHub 계정으로 연결

2. **New app 생성**
   - "New app" 버튼 클릭
   - Repository: `amnotyoung/koica-project-appraisal`
   - Branch: `main`
   - Main file path: `koica_appraisal_app.py`
   - App URL: `koica-appraisal` (원하는 이름)

3. **Advanced settings** 클릭

4. **Secrets 설정** (아래 참조)

5. **Deploy** 클릭!

### B. 관리자 대시보드 배포

1. **New app 생성** (다시)
   - "New app" 버튼 클릭
   - Repository: `amnotyoung/koica-project-appraisal`
   - Branch: `main`
   - Main file path: `admin/dashboard.py`
   - App URL: `koica-admin-dashboard` (원하는 이름)

2. **Advanced settings** 클릭

3. **Secrets 설정** (아래 참조)

4. **Deploy** 클릭!

---

## 4️⃣ 환경 변수 설정

### 메인 웹앱 Secrets

Streamlit Cloud의 **Advanced settings → Secrets**에 다음을 입력:

```toml
# Gemini API 키
GEMINI_API_KEY = "AIzaSy..."

# PostgreSQL 연결 문자열 (Neon.tech에서 복사)
DATABASE_URL = "postgresql://user:password@host/database"

# 관리자 비밀번호 해시 (선택사항, 대시보드에서만 필요)
ADMIN_PASSWORD_HASH = "240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9"
```

### 관리자 대시보드 Secrets

Streamlit Cloud의 **Advanced settings → Secrets**에 다음을 입력:

```toml
# Gemini API 키 (대시보드에서는 필수 아님, 하지만 있어도 무방)
GEMINI_API_KEY = "AIzaSy..."

# PostgreSQL 연결 문자열 (메인 앱과 동일)
DATABASE_URL = "postgresql://user:password@host/database"

# 관리자 비밀번호 해시 (필수!)
ADMIN_PASSWORD_HASH = "240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9"
```

### 관리자 비밀번호 해시 생성

기본 비밀번호 `admin123`의 해시:
```
240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9
```

**새 비밀번호로 변경하려면:**

```bash
# 터미널에서 실행
python3 -c "
import hashlib
password = '원하는비밀번호'
print(hashlib.sha256(password.encode()).hexdigest())
"
```

또는:

```bash
# 프로젝트 디렉토리에서
python3 generate_admin_password_hash.py
```

---

## 5️⃣ 배포 후 확인

### 메인 웹앱 테스트

1. 배포된 URL 접속 (예: `https://koica-appraisal.streamlit.app`)
2. PDF 업로드 또는 텍스트 입력
3. 분석 실행
4. 결과 확인

### 관리자 대시보드 테스트

1. 배포된 URL 접속 (예: `https://koica-admin-dashboard.streamlit.app`)
2. 비밀번호 입력 (기본: `admin123`)
3. 로그인 후 통계 확인
4. 메인 앱에서 분석한 데이터가 대시보드에 표시되는지 확인

### 로그 확인

Streamlit Cloud에서 앱 로그 확인:

**성공적인 배포 로그:**
```
✓ PostgreSQL 모드로 실행 중 (배포 환경)
✓ 데이터베이스 초기화 완료 (postgresql)
✓ 애플리케이션 시작
```

**문제가 있는 경우:**
```
✗ 데이터베이스 초기화 실패: ...
```

---

## 🔧 문제 해결

### 1. "ModuleNotFoundError: No module named 'psycopg2'"

**원인**: requirements.txt에 psycopg2-binary가 없음

**해결**:
```bash
# requirements.txt 확인
cat requirements.txt | grep psycopg2

# 없으면 추가
echo "psycopg2-binary>=2.9.9,<3.0.0" >> requirements.txt
git add requirements.txt
git commit -m "Add psycopg2-binary"
git push origin main
```

### 2. "could not connect to server"

**원인**: DATABASE_URL이 잘못되었거나 Neon.tech 서버 문제

**해결**:
1. Neon.tech 대시보드에서 연결 문자열 다시 복사
2. Streamlit Cloud Secrets에서 DATABASE_URL 업데이트
3. 앱 재시작

### 3. "대시보드에 데이터가 안 보임"

**원인**: 메인 앱과 대시보드가 다른 데이터베이스를 사용

**해결**:
1. 두 앱의 Secrets에서 DATABASE_URL이 **정확히 동일**한지 확인
2. 새로고침 버튼 클릭
3. 메인 앱에서 분석을 다시 실행

### 4. "로컬에서 작동하지만 배포하면 실패"

**원인**: 환경 변수 누락

**해결**:
1. Streamlit Cloud Secrets에 모든 필수 변수 설정
2. 로그에서 정확한 에러 메시지 확인
3. 앱 재배포

---

## 📊 데이터베이스 마이그레이션

### 로컬 SQLite → PostgreSQL 데이터 이전 (선택사항)

로컬에서 쌓인 analytics 데이터를 PostgreSQL로 옮기려면:

```bash
# 1. 로컬 데이터베이스 확인
sqlite3 analytics/usage_data.db "SELECT COUNT(*) FROM sessions;"

# 2. 데이터 내보내기 (CSV)
sqlite3 analytics/usage_data.db <<EOF
.headers on
.mode csv
.output sessions_export.csv
SELECT * FROM sessions;
.output activity_logs_export.csv
SELECT * FROM activity_logs;
.output daily_stats_export.csv
SELECT * FROM daily_stats;
EOF

# 3. PostgreSQL로 가져오기
# (psql 또는 Neon.tech 웹 콘솔에서 수동 import)
```

---

## 🔐 보안 권장사항

### 1. 비밀번호 변경

배포 후 **반드시** 기본 비밀번호를 변경하세요:

```bash
# 새 비밀번호 해시 생성
python3 -c "
import hashlib
password = '강력한비밀번호123!@#'
print(hashlib.sha256(password.encode()).hexdigest())
"

# Streamlit Cloud Secrets에서 ADMIN_PASSWORD_HASH 업데이트
```

### 2. DATABASE_URL 보호

- ❌ GitHub에 커밋하지 마세요
- ❌ 공개 채널에 공유하지 마세요
- ✅ Streamlit Cloud Secrets에만 저장

### 3. API 키 관리

- Google Cloud Console에서 API 키 사용량 모니터링
- 필요 시 rate limiting 설정

---

## 📈 성능 최적화

### Streamlit Cloud 무료 플랜 제한

- **리소스**: 1 CPU, 1GB RAM
- **동시 사용자**: ~10-20명
- **비활동 시**: 7일 후 자동 휴면

### 성능 향상 팁

1. **캐싱 활용**: `@st.cache_data` 데코레이터 사용
2. **PDF 크기 제한**: config.py에서 MAX_FILE_SIZE 조정
3. **PostgreSQL 인덱스**: activity_logs 테이블에 timestamp 인덱스 추가

---

## 🆘 지원

문제가 발생하면:

1. **로그 확인**: Streamlit Cloud 앱 페이지에서 로그 보기
2. **GitHub Issues**: 버그 리포트 제출
3. **Streamlit Community**: https://discuss.streamlit.io

---

## ✅ 체크리스트

배포 전 확인:

- [ ] GitHub에 최신 코드 push
- [ ] Neon.tech PostgreSQL 생성 완료
- [ ] DATABASE_URL 복사
- [ ] Gemini API 키 준비
- [ ] 관리자 비밀번호 해시 생성
- [ ] requirements.txt에 psycopg2-binary 추가 확인
- [ ] .gitignore에 secrets.toml 포함 확인

배포 후 확인:

- [ ] 메인 앱 접속 가능
- [ ] 대시보드 접속 가능
- [ ] 메인 앱에서 분석 실행 성공
- [ ] 대시보드에서 데이터 확인
- [ ] 로그에 에러 없음
- [ ] 기본 비밀번호 변경 완료

---

**배포 완료! 🎉**

불특정 다수가 메인 웹앱을 사용하고, 관리자는 대시보드에서 사용 통계를 모니터링할 수 있습니다!
