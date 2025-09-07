# Config-Txt

This package is used to return content of .txt(or any other text based file such as .md .toml files) file or return string that returned by .py file(which will be excuted by `uv run some_python_file.py`)

## Rerurn content of text based file

Static text based files servered by flask will be returned derectly

For example: demo.txt

> demo.txt
> This content will be returned as flask static file.

## Return content by running .py file using uv

[uv](https://github.com/astral-sh/uv) can run remote file just like run local file.

Just type command like this: `uv run https://example.com/script.py`
