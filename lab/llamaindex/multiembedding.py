import os
import concurrent.futures
from typing import Any, List
from llm.api.func_get_openai import OpenaiApi
# from sentence_transformers import SentenceTransformer
# import torch
from llama_index.core.embeddings import BaseEmbedding
class MultiEmbeddings(BaseEmbedding):
    model: OpenaiApi = None  # 声明类型，初始化为 None
    embedding_type: str = None
    device: str = None
    model_name: str = None
    def __init__(self, model_name="text-embedding-v3", **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.model_name = model_name
        
        if model_name in ["text-embedding-v3"]:
            self.embedding_type = "openai"
            self.model = OpenaiApi(api_key=os.getenv("OPENAI_API_KEY"), base_url=os.getenv("OPENAI_API_BASE_URL"))
        # else:
        #     self.embedding_type = "sentence_transformer"
            
        #     self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        #     if torch.backends.mps.is_available():
        #         self.device = torch.device('mps')
        #     print(f"使用sentence_transformer {model_name} 进行embedding device: {self.device}")
        #     self.model = SentenceTransformer(model_name).to(self.device)

    @classmethod
    def class_name(cls) -> str:
        return "multi_embeddings"

    async def _aget_query_embedding(self, query: str) -> List[float]:
        return self._get_query_embedding(query)

    async def _aget_text_embedding(self, text: str) -> List[float]:
        return self._get_text_embedding(text)

    def _get_query_embedding(self, query: str) -> List[float]:
        if self.embedding_type == "sentence_transformer":
            return self.model.encode(query, convert_to_tensor=False).tolist()
        elif self.embedding_type == "openai":
            response = self.model.embedding_model(text=query, model=self.model_name)
            return response

    def _get_text_embedding(self, text: str) -> List[float]:
        return self._get_query_embedding(text)

    def _get_text_embeddings(self, texts: List[str]) -> List[List[float]]:
        if self.embedding_type == "sentence_transformer":
            embeddings = []
            for text in texts:
                embedding_result = self.model.encode([text], convert_to_tensor=False).tolist()
                embeddings.extend(embedding_result)
            return embeddings
        elif self.embedding_type == "openai":
            def get_embedding(text):
                return self.model.embedding_model(text=text, model=self.model_name)

            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                embeddings = list(executor.map(get_embedding, texts))
            
            return embeddings