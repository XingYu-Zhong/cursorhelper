import asyncio
import os
import chainlit as cl
from chainlit.input_widget import Slider, Switch
import json

import re
from dotenv import load_dotenv
from lab.mainlab import MainLab
from llm.api.func_get_openai import OpenaiApi
from agent import QuestionAgent,PlanAgent
from utils.tools import clone_repo, get_directory_structure

load_dotenv()
client = OpenaiApi(api_key=os.getenv("OPENAI_API_KEY"), base_url=os.getenv("OPENAI_API_BASE_URL"), model='qwen-plus')


@cl.on_chat_start
async def start():
    res = await cl.AskActionMessage(
        content="请选择哪种方式开发",
        actions=[
            cl.Action(name="new", label="新开发项目", payload={"value": "new"}),
            cl.Action(name="old", label="基于已有项目", payload={"value": "old"}),
        ],
    ).send()
    
    if res:
        if res.get("payload").get("value") == "new":
            await handle_new()
        elif res.get("payload").get("value") == "old":
            await handle_old()
    else:
        await cl.Message(content="未收到选择，请重新开始").send()


async def handle_new():
    await cl.Message(content="您选择了新开发项目").send()
    # 发送初始消息
    msg = await cl.AskUserMessage(content="你希望开发一个什么样的项目？可以先告诉我你的想法，然后我再根据你的想法进行针对性的提问！", timeout=36000).send()
    
    # 询问最大提问次数
    max_q_res = await cl.AskActionMessage(
        content="您希望我最多进行几轮提问来澄清您的需求？",
        actions=[
            cl.Action(name="2_questions", payload={"value": 2}, label="2轮"),
            cl.Action(name="4_questions", payload={"value": 4}, label="4轮"),
            cl.Action(name="8_questions", payload={"value": 8}, label="8轮"),
        ],
        timeout=36000
    ).send()

    max_question_times = 2  # 默认值
    if max_q_res and max_q_res.get("payload"):
        max_question_times = int(max_q_res.get("payload").get("value"))

    question_agent = QuestionAgent(max_question_times=max_question_times, is_old=False)
    end_type = 0
    user_responses = []
    
    # 多轮对话收集信息
    while end_type == 0:
        # 等待用户回复
        user_msg = msg['output']
        user_responses.append(user_msg)
        
        # 获取下一个问题
        question, end_type = question_agent.get_question(user_msg)
        
        if end_type == 0:
            # 如果还有问题要问，发送下一个问题
            msg = await cl.AskUserMessage(content=question).send()
    
    # 获取对话历史记录
    history = question_agent.get_history_str()
    
    # 生成计划
    plan_agent = PlanAgent(is_old=False)
    
    # 创建消息并开始流式处理
    msg = cl.Message(content="")
    await msg.send()
    
    # 使用流式处理获取计划
    for chunk in plan_agent.get_plan(history, stream=True):
        await msg.stream_token(chunk)
    
    # 更新消息
    await msg.update()
    
    # 保存消息历史
    sys_prompt ="""
    你是一名资深的系统架构师，目前已经根据用户的需求，构建了一个完整的开发计划，请你结合用户的需求，来完善这个开发计划。
"""
    cl.user_session.set("message_history", [{"role": "system", "content": sys_prompt}, {"role": "assistant", "content": msg.content}])

extract_dir = "repodata"
async def handle_old():
    await cl.Message(content="您选择了基于已有项目").send()
    repo_path = None
    while repo_path == None:
        res = await cl.AskUserMessage(content="请你在下面消息框中提供GitHub仓库URL? ex：https://github.com/xxx/xxxxx", timeout=36000).send()
        if res:
            repo_path = clone_repo(res['output'], extract_dir)
            if repo_path is None:
                await cl.Message(
                        content=f"您的github链接无法正常下载，请检查项目链接或github网络连通情况。",
                    ).send()
            else:
                # 初始化项目
                await cl.Message(content="正在解析项目，请稍候...").send()
                cl.user_session.set("project_repo_path", repo_path)
                #获取项目目录
                notallow_dict = {'locale', 'static', 'docs', 'templates','tests','js_tests','jinja2','extras'}
                directory_structure = get_directory_structure(repo_path,notallow_dict)
                ml = MainLab("qwen-max","text-embedding-v3")
                # 发送初始消息
                msg = await cl.AskUserMessage(content="你希望对当前项目进行哪些方面的优化或者修改？可以先告诉我你的想法，然后我再根据你的想法进行针对性的提问！", timeout=36000).send()
                
                # 询问最大提问次数
                max_q_res_old = await cl.AskActionMessage(
                    content="您希望我最多进行几轮提问来分析您的项目和需求？",
                    actions=[
                        cl.Action(name="2_questions_old", payload={"value": 2}, label="2轮"),
                        cl.Action(name="4_questions_old", payload={"value": 4}, label="4轮"),
                        cl.Action(name="8_questions_old", payload={"value": 8}, label="8轮"),
                    ],
                    timeout=36000
                ).send()

                max_question_times = 2  # 默认值
                if max_q_res_old and max_q_res_old.get("payload"):
                    max_question_times = int(max_q_res_old.get("payload").get("value"))
                
                question_agent = QuestionAgent(max_question_times,True)
                end_type = 0
                user_responses = []
                user_msg = f"[directory_structure]\n{directory_structure}\n[user_request]\n{msg['output']}"
                while end_type == 0:
                    await cl.Message(content="[thinking].....").send()
                    user_responses.append(user_msg)
                    question, end_type = question_agent.get_question(user_msg)
                    if end_type == 1:
                        break
                    
                    # 修改部分开始
                    # 发送问题消息，并确保它可以被用户看到
                    question_msg = cl.Message(content=f"[开始查找]问题: {question}")
                    await question_msg.send()
                    
                    # 添加明确的回答前缀消息
                    t1 = cl.Message(content="正在通过oceanbase检索项目信息...")
                    await t1.send()
                    await asyncio.sleep(1)  # 添加一个短暂的延迟，确保消息被用户看到
                    # 修改部分结束
                    
                    # 获取流式输出生成器
                    response_generator = ml.run_lab(question, repo_path)
                    
                    # 创建新消息用于流式输出
                    response_msg = cl.Message(content="检索的相关信息: ")  # 添加前缀标识这是回答
                    await response_msg.send()
                    await asyncio.sleep(1)  # 添加一个短暂的延迟，确保消息被用户看到
                    
                    # 处理流式输出
                    full_response = ""
                    for token in response_generator:
                        full_response += token
                        await response_msg.stream_token(token)
                        await asyncio.sleep(0.01)
                    user_msg = full_response

                    # 更新消息内容
                    await response_msg.update()

    history = question_agent.get_history_str()
    plan_agent = PlanAgent(True)
    msg = cl.Message(content="# 开发计划 \n")
    await msg.send()
    await asyncio.sleep(1)  # 添加一个短暂的延迟，确保消息被用户看到
    
    for chunk in plan_agent.get_plan(history, stream=True):
        await msg.stream_token(chunk)
    await msg.update()
    plan = msg.content
    sys_prompt ="""
    你是一名资深的系统架构师，目前已经根据用户的需求，构建了一个完整的开发计划，请你结合用户的需求，来完善这个开发计划。
"""
    cl.user_session.set("message_history", [{"role": "system", "content": sys_prompt}, {"role": "assistant", "content":plan}])


@cl.on_message
async def main(message: cl.Message):
    msg = cl.Message(content="")
    await msg.send()
    # 获取历史消息
    message_history = cl.user_session.get("message_history") or []
    message_history.append({"role": "user", "content": message.content})
    # 只保留最后 10 条
    message_history = message_history[-10:]
   
    # 获取流式响应
    response_stream = client.stream_chat_model(message_history)
    
    # 处理流式输出
    full_response = ""
    for chunk in response_stream:
        if chunk.choices and len(chunk.choices) > 0:
            content = chunk.choices[0].delta.content
            if content:
                full_response += content
                await msg.stream_token(content)
    
    # 更新消息
    await msg.update()
    message_history.append({'role': 'assistant', 'content': msg.content})
    cl.user_session.set("message_history", message_history)