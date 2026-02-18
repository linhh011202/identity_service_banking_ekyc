run:
	uv run fastapi dev ./app/main.py

remove-pycache:
	find . -type d -name "__pycache__" -exec rm -r {} +