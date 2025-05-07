

import json
import urllib.parse
import os
import zipfile
import git
import shutil

from utils.extractfile import Parser

def migrate_directory(min_commit_dir, current_commit_dir):
    # 如果目标目录不存在，则创建它
    if not os.path.exists(current_commit_dir):
        os.makedirs(current_commit_dir)
    
    # 遍历源目录中的所有项目
    for item in os.listdir(min_commit_dir):
        s = os.path.join(min_commit_dir, item)  # 源文件/目录路径
        d = os.path.join(current_commit_dir, item)  # 目标文件/目录路径
        
        # 如果是目录，使用copytree进行复制
        if os.path.isdir(s):
            shutil.copytree(s, d, dirs_exist_ok=True)
        else:
            # 如果是文件，使用copy2进行复制
            shutil.copy2(s, d)
def clone_repo(repo_url, clone_to):
    """
    克隆一个GitHub仓库。

    参数:
    repo_url (str): 原始仓库的URL。
    clone_to (str): 克隆到的本地目录。

    返回:
    str: 成功时返回克隆到的本地目录（包含子目录），不成功时返回空字符串。
    """
    try:
        if not os.path.exists(clone_to):
            os.makedirs(clone_to)

        # 从URL中提取仓库名称
        repo_name = urllib.parse.urlparse(repo_url).path.split('/')[-1]

        # 在clone_to目录下创建新的目录
        cloned_path = os.path.join(clone_to, repo_name)
        if os.path.exists(cloned_path):
            return cloned_path

        # 克隆仓库
        repo = git.Repo.clone_from(repo_url, cloned_path)
        
        print(f"Repository cloned to {cloned_path}")
        return cloned_path
    except Exception as e:
        print(f"Failed to clone repository: {e}")
        return None
def unzip_file(zip_path, extract_dir):
    """
    解压zip文件到指定目录，并在指定目录下创建一个新的目录存放解压后的文件

    参数:
    zip_path (str): zip压缩包的地址
    extract_dir (str): 指定解压的目录

    返回:
    str: 解压后的路径
    """
    if not os.path.exists(extract_dir):
        os.makedirs(extract_dir)

    base_name = os.path.basename(zip_path)
    dir_name = os.path.splitext(base_name)[0]
    new_extract_dir = os.path.join(extract_dir, dir_name)

    if not os.path.exists(new_extract_dir):
        os.makedirs(new_extract_dir)

    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(new_extract_dir)

    return new_extract_dir
def get_directory_structure(directory_path:str, notallow:set=None):
    """
    获取指定目录下的文件结构并返回为字符串格式。

    :param directory_path: str, 目录路径
    :param notallow: set, 不允许包含的文件或目录集合，默认值为None
    :return: str, 文件结构
    """
    structure = []
    notallow_dict = {'.git', '__pycache__', '.idea','.github','.tx'}

    # 如果 notallow 参数不为空，将其合并到 notallow_dict 中
    if notallow:
        notallow_dict.update(notallow)
    for root, dirs, files in os.walk(directory_path):
        # 过滤掉不需要的目录
        dirs[:] = [d for d in dirs if d not in notallow_dict]

        level = root.replace(directory_path, '').count(os.sep)
        indent = ' ' * 4 * level
        structure.append(f"{indent}{os.path.basename(root)}/")
        sub_indent = ' ' * 4 * (level + 1)
        for file in files:
            structure.append(f"{sub_indent}{file}")

    return "\n".join(structure)

def count_directory_files(directory):
    count = 0
    for root, dirs, files in os.walk(directory):
        count += len(files)
    return count

def get_split_code(file_path):
    p = Parser()
    code = p.parse(file_path)
    return code

def read_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()




def filter_path(obj):
    LANGUAGE_TAG = {
    "c++"          : "// C++",
    "cpp"          : "// C++",
    "c"            : "// C",
    "c#"           : "// C#",
    "c-sharp"      : "// C#",
    "css"          : "/* CSS */",
    "cuda"         : "// Cuda",
    "fortran"      : "! Fortran",
    "go"           : "// Go",
    "html"         : "<!-- HTML -->",
    "java"         : "// Java",
    "js"           : "// JavaScript",
    "javascript"   : "// JavaScript",
    "kotlin"       : "// Kotlin",
    "lean"         : "-- Lean",
    "lua"          : "-- Lua",
    "objectivec"  : "// Objective-C",
    "objective-c"  : "// Objective-C",
    "objective-c++": "// Objective-C++",
    "pascal"       : "// Pascal",
    "php"          : "// PHP",
    "python"       : "# Python",
    "r"            : "# R",
    "rust"         : "// Rust",
    "ruby"         : "# Ruby",
    "scala"        : "// Scala",
    "shell"        : "# Shell",
    "sql"          : "-- SQL",
    "tex"          : f"% TeX",
    "typescript"   : "// TypeScript",
    "vue"          : "<!-- Vue -->",

    "assembly"     : "; Assembly",
    "dart"         : "// Dart",
    "perl"         : "# Perl",
    "prolog"       : f"% Prolog",
    "swift"        : "// swift",
    "lisp"         : "; Lisp",
    "vb"           : "' Visual Basic",
    "visual basic" : "' Visual Basic",
    "matlab"       : f"% Matlab",
    "delphi"       : "{ Delphi }",
    "scheme"       : "; Scheme",
    "basic"        : "' Basic",
    "assembly"     : "; Assembly",
    "groovy"       : "// Groovy",
    "abap"         : "* Abap",
    "gdscript"     : "# GDScript",
    "haskell"      : "-- Haskell",
    "julia"        : "# Julia",
    "elixir"       : "# Elixir",
    "excel"        : "' Excel",
    "clojure"      : "; Clojure",
    "actionscript" : "// ActionScript",
    "solidity"     : "// Solidity",
    "powershell"   : "# PowerShell",
    "erlang"       : f"% Erlang",
    "cobol"        : "// Cobol",
    "batchfile"  : ":: Batch file",
    "makefile"     : "# Makefile",
    "dockerfile"   : "# Dockerfile",
    "markdown"     : "<!-- Markdown -->",
    "cmake"        : "# CMake",
    "dockerfile"   : "# Dockerfile",
    }

    programming_languages_to_file_extensions = json.load(open('utils/programming-languages-to-file-extensions.json'))
    need2del = []
    for key in programming_languages_to_file_extensions.keys():
        if key.lower() not in LANGUAGE_TAG:
            need2del.append(key)

    for key in need2del:
        del programming_languages_to_file_extensions[key]

    ext_to_programming_languages = {}
    want_languages = []
    for key in programming_languages_to_file_extensions:
        for item in programming_languages_to_file_extensions[key]:
            ext_to_programming_languages[item] = key
            want_languages.append(item)

    ext = '.'+obj.split('.')[-1]
    with open('utils/keep.txt', 'r') as f:
        keep_files = f.readlines()
        keep_files = [l.strip() for l in keep_files]
    #print(ext)
    if ext not in want_languages:
        if obj in keep_files:
            return True
        return False
    else:
        return True