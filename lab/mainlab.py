
import json
import json_repair
import os
import concurrent.futures
from lab.llamaindex.createindex import IndexStore
from lab.llmresponse.answeruser import AnswerUser
from utils.get_rerank import get_rerank_score_api
from utils.tools import get_directory_structure,count_directory_files,read_file
from utils.compress_file import get_skeleton
from utils.split_python import parse_python_file
from llm.api.func_get_openai import OpenaiApi
from lab.prompts.prompt_stores import generate_new_user_issue_prompt,analyze_folders_project_tree_prompt,analyze_files_project_tree_prompt,analyze_folders_project_tree_prompt_add_prompt,analyze_project_tree_prompt_add_prompt,judge_index_prompt,find_files_prompt,find_func_for_files_prompt

class MainLab:
    def __init__(self,llm_model_name,embedding_model_name) -> None:
        self.llm_model_name = llm_model_name
        self.embedding_model_name = embedding_model_name
        self.history_message = []
        self.llm = OpenaiApi(api_key=os.getenv("OPENAI_API_KEY"), base_url=os.getenv("OPENAI_API_BASE_URL"))

    def run_lab(self,user_question,project_file_path,is_stream=True):
        return self.reduce_index_lab(user_question,project_file_path,self.history_message,4,is_stream)
            
    
    def reduce_index_lab(self,user_question,project_file_path,history_message,index_type,is_stream):
        notallow_dict = {'locale', 'static', 'docs', 'templates','tests','js_tests','jinja2','extras'}
        directory_structure = get_directory_structure(project_file_path,notallow_dict)
        #TODO：step 1:去结合历史记录上下文来生成新的user_question
        new_user_issue_prompt = generate_new_user_issue_prompt+f"\n[user issue]\n{user_question}\n[project tree]\n{directory_structure}\n[history message]\n{self.history_message}\nOutput:\n"
        messages = [{
                "role":"user",
                "content": new_user_issue_prompt
            }]
        response = self.llm.chat_model(messages)
        print(response)
        new_user_issue = json_repair.loads(response)['result']
        user_question = new_user_issue['user_issue']

        
        prompt = analyze_files_project_tree_prompt + str(analyze_project_tree_prompt_add_prompt.format(dictory_structure=directory_structure,user_issue=user_question))
        messages = [{
                "role":"user",
                "content": prompt
            }]
            
        response = self.llm.chat_model(messages)
        print(response)
        llm_analyze_dict = json_repair.loads(response)
        files_data = llm_analyze_dict['files']['file_path']
        
        def process_folder(folder: str, project_file_path: str, embedding_model_name: str, user_question: str):
            result_list = []
            folder = os.path.dirname(project_file_path) + '/' + str(folder)
            count_files = count_directory_files(folder)
            print(f"folder path:{folder} count files:{count_files}")
            if count_files > 10:
                #TODO 超过10个文件的目录，用llm来处理，先通过llm来查看目录来筛选，把文件数控制到10个以内保证速度
                return []
            embedding_index = IndexStore(file_dir=folder, model_name=embedding_model_name)
            embedding_index.init_index(chunk_type=index_type)
            result = embedding_index.search(user_question)
            for item in result:
                item.metadata['embedding_text'] = item.text
                result_list.append(item.metadata)
            return result_list
        
        
        files_list = []
        if len(files_data) > 0:
            for file in files_data:
                files_list.append(os.path.dirname(project_file_path) + '/'+ file)
            print(files_list)
        judge_index_dict = self.llm_judge_index(user_question,files_list)
        new_files = []
        if judge_index_dict['is_answerable'] != 0:
            for file in files_data:
                new_files.append(os.path.dirname(project_file_path) + '/'+ file)
        result_list = []
        error_files_list = files_list
        if judge_index_dict['is_answerable'] != 3:
            error_files = ''
            max_count = 0
            while judge_index_dict['is_answerable'] != 1 and max_count <1:
                max_count += 1
                # 走embedding 目录
                error_files += '\n[file_path_list]\n'+str(error_files_list)+'\n[Reason]\n'+judge_index_dict['thoughts']+'\n'
                print(f'error:\n{error_files}')
                prompt = analyze_folders_project_tree_prompt + str(analyze_folders_project_tree_prompt_add_prompt.format(dictory_structure=directory_structure,user_issue=user_question,error_files=error_files))
                messages = [{
                        "role":"user",
                        "content": prompt
                    }]
                    
                response = self.llm.chat_model(messages)
                llm_analyze_dict = json_repair.loads(response)
                folders_data = llm_analyze_dict['folders']['folder_path']
                
    

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future_to_folder = {executor.submit(process_folder, folder, project_file_path, self.embedding_model_name, user_question): folder for folder in folders_data}
                    for future in concurrent.futures.as_completed(future_to_folder):
                        folder = future_to_folder[future]
                        try:
                            result = future.result()
                            result_list.extend(result)
                        except Exception as exc:
                            print(f'{folder} generated an exception: {exc}')
                #top30rerank
                # print("begin to calculate reranking score...")
                # for result in result_list: 
                #     rag_result = str(result['embedding_text'])
                #     context_list = [user_question,rag_result] 
                #     rerank_score = get_rerank_score_api(context_list)
                #     result['rerank_score'] = rerank_score[0]
                # result_list = sorted(result_list, key=lambda x: x['rerank_score'], reverse=True)
                # print(f"end to calculate reranking score...")
                print("开始对文档进行重排序...")
                if result_list:
                    # 收集所有文档文本
                    all_documents = [str(result['embedding_text']) for result in result_list]
                    
                    # 一次性请求所有文档的排序
                    context_list = [user_question, all_documents]
                    rerank_scores = get_rerank_score_api(context_list)
                    
                    # 将分数分配给结果列表
                    for i, score in enumerate(rerank_scores):
                        if i < len(result_list):
                            result_list[i]['rerank_score'] = score
                    
                    # 按相关性分数排序
                    result_list = sorted(result_list, key=lambda x: x.get('rerank_score', 0), reverse=True)
                print("文档重排序完成")
                
                result_list = result_list[:30]

                
                #LLM确定file 精排
                file_path_list = []
                for item in result_list:
                    file_path_list.append({item['path']:item['embedding_text']})
                input_prompt = f"""\n[error files]\n{error_files}\nInput:\n[user query]\n{str(user_question)}\n[Related filepath]\n{str(file_path_list)}\nOutput:\n"""
                find_file_final_prompt = find_files_prompt + input_prompt
                messages = [{
                        "role":"user",
                        "content": find_file_final_prompt
                    }]
                response = self.llm.chat_model(messages)
                # print(input_prompt)
                print(response)
                llm_file_path_list = json_repair.loads(response)['result']['file_path_list']
                judge_index_dict = self.llm_judge_index(user_question,llm_file_path_list)
                if judge_index_dict['is_answerable'] != 0:
                    existing_files_set = set(new_files)
                    for file_path in llm_file_path_list:
                        if file_path not in existing_files_set:
                            new_files.append(file_path)
                            existing_files_set.add(file_path)
                    if judge_index_dict['is_answerable'] == 1:
                        break
                print(f'new_files:{new_files}')
                if judge_index_dict['is_answerable'] != 1:
                    error_files_list = llm_file_path_list
                judge_index_dict = self.llm_judge_index(user_question,new_files)
                
            
            result_list = self.get_result_list(new_files)
     

        print(result_list)
        if is_stream:
            print("开始回答用户问题...")
            au = AnswerUser(user_question,directory_structure,is_stream=is_stream)
            response = au.get_answer(result_list,history_message) 
            self.history_message.append({'role':'user','content':user_question})
            return response
        else:
            au = AnswerUser(user_question,directory_structure)
            response = au.get_answer(result_list,history_message) 
            self.history_message.append({'role':'user','content':user_question})
            self.history_message.append({'role':'assistant','content':response})
            return response
            
    def stream_history_message_append(self,message_dict):
        self.history_message.append(message_dict)

    def llm_judge_index(self,user_question,files_data):
        compress_file_context = ""
        for file in files_data:
            file_context = read_file(file)
            file_suffix = file.split('.')[-1]
            if file_suffix == 'py':
                compress_file_context += (f"\nfile path:{file}"+get_skeleton(file_context,True))
            else:
                compress_file_context += (f"file path:{file}"+file_context)
        judge_prompt = judge_index_prompt+str(user_question)+'\n[Related information]\n'+compress_file_context+"\nOutput:\n"
        messages = [{
                "role":"user",
                "content": judge_prompt
            }]
        response = self.llm.chat_model(messages)
        # print(judge_prompt)
        print(response)
        judge_index_dict = json_repair.loads(response)['result']
        return judge_index_dict
    def get_result_list(self,file_path_list):
        # 做函数定位切片 已实现py 
        result_list = []
        for file in file_path_list:
            # 如果是py文件，则可以确定func和line
            file_suffix = file.split('.')[-1]
            if file_suffix == 'py':
                #llm确定func和line 
                class_info,func_info,line_info,var_info = parse_python_file(file)
                class_input_prompt = '\n[Class Info]\n'
                function_input_prompt = '\n[Global Function Info]\n'
                var_input_prompt = '\n[Global Var Info]\n'
                for i,class_content in enumerate(class_info):
                    content = f'[item {i}]:\n'+str(class_content['text'])+'\n'
                    class_input_prompt += content
                for i,func_content in enumerate(func_info):
                    content = f'[item {i}]:\n'+str(func_content['text'])+'\n'
                    function_input_prompt += content
                for i,var_content in enumerate(var_info):
                    content = f'[item {i}]:\n'+str(var_content['text'])+'\n'
                    var_input_prompt += content
                input_prompt = find_func_for_files_prompt+class_input_prompt+function_input_prompt+var_input_prompt
                messages = [{
                    "role":"user",
                    "content": input_prompt
                }]
                response = self.llm.chat_model(messages)
                print(response)
                class_list = json_repair.loads(response)['result']['class_list']
                global_function_list= json_repair.loads(response)['result']['global_function_list']
                global_var_list= json_repair.loads(response)['result']['global_var_list']
                
                if len(class_list) > 0:
                    for class_item in class_list:
                        result_context = ''
                        class_name = class_item
                        for class_org_item in class_info:
                            if class_org_item['name'] == class_name:
                                class_content = '\n'.join(text for text in class_org_item['text'])
                                result_context = f"\nfile path:{file}\n[Class Name]:{class_name}\n[Class Content]:\n```\n{class_content}```\n"
                        result_list.append(result_context)
                if len(global_function_list) > 0:
                    for func_item in global_function_list:
                        result_context = ''
                        func_name = func_item
                        for func_org_item in func_info:
                            if func_org_item['name'] == func_name:
                                func_content = '\n'.join(text for text in func_org_item['text'])
                                result_context = f"\nfile path:{file}\n[Func Name]:{func_name}\n[Func Content]:\n```\n{func_content}\n```\n"
                        result_list.append(result_context)
                if len(global_var_list) > 0:
                    for var_item in global_var_list:
                        result_context = ''
                        var_name = var_item
                        for var_org_item in var_info:
                            if var_org_item['name'] == var_name:
                                var_content = '\n'.join(text for text in var_org_item['text'])
                                result_context = f"\nfile path:{file}\n[Var Name]:{var_name}\n[Var Content]:\n```\n{var_content}```\n"
                        result_list.append(result_context)
            else:
                file_context = read_file(file)
                result_file_context = (f"file path:{file}\n"+file_context)
                result_list.append(result_file_context)
        return result_list