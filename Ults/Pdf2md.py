# Copy hết vào 1 folder /pdfs
# md file sẽ được export vào folder /markdowns

import sys
from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

from lstPara import DATAFILE_PATH

from markitdown import MarkItDown
from pathlib import Path

input_dir = DATAFILE_PATH / "pdfs"
output_dir = DATAFILE_PATH / "markdowns"

output_dir.mkdir(exist_ok=True)
md = MarkItDown()
# Final merged markdown file
merged_output = output_dir / "merged_output.md"

# ===== MERGE ALL PDFs =====
with open(merged_output, "w", encoding="utf-8") as merged_file:

    for pdf_file in input_dir.glob("*.pdf"):

        try:
            print(f"Processing: {pdf_file.name}")

            result = md.convert(str(pdf_file))

            # Add separator/title
            merged_file.write(f"\n\n# {pdf_file.stem}\n\n")

            # Add markdown content
            merged_file.write(result.text_content)

            # Add spacing
            merged_file.write("\n\n---\n\n")

            print(f"Done: {pdf_file.name}")

        except Exception as e:
            print(f"Error {pdf_file.name}: {e}")

print(f"\nMerged markdown saved to:\n{merged_output}")
