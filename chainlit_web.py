import os
import chainlit as cl
from chainlit.input_widget import Slider,Switch
import json
import re
from dotenv import load_dotenv
from llm.api.func_get_openai import OpenaiApi

load_dotenv()
client = OpenaiApi(api_key=os.getenv("OPENAI_API_KEY"), base_url=os.getenv("OPENAI_API_BASE_URL"),model='qwen-plus')



@cl.on_chat_start
async def start():
    
    cl.user_session.set("message_history", [])
    
    res = await cl.AskActionMessage(
        content="请选择项目上传方式",
        actions=[
            cl.Action(name="new", value="new", label="新开发项目", payload={}),
            cl.Action(name="old", value="old", label="基于已有项目", payload={}),
        ],
    ).send()

    if res:
        if res.get("value") == "new":
            await handle_new()
        elif res.get("value") == "old":
            await handle_old()
    else:
        await cl.Message(content="未收到选择，请重新开始").send()

async def handle_new():
    print("新开发项目")
    # await cl.Message(content="你希望开发一个什么样的项目？可以先告诉我你的想法，然后我再根据你的想法进行针对性的提问！").send()

async def handle_old():
    print("基于已有项目")


@cl.on_message
async def main(message: cl.Message):
    msg = cl.Message(content="")
    await msg.send()
    BATCH_SIZE = 5

    # 获取历史消息
    message_history = cl.user_session.get("message_history") or []
    message_history.append({"role": "user", "content": message.content})
    # 只保留最后 10 条
    message_history = message_history[-10:]
   
    response_stream = client.stream_chat_model(message_history)
    tokens = []
    for part in response_stream:
        token = getattr(part.choices[0].delta, 'content', "")
        if token:
            tokens.append(token)
            if len(tokens) >= BATCH_SIZE:
                await msg.stream_token("".join(tokens))
                tokens = []
    if tokens:
        await msg.stream_token("".join(tokens))

    await msg.update()
    message_history.append({'role': 'assistant', 'content': msg.content})
    cl.user_session.set("message_history", message_history)