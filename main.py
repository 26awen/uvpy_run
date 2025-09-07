import os
from flask import Flask
from flask import send_from_directory
from flask import render_template_string

from dotenv import load_dotenv

_ = load_dotenv()

FLASK_SECRET = os.environ.get("FLASK_SECRET")


STATIC_PYFILES_ROOT = "./static_pyfiles/"
STATIC_TEXTBASEDFILES_ROOT = "./static_textbasedfiles/"
DEBUG_HOST = "0.0.0.0"
DEBUG_PORT = 9999

app = Flask(__name__)
app.secret_key = FLASK_SECRET


html_file_not_found = f"""
<html>
<head><title>文件未找到</title></head>
<body>
    <h1>404 - 文件未找到</h1>
    <p>抱歉，您请求的文件不存在。</p>
</body>
</html>
"""


@app.route("/runpy/<filename>")
def server_pyfiles(filename: str):
    try:
        return send_from_directory(STATIC_PYFILES_ROOT, filename)
    except FileNotFoundError:
        return render_template_string(html_file_not_found)


@app.route("/text/<filename>")
def server_textbasedfiles(filename: str):
    return send_from_directory(STATIC_TEXTBASEDFILES_ROOT, filename)


if __name__ == "__main__":
    app.run(debug=True, host=DEBUG_HOST, port=DEBUG_PORT)
