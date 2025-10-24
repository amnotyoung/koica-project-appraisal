# 🚀 Streamlit Cloud 배포 완벽 가이드

## 📝 배포 전 체크리스트

- [ ] 코드에서 API 키 제거 확인
- [ ] .gitignore 파일 있음
- [ ] requirements.txt 파일 있음
- [ ] README.md 작성 완료
- [ ] 로컬에서 테스트 완료

## 1단계: 로컬 테스트 (필수) ✅

### 1-1. 패키지 설치
```bash
pip install -r requirements.txt
```

### 1-2. API 키 설정 (임시 테스트용)
```bash
# 방법 1: 환경변수
export GEMINI_API_KEY="your-api-key-here"

# 방법 2: .streamlit/secrets.toml
mkdir .streamlit
echo 'GEMINI_API_KEY = "your-api-key-here"' > .streamlit/secrets.toml
```

### 1-3. 앱 실행
```bash
streamlit run koica_appraisal_app.py
```

### 1-4. 테스트 확인
- [ ] PDF 업로드 작동
- [ ] 텍스트 분석 작동
- [ ] AI 분석 결과 표시
- [ ] 다운로드 버튼 작동

**문제가 있으면 배포하지 말고 먼저 해결하세요!**

---

## 2단계: GitHub 저장소 생성 📦

### 2-1. GitHub에서 저장소 생성
1. https://github.com 로그인
2. 우측 상단 "+" → "New repository"
3. 저장소 정보 입력:
   - **Repository name**: `koica-auditor`
   - **Description**: "KOICA 사업 예비조사 심사 시스템"
   - **Public** 또는 **Private** 선택
   - ❌ **"Add README" 체크 해제** (이미 있음)
4. "Create repository" 클릭

### 2-2. 로컬 코드를 GitHub에 업로드

```bash
# Git 초기화 (아직 안 했으면)
git init

# 파일 추가
git add .

# 커밋
git commit -m "Initial commit: KOICA 심사 시스템"

# GitHub 저장소 연결 (your-username을 실제 GitHub ID로 변경)
git remote add origin https://github.com/your-username/koica-auditor.git

# 푸시
git branch -M main
git push -u origin main
```

### 2-3. GitHub에서 확인
- [ ] 모든 파일 업로드 확인
- [ ] ❌ `.streamlit/secrets.toml` 파일이 **없는지** 확인 (보안!)
- [ ] ❌ API 키가 코드에 **없는지** 확인 (보안!)

---

## 3단계: Streamlit Cloud 배포 🌐

### 3-1. Streamlit Cloud 계정 생성
1. https://streamlit.io/cloud 접속
2. "Sign up" 클릭
3. **GitHub 계정으로 로그인** (권장)

### 3-2. 새 앱 배포
1. "New app" 버튼 클릭
2. 배포 설정:

**Repository, branch, and file**
```
Repository: your-username/koica-auditor
Branch: main
Main file path: koica_appraisal_app.py
```

**App URL** (선택사항)
```
Custom subdomain: koica-auditor
```

3. "Advanced settings" 클릭

### 3-3. Secrets 설정 (중요! 🔒)
"Secrets" 섹션에 다음 입력:
```toml
GEMINI_API_KEY = "your-actual-api-key-here"
```

**⚠️ 주의사항:**
- 반드시 **실제 API 키**로 변경
- 따옴표 포함해서 입력
- 다른 사람과 공유하지 말 것

### 3-4. Python 버전 설정
```
Python version: 3.10
```

### 3-5. 배포 시작
"Deploy!" 버튼 클릭

---

## 4단계: 배포 확인 및 테스트 ✨

### 4-1. 배포 진행 상황 확인
- 화면에 로그가 표시됨
- 패키지 설치: 1-2분 소요
- 앱 시작: 30초 소요

### 4-2. 배포 완료
✅ 성공 메시지: "Your app is live!"
- 앱 URL: `https://your-app-name.streamlit.app`

### 4-3. 실제 테스트
배포된 앱에서 다음 테스트:
- [ ] 페이지 로딩
- [ ] PDF 업로드
- [ ] 분석 실행
- [ ] 결과 표시
- [ ] 다운로드

---

## 🔧 배포 후 관리

### 코드 수정 및 재배포
```bash
# 코드 수정 후
git add .
git commit -m "기능 개선: ..."
git push

# Streamlit Cloud가 자동으로 재배포함 (약 2-3분 소요)
```

### 앱 재시작
Streamlit Cloud 대시보드 → "⋮" 메뉴 → "Reboot app"

### 로그 확인
Streamlit Cloud 대시보드 → "Manage app" → "Logs"

### Secrets 수정
Streamlit Cloud 대시보드 → "⚙️ Settings" → "Secrets" → 수정

---

## ❌ 자주 발생하는 오류 및 해결

### 오류 1: "Module not found"
**원인**: requirements.txt에 패키지 누락
**해결**:
```bash
# requirements.txt에 패키지 추가
echo "missing-package==1.0.0" >> requirements.txt
git add requirements.txt
git commit -m "패키지 추가"
git push
```

### 오류 2: "Secret not found"
**원인**: Secrets 설정 안 함 또는 오타
**해결**:
1. Streamlit Cloud → Settings → Secrets
2. `GEMINI_API_KEY` 정확히 입력 확인
3. 따옴표 포함 여부 확인
4. "Save" 후 앱 재시작

### 오류 3: "API Key Invalid"
**원인**: 잘못된 API 키
**해결**:
1. Google AI Studio에서 새 키 발급
2. Secrets 업데이트
3. 앱 재시작

### 오류 4: 앱이 느림
**원인**: Streamlit Cloud 무료 플랜 제한
**해결**:
- 대용량 PDF 처리 최적화
- 캐싱 추가: `@st.cache_data`
- 또는 유료 플랜 고려

---

## 💰 비용 안내

### Streamlit Cloud
- **무료 플랜**: 
  - 공개 앱 1개
  - 제한된 리소스
  - 커뮤니티 지원
  
- **유료 플랜** ($20/월~):
  - 비공개 앱
  - 더 많은 리소스
  - 우선 지원

### Gemini API
- **무료 할당량**: 
  - 분당 15 요청
  - 일일 1500 요청
  
- **유료**: 초과 시 자동 과금

**예상 비용**: 소규모 사용 시 무료 가능

---

## 🎯 배포 완료 후 할 일

- [ ] 앱 URL 저장 및 공유
- [ ] 사용자 가이드 작성
- [ ] 피드백 수집 채널 마련
- [ ] 정기 업데이트 계획 수립

---

## 📞 도움이 필요하면

- Streamlit 문서: https://docs.streamlit.io
- Streamlit 커뮤니티: https://discuss.streamlit.io
- Gemini API 문서: https://ai.google.dev

---

**축하합니다! 🎉**
KOICA 심사 시스템이 성공적으로 배포되었습니다!
