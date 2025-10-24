# 🔑 API 키 설정 가이드

**중요**: 데모 모드가 제거되었습니다. 이제 Gemini API 키가 필수입니다!

---

## 📋 설정 방법 (로컬 테스트용)

### 1단계: .streamlit 폴더 생성

프로젝트 폴더에서:

```bash
mkdir .streamlit
```

### 2단계: secrets.toml 파일 생성

```bash
nano .streamlit/secrets.toml
```

또는 직접 파일을 생성하고 다음 내용 입력:

```toml
GEMINI_API_KEY = "여기에_실제_API_키_붙여넣기"
```


⚠️ **따옴표를 반드시 포함**하세요!

### 3단계: 앱 재시작

```bash
# 기존 앱 종료 (Ctrl+C)
# 다시 시작
streamlit run koica_appraisal_app.py
```

---

## 🌐 Streamlit Cloud 배포 시 설정

### 배포 과정에서 Secrets 추가

1. Streamlit Cloud에서 "New app" 클릭
2. 저장소 설정
3. **"Advanced settings"** 클릭
4. **"Secrets"** 섹션에 입력:

```toml
GEMINI_API_KEY = "your-actual-api-key-here"
```

5. "Deploy!" 클릭

### 배포 후 Secrets 수정

1. Streamlit Cloud 대시보드 접속
2. 앱 선택
3. ⚙️ "Settings" → "Secrets"
4. 수정 후 "Save"
5. 앱 자동 재시작됨

---

## 🔒 보안 주의사항

### ✅ 안전한 방법
- `.streamlit/secrets.toml` 파일 사용 (로컬)
- Streamlit Cloud Secrets 사용 (배포)
- 환경변수 사용

### ❌ 위험한 방법
- 코드에 직접 API 키 입력
- GitHub에 API 키 업로드
- 공개 저장소에 secrets.toml 업로드

---

## 📁 파일 구조

```
koica-auditor/
├── koica_appraisal_app.py      # 메인 앱
├── requirements.txt           # 패키지 목록
├── .gitignore                 # Git 제외 파일 (secrets 포함!)
├── .streamlit/               
│   └── secrets.toml          # API 키 (절대 업로드 금지!)
└── README.md
```

---

## ✅ 설정 확인 방법

앱을 실행했을 때:

### 성공한 경우 ✅
```
좌측 사이드바에 다음 표시:
🔑 API 상태
✅ API 연결됨
```

### 실패한 경우 ❌
```
화면에 빨간 에러 메시지:
⚠️ Gemini API 키가 설정되지 않았습니다.
```

---

## 🚨 문제 해결

### 문제 1: "API 키가 설정되지 않았습니다"

**원인**: secrets.toml 파일이 없거나 경로가 잘못됨

**해결:**
```bash
# 현재 위치 확인
pwd

# .streamlit 폴더가 있는지 확인
ls -la | grep streamlit

# 없으면 생성
mkdir .streamlit

# secrets.toml 파일 확인
cat .streamlit/secrets.toml
```

### 문제 2: "Gemini API 연결 실패"

**원인**: 잘못된 API 키

**해결:**
1. Google AI Studio에서 새 키 발급
2. secrets.toml에 정확히 복사
3. 따옴표 포함 확인
4. 앱 재시작

### 문제 3: 로컬에서는 작동하는데 배포에서 안 됨

**원인**: Streamlit Cloud Secrets 미설정

**해결:**
1. Streamlit Cloud 대시보드
2. Settings → Secrets
3. API 키 입력
4. Save

---

## 💡 대안 방법: 환경변수 사용

secrets.toml 대신 환경변수를 사용할 수도 있습니다:

### macOS/Linux
```bash
export GEMINI_API_KEY="your-api-key-here"
streamlit run koica_appraisal_app.py
```

### Windows (PowerShell)
```powershell
$env:GEMINI_API_KEY="your-api-key-here"
streamlit run koica_appraisal_app.py
```

### Windows (CMD)
```cmd
set GEMINI_API_KEY=your-api-key-here
streamlit run koica_appraisal_app.py
```

**참고**: 환경변수는 터미널을 닫으면 사라집니다. 영구 설정을 원하면 secrets.toml 사용을 권장합니다.

---

## 📞 도움이 필요하면

1. secrets.toml 파일 위치 확인
2. API 키 형식 확인 (따옴표 포함)
3. 앱 재시작
4. 에러 메시지 스크린샷

위 단계로 해결되지 않으면 구체적인 에러 메시지를 알려주세요!
