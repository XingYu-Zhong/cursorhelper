
import re
import os
import time
import shutil
import hashlib
from tqdm import tqdm
import concurrent.futures
from functools import partial
from dotenv import load_dotenv
from llama_index.core import VectorStoreIndex,Document,StorageContext,load_index_from_storage
from llama_index.core import Settings
from llm.api.func_get_openai import OpenaiApi
from utils.diff_tools import find_min_diff_commit, get_changed_files,reset_to_commit
from utils.tools import filter_path,get_split_code,migrate_directory,read_file,get_directory_structure
from utils.compress_file import get_skeleton
from lab.llamaindex.instructorembedding import InstructorEmbeddings
from lab.llamaindex.multiembedding import MultiEmbeddings
from lab.prompts.prompt_stores import code_system_prompt,code_to_text_prompt_v1,file_to_text_prompt_v1
# FILE_DIR_BASE = ".llamaindex"
class IndexStore:
    def __init__(self,file_dir,model_name="text-embedding-v3"):
        self.file_dir = file_dir
        load_dotenv()
        # Settings.embed_model = InstructorEmbeddings(model_name=model_name)
        Settings.embed_model = MultiEmbeddings(model_name=model_name)
        self.llmmodel = OpenaiApi(api_key=os.getenv("OPENAI_API_KEY"), base_url=os.getenv("OPENAI_API_BASE_URL"))


    def init_index(self, chunk_type=1, current_commit_group=None,repo_path=None,excluded_dirs = ['conf', 'tests'],is_new = False):
        # 根据chunk_type设置文件路径基础目录
        self.FILE_DIR_BASE = {
            1: ".llamaindex_onlycode",
            2: ".llamaindex_codetotext",
            3: ".llamaindex_lowcodetotext",
            4: ".llamaindex_filetotext",
        }.get(chunk_type, ".llamaindex_onlycode")

        self.file_dir_index = os.path.join(self.FILE_DIR_BASE, self.file_dir) if current_commit_group is None else os.path.join(os.path.join(self.FILE_DIR_BASE, self.file_dir), current_commit_group)
        print(f'Indexing {self.file_dir}...to {self.file_dir_index}')
        if current_commit_group is None:
            if os.path.exists(self.file_dir_index):
                print(f'type 1, skipping indexing...')
                self._load_existing_index()
                return 0
            else:
                print(f'type 2, begin indexing...')
                embedding_time = self._create_new_index(chunk_type)
                return embedding_time
        else:
            is_exist = os.path.exists(self.file_dir_index)
            print(f'{self.file_dir_index} is_exist: {is_exist} -----is_new: {is_new}')
            if is_exist and not is_new:
                print(f'type 3, skipping indexing...')
                self._load_existing_index()
                return 0
            else:
                if is_new:
                    # 检查文件夹是否存在
                    if os.path.exists(self.file_dir_index):
                        # 删除旧的index文件夹
                        shutil.rmtree(self.file_dir_index)
                print(f'type 4, update indexing...')
                embedding_time = self._update_index_for_commit_group(chunk_type, current_commit_group,excluded_dirs,repo_path)
                return embedding_time

    def _load_existing_index(self):
        print(f'Loading existing index...{self.file_dir_index}')
        storage_context = StorageContext.from_defaults(persist_dir=self.file_dir_index)
        self.index = load_index_from_storage(storage_context)
        self.index_context = storage_context

    def _create_new_index(self, chunk_type):
        # os.makedirs(self.file_dir, exist_ok=True)  # 确保目录被创建 TODO：check 感觉逻辑要重新确认一下
        file_list = self.get_file_list(self.file_dir)
        document_data = self.get_document_data(chunk_type, file_list)
        print(f'{len(document_data)} documents loaded; creating index...')
        start_time = time.perf_counter()
        self.index = VectorStoreIndex(document_data)
        end_time = time.perf_counter()
        execution_time = end_time - start_time
        self.index.storage_context.persist(persist_dir=self.file_dir_index)
        self.index_context = self.index.storage_context
        return execution_time

    def _update_index_for_commit_group(self, chunk_type, current_commit_group,excluded_dirs,repo_path=None):
        self.file_dir_index = os.path.join(os.path.join(self.FILE_DIR_BASE, self.file_dir), current_commit_group)
        if repo_path is None:
            reset_to_commit(self.file_dir, current_commit_group)
        else:
            reset_to_commit(repo_path, current_commit_group)
        target_dir = os.path.join(self.FILE_DIR_BASE, self.file_dir)
        if os.path.exists(target_dir):
            target_dir = os.path.join(self.FILE_DIR_BASE, self.file_dir)
            # 获取目录下的所有子目录名列表
            commit_id_pattern = re.compile(r'^[0-9a-f]{40}$')  # 假设commitid是40位的SHA-1哈希
            commit_dirs = [
                name for name in os.listdir(target_dir)
                if os.path.isdir(os.path.join(target_dir, name)) and commit_id_pattern.match(name)
            ]
            
            # 如果没有符合条件的子目录，则返回 False
            if not commit_dirs:
                embedding_time = self._create_new_index(chunk_type)
                return embedding_time
            if repo_path is None:
                min_commit, _ = find_min_diff_commit(self.file_dir, current_commit_group, commit_dirs)
            else:
                min_commit, _ = find_min_diff_commit(repo_path, current_commit_group, commit_dirs)
            min_commit_dir = os.path.join(os.path.join(self.FILE_DIR_BASE, self.file_dir), min_commit)
            current_commit_dir = self.file_dir_index

            migrate_directory(min_commit_dir, current_commit_dir)

            storage_context = StorageContext.from_defaults(persist_dir=self.file_dir_index)
            self.index = load_index_from_storage(storage_context)
            self.index_context = storage_context
            if repo_path is None:
                change_files = get_changed_files(self.file_dir, current_commit_group, min_commit)
            else:
                change_files = get_changed_files(repo_path, current_commit_group, min_commit,self.file_dir)

            diff_files = [change_file for change_file in change_files if filter_path(change_file)]
            excluded_dirs = ['conf', 'tests']  # 你可以根据需要修改这个列表，或者它可能为空 []

            diff_files = [
                change_file for change_file in change_files
                if filter_path(change_file) and (not excluded_dirs or not any(excluded_dir in change_file for excluded_dir in excluded_dirs))
            ]
            for change_file in diff_files:
                self.del_doc_for_path(change_file)
            current_file_list = self.get_file_list(self.file_dir)
            #过滤掉删除的那些文件
            diff_files = [change_file for change_file in change_files if change_file in current_file_list]
            document_data = self.get_document_data(chunk_type, diff_files)
            self.index.insert_nodes(document_data)
            self.index.storage_context.persist(persist_dir=self.file_dir_index)
            self.index_context = self.index.storage_context
            return 0
        else:
            embedding_time = self._create_new_index(chunk_type)
            return embedding_time



    def get_document_data(self,chunk_type:int,file_list:list):
        match chunk_type:
            case 1:
                document_data = self.to_documents_only_code(file_list)
            case 2:
                document_data = self.to_documents_code_to_text(file_list)
            case 3:
                document_data = self.to_documents_code_to_text(file_list)
            case 4:
                document_data = self.to_documents_file_to_text(file_list)
            case _:
                document_data = self.to_documents_only_code(file_list)
        return document_data
    def get_file_list(self,file_dir:str):
        file_list = []
        for root, dirs, files in os.walk(file_dir):
            for filename in files:
                full_path = os.path.join(root, filename)  # 构建完整路径
                normalized_path = os.path.normpath(full_path)  # 标准化路径
                file_list.append(normalized_path)
        return file_list


    def to_documents_file_to_text(self, file_list:list, fast_type:bool=True):
        documents = []

        def process_file(file):
            if filter_path(file):
                result_list = get_split_code(file)
                if 'suffix' in result_list or result_list is None:
                    return None
                lang = result_list['lang']
                org_file_context = read_file(file)
                file_context = get_skeleton(org_file_context, True)
                folder_path = os.path.dirname(file)
                pivotal_info = get_directory_structure(folder_path)
                prompt = file_to_text_prompt_v1.format(lang=lang, pivotal_info=pivotal_info, file_context=file_context)
                messages_list = [
                    {
                        'role': 'system', 'content': code_system_prompt,
                    }, {
                        'role': 'user', 'content': prompt,            
                    }
                ]
                md5 = hashlib.md5(file.encode('utf-8'), usedforsecurity=False).hexdigest()
                text = self.llmmodel.chat_model(messages_list)
                return Document(
                    text=str(text),
                    metadata={'path':file, 'md5':md5, 'file_context':org_file_context},
                )
            return None

        if fast_type:
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                for document in tqdm(executor.map(process_file, file_list), total=len(file_list)):
                    if document:
                        documents.append(document)
        else:
            for file in tqdm(file_list):
                document = process_file(file)
                if document:
                    documents.append(document)

        return documents
    def to_documents_code_to_text(self, file_list:list):
        text_file = ['txt', 'md']
        documents = []
        for file in tqdm(file_list):
            if filter_path(file):
                result_list = get_split_code(file)
                if 'suffix' in result_list or result_list is None:
                    continue
                lang = result_list['lang']
                for result in result_list['codes']:
                    try:
                        text = {
                            'code_comment': ''
                        }
                        # prompt = code_to_text_prompt_v1.format(lang=lang, pivotal_info=result.get('class_code', ''), code=result['code'])
                        prompt = code_to_text_prompt_v1.format(lang=lang, pivotal_info='', code=result['code'])
                        messages_list = [
                            {
                                'role': 'system', 'content': code_system_prompt,
                            }, {
                                'role': 'user', 'content':prompt,            
                            }
                        ]
                        if lang in text_file:
                            response = str(result['code'])
                        else:
                            
                            response = self.llmmodel.chat_model(messages_list)
                        
                        if response is None:
                            text['code_comment'] = str(result['code'])
                            
                        else:
                            text['code_comment'] = response

                        if text['code_comment'] is None or text['code_comment'] == '':
                            continue
                        result['embedding_text'] = text['code_comment']
                        document = Document(
                            text=str(text['code_comment']),
                            metadata=result,
                        )
                        documents.append(document)
                    except Exception as e:
                        print(f"Error reading file : {e}")
                        continue
        return documents

    def to_documents_only_code(self, file_list):
        document_list = []
        for file in tqdm(file_list):
            if filter_path(file):
                result_list = get_split_code(file)
                if 'suffix' in result_list or result_list is None:
                    continue
                for result in result_list['codes']:
                    try:
                        text = {
                            'code' :''
                        }
                        text['code'] = str(result['code'])
                        if text['code'] is None or text['code'] == '':
                            continue
                        document = Document(
                            text=str(text),
                            metadata=result,
                        )
                        document_list.append(document)
                    except Exception as e:
                        print(f"Error reading file : {e}")
                        continue
        return document_list
    
    def search(self, query: str,topk:int=5):
        retriever = self.index.as_retriever(similarity_top_k=topk)
        result = retriever.retrieve(query)
        return result

    def del_doc_for_path(self,path):
        metadata_dict = self.index_context.vector_stores['default'].data.metadata_dict
        del_node = []
        for key, value in metadata_dict.items():
            if value['path'] == path:
                del_node.append(key)
                print(f'delete {key}')
        for key in del_node:
            del self.index_context.vector_stores['default'].data.metadata_dict[key]
            del self.index_context.vector_stores['default'].data.embedding_dict[key]
            del self.index_context.vector_stores['default'].data.text_id_to_ref_doc_id[key]
            self.index_context.docstore.delete_document(key, raise_error=False)
        self.index = load_index_from_storage(self.index_context)
        self.index.storage_context.persist(persist_dir=self.file_dir_index)
        

        