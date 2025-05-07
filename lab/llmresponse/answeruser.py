import os
from dotenv import load_dotenv
load_dotenv()

from llm.api.func_get_openai import OpenaiApi
from lab.prompts.prompt_stores import llm_response_prompt_v1,code_system_prompt

class AnswerUser:
    def __init__(self,user_question,project_information= None,model_name="qwen-plus",is_stream=False):
        self.model_name = model_name
        self.user_question = user_question
        self.project_information = project_information
        self.llmmodel = OpenaiApi(api_key=os.getenv("OPENAI_API_KEY"), base_url=os.getenv("OPENAI_API_BASE_URL"))
        self.is_stream = is_stream
    
    def get_answer(self,index_information,history_message,extra_information=None):
        code_snippets = "" if extra_information is None else f"[citation:{0}]\n{extra_information}\n"
        # code_dist = {}
        for i,itme in enumerate(index_information):
            code_snippets += f"[citation:{i+1}]\n{itme}\n"

        prompt = llm_response_prompt_v1.format(project_information=self.project_information, code_snippets=code_snippets,question=self.user_question)
        messages_list = [
            {
                'role':'system','content':code_system_prompt,
            }
        ]
        for message in history_message:
            messages_list.append(message)
        messages_list.append({
                'role':'user','content':prompt,
            })
        with open("test_prompt.txt", 'w', encoding='utf-8') as file:
            file.write(prompt)
        if self.is_stream:
            try:
                stream_response = self.llmmodel.stream_chat_model(messages_list,model=self.model_name)
                # 返回生成器，直接处理OpenAI流式响应对象
                def stream_generator():
                    collected_content = ""
                    for chunk in stream_response:
                        if chunk.choices and len(chunk.choices) > 0:
                            content = chunk.choices[0].delta.content
                            if content:
                                collected_content += content
                                yield content
                    return collected_content
                return stream_generator()
            except Exception as e:
                # 发生错误时返回错误信息
                return (token for token in [f"流式输出错误: {str(e)}"])
        else:
            response = self.llmmodel.chat_model(messages_list,model=self.model_name)
            return response