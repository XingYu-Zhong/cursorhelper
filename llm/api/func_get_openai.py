import openai
import time

class OpenaiApi:
    def __init__(self, api_key, base_url="",model = 'qwen-plus'):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model

        self.client = openai.OpenAI(api_key=self.api_key,base_url=self.base_url) if base_url!="" else openai.OpenAI(api_key=self.api_key)
    def stream_chat_model(self, messages_list, model=None, temperature=0.2, top_p=0.95):
        model = model if model else self.model
        stream = self.client.chat.completions.create(
            model=model,
            messages=messages_list,
            temperature=temperature,
            top_p=top_p,
            stream=True  # 启用流式输出
        )
        return stream
    

    def chat_model(self, messages_list, model=None, temperature=0.2, top_p=0.95):
        model = model if model else self.model
        
        try:
            resp = self.client.chat.completions.create(
                model=model,
                messages=messages_list,
                temperature=temperature,
                top_p=top_p,
            )
            return resp.choices[0].message.content
        
        except Exception as e:
            print(f"An error occurred: {e}. Retrying in 1 minute...model:{model}")
            time.sleep(60)  # Wait for 1 minute before retrying
            return self.chat_model(messages_list, model=model, temperature=temperature, top_p=top_p)

    def embedding_model(self,text,model = "text-embedding-v3"):
        if len(text) > 5120:
            text = text[:5120]
        max_retries = 50
        retries = 0
        while retries < max_retries:
            try:
                response = self.client.embeddings.create(
                    model=model,
                    input=text
                )
                break
            except Exception as e:
                print(f"An error occurred: {e},query:{text}")
                retries += 1
                if retries >= max_retries:
                    raise e
                time.sleep(60)  # Optional: wait for 2 seconds before retrying
        return response.data[0].embedding