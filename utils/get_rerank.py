import requests
import json
import os
from dotenv import load_dotenv



def get_rerank_score_api(context_list):
    load_dotenv()
    """
    使用阿里云DashScope的文本重排序API对文档进行排序
    
    Args:
        context_list: 包含查询和文档的列表，第一个元素是查询字符串，第二个元素是文档列表
        
    Returns:
        返回所有文档的相关性分数列表
    """
    query = context_list[0]
    documents = context_list[1]
    
    # 确保documents是字符串列表
    if not isinstance(documents, list):
        documents = [documents]
    elif len(documents) == 0:
        return [0.0]  # 如果没有文档，返回默认分数
    
    # 去除可能的空文档
    documents = [doc for doc in documents if doc and isinstance(doc, str)]
    
    if not documents:
        return [0.0]  # 如果过滤后没有有效文档，返回默认分数
    
    # 获取API密钥，优先从环境变量获取
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY环境变量未设置")
    
    url = "https://dashscope.aliyuncs.com/api/v1/services/rerank/text-rerank/text-rerank"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    data = {
        "model": "gte-rerank-v2",
        "input": {
            "query": query,
            "documents": documents
        },
        "parameters": {
            "return_documents": True,
            "top_n": min(len(documents), 30)  # 确保top_n不超过文档数量，最多返回30个
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=120)  # 增加超时时间以处理更多文档
        
        if response.status_code == 200:
            # 返回所有文档的相关性分数列表
            return [result['relevance_score'] for result in response.json()["output"]["results"]]
        else:
            error_info = response.json()
            print(f"API错误: {error_info}")
            # 在出错时返回默认值列表，长度与文档数量一致
            return [0.0] * len(documents)
    except Exception as e:
        print(f"请求异常: {str(e)}")
        return [0.0] * len(documents)  # 返回默认分数列表，保证程序继续运行


# 使用示例
# test = ["什么是文本排序模型", ["文本排序模型广泛用于搜索引擎和推荐系统中，它们根据文本相关性对候选文本进行排序", 
#                      "量子计算是计算科学的一个前沿领域", 
#                      "预训练语言模型的发展给文本排序模型带来了新的进展"]]
# results = get_rerank_score_api(test)
# print(results) 