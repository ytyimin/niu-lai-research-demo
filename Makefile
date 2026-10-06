.PHONY: demo test check app

demo:
	python -m contradiction_workflow.demo --output runs/demo-$$(date -u +%Y%m%dT%H%M%SZ)

test:
	python -m unittest discover -s tests -v

check:
	python -m compileall -q app.py contradiction_workflow tests
	python -m unittest discover -s tests -v

app:
	streamlit run app.py
