import re
import git
import os
def extract_changes_from_diff(diff_text):
    # 提取文件路径
    file_pattern = re.compile(r'diff --git a/(\S+) b/(\S+)')
    # 提取函数名称
    function_pattern = re.compile(r'^\s*def\s+(\w+)\s*\(')

    result = {}
    current_file = None

    for line in diff_text.splitlines():
        file_match = file_pattern.match(line)
        if file_match:
            current_file = file_match.group(2)
            if current_file not in result:
                result[current_file] = {'functions': []}
        elif current_file:
            function_match = function_pattern.match(line)
            if function_match:
                function_name = function_match.group(1)
                result[current_file]['functions'].append(function_name)

    return result

# def get_changed_files(file_dir, commit_hash1, commit_hash2):
#     """获取两个提交之间的改动文件列表"""
#     repo = git.Repo(file_dir)
#     diff_index = repo.commit(commit_hash1).diff(commit_hash2)
#     return [os.path.join(repo.working_tree_dir, d.b_path) for d in diff_index if d.b_path]
def get_changed_files(file_dir, commit_hash1, commit_hash2, base_dir_name="testrepo"):
    """获取两个提交之间的改动文件列表，并返回相对于base_dir_name的路径"""
    repo = git.Repo(file_dir)
    diff_index = repo.commit(commit_hash1).diff(commit_hash2)
    changed_files = []

    for d in diff_index:
        if d.b_path:
            full_path = os.path.join(repo.working_tree_dir, d.b_path)
            # 查找 base_dir_name 在路径中的位置并截断路径
            relative_path_index = full_path.find(base_dir_name)
            if relative_path_index != -1:
                relative_path = full_path[relative_path_index:]
                changed_files.append(relative_path)
    
    return changed_files

def reset_to_commit(project_path, commit_id):
    # 检查项目路径是否存在
    if not os.path.exists(project_path):
        raise ValueError(f"项目路径 {project_path} 不存在")

    # 打开Git仓库
    repo = git.Repo(project_path)
    
    # 检查输入的commit ID是否有效
    try:
        commit = repo.commit(commit_id)
    except git.exc.BadName:
        raise ValueError(f"无效的commit ID: {commit_id}")
    
    # 执行硬重置到指定的commit
    repo.git.reset('--hard', commit_id)
    print(f"项目已成功重置到commit {commit_id}")


def find_min_diff_commit(repo_path, target_commit, commit_list):
    """
    找到与目标提交之间改动最小的提交。
    """
    def get_diff_stat(repo, commit_hash1, commit_hash2):
        """
        计算两个提交之间的改动统计信息。
        返回增量和删除量的总和。
        """
        print(f"计算{commit_hash1}和{commit_hash2}之间的改动统计信息...")
        diff_index = repo.commit(commit_hash1).diff(commit_hash2)
        return sum(d.a_blob.size if d.a_blob else 0 for d in diff_index.iter_change_type('A')) + \
            sum(d.b_blob.size if d.b_blob else 0 for d in diff_index.iter_change_type('D')) + \
            sum(d.a_blob.size + d.b_blob.size for d in diff_index.iter_change_type('M') if d.a_blob and d.b_blob)
    repo = git.Repo(repo_path)
    min_diff = None
    min_diff_commit = None
    for commit in commit_list:
        diff_stat = get_diff_stat(repo, target_commit, commit)
        if min_diff is None or diff_stat < min_diff:
            min_diff = diff_stat
            min_diff_commit = commit
    return min_diff_commit, min_diff