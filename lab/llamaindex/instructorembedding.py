from typing import Any, List
import os
from dotenv import load_dotenv
load_dotenv()

from llama_index.core.embeddings import BaseEmbedding
from llm.api.func_get_openai import OpenaiApi


class InstructorEmbeddings(BaseEmbedding):
    llmmodel: OpenaiApi = None  # 声明类型，初始化为 None

    def __init__(self,model_name="text-embedding-v3", **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.llmmodel = OpenaiApi(api_key=os.getenv("OPENAI_API_KEY"), base_url=os.getenv("OPENAI_API_BASE_URL"))
        self.model_name = model_name

    @classmethod
    def class_name(cls) -> str:
        return "instructor"

    async def _aget_query_embedding(self, query: str) -> List[float]:
        return self._get_query_embedding(query)

    async def _aget_text_embedding(self, text: str) -> List[float]:
        return self._get_text_embedding(text)

    def _get_query_embedding(self, query: str) -> List[float]:
        embeddings = self.llmmodel.embedding_model(text=query,model=self.model_name)
        return embeddings

    def _get_text_embedding(self, text: str) -> List[float]:
        embeddings = self.llmmodel.embedding_model(text=text,model=self.model_name)
        return embeddings

    def _get_text_embeddings(self, texts: List[str]) -> List[List[float]]:
        embeddings= []
        for text in texts:
            embedding= self.llmmodel.embedding_model(text=text,model=self.model_name)
            embeddings.append(embedding)
        return embeddings