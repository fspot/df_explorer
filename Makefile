start:
	python3 tb_explorer/app.py

install-dependencies:
	pip install -r requirements.txt

clean:
	rm -rf build dist *.egg-info
