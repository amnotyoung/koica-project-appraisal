"""
KOICA 사업 예비조사 심사 시스템 - 데이터 모델
심사 관련 데이터 클래스 정의
"""

from dataclasses import dataclass
from typing import List, Dict, Any


@dataclass
class AuditEvidence:
    """심사 근거 데이터 클래스

    Attributes:
        score: 획득 점수
        max_score: 만점
        percentage: 백분율 (0-100)
        detailed_scores: 세부 항목별 점수 리스트
        reasoning: 점수 산정 논리 설명
        strengths: 강점 리스트
        weaknesses: 약점 리스트
        recommendations: 개선 제안 리스트
    """

    score: int
    max_score: int
    percentage: float
    detailed_scores: List[Dict[str, Any]]
    reasoning: str
    strengths: List[str]
    weaknesses: List[str]
    recommendations: List[str]

    def __post_init__(self):
        """데이터 검증"""
        if self.score < 0 or self.score > self.max_score:
            raise ValueError(f"점수는 0과 {self.max_score} 사이여야 합니다.")

        if self.percentage < 0 or self.percentage > 100:
            raise ValueError("백분율은 0과 100 사이여야 합니다.")

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "score": self.score,
            "max_score": self.max_score,
            "percentage": self.percentage,
            "detailed_scores": self.detailed_scores,
            "reasoning": self.reasoning,
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
            "recommendations": self.recommendations
        }

    @classmethod
    def create_failed(cls, max_score: int, error_message: str) -> "AuditEvidence":
        """실패 결과 생성"""
        return cls(
            score=0,
            max_score=max_score,
            percentage=0.0,
            detailed_scores=[],
            reasoning=f"분석 실패: {error_message}",
            strengths=[],
            weaknesses=[],
            recommendations=[]
        )
