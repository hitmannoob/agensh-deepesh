import re
import sys

path = sys.argv[1]
problems = [f"{path}:{number}: a figure without a citation: {line.strip()}"
            for number, line in enumerate(open(path, encoding="utf-8"), 1)
            if re.search(r"\$[0-9]", line) and "[^" not in line and not line.startswith("[^")]
print("\n".join(problems))
sys.exit(1 if problems else 0)
