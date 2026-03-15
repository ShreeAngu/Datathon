import ast, pathlib, sys

files = list(pathlib.Path("frontend").rglob("*.py"))
errors = []
for f in files:
    try:
        ast.parse(f.read_text(encoding="utf-8-sig"))
    except SyntaxError as e:
        errors.append((f, e))

print(f"Checked {len(files)} files")
if errors:
    for f, e in errors:
        print(f"  ERROR {f}: {e}")
    sys.exit(1)
else:
    print("All OK")
