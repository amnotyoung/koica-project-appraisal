# ⚡ 빠른 시작 가이드 (5분 완성)

KOICA 심사 시스템을 가장 빠르게 배포하는 방법

## 🎯 목표
5-10분 안에 웹에서 작동하는 앱 배포하기

---

## Step 1: 준비 (1분)

### 필요한 것
- [ ] GitHub 계정 (없으면 https://github.com/signup)
- [ ] Gemini API 키 (https://aistudio.google.com/app/apikey)

**API 키 발급:**
1. 링크 접속 → Google 로그인
2. "Create API Key" 클릭
3. 키 복사 (예: `AIzaSy...`)
4. 안전한 곳에 저장

---

## Step 2: GitHub 업로드 (2분)

### 2-1. 저장소 생성
1. GitHub 로그인
2. 우측 상단 "+" → "New repository"
3. 입력:
   - Name: `koica-auditor`
   - Public 선택
   - **README 체크 해제**
4. "Create repository"

### 2-2. 파일 업로드
방법 1: **웹에서 직접** (초보자 추천)
```
1. "uploading an existing file" 클릭
2. 다음 파일들 드래그 앤 드롭:
   - koica_appraisal_app.py
   - requirements.txt
   - .gitignore
   - README.md
3. "Commit changes"
```

방법 2: **Git 명령어** (개발자용)
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/your-username/koica-auditor.git
git push -u origin main
```

---

## Step 3: Streamlit 배포 (2분)

### 3-1. 로그인
1. https://streamlit.io/cloud
2. "Sign up" → **GitHub로 로그인**

### 3-2. 배포
1. "New app" 클릭
2. 입력:
   ```
   Repository: your-username/koica-auditor
   Branch: main
   Main file: koica_appraisal_app.py
   ```
3. "Advanced settings" → "Secrets" 입력:
   ```toml
   GEMINI_API_KEY = "여기에_당신의_API_키_붙여넣기"
   ```
   ⚠️ 따옴표 포함!

4. "Deploy!" 클릭

---

## Step 4: 완료! (1분)

### 배포 완료 대기
- 진행 바 표시됨 (2-3분)
- ✅ "Your app is live!" 나오면 성공

### 앱 테스트
1. 생성된 URL 접속 (예: `https://koica-auditor.streamlit.app`)
2. 샘플 텍스트로 테스트:
   - "텍스트 분석" 탭
   - sample_report.txt 내용 붙여넣기
   - "분석 시작" 클릭

---

## ✅ 체크리스트

배포 성공 확인:
- [ ] 앱 URL이 작동함
- [ ] PDF 업로드 가능
- [ ] "분석 시작" 버튼 작동
- [ ] 결과가 표시됨
- [ ] 다운로드 버튼 작동

---

## 🔧 문제 해결

### "Module not found" 오류
→ requirements.txt 파일이 있는지 확인

### "Secret not found" 오류
→ Streamlit Cloud → Settings → Secrets → API 키 다시 입력

### 앱이 안 열림
→ 2-3분 기다린 후 새로고침

---

## 🎉 다음 단계

배포 완료! 이제:
1. **URL 공유**: 팀원들에게 링크 전달
2. **테스트**: 실제 PDF로 분석
3. **피드백**: 사용자 의견 수집
4. **개선**: 코드 수정 → git push → 자동 재배포

---

## 📚 더 알아보기

- 상세 가이드: `DEPLOYMENT_GUIDE.md` 참조
- 사용법: `README.md` 참조
- Streamlit 문서: https://docs.streamlit.io

---

**🎊 축하합니다!**
당신의 KOICA 심사 시스템이 이제 웹에서 작동합니다!
