"""
KOICA 사업 예비조사 심사 시스템 - 벡터 스토어
Gemini API를 사용한 간단한 벡터 저장소 구현
"""

import time
import logging
from typing import List, Optional
import streamlit as st
import google.generativeai as genai
import numpy as np

from config import RAGConfig, APIConfig

logger = logging.getLogger(__name__)


class SimpleVectorStore:
    """Gemini API를 사용한 간단한 벡터 스토어

    텍스트를 벡터로 임베딩하고 유사도 검색을 수행합니다.
    """

    def __init__(self, api_key: str):
        """벡터 스토어 초기화

        Args:
            api_key: Gemini API 키
        """
        self.api_key = api_key
        genai.configure(api_key=api_key)
        self.chunks: List[str] = []
        self.embeddings: List[List[float]] = []
        logger.info("SimpleVectorStore 초기화 완료")

    def add_texts(self, texts: List[str], batch_size: int = 1) -> None:
        """텍스트를 임베딩하여 저장

        단일 텍스트씩 처리하여 API 배치 문제 회피

        Args:
            texts: 임베딩할 텍스트 리스트
            batch_size: 배치 크기 (현재 1로 고정)
        """
        self.chunks = texts
        total = len(texts)
        logger.info(f"총 {total}개 텍스트 임베딩 시작")

        progress_bar = st.progress(0)
        failed_count = 0

        for i, text in enumerate(texts, 1):
            try:
                # 단일 텍스트씩 임베딩 생성
                result = genai.embed_content(
                    model=RAGConfig.EMBEDDING_MODEL,
                    content=text,
                    task_type=RAGConfig.EMBEDDING_TASK_TYPE_DOC
                )

                # 응답 처리
                embedding = self._extract_embedding(result, i)
                self.embeddings.append(embedding)

                # 진행 상황 업데이트
                progress = i / total
                progress_bar.progress(
                    progress,
                    text=f"임베딩 생성 중: {i}/{total}"
                )

                # Rate Limiting
                if i % APIConfig.RATE_LIMIT_BATCH_SIZE == 0:
                    time.sleep(APIConfig.RATE_LIMIT_BATCH_DELAY)
                else:
                    time.sleep(APIConfig.RATE_LIMIT_DELAY)

            except Exception as e:
                logger.error(f"청크 {i} 임베딩 실패: {e}")
                st.warning(f"청크 {i} 임베딩 실패: {e}")
                # 실패한 청크는 제로 벡터로 대체
                self.embeddings.append([0.0] * RAGConfig.EMBEDDING_DIMENSION)
                failed_count += 1

        progress_bar.empty()

        success_count = total - failed_count
        logger.info(f"임베딩 완료: {success_count}/{total} 성공")

        if failed_count > 0:
            st.warning(f"⚠️ {failed_count}개 청크 임베딩 실패 (제로 벡터로 대체)")

        st.success(f"✅ {success_count}개 청크 임베딩 완료!")

    def _extract_embedding(self, result: any, chunk_index: int) -> List[float]:
        """API 응답에서 임베딩 추출

        Args:
            result: API 응답
            chunk_index: 청크 인덱스 (로깅용)

        Returns:
            임베딩 벡터
        """
        if isinstance(result, dict) and 'embedding' in result:
            return result['embedding']
        elif isinstance(result, list):
            return result
        else:
            logger.warning(f"청크 {chunk_index}: 예상치 못한 응답 구조 - {type(result)}")
            st.warning(f"청크 {chunk_index}: 예상치 못한 응답 구조")
            return [0.0] * RAGConfig.EMBEDDING_DIMENSION

    def similarity_search(
        self,
        query: str,
        k: int = RAGConfig.DEFAULT_K_SEARCH
    ) -> List[str]:
        """쿼리와 유사한 청크 검색

        Args:
            query: 검색 쿼리
            k: 반환할 상위 결과 수

        Returns:
            유사도가 높은 청크 리스트
        """
        if not self.embeddings:
            logger.warning("임베딩이 비어있어 검색 불가")
            return []

        try:
            # 쿼리 임베딩 생성
            result = genai.embed_content(
                model=RAGConfig.EMBEDDING_MODEL,
                content=query,
                task_type=RAGConfig.EMBEDDING_TASK_TYPE_QUERY
            )

            # 쿼리 임베딩 추출
            query_embedding = self._extract_query_embedding(result)
            if not query_embedding:
                logger.warning("쿼리 임베딩 생성 실패, 앞부분 반환")
                return self.chunks[:k]

            # 코사인 유사도 계산
            similarities = []
            for idx, doc_embedding in enumerate(self.embeddings):
                similarity = self._cosine_similarity(query_embedding, doc_embedding)
                similarities.append((idx, similarity))

            # 상위 k개 선택
            similarities.sort(key=lambda x: x[1], reverse=True)
            top_k = similarities[:k]

            logger.info(f"검색 완료: 상위 {len(top_k)}개 청크 반환")
            return [self.chunks[idx] for idx, _ in top_k]

        except Exception as e:
            logger.error(f"검색 중 오류: {e}")
            st.warning(f"검색 중 오류: {e}")
            # 실패 시 앞부분 반환
            return self.chunks[:k]

    def _extract_query_embedding(self, result: any) -> Optional[List[float]]:
        """쿼리 API 응답에서 임베딩 추출

        Args:
            result: API 응답

        Returns:
            임베딩 벡터 또는 None
        """
        if isinstance(result, dict) and 'embedding' in result:
            return result['embedding']
        elif isinstance(result, list):
            return result
        else:
            logger.warning(f"예상치 못한 쿼리 응답 구조: {type(result)}")
            return None

    @staticmethod
    def _cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """코사인 유사도 계산

        Args:
            vec1: 첫 번째 벡터
            vec2: 두 번째 벡터

        Returns:
            코사인 유사도 (0-1)
        """
        try:
            vec1_np = np.array(vec1)
            vec2_np = np.array(vec2)

            # 제로 벡터 체크
            norm1 = np.linalg.norm(vec1_np)
            norm2 = np.linalg.norm(vec2_np)

            if norm1 == 0 or norm2 == 0:
                return 0.0

            return float(np.dot(vec1_np, vec2_np) / (norm1 * norm2))

        except Exception as e:
            logger.error(f"코사인 유사도 계산 오류: {e}")
            return 0.0

    def get_stats(self) -> dict:
        """벡터 스토어 통계 정보 반환

        Returns:
            통계 정보 딕셔너리
        """
        return {
            "total_chunks": len(self.chunks),
            "total_embeddings": len(self.embeddings),
            "embedding_dimension": RAGConfig.EMBEDDING_DIMENSION,
            "zero_vectors": sum(1 for emb in self.embeddings if all(v == 0.0 for v in emb))
        }
