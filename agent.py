from prompt.newproject_prompt import question_sys_prompt as question_sys_prompt_new, question_user_prompt as question_user_prompt_new,plan_sys_prompt as plan_sys_prompt_new,plan_user_prompt as plan_user_prompt_new
from prompt.oldproject_prompt import question_sys_prompt as question_sys_prompt_old, question_user_prompt as question_user_prompt_old,plan_sys_prompt as plan_sys_prompt_old,plan_user_prompt as plan_user_prompt_old       
from llm.api.func_get_openai import OpenaiApi

import os
import json
import json_repair
from dotenv import load_dotenv

class QuestionAgent:
    def __init__(self,max_question_times=5,is_old=False):
        load_dotenv()
        if is_old:
            self.sys_prompt = question_sys_prompt_old
            self.user_prompt = question_user_prompt_old
        else:
            self.sys_prompt = question_sys_prompt_new
            self.user_prompt = question_user_prompt_new
        self.input_history = [{
            "role": "system",
            "content": self.sys_prompt
        }]
        self.true_history = []
        self.llm_client = OpenaiApi(api_key=os.getenv("OPENAI_API_KEY"), base_url=os.getenv("OPENAI_API_BASE_URL"),model='qwen-plus')
        self.max_question_times = max_question_times


    def get_question(self, user_input):
        if self.max_question_times <= 0:
            return '',1
        self.true_history.append({
            "role": "user",
            "content": user_input
        })
        self.input_history.append({
            "role": "user",
            "content": self.user_prompt+json.dumps(self.true_history)+'\nOutput:'
        })
        llm_response = self.llm_client.chat_model(self.input_history)
        result = json_repair.loads(llm_response)['result']
        end_type = int(result['is_true'])
        question = result['question']
        self.true_history.append({
            "role": "assistant",
            "content": question
        })
        self.max_question_times -= 1
        return question,end_type
    
    def get_history(self):
        return self.true_history
    
    def get_history_str(self):
        return str(json.dumps(self.true_history))
            

class PlanAgent:
    def __init__(self,is_old=False):
        if is_old:
            self.sys_prompt = plan_sys_prompt_old
            self.user_prompt = plan_user_prompt_old
        else:
            self.sys_prompt = plan_sys_prompt_new
            self.user_prompt = plan_user_prompt_new
        self.history = [{
            "role": "system",
            "content": self.sys_prompt
        }]
        self.llm_client = OpenaiApi(api_key=os.getenv("OPENAI_API_KEY"), base_url=os.getenv("OPENAI_API_BASE_URL"),model='qwen-plus')

    def get_plan(self,history,stream=False):
        history_str = json.dumps(history) if isinstance(history, list) else history
        prompt = self.user_prompt+history_str+'\nOutput:'
        self.history.append({
            "role": "user",
            "content": prompt
        })
        if stream:
            stream_llm_response = self.llm_client.stream_chat_model(self.history)
            for chunk in stream_llm_response:
                if hasattr(chunk.choices[0].delta, 'content') and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                elif chunk.choices[0].finish_reason == 'stop':
                    break
        else:
            llm_response = self.llm_client.chat_model(self.history)
            return llm_response