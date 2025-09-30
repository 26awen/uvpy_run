import os
from flask import Flask, request
from flask import send_from_directory
from flask import render_template_string, render_template

from dotenv import load_dotenv

_ = load_dotenv()

FLASK_SECRET = os.environ.get("FLASK_SECRET")
FORCE_HTTPS = os.environ.get("FORCE_HTTPS", "false").lower() == "true"


STATIC_PYFILES_ROOT = "./static_pyfiles/"
STATIC_TEXTBASEDFILES_ROOT = "./static_textbasedfiles/"
DEBUG_HOST = "0.0.0.0"
DEBUG_PORT = 9999

app = Flask(__name__)
app.secret_key = FLASK_SECRET


@app.after_request
def add_security_headers(response):
    """Add security headers to all responses"""
    # Content Security Policy
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "font-src 'self'; "
        "connect-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    )
    
    # Other security headers
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    
    # HSTS for HTTPS (only add if using HTTPS)
    if request.is_secure or request.headers.get('X-Forwarded-Proto') == 'https':
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    
    return response


def get_base_url():
    """
    动态获取基础URL，根据环境自动选择HTTP或HTTPS
    在调试环境使用HTTP，生产环境或未知域名时使用HTTPS
    """
    # 如果强制使用HTTPS
    if FORCE_HTTPS:
        protocol = 'https'
    # 检查是否在调试模式且是本地地址
    elif app.debug and request.host.startswith(('localhost', '127.0.0.1', '0.0.0.0')):
        protocol = 'http'
    else:
        # 检查请求头中的协议信息（代理服务器设置）
        if request.headers.get('X-Forwarded-Proto') == 'https':
            protocol = 'https'
        elif request.headers.get('X-Forwarded-Ssl') == 'on':
            protocol = 'https'
        elif request.is_secure:
            protocol = 'https'
        else:
            # 默认使用HTTPS，特别是对于未知域名
            protocol = 'https'
    
    return f"{protocol}://{request.host}"


html_file_not_found = f"""
<html>
<head><title>文件未找到</title></head>
<body>
    <h1>404 - 文件未找到</h1>
    <p>抱歉，您请求的文件不存在。</p>
</body>
</html>
"""


@app.route("/<filename>")
def server_pyfiles(filename: str):
    try:
        return send_from_directory(STATIC_PYFILES_ROOT, filename)
    except FileNotFoundError:
        return render_template_string(html_file_not_found)


# @app.route("/text/<filename>")
# def server_textbasedfiles(filename: str):
#     return send_from_directory(STATIC_TEXTBASEDFILES_ROOT, filename)

@app.route("/static/<filename>")
def serve_static_files(filename: str):
    """Serve static files like icons, CSS, JS, etc."""
    return send_from_directory("./static/", filename)


@app.route("/robots.txt")
def robots_txt():
    """Serve robots.txt file"""
    return send_from_directory(".", "robots.txt")


@app.route("/sitemap.xml")
def sitemap_xml():
    """Serve sitemap.xml file"""
    return send_from_directory(".", "sitemap.xml")

@app.route("/detail/<script_name>")
def script_detail(script_name):
    """Show detailed information about a specific script."""
    try:
        # Ensure script_name ends with .py
        if not script_name.endswith('.py'):
            script_name += '.py'
        
        file_path = os.path.join(STATIC_PYFILES_ROOT, script_name)
        
        # Check if file exists
        if not os.path.exists(file_path):
            return render_template_string(html_file_not_found), 404
        
        # Extract detailed information from the file
        file_info = extract_detailed_file_info(file_path)
        
        # Get the base URL with correct protocol
        base_url = get_base_url()
        
        # Use detail template
        return render_template('script_detail.html',
                             script_info=file_info,
                             base_url=base_url,
                             script_name=script_name)
        
    except Exception as e:
        error_html = f"""
        <html>
        <head><title>Error</title></head>
        <body>
            <h1>Error loading script details</h1>
            <p>An error occurred while loading script details: {str(e)}</p>
        </body>
        </html>
        """
        return render_template_string(error_html), 500


@app.route("/")
def list_tools():
    """List all available Python tools in the static_pyfiles directory."""
    try:
        # Get all Python files from the static_pyfiles directory
        py_files = []
        if os.path.exists(STATIC_PYFILES_ROOT):
            for filename in os.listdir(STATIC_PYFILES_ROOT):
                if filename.endswith('.py'):
                    file_path = os.path.join(STATIC_PYFILES_ROOT, filename)
                    
                    # Extract structured information from the file
                    file_info = extract_file_info(file_path)
                    
                    py_files.append({
                        'filename': filename,
                        'description': file_info['description'],
                        'version': file_info['version'],
                        'category': file_info['category'],
                        'author': file_info['author'],
                        'url': f'/{filename}',
                        'detail_url': f'/detail/{filename.replace(".py", "")}'
                    })
        
        # Sort files alphabetically
        py_files.sort(key=lambda x: x['filename'])
        
        # Get the base URL with correct protocol
        base_url = get_base_url()
        
        # Use external HTML template with base_url context
        return render_template('list_tools.html', tools=py_files, base_url=base_url)
        
    except Exception as e:
        error_html = f"""
        <html>
        <head><title>Error</title></head>
        <body>
            <h1>Error listing tools</h1>
            <p>An error occurred while listing the available tools: {str(e)}</p>
        </body>
        </html>
        """
        return render_template_string(error_html), 500


def extract_detailed_file_info(file_path):
    """Extract detailed information from Python file including usage examples, dependencies, and full content."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        info = {
            'filename': os.path.basename(file_path),
            'title': 'N/A',
            'description': 'N/A',
            'version': 'N/A',
            'category': 'N/A',
            'author': 'N/A',
            'dependencies': [],
            'usage_examples': [],
            'full_docstring': '',
            'source_lines': len(content.split('\n'))
        }
        
        lines = content.split('\n')
        
        # Extract PEP 723 dependencies
        in_script_block = False
        for line in lines:
            stripped = line.strip()
            if stripped == '# /// script':
                in_script_block = True
                continue
            elif stripped == '# ///':
                in_script_block = False
                continue
            elif in_script_block:
                if stripped.startswith('# dependencies = ['):
                    # Extract dependencies from the list
                    deps_line = stripped.replace('# dependencies = [', '').replace(']', '')
                    if deps_line.strip():
                        # Parse the dependencies
                        import re
                        deps = re.findall(r'"([^"]*)"', deps_line)
                        info['dependencies'] = deps
        
        # Extract docstring information
        in_docstring = False
        docstring_lines = []
        
        for line in lines:
            stripped = line.strip()
            
            if '"""' in stripped and not in_docstring:
                in_docstring = True
                if stripped.count('"""') == 2:
                    # Single line docstring
                    docstring_content = stripped.split('"""')[1].strip()
                    if docstring_content:
                        info['title'] = docstring_content
                        info['description'] = docstring_content[:100] + ('...' if len(docstring_content) > 100 else '')
                        info['full_docstring'] = docstring_content
                    in_docstring = False
                else:
                    # Multi-line docstring start
                    after_quotes = stripped.split('"""', 1)[1].strip()
                    if after_quotes:
                        docstring_lines.append(after_quotes)
                continue
            
            if in_docstring:
                if '"""' in stripped:
                    # End of docstring
                    before_quotes = stripped.split('"""')[0].strip()
                    if before_quotes:
                        docstring_lines.append(before_quotes)
                    break
                else:
                    if stripped:
                        docstring_lines.append(stripped)
        
        if docstring_lines:
            full_docstring = '\n'.join(docstring_lines)
            info['full_docstring'] = full_docstring
            
            # Extract first line as title
            if docstring_lines:
                info['title'] = docstring_lines[0].strip()
                info['description'] = info['title'][:100] + ('...' if len(info['title']) > 100 else '')
            
            # Extract metadata fields and usage examples
            collecting_examples = False
            for line in docstring_lines:
                line = line.strip()
                if line.startswith('Version:'):
                    info['version'] = line.split('Version:', 1)[1].strip()
                elif line.startswith('Category:'):
                    info['category'] = line.split('Category:', 1)[1].strip()
                elif line.startswith('Author:'):
                    info['author'] = line.split('Author:', 1)[1].strip()
                elif line.startswith('Usage Examples:') or line.startswith('Examples:'):
                    collecting_examples = True
                    continue
                elif collecting_examples and line.strip().startswith('uv run '):
                    info['usage_examples'].append(line.strip())
        
        # Also look for usage examples in comments
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('#') and ('uv run ' in stripped or 'python ' in stripped):
                example = stripped[1:].strip()
                if example not in info['usage_examples']:
                    info['usage_examples'].append(example)
        
        # Set defaults if not found
        if info['title'] == 'N/A':
            info['title'] = f"Python Script: {info['filename']}"
        if info['description'] == 'N/A':
            info['description'] = f"Python utility script: {info['filename']}"
        
        return info
        
    except Exception as e:
        return {
            'filename': os.path.basename(file_path),
            'title': f"Python Script: {os.path.basename(file_path)}",
            'description': f"Python utility script: {os.path.basename(file_path)}",
            'version': 'N/A',
            'category': 'N/A',
            'author': 'N/A',
            'dependencies': [],
            'usage_examples': [],
            'full_docstring': f'Error reading file: {str(e)}',
            'source_lines': 0
        }


def extract_file_info(file_path):
    """Extract structured information from Python file docstring."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Try to extract from module docstring
        lines = content.split('\n')
        in_docstring = False
        docstring_lines = []
        
        for line in lines:
            stripped = line.strip()
            
            # Check for triple quote docstring
            if '"""' in stripped and not in_docstring:
                in_docstring = True
                # Handle single line docstring
                if stripped.count('"""') == 2:
                    docstring_content = stripped.split('"""')[1].strip()
                    if docstring_content:
                        return {
                            'description': docstring_content[:80] + ('...' if len(docstring_content) > 80 else ''),
                            'version': 'N/A',
                            'category': 'N/A',
                            'author': 'N/A'
                        }
                    in_docstring = False
                else:
                    # Multi-line docstring start
                    after_quotes = stripped.split('"""', 1)[1].strip()
                    if after_quotes:
                        docstring_lines.append(after_quotes)
                continue
            
            if in_docstring:
                if '"""' in stripped:
                    # End of docstring
                    before_quotes = stripped.split('"""')[0].strip()
                    if before_quotes:
                        docstring_lines.append(before_quotes)
                    break
                else:
                    if stripped:
                        docstring_lines.append(stripped)
        
        if docstring_lines:
            # Extract structured information
            info = {
                'description': 'N/A',
                'version': 'N/A',
                'category': 'N/A',
                'author': 'N/A'
            }
            
            # Extract the first line as the main description
            if docstring_lines:
                title = docstring_lines[0].strip()
                if len(title) > 80:
                    title = title[:77] + "..."
                info['description'] = title
            
            # Extract metadata fields
            for line in docstring_lines:
                line = line.strip()
                if line.startswith('Version:'):
                    info['version'] = line.split('Version:', 1)[1].strip()
                elif line.startswith('Category:'):
                    info['category'] = line.split('Category:', 1)[1].strip()
                elif line.startswith('Author:'):
                    info['author'] = line.split('Author:', 1)[1].strip()
            
            return info
        
        # Fallback: look for comment-based description
        for line in lines[:20]:  # Check first 20 lines
            stripped = line.strip()
            if stripped.startswith('#') and len(stripped) > 2:
                comment = stripped[1:].strip()
                if len(comment) > 10 and not comment.startswith('///'):
                    # Truncate if too long
                    if len(comment) > 80:
                        comment = comment[:77] + "..."
                    return {
                        'description': comment,
                        'version': 'N/A',
                        'category': 'N/A',
                        'author': 'N/A'
                    }
        
        # Default description based on filename
        filename = os.path.basename(file_path)
        default_descriptions = {
            'demo.py': "Demo script for testing remote execution",
            'flask_secret.py': "Generate secure secret keys for Flask applications",
            'passwordgen.py': "Generate secure passwords with customizable options",
            'cld.py': "Beautiful calendar printer with highlighting features",
            'imgtr.py': "Image processing tool with various operations",
            'imgtrans.py': "Image conversion and compression utility",
            'qr.py': "QR code generator with customizable styles"
        }
        
        return {
            'description': default_descriptions.get(filename, f"Python utility script: {filename}"),
            'version': 'N/A',
            'category': 'N/A',
            'author': 'N/A'
        }
            
    except Exception:
        return {
            'description': f"Python script: {os.path.basename(file_path)}",
            'version': 'N/A',
            'category': 'N/A',
            'author': 'N/A'
        }


if __name__ == "__main__":
    # 添加配置以支持代理后的HTTPS检测
    app.config['PREFERRED_URL_SCHEME'] = 'https'
    app.run(debug=True, host=DEBUG_HOST, port=DEBUG_PORT)
