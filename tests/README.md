# Pipeline test (synthetic data only)

`make_fixture.py` writes fake fixed-width files that follow the layout, with planted not-stated, structural and imputed cells. It exercises the code; it says nothing about real births.

```bash
cp -r code tests docs /tmp/phmb_test && cd /tmp/phmb_test
python tests/make_fixture.py . 8000
python code/02_parse.py && python code/03_audit.py && python code/04_tasks.py --freeze
```
