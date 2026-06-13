import os
from xml.sax.saxutils import escape

from flask import Flask, Response, request
from flask import send_from_directory
from flask import render_template_string, render_template

from dotenv import load_dotenv
from tool_metadata import build_remote_usage_examples, parse_tool_metadata

_ = load_dotenv()

FLASK_SECRET = os.environ.get("FLASK_SECRET")
FORCE_HTTPS = os.environ.get("FORCE_HTTPS", "false").lower() == "true"


STATIC_PYFILES_ROOT = "./static_pyfiles/"
STATIC_TEXTBASEDFILES_ROOT = "./static_textbasedfiles/"
DEBUG_HOST = "0.0.0.0"
DEBUG_PORT = 9999
OPEN_SOURCE_URL = "https://github.com/26awen/uvpy_run"
CANONICAL_BASE_URL = os.environ.get(
    "CANONICAL_BASE_URL",
    "https://uvpy.run",
).rstrip("/")

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


def get_canonical_url(path=None):
    """Build the preferred public URL for SEO metadata."""
    return f"{CANONICAL_BASE_URL}{path or request.path}"


def iter_public_python_tools():
    """Yield public Python tool filenames and filesystem paths."""
    if not os.path.exists(STATIC_PYFILES_ROOT):
        return

    for filename in sorted(os.listdir(STATIC_PYFILES_ROOT)):
        if filename.endswith(".py"):
            yield filename, os.path.join(STATIC_PYFILES_ROOT, filename)


html_file_not_found = f"""
<html>
<head><title>文件未找到</title></head>
<body>
    <h1>404 - 文件未找到</h1>
    <p>抱歉，您请求的文件不存在。</p>
</body>
</html>
"""


@app.route("/robots.txt")
def robots_txt():
    """Serve robots.txt file"""
    return send_from_directory(".", "robots.txt")


@app.route("/sitemap.xml")
def sitemap_xml():
    """Serve a sitemap generated from the current public tool catalog."""
    entries = [
        {
            "loc": get_canonical_url("/"),
            "changefreq": "weekly",
            "priority": "1.0",
        }
    ]

    for filename, file_path in iter_public_python_tools():
        script_slug = filename[:-3]
        file_info = parse_tool_metadata(file_path).to_dict()
        entries.append(
            {
                "loc": get_canonical_url(f"/detail/{script_slug}"),
                "lastmod": file_info["updated_at"],
                "changefreq": "monthly",
                "priority": "0.8",
            }
        )

    lines = ['<?xml version="1.0" encoding="UTF-8"?>']
    lines.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')
    for entry in entries:
        lines.append("    <url>")
        lines.append(f"        <loc>{escape(entry['loc'])}</loc>")
        if entry.get("lastmod") and entry["lastmod"] != "N/A":
            lines.append(f"        <lastmod>{escape(entry['lastmod'])}</lastmod>")
        lines.append(f"        <changefreq>{entry['changefreq']}</changefreq>")
        lines.append(f"        <priority>{entry['priority']}</priority>")
        lines.append("    </url>")
    lines.append("</urlset>")

    return Response("\n".join(lines) + "\n", mimetype="application/xml")


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
        file_info = parse_tool_metadata(file_path).to_dict()
        
        # Get the base URL with correct protocol
        base_url = get_base_url()
        script_slug = script_name[:-3]
        canonical_url = get_canonical_url(f"/detail/{script_slug}")
        raw_source_url = get_canonical_url(f"/{script_name}")
        file_info['run_command'] = f'uv run {base_url}/{script_name}'
        file_info['remote_usage_examples'] = build_remote_usage_examples(
            file_info['usage_examples'],
            base_url,
            script_name,
        )
        structured_data = {
            "@context": "https://schema.org",
            "@type": "SoftwareSourceCode",
            "name": file_info["title"],
            "description": file_info["description"],
            "url": canonical_url,
            "codeRepository": OPEN_SOURCE_URL,
            "programmingLanguage": "Python",
            "runtimePlatform": f"Python {file_info['requires_python']}",
            "applicationCategory": file_info["category"],
            "author": {
                "@type": "Organization",
                "name": file_info["author"],
            },
            "isAccessibleForFree": True,
            "codeSampleType": "full",
            "encoding": {
                "@type": "MediaObject",
                "contentUrl": raw_source_url,
                "encodingFormat": "text/x-python",
            },
        }
        
        # Use detail template
        return render_template('script_detail.html',
                             script_info=file_info,
                             base_url=base_url,
                             canonical_url=canonical_url,
                             structured_data=structured_data,
                             open_source_url=OPEN_SOURCE_URL,
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


@app.route("/<filename>")
def server_pyfiles(filename: str):
    if not filename.endswith('.py'):
        return render_template_string(html_file_not_found), 404

    try:
        response = send_from_directory(STATIC_PYFILES_ROOT, filename)
        script_slug = filename[:-3]
        response.headers["X-Robots-Tag"] = "noindex, follow"
        response.headers.add(
            "Link",
            f'<{get_canonical_url(f"/detail/{script_slug}")}>; rel="canonical"',
        )
        return response
    except FileNotFoundError:
        return render_template_string(html_file_not_found), 404


@app.route("/")
def list_tools():
    """List all available Python tools in the static_pyfiles directory."""
    try:
        base_url = get_base_url()

        # Get all Python files from the static_pyfiles directory
        py_files = []
        if os.path.exists(STATIC_PYFILES_ROOT):
            for filename in os.listdir(STATIC_PYFILES_ROOT):
                if filename.endswith('.py'):
                    file_path = os.path.join(STATIC_PYFILES_ROOT, filename)
                    
                    # Extract structured information from the file
                    file_info = parse_tool_metadata(file_path).to_dict()
                    run_command = f'uv run {base_url}/{filename}'
                    
                    py_files.append({
                        'filename': filename,
                        'title': file_info['title'],
                        'description': file_info['description'],
                        'overview': file_info['overview'],
                        'version': file_info['version'],
                        'category': file_info['category'],
                        'author': file_info['author'],
                        'requires_python': file_info['requires_python'],
                        'dependency_count': len(file_info['dependencies']),
                        'source_lines': file_info['source_lines'],
                        'updated_at': file_info['updated_at'],
                        'run_command': run_command,
                        'url': f'/{filename}',
                        'detail_url': f'/detail/{filename.replace(".py", "")}'
                    })
        
        # Sort files alphabetically
        py_files.sort(key=lambda x: x['filename'])
        categories = sorted({
            tool['category']
            for tool in py_files
            if tool['category'] and tool['category'] != 'N/A'
        })
        
        # Use external HTML template with base_url context
        return render_template(
            'list_tools.html',
            tools=py_files,
            categories=categories,
            base_url=base_url,
            canonical_url=get_canonical_url("/"),
            open_source_url=OPEN_SOURCE_URL,
        )
        
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


if __name__ == "__main__":
    # 添加配置以支持代理后的HTTPS检测
    app.config['PREFERRED_URL_SCHEME'] = 'https'
    app.run(debug=True, host=DEBUG_HOST, port=DEBUG_PORT)
