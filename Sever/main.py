from flask import Flask, render_template
from markupsafe import Markup
import os
import json
from pathlib import Path
import markdown
from markdown.extensions.tables import TableExtension
from markdown.extensions.fenced_code import FencedCodeExtension
from markdown.extensions.toc import TocExtension

# 主题模式管理
THEME_COOKIE = 'knowledgewiki_theme'

app = Flask(__name__)

# 配置
WIKI_ROOT = os.path.join(os.path.dirname(__file__), 'Docs')
CONTENT_FILE = 'Content.json'

# 添加模板全局函数
@app.context_processor
def utility_processor():
    def render_tree(data, path=''):
        if not data or '_content' not in data:
            return Markup('')
            
        html = '<ul>'
        content = data['_content']
        meta = data.get('_meta', {})
        
        for key, value in content.items():
            if isinstance(value, dict) and 'path' in value:
                # 文件节点
                html += f'<li><a href="/view/{value["path"]}">{value["zh_CN"]}</a></li>'
            elif isinstance(value, dict):
                # 目录节点
                dir_name = value.get('_meta', {}).get('zh_CN', key)
                html += f'<li>{dir_name}'
                html += render_tree(value, os.path.join(path, key))
                html += '</li>'
        html += '</ul>'
        return Markup(html)
    
    return dict(render_tree=render_tree)

@app.route('/')
def index():
    # 生成或读取目录结构
    content = generate_or_load_content()
    return render_template('index.html', content=content)



def generate_or_load_content():
    """
    生成或加载Content.json文件
    """
    if not os.path.exists(CONTENT_FILE):
        content = scan_directory(WIKI_ROOT)
        with open(CONTENT_FILE, 'w', encoding='utf-8') as f:
            json.dump(content, f, indent=2, ensure_ascii=False)
        return content
    else:
        with open(CONTENT_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)

def scan_directory(root_path, parent_key='/'):
    """
    递归扫描目录结构，生成符合要求的Content.json格式
    """
    result = {}
    settings_path = os.path.join(root_path, 'settings.json')
    
    # 读取目录设置
    dir_settings = {'zh_CN': Path(root_path).name, 'en_US': Path(root_path).name}
    if os.path.exists(settings_path):
        try:
            with open(settings_path, 'r', encoding='utf-8') as f:
                dir_settings.update(json.load(f))
        except:
            pass
    
    for item in Path(root_path).iterdir():
        if item.name == 'settings.json':
            continue
            
        if item.is_dir():
            # 处理子目录
            sub_result = scan_directory(item, os.path.join(parent_key, item.name))
            if sub_result:
                result[item.name] = sub_result
        elif item.suffix == '.md':
            # 处理markdown文件
            zh_title = item.stem
            try:
                with open(item, 'r', encoding='utf-8') as f:
                    first_line = f.readline().strip()
                    if first_line.startswith('# '):
                        zh_title = first_line[2:]
            except:
                pass
            
            result[item.stem] = {
                'zh_CN': zh_title,
                'en_US': item.stem,
                'path': str(item.relative_to(WIKI_ROOT))
            }
    
    # 添加目录设置信息
    if dir_settings['zh_CN'] or result:
        return {
            '_meta': dir_settings,
            '_content': result
        }
    return None

@app.route('/view/<path:filepath>')
def view_file(filepath):
    # 渲染markdown文件
    full_path = os.path.normpath(os.path.join(WIKI_ROOT, filepath))
    if not os.path.exists(full_path):
        return "File not found", 404
    
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        with open(full_path, 'r', encoding='gbk') as f:
            content = f.read()
    
    # 转换markdown为HTML
    md = markdown.Markdown(extensions=[
        'extra',
        'codehilite',
        TableExtension(),
        FencedCodeExtension(),
        TocExtension(),
        'admonition',
        'nl2br'
    ])
    html_content = md.convert(content)
    
    # 添加MathJax支持
    mathjax_script = '''
    <script>
    MathJax = {
        tex: {
            inlineMath: [['$', '$'], ['\\(', '\\)']]
        }
    };
    </script>
    <script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
    '''
    
    return render_template('view.html', content=html_content + mathjax_script)

if __name__ == '__main__':
    app.run(debug=True)
