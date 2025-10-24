# 📊 KOICA 사업 심사 분석 도구 (비공식 개인 프로젝트)

**⚠️ 본 도구는 KOICA 공식 서비스가 아닙니다.**

개인이 KOICA (한국국제협력단) 사업 예비조사 심사 기준을 참고하여 독자적으로 개발한 AI 기반 분석 도구입니다.

## 📢 중요 공지

- 🚫 **KOICA 공식 서비스 아님**: KOICA와 법적/업무적 관계 없음
- 📝 **참고용 도구**: 분석 결과는 참고 자료이며 공식 심사 결과와 다를 수 있음
- 🤖 **AI 기반 분석**: Google Gemini AI를 활용한 자동 분석
- ⚖️ **면책**: 본 도구 사용으로 인한 결과에 대해 개발자는 책임지지 않음

## ✨ 주요 기능

- 📄 **PDF 자동 분석**: 예비조사 보고서 PDF 업로드 및 텍스트 추출
- 🤖 **AI 기반 심사**: Google Gemini AI를 활용한 전문가 수준의 평가
- 📊 **상세 보고서**: 항목별 점수, 강점/약점 분석, 개선 제안 제공
- 💾 **결과 다운로드**: 심사 결과를 텍스트 파일로 저장

## 📋 평가 기준

### 국내외 정책 부합성 (30점)
- SDGs와의 연관성 및 기여도
- 수원국 정책 부합성
- 한국 정부 CPS 연계성
- 코이카 전략 부합성
- 타 공여기관 중복 분석

### 사업 추진 여건 (70점)
- 문제/수요 분석 체계성
- 법제도적 여건
- 대상지 분석
- 이해관계자 분석
- 경제성 분석
- 지속가능성 및 출구전략
- 리스크 관리

## 🚀 로컬 실행 방법

### 1. 저장소 클론
```bash
git clone https://github.com/your-username/koica-auditor.git
cd koica-auditor
```

### 2. 가상환경 생성 (권장)
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 3. 패키지 설치
```bash
pip install -r requirements.txt
```

### 4. API 키 설정 (선택사항)

Gemini API 키가 있으면 고급 AI 분석을 사용할 수 있습니다.

#### 방법 1: secrets.toml 파일 사용 (추천)
```bash
mkdir .streamlit
nano .streamlit/secrets.toml
```

다음 내용 입력:
```toml
GEMINI_API_KEY = "your-api-key-here"
```

#### 방법 2: 환경변수 사용
```bash
export GEMINI_API_KEY="your-api-key-here"
```

#### API 키 발급 방법
1. [Google AI Studio](https://aistudio.google.com/app/apikey) 접속
2. "Create API Key" 클릭
3. 발급된 키 복사

### 5. 앱 실행
```bash
streamlit run koica_appraisal_app.py
```

브라우저에서 자동으로 http://localhost:8501 열림

## 🌐 Streamlit Cloud 배포

### 1. GitHub 저장소 생성
1. GitHub에서 새 저장소 생성
2. 코드 푸시:
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/your-username/koica-auditor.git
git push -u origin main
```

### 2. Streamlit Cloud 배포
1. [Streamlit Cloud](https://streamlit.io/cloud) 접속
2. "New app" 클릭
3. GitHub 저장소 연결
4. 배포 설정:
   - **Main file path**: `koica_appraisal_app.py`
   - **Python version**: 3.10
5. "Advanced settings" → "Secrets" 추가:
```toml
GEMINI_API_KEY = "your-api-key-here"
```
6. "Deploy!" 클릭

**배포 완료!** 몇 분 후 공개 URL 생성됨

## 📝 사용 방법

### PDF 분석
1. 사이드바에서 "Gemini API 사용" 체크 (선택)
2. API 키 입력 (또는 secrets 사용)
3. "PDF 분석" 탭에서 파일 업로드
4. "분석 시작" 버튼 클릭
5. 결과 확인 및 다운로드

### 텍스트 분석
1. "텍스트 분석" 탭 선택
2. 보고서 내용 직접 입력
3. "분석 시작" 버튼 클릭

## 🛠️ 기술 스택

- **Frontend**: Streamlit
- **AI Model**: Google Gemini 2.0 Flash
- **PDF Processing**: PyPDF2
- **Language**: Python 3.10+

## 🔒 보안 주의사항

- ⚠️ **절대 API 키를 코드에 하드코딩하지 마세요**
- ⚠️ **secrets.toml 파일을 GitHub에 업로드하지 마세요** (.gitignore에 포함됨)
- ⚠️ 공개 저장소에서는 Streamlit Cloud의 Secrets 관리 기능 사용

## ⚠️ 면책 조항

**중요**: 본 도구를 사용하기 전에 반드시 읽어주세요.

1. **비공식 도구**: 본 도구는 KOICA 공식 서비스가 아니며, KOICA와 어떠한 법적/업무적 관계도 없습니다.
2. **참고용 분석**: AI 기반 분석 결과는 참고 자료일 뿐이며, KOICA 공식 심사 결과와 다를 수 있습니다.
3. **책임 제한**: 본 도구 사용으로 인한 어떠한 결과에 대해서도 개발자는 책임지지 않습니다.
4. **공식 가이드 우선**: 실제 사업 심사는 [KOICA 공식 가이드라인](https://www.koica.go.kr)을 반드시 참조하세요.

## 🤝 기여

개선 사항이나 버그 리포트는 Issues 또는 Pull Request로 제출해주세요.

## 📄 라이선스

MIT License

## 📧 개발자

- 개인 프로젝트 (비공식)
- KOICA 심사 기준 참고: [KOICA 공식 웹사이트](https://www.koica.go.kr)

---

**본 도구는 KOICA와 무관한 개인 개발 프로젝트입니다.**
