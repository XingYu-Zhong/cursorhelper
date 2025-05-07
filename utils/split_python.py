import ast  
import os   
import libcst as cst
import libcst.matchers as m
from libcst.display import dump


class GlobalVariableVisitor(cst.CSTVisitor):
    METADATA_DEPENDENCIES = (cst.metadata.PositionProvider,)

    def __init__(self):
        self.global_assigns = []

    def leave_Module(self, original_node: cst.Module) -> list:
        assigns = []
        for stmt in original_node.body:
            if m.matches(stmt, m.SimpleStatementLine()) and m.matches(
                stmt.body[0], m.Assign()
            ):
                start_pos = self.get_metadata(cst.metadata.PositionProvider, stmt).start
                end_pos = self.get_metadata(cst.metadata.PositionProvider, stmt).end
                assigns.append([stmt, start_pos, end_pos])
        self.global_assigns.extend(assigns)


def parse_global_var_from_code(file_content: str) -> dict[str, dict]:
    """Parse global variables."""
    try:
        tree = cst.parse_module(file_content)
    except:
        return file_content

    wrapper = cst.metadata.MetadataWrapper(tree)
    visitor = GlobalVariableVisitor()
    wrapper.visit(visitor)

    global_assigns = {}
    for assign_stmt, start_pos, end_pos in visitor.global_assigns:
        for t in assign_stmt.body:
            try:
                targets = [t.targets[0].target.value]
            except:
                try:
                    targets = t.targets[0].target.elements
                    targets = [x.value.value for x in targets]
                except:
                    targets = []
            for target_var in targets:
                global_assigns[target_var] = {
                    "start_line": start_pos.line,
                    "end_line": end_pos.line,
                }
    return global_assigns

def parse_python_file(file_path, file_content=None):
    """解析一个Python文件，提取类和函数定义以及它们的行号。
    :param file_path: Python文件的路径。
    :return: 类名、函数名以及文件内容
    """
    if file_content is None:
        try:
            with open(file_path, "r") as file:
                file_content = file.read()
                parsed_data = ast.parse(file_content)
        except Exception as e:  # 捕获所有类型的异常
            print(f"文件 {file_path} 解析错误: {e}")
            return [], [], ""
    else:
        try:
            parsed_data = ast.parse(file_content)
        except Exception as e:  # 捕获所有类型的异常
            print(f"文件 {file_path} 解析错误: {e}")
            return [], [], ""

    class_info = []
    function_names = []
    class_methods = set()
    global_var = parse_global_var_from_code(file_content)
    for node in ast.walk(parsed_data):
        if isinstance(node, ast.ClassDef):
            methods = []
            for n in node.body:
                if isinstance(n, ast.FunctionDef):
                    methods.append(
                        {
                            "name": n.name,
                            "start_line": n.lineno,
                            "end_line": n.end_lineno,
                            "text": file_content.splitlines()[
                                n.lineno - 1 : n.end_lineno
                            ],
                        }
                    )
                    class_methods.add(n.name)
            class_info.append(
                {
                    "name": node.name,
                    "start_line": node.lineno,
                    "end_line": node.end_lineno,
                    "text": file_content.splitlines()[
                        node.lineno - 1 : node.end_lineno
                    ],
                    "methods": methods,
                }
            )
        elif isinstance(node, ast.FunctionDef) and not isinstance(
            node, ast.AsyncFunctionDef
        ):
            if node.name not in class_methods:
                function_names.append(
                    {
                        "name": node.name,
                        "start_line": node.lineno,
                        "end_line": node.end_lineno,
                        "text": file_content.splitlines()[
                            node.lineno - 1 : node.end_lineno
                        ],
                    }
                )
        file_spilt = file_content.splitlines()
        global_var_list=[]
        for var_name,lines_num in global_var.items():
            var_info = {}
            start_line = lines_num['start_line']
            end_line = lines_num['end_line']
            text = file_spilt[start_line-1:end_line-1]
            var_info['name'] = var_name
            var_info['start_line'] = start_line
            var_info['end_line'] = end_line
            var_info['text'] = text
            global_var_list.append(var_info)
    return class_info, function_names, file_spilt,global_var_list
