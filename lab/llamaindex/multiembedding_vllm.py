# import os
# import concurrent.futures
# from typing import Any, List
# from llm.api.func_get_openai import OpenaiApi
# from sentence_transformers import SentenceTransformer
# import torch
# from llama_index.core.embeddings import BaseEmbedding
# from llm.local.get_vllm import CodeFuse_Vllm
# class MultiEmbeddings(BaseEmbedding):
#     model: OpenaiApi = None  # 声明类型，初始化为 None
#     embedding_type: str = None
#     device: str = None
#     model_name: str = None
#     def __init__(self, model_name="text-embedding-ada-002", **kwargs: Any) -> None:
#         super().__init__(**kwargs)
#         self.model_name = model_name
        
#         if model_name in ["text-embedding-ada-002", "text-embedding-3-large", "text-embedding-3-small"]:
#             self.embedding_type = "openai"
#             self.model = OpenaiApi(api_key=os.getenv("openai_api_key"), base_url=os.getenv("openai_base_url"))
#         elif "CodeFuse-CGE" in model_name:
#             self.embedding_type = "vllm"
#             self.model = CodeFuse_Vllm(model_name)
#         else:
#             self.embedding_type = "sentence_transformer"
            
#             self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
#             if torch.backends.mps.is_available():
#                 self.device = torch.device('mps')
#             print(f"使用sentence_transformer {model_name} 进行embedding device: {self.device}")
#             self.model = SentenceTransformer(model_name).to(self.device)

#     @classmethod
#     def class_name(cls) -> str:
#         return "multi_embeddings"

#     async def _aget_query_embedding(self, query: str) -> List[float]:
#         return self._get_query_embedding(query)

#     async def _aget_text_embedding(self, text: str) -> List[float]:
#         return self._get_text_embedding(text)

#     def _get_query_embedding(self, query: str) -> List[float]:
#         if self.embedding_type == "sentence_transformer":
#             return self.model.encode(query, convert_to_tensor=False).tolist()
#         elif self.embedding_type == "openai":
#             response = self.model.embedding_model(text=query, model=self.model_name)
#             return response
#         elif self.embedding_type == "vllm":
#             response = self.model.get_embedding(embedding_text=query)
#             return [response]

#     def _get_text_embedding(self, text: str) -> List[float]:
#         return self._get_query_embedding(text)

#     def _get_text_embeddings(self, texts: List[str]) -> List[List[float]]:
#         if self.embedding_type == "sentence_transformer" or self.embedding_type == "vllm":
#             embeddings = []
#             for text in texts:
#                 embedding_result = self._get_query_embedding(text)
#                 embeddings.extend(embedding_result)
#             return embeddings
#         elif self.embedding_type == "openai":
#             def get_embedding(text):
#                 return self.model.embedding_model(text=text, model=self.model_name)

#             with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
#                 embeddings = list(executor.map(get_embedding, texts))
            
#             return embeddings