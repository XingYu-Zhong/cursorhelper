# 技术文档：AI 驱动的开发助手

## 1. 项目概述

### 1.1 背景
本项目旨在构建一个 AI 驱动的开发助手，通过与用户进行交互式对话，协助开发者完成新项目的规划或对现有项目进行分析和优化。该助手能够理解用户需求，提出针对性问题，并最终生成开发计划，从而提高开发效率和项目规划的准确性。

### 1.2 目标
*   **新项目开发辅助**：通过多轮对话收集用户对新项目的初步想法和需求，自动生成结构化的开发计划。
*   **现有项目分析与优化**：允许用户提供 GitHub 仓库链接，助手能够解析项目结构，并结合用户提出的优化或修改需求，通过与代码库的智能问答和分析，生成相应的开发计划。
*   **提升开发效率**：减少项目初期规划和需求细化所需的人力投入。
*   **智能化交互**：利用大语言模型（LLM）提供流畅、智能的对话体验。

### 1.3 解决的问题
*   **需求模糊**：在项目启动初期，用户可能只有初步想法，难以形成清晰完整的需求文档。本助手通过引导式提问，帮助用户明确需求。
*   **信息过载**：对于大型或陌生的现有项目，开发者理解和修改代码库可能面临挑战。本助手通过与代码库的交互式问答，辅助开发者快速定位信息。
*   **重复性规划工作**：开发计划的撰写往往涉及固定模式和结构，AI 可以辅助完成这部分工作。

### 1.4 OceanBase 与 AI 技术优势
*   **AI 技术 (大语言模型)**：
    *   **自然语言理解与生成**：利用如 `qwen-plus` 和 `qwen-max` 等先进的 LLM，实现对用户输入的深度理解、智能提问以及开发计划的自动生成。
    *   **文本嵌入**：通过 `text-embedding-v3` 等模型，将文本信息（如用户需求、代码片段）转化为向量表示，为后续的语义理解和信息检索提供支持。
    *   **智能代理 (Agent)**：`QuestionAgent` 和 `PlanAgent` 的设计，使得 AI 能够有策略地进行信息收集和任务规划。
*   **OceanBase 数据库**：
    *   **高效信息检索**：在处理现有项目时，应用提示"正在通过oceanbase检索项目信息..."。这表明 OceanBase 用于存储和检索代码库的元数据、代码片段的嵌入向量。
    *   **RAG (Retrieval Augmented Generation)**：结合 OceanBase 的数据存储和检索能力与 LLM 的生成能力，可以实现对现有代码库的深度分析和智能问答。当用户询问关于现有项目的问题时，系统可以从 OceanBase 中检索相关上下文信息，辅助 LLM 生成更准确、更具针对性的回答。
    *   **可扩展性与可靠性**：对于需要处理大量项目数据或高并发用户请求的场景，OceanBase 的分布式架构能提供良好的可扩展性和数据可靠性。

## 2. 技术方案

### 2.1 技术架构
本项目采用基于 Python 的后端和 Chainlit 构建的 Web 交互界面。
*   **用户界面 (UI)**：Chainlit (`chainlit as cl`)，提供异步的、基于消息的交互。
*   **核心逻辑层**：Python。
    *   **LLM 交互模块**：`llm.api.func_get_openai.OpenaiApi` 类封装了对大语言模型（如 `qwen-plus`）的 API 调用。
    *   **核心分析模块 (`MainLab`)**：`lab.mainlab.MainLab` 类，使用 `qwen-max` 模型和 `text-embedding-v3` 嵌入模型，负责处理与项目代码库相关的分析和问答，尤其在"基于已有项目"的场景下，通过 `ml.run_lab(question, repo_path)` 实现。此模块与 OceanBase 数据库集成，用于信息检索。
    *   **智能代理 (`Agent`)**：
        *   `QuestionAgent`: 负责根据用户输入和当前对话状态，动态生成引导性问题，以收集充分的项目需求或分析点。
        *   `PlanAgent`: 负责基于 `QuestionAgent` 收集到的完整信息，生成结构化的开发计划。
    *   **工具模块 (`utils.tools`)**：
        *   `clone_repo`: 用于从 GitHub 克隆项目仓库。
        *   `get_directory_structure`: 用于解析项目的文件目录结构。
*   **数据持久化/检索**：OceanBase，用于存储项目代码分析结果、嵌入向量等，支持 `MainLab` 的信息检索功能。

### 2.2 技术栈
*   **编程语言**: Python
*   **Web 框架/UI**: Chainlit
*   **AI 模型**:
    *   大型语言模型: `qwen-plus`, `qwen-max` (通过 `OpenaiApi` 访问)
    *   文本嵌入模型: `text-embedding-v3` (通过 `MainLab` 使用)
*   **数据库 (推测)**: OceanBase
*   **版本控制**: Git (通过 `clone_repo` 功能间接使用)
*   **环境变量管理**: `python-dotenv`

### 2.3 数据处理流程

#### 2.3.1 新项目开发流程
1.  **启动与选择**：用户通过 Chainlit UI 选择"新开发项目"。
2.  **初始需求输入**：系统提示用户描述项目想法。
3.  **多轮提问 (`QuestionAgent`)**：
    *   `QuestionAgent` 初始化 ( `is_old=False`)。
    *   根据用户回复，`question_agent.get_question(user_msg)` 生成下一个问题。
    *   此过程循环，直到 `end_type` 标记提问结束。
4.  **历史信息整合**：`question_agent.get_history_str()` 获取完整的对话历史。
5.  **开发计划生成 (`PlanAgent`)**：
    *   `PlanAgent` 初始化 (`is_old=False`)。
    *   `plan_agent.get_plan(history, stream=True)` 利用 LLM 根据对话历史流式生成开发计划。
    *   计划内容通过 Chainlit 实时展示给用户。
6.  **会话状态保存**：生成的计划和系统提示词被保存到 `cl.user_session` 中，用于后续对话。

#### 2.3.2 基于已有项目流程
1.  **启动与选择**：用户选择"基于已有项目"。
2.  **仓库链接输入**：用户提供 GitHub 仓库 URL。
3.  **仓库克隆与解析**：
    *   `clone_repo(res['output'], extract_dir)` 下载仓库。
    *   `get_directory_structure(repo_path, notallow_dict)` 解析项目目录结构。
4.  **项目分析与交互 (`MainLab`, `QuestionAgent`)**:
    *   用户输入初步的优化或修改想法。
    *   `QuestionAgent` 初始化。
    *   初始用户消息会附加上项目目录结构信息。
    *   在提问循环中：
        *   `question_agent.get_question(user_msg)` 生成针对当前项目的问题。
        *   系统显示"正在通过oceanbase检索项目信息..."。
        *   `ml.run_lab(question, repo_path)` (其中 `ml` 是 `MainLab` 实例) 被调用，这是利用项目路径和当前问题，结合 OceanBase 中的数据进行检索和分析，生成上下文信息。
        *   `run_lab` 的流式输出作为 `user_msg` 输入到下一轮 `QuestionAgent` 的 `get_question` 中，或直接展示给用户。
5.  **历史信息整合**：`question_agent.get_history_str()` 获取完整的对话历史（包含项目分析的问答）。
6.  **开发计划生成 (`PlanAgent`)**：
    *   `PlanAgent` 初始化 (`is_old=True`)。
    *   `plan_agent.get_plan(history, stream=True)` 根据对话历史和项目分析结果生成开发计划。
7.  **会话状态保存**：同新项目流程。

#### 2.3.3 后续通用对话流程 (`@cl.on_message`)
1.  用户发送消息。
2.  从 `cl.user_session` 加载历史消息，并追加当前用户消息。
3.  历史消息被截断，只保留最近10条。
4.  调用 `client.stream_chat_model(message_history)` (其中 `client` 是 `OpenaiApi` 实例) 获取 LLM 的流式响应。
5.  响应流式输出给用户，并更新到消息历史中。

### 2.4 算法模型
*   **大语言模型 (LLM)**: `qwen-plus` (用于通用对话、计划生成初稿等) 和 `qwen-max` (用于 `MainLab` 中的深度分析)。这些模型负责自然语言理解、生成、推理和代码理解（在一定程度上）。
*   **文本嵌入模型**: `text-embedding-v3`。用于将文本（如用户需求、代码片段、文档）转换为高维向量。这些向量可以用于：
    *   **语义相似度计算**：找到与用户查询最相关的代码片段或文档。
    *   **RAG (Retrieval Augmented Generation)**：在 `MainLab` 与 OceanBase 交互时，用户问题可能被转换为嵌入向量，用于在 OceanBase 中存储的预处理代码嵌入中进行相似性搜索，检索到的相关上下文再提供给 LLM 以生成更准确的回答。
*   **智能代理算法**:
    *   `QuestionAgent`: 内部逻辑未展示，但其核心是通过维护对话状态和历史，迭代地向 LLM 请求生成最合适的问题，以引导对话并收集足够信息。
    *   `PlanAgent`: 接收结构化的历史信息，通过向 LLM 发出特定指令（prompt）来生成开发计划。

## 3. 实施细节

### 3.1 系统设计图
(由于文本格式限制，此处无法提供图形化系统设计图。一个典型的设计图会展示用户界面、Chainlit 服务、Python 后端各模块（如 `QuestionAgent`, `PlanAgent`, `MainLab`, `OpenaiApi`）、以及与外部服务（如 GitHub API, LLM API, OceanBase 数据库）的交互流程。)

### 3.2 关键代码片段

**LLM 客户端初始化:**
```python
# llm.api.func_get_openai.py (推测路径) 或 chainlit_web.py
client = OpenaiApi(api_key=os.getenv("OPENAI_API_KEY"), base_url=os.getenv("OPENAI_API_BASE_URL"), model='qwen-plus')
```

**MainLab 初始化 (用于代码分析):**
```python
# chainlit_web.py
# ... 在 handle_old 函数中 ...
ml = MainLab("qwen-max","text-embedding-v3")
```

**新项目 - 问题收集循环:**
```python
# chainlit_web.py
async def handle_new():
    # ...
    question_agent = QuestionAgent(max_question_times=1, is_old=False)
    end_type = 0
    user_responses = []
    
    while end_type == 0:
        user_msg = msg['output']
        user_responses.append(user_msg)
        question, end_type = question_agent.get_question(user_msg)
        if end_type == 0:
            msg = await cl.AskUserMessage(content=question).send()
    # ...
```

**现有项目 - 信息检索与问题引导:**
```python
# chainlit_web.py
async def handle_old():
    # ...
    # 获取流式输出生成器
    # question 是由 QuestionAgent 生成的
    response_generator = ml.run_lab(question, repo_path) 
    
    response_msg = cl.Message(content="检索的相关信息: ")
    await response_msg.send()
    # ...
    full_response = ""
    for token in response_generator:
        full_response += token
        await response_msg.stream_token(token)
    user_msg = full_response # 检索到的信息成为下一轮提问的输入
    # ...
```
**指示使用 OceanBase 进行检索的消息:**
```python
# chainlit_web.py
# ... 在 handle_old 函数的问题循环内 ...
t1 = cl.Message(content="正在通过oceanbase检索项目信息...")
await t1.send()
```

**计划生成:**
```python
# chainlit_web.py
# ... 在 handle_new 和 handle_old 函数的末尾 ...
plan_agent = PlanAgent(is_old=...) # 根据场景初始化
history = question_agent.get_history_str()
msg = cl.Message(content="") # 或 "# 开发计划 \n"
await msg.send()
for chunk in plan_agent.get_plan(history, stream=True):
    await msg.stream_token(chunk)
await msg.update()
```

### 3.3 关键算法说明

*   **引导式问题生成 (`QuestionAgent`)**:
    *   该代理维护对话历史。
    *   每次调用 `get_question` 时，它会向 LLM 提供当前的对话历史和用户的最新回复，并请求 LLM 生成下一个最合适的问题，以逐步澄清需求或分析点。
    *   `max_question_times` 参数可能用于限制提问轮次，避免无限循环。
    *   `is_old` 参数区分了新项目和现有项目场景，可能会导致 LLM 使用不同的提示词或策略来生成问题。

*   **RAG 结合 OceanBase**:
    *   **数据预处理**: 当克隆一个现有项目后，项目代码和相关文档被分块、计算嵌入向量，并与原文一同存储在 OceanBase 中。
    *   **检索**: 当 `ml.run_lab(question, repo_path)`被调用时：
        1.  用户的问题 (`question`) 可能被转换为嵌入向量。
        2.  使用此向量在 OceanBase 中进行相似性搜索，找出相关的代码片段或文档块。
    *   **增强生成**: 检索到的上下文信息与原始问题一起被提供给 `qwen-max` (LLM)，以生成更全面、更准确的回答或分析。这个回答随后会流式传输给用户。

*   **开发计划生成 (`PlanAgent`)**:
    *   该代理接收由 `QuestionAgent` 整理的完整对话历史/需求摘要。
    *   它使用一个特定的提示词（prompt）指导 LLM（如 `qwen-plus`）将这些信息组织成一个结构化的开发计划。
    *   计划的生成是流式的，以提供即时反馈。

## 4. 测试与验证


### 4.1 测试环境设置
*   **本地开发环境**: Python 环境，安装所有 `requirements.txt` 中列出的依赖。配置好 `OPENAI_API_KEY`, `OPENAI_API_BASE_URL` 等环境变量。需要远程的 OceanBase 实例，并配置连接参数。
*   **模拟服务**: 对于外部依赖（如 OpenAI API, GitHub），在测试时可能需要使用模拟服务（Mocks）来隔离测试单元并确保测试的确定性。

### 4.2 测试用例

#### 4.2.1 `QuestionAgent` 测试
*   **用例1 (新项目)**: 输入初步的项目想法，验证 `QuestionAgent` 是否能生成合理的、逐步深入的问题。
*   **用例2 (现有项目)**: 输入 GitHub 链接和一个修改意图，结合模拟的 `MainLab` 返回，验证 `QuestionAgent` 是否能提出与代码库相关的探究性问题。
*   **用例3 (结束条件)**: 验证在达到 `max_question_times` 或用户明确表示信息完整时，`QuestionAgent` 能否正确结束提问。

#### 4.2.2 `PlanAgent` 测试
*   **用例1 (新项目)**: 提供一份模拟的对话历史，验证 `PlanAgent` 能否生成结构清晰、内容相关的开发计划。
*   **用例2 (现有项目)**: 提供一份包含代码分析和用户需求的模拟对话历史，验证计划的针对性。

#### 4.2.3 `MainLab` 与 OceanBase 集成测试
*   **用例1 (信息检索)**: 针对预存入 OceanBase 的项目代码片段，构造查询，验证 `MainLab` 是否能准确检索到相关信息。
*   **用例2 (RAG 准确性)**: 结合 LLM，验证端到端的 RAG 流程能否针对特定代码问题给出正确答案。

#### 4.2.4 端到端流程测试
*   **新项目流程**:
    *   完整走通从选择"新开发项目"到生成最终开发计划的全过程。
    *   测试不同类型项目想法的输入，观察提问逻辑和计划质量。
*   **现有项目流程**:
    *   使用一个公开的、结构适中的 GitHub 仓库。
    *   测试克隆、目录解析功能。
    *   针对该仓库提出具体的修改或查询需求，验证问答交互和最终计划的质量。
    *   测试无效 GitHub 链接的处理。

### 4.3 测试结果 (预期)
*   **有效性**: 助手能够根据用户输入成功引导对话，并生成相关且有用的开发计划。对于现有项目，能够结合代码库信息进行有效分析。
*   **可靠性**: 在各种正常和边界输入下，系统应保持稳定，不会轻易崩溃。错误处理机制（如无效的 GitHub 链接）能按预期工作。
*   **用户体验**: Chainlit 界面交互流畅，消息传递清晰，流式输出响应及时。
