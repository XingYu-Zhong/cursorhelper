# coding: utf8
from tree_sitter_languages import get_parser
import re
import os
import hashlib
import chardet


SKIP_NODE_TYPE = {
    'variable',
    'scoped_identifier',
    'modifiers',
    'attribute',
    'binary_operator',
    'expression_list',

    'parameters',
    'comparison_operator',
    'type_list',
    'declaration',
    'set',
    'named_expression',
    'unary_operator',
    'call',

    # class_declaration 块已经定了整个 class 的所有 text 了
    'class_body',
    'super_interfaces',
    'function_declarator',
    'dotted_name',

    # 变量
    'parameter_list',
    'parameter_declaration',
    'pointer_declarator',

    'field_declaration',
    'variable_declarator',

    'binary_expression',
    'if_statement',

    'update_expression',
    'assignment_expression'
    'subscript_expression',

    'field_expression',
    'field_declaration_list',
    'argument_list',

    'type_qualifier',       # const 关键字
    'storage_class_specifier',

    'sized_type_specifier',  # 类型长度
    'integral_type',
    'char_literal',
    'ERROR',
    'return_statement',
    'expression_statement',
    'labeled_statement',

    'init_declarator',
    'string_literal',
    'initializer_pair',
    'field_designator'
}

LANG_MAP = {
    'java': 'java',
    'py': 'python',
    'go': 'go',
    'c': 'c',
    'cc': 'cpp',
    'lua': 'lua',
    'cpp': 'cpp',
    'h': 'c',
    'js': 'javascript',
    'jsx': 'javascript',
    'ts': 'typescript',
    'tsx': 'typescript',
    'lpc': 'c',
    'kt': 'kotlin'

}

FUNC_BODY_FLAG = {
    'function_declaration',
    'class_definition',
    'definition',
    'method_declaration',
    'class_declaration',
    'function_definition',
}


def check_encoding_method(file_path):
    with open(file_path, 'rb') as f:
        data = f.read()
        return chardet.detect(data)['encoding']


class Parser(object):
    def __init__(self):
        self.parsers = {}

    def get_decode_text(self, text):

        for decode_type in ['utf8', 'gb18030', 'gbk', 'gb2312']:
            try:
                return text.decode(decode_type)
            except UnicodeDecodeError:
                print(f'text {decode_type} 解码失败')

    def get_file_content(self, file_path):
        try:
            file_encoding = check_encoding_method(file_path)
            with open(file_path, "r", encoding=file_encoding) as f:
                code = f.read()
        except Exception as ex:
            print(
                f"{file_path}: can not read code {ex}, try gb18030")
            try:
                with open(file_path, "r", encoding="gb18030") as f:
                    code = f.read()
            except Exception as ex:
                print(f"{file_path}: can not read code {ex}")
                return ""
        return code

    def get_valid_lang(self, file_path):
        suffix = file_path.split('.')[-1]
        lang = LANG_MAP.get(suffix)
        return lang, suffix

    def get_lang_list(self):
        return LANG_MAP.keys()

    def parse(self, file_path, code=""):
        """
        返回：
        {
            'lang': lang,
            'classes':  [{
                'name': 'Main',
                'desc': 'xxx',
                'code': 'class Main(): xxx',
                'methods':[{
                    'name': 'test()',
                    'comment': '测试函数',
                    'code': 'def test(): ...',
                    'extral_info': '# add_method()方法'
                }]
            }],
            'functions': [{
                'name': 'test()',
                'comment': '测试函数',
                'code': 'def test(): ...',
                'extral_info': '# add_method()方法'
            }]
        }
        """
        lang, suffix = self.get_valid_lang(file_path)
        if not lang:
            print('unsupported language, file suffix: %s' % suffix)
            return {
            'suffix':suffix,
        }

        if lang not in self.parsers:
            # 根据语言创建解析器
            # print('create parser for %s' % lang)
            parser = get_parser(lang)
            self.parsers[lang] = parser

        else:
            parser = self.parsers[lang]

        if not code:
            code = bytes(self.get_file_content(file_path), "utf8")

        if os.path.basename(file_path) == 'GMCommandData.py':
            return {
                'lang': lang,
                'codes': self.g108_gm_parse(code),
                'subset': '',
            }

        tree = parser.parse(code)
        subset = ''
        if lang not in ['javascript', 'typescript']:
            codes, subset = self.build_snippet(tree.root_node, file_path)
        else:
            codes = self.build_front_snippet(
                tree.root_node.named_children, file_path)
            if suffix == 'jsx':
                lang = 'javascript-react'
            elif suffix == 'tsx':
                lang = 'typescript-react'

        return {
            'lang': lang,
            'codes': codes,
            'subset': subset
        }

    def generate_md5(self, text):
        m = hashlib.md5()
        m.update(text.encode('utf-8'))
        return m.hexdigest()

    def _build_front_snippet(self, nodes, file_path, class_name='', comment='', identifier=''):
        functions = []

        for n in nodes:
            # 将注释向下补充到代码块上，增强代码解析准确度
            if 'comment' in n.type:
                comment += self.get_decode_text(n.text) + '\n'
                continue

            # # 常量定义，可能出现箭头函数定义
            # if n.type == 'lexical_declaration':
            #     self._build_front_snippet([n.named_children], file_path)
            #     continue

            # # 变量定义，可能出现箭头函数定义
            # if n.type == 'variable_declarator':
            #     self.build_front_snippet([n.named_children], file_path)
            #     continue

            # arrow_function, function_declaration
            if n.type not in ['function_declaration', 'arrow_function', 'method_definition']:
                comment = ''
                continue

            # 箭头函数需要处理函数名，将变量名设为其函数名
            # function 一般最后的元素为 block，代表函数体
            texts = []
            args = ''
            if n.type == 'arrow_function':
                texts.append(identifier)

            for _n in n.named_children[:-1]:
                content = self.get_decode_text(_n.text)
                if _n.type == 'comment':
                    comment += content + '\n'
                    continue
                if _n.type in ['parameter_list', 'parameters', 'formal_parameters']:
                    args = content
                    continue

                texts.append(content)

            func_name = ' '.join(texts)
            name = re.sub(r'\([^)]*\)|[#-/].*', '', func_name).strip()

            # n 表示完整的代码区域
            code = self.get_decode_text(n.text)

            key_msgs = []
            if comment:
                key_msgs.append(comment)
            key_msgs.append(os.path.basename(file_path))

            function = {
                'type': 'function',
                'path': file_path,
                'name': name,
                'func_name': func_name,
                'args': args,
                'class_name': class_name,
                'key_msg': ' '.join(set(' '.join(key_msgs).split())),
                'comment': comment,
                'code': comment + code,
                'md5': self.generate_md5(file_path+class_name+code),
            }
            functions.append(function)
            comment = ''

        return functions

    def build_front_snippet(self, nodes, file_path, parent_node_type='', identifier=''):
        codes = []
        comment = ''
        exports = []
        for node in nodes:
            node_type = node.type
            # print(f'start from: {node_type}')
            if node_type == 'comment':
                comment += self.get_decode_text(node.text) + '\n'
                continue

            if node_type == 'identifier':
                continue

            # 函数包裹在 export 语句里
            if node_type == 'export_statement':
                # print(f'export_statement children: {node.named_children}')
                # 解析下一层
                codes.extend(self.build_front_snippet(
                    node.named_children, file_path, node_type))

                # 记录导出清单，便于补全引用
                exports.append(self.get_decode_text(node.text))

            # 常量定义，可能出现箭头函数定义
            if node_type == 'lexical_declaration':
                # print(f'lexical_declaration node: {node}, children: {node.named_children}')
                codes.extend(self.build_front_snippet(
                    node.named_children, file_path))

            # 变量定义，可能出现箭头函数定义
            if node_type == 'variable_declarator':
                codes.extend(self.build_front_snippet(
                    node.named_children,
                    file_path,
                    identifier=self.get_decode_text(node.named_children[0].text)))

            # 出现函数的 function_declaration/arrow_function
            if node_type in ['function_declaration', 'arrow_function']:
                # 这层arrow function 无实际意义
                if parent_node_type == 'export_statement':
                    # print(f'parent is export_statement, {node_type} children: {node.named_children}')
                    codes.extend(self.build_front_snippet(
                        node.named_children[-1].named_children, file_path, parent_node_type=node_type))
                else:
                    # print(f'{node_type} node: {node}, children: {node.named_children}')
                    # 提取函数
                    codes.extend(self._build_front_snippet(
                        [node], file_path, comment=comment, identifier=identifier))

            if node_type == 'class_definition':
                class_definition = ' '.join(self.get_decode_text(
                    n.text) for n in node.named_children[:-1])
                class_code = self.get_decode_text(node.text)
                methods = self._build_func_snippet(
                    node.named_children[-1].named_children,
                    file_path,
                    class_name=class_definition,
                    comment=comment
                )
                for m in methods:
                    m['class_code'] = class_code
                    codes.append(m)

            comment = ''

        return codes

    def build_snippet(self, nodes, file_path):
        """
        返回 :
        [{
            'type': 'class'
            'name': 'Main',
            'comment': '',
            'path': 'main/test.py',
            'code': 'class Main(): xxx',
            'methods':[{
                'name': 'test()',
                'comment': '测试函数',
                'code': 'def test(): ...',
                'extral_info': '# add_method()方法'
            }]
        },
        {
            'type': 'function'
            'name': 'test()',
            'comment': '测试函数',
            'code': 'def test(): ...',
            'extral_info': '# add_method()方法'
        }]

        """

        codes = []
        comment = ''
        subset = ''
        for node in nodes.named_children:
            node_type = node.type
            if node_type == 'ERROR':
                # print(f'ERROR: {node}')
                continue
            if node_type == 'package_declaration':
                pattern = r"package\s(.+);"
                match = re.search(pattern, str(node.text))
                if match:
                    subset = match.group(1)
                else:
                    subset = node.text
            if node_type == 'comment':
                comment += self.get_decode_text(node.text) + '\n'
                continue

            if node_type == 'decorated_definition':
                codes.extend(self._build_func_snippet(
                    [node], file_path, comment=comment))

            elif node_type.startswith('class') or node_type == 'object_declaration':
                class_definition = ' '.join(
                    self.get_decode_text(n.text) for n in node.named_children[:-1])
                class_code = self.get_decode_text(node.text)
                methods = self._build_func_snippet(
                    node.named_children[-1].named_children,
                    file_path,
                    class_name=class_definition,
                    comment=comment
                )
                for m in methods:
                    m['class_code'] = class_code
                    codes.append(m)

            elif node_type.startswith('function'):
                codes.extend(self._build_func_snippet(
                    [node], file_path, comment=comment))

            elif node_type == 'export_statement':
                codes.extend(self._build_func_snippet(
                    [node], file_path, comment=comment))
            comment = ''

            if len(codes) > 4000:
                print(f'{file_path} 解析函数数量过多，超过4000个, 先退出')
                break

        return codes, subset

    def _build_func_snippet(self, nodes, file_path, class_name='', decorator='', comment=''):
        """
        切分函数粒度的分片，返回 

        functions = [{
            'name': 'test()',
            'comment': '测试函数',
            'code': 'def test(): ...',
            'extral_info': '# add_method()方法'
        }]
        """
        functions = []

        if decorator:
            decorator += '\n'
        for n in nodes:
            if n.type == 'decorated_definition':
                functions.extend(self._build_func_snippet(
                    [n.named_children[-1]],
                    file_path,
                    class_name=class_name,
                    decorator='\n'.join(
                        self.get_decode_text(n.text) for n in n.named_children[:-1])
                ))
                continue

            # 将注释向下补充到代码块上，增强代码解析准确度
            if 'comment' in n.type:
                comment += self.get_decode_text(n.text) + '\n'
                continue

            if not n.type.startswith(('function', 'method', 'class_body')):
                comment = ''
                continue

            # 函数定义部分切分，其中最后的元素一般为 block，代表函数体
            texts = []
            args = []

            r = 0
            while r < len(n.named_children)-1:
                _n = n.named_children[r]
                content = self.get_decode_text(_n.text)
                if _n.type == 'comment':
                    comment += content + '\n'
                    r += 1
                    continue

                # 处理参数列表
                if 'parameter' in _n.type:
                    __n = n.named_children[r+1]
                    if 'parameter' not in __n.type and 'block' not in __n.type:
                        r += 1
                        content = f'{content}=' + \
                            self.get_decode_text(__n.text)
                    args.append(content)
                else:
                    texts.append(content)
                r += 1

            func_name = ' '.join(texts)
            name = re.sub(r'\([^)]*\)|[#-/].*', '', func_name).strip()

            # n 表示完整的代码区域
            code = decorator + self.get_decode_text(n.text)

            # 提取代码区域内的中文字符
            key_msgs = re.findall('([\u4e00-\u9fa5]\w*)', code)

            if comment:
                key_msgs.append(comment)
            key_msgs.append(os.path.basename(file_path))
            functions.append({
                'type': 'function',
                'path': file_path,
                'name': name,
                'func_name': decorator+func_name,
                'args': ','.join(args),
                'class_name': class_name,
                'key_msg': ' '.join(set(' '.join(key_msgs).split())),
                'comment': comment,
                'code': comment + code,
                'md5': self.generate_md5(file_path+class_name+code),
            })
            comment = ''
            decorator = ''

        return functions

    def g108_gm_parse(self, str_content):
        """
        Data = TD({
            "Jump to [empty test scene](Goto 9906)2": TD({
                "name": "Jump to [empty test scene](Goto 9906)2",
                "cmdName": ZH_STR("前往 9906", "TID_CA.GMCommandData.Jump to [empty test scene](Goto 9906)2.cmdName"),
                "contextTag": "GM Panel",
                "GMType": 1,
                "subType": "Hot",
                "tabType": 1,
                "desc": ZH_STR("跳转至[测试空场景](Goto 9906 )", "TID_CA.GMCommandData.Jump to [empty test scene](Goto 9906)2.desc"),
                "successResult": "Goto scene success",
                "cmd": "$goto",
                "paramDesc1": "dungeon no",
                "paramDefault1": 9906,
                "priority": 1,
            }),
            ...
        })
        """
        targets = re.findall(
            '("[^"]+": TD\({[^}]+})\)', str_content, re.MULTILINE | re.DOTALL)

        result = []
        for t in targets:
            key_msg = ' '.join(re.findall('([\u4e00-\u9fa5]\w*)', t))
            name = re.findall('"name": (.*),', t)[0]
            cmd = re.findall('"cmdName": (.*),', t)
            desc = re.findall('"desc": (.*),', t)
            result.append({
                'type': '',
                'name': name,
                'func_name': name,
                'comment': '',
                'class_name': '',
                'key_msg': ' '.join(desc + cmd) + key_msg,
                'code': t,
                'md5': self.generate_md5(t),
            })
        return result


# if __name__ == '__main__':
#     p = Parser()
#     # filepath = "/Users/eve/work/dev/scripts/code_test/cs/js/mds_Affix_demo.jsx"
#     # filepath = "/Users/eve/work/dev/scripts/code_test/cs/ts/Field.tsx"
#     # filepath = "/Users/eve/work/dev/scripts/code_test/cs/ts/SchemaField.tsx"
#     filepath = "/Users/xingyu/Desktop/codeproject/RepoAgent/tests/test_openai.py"
#     t = p.parse(filepath)
#     print(t)
