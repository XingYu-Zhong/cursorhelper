# from llm.api.func_get_openai import OpenaiApi
# import os
# from dotenv import load_dotenv
# # import sys


# # # 添加项目根目录到sys.path
# # sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# load_dotenv()

# client = OpenaiApi(api_key=os.getenv("OPENAI_API_KEY"), base_url=os.getenv("OPENAI_API_BASE_URL"),model='qwen-plus')

# history_message = []

# history_message.append({'role':'user','content':'你好'})

# response = client.chat_model(history_message)

# print(response)


# stream_response = client.stream_chat_model(history_message)

# for chunk in stream_response:
#     print(chunk.choices[0].delta.content)

# embedding_response = client.embedding_model('你好')

# print(embedding_response)




from utils.get_rerank import get_rerank_score_api




test = ["什么是文本排序模型", "文本排序模型广泛用于搜索引擎和推荐系统中，它们根据文本相关性对候选文本进行排序"]
results = get_rerank_score_api(test)
print(results)