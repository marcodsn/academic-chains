pipreqs ./ --savepath requirements.in --force --ignore ./venv/,./test_venv/ --mode no-pin && uv pip compile requirements.in -o requirements.txt
