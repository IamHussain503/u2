import os

def merge_py_files_to_text(root_dir, output_file):
    with open(output_file, 'w', encoding='utf-8') as outfile:
        for subdir, _, files in os.walk(root_dir):
            for file in files:
                if file.endswith('.py'):
                    filepath = os.path.join(subdir, file)
                    outfile.write(f"File: {filepath}\n")
                    outfile.write("=" * (len(filepath) + 6) + "\n\n")

                    with open(filepath, 'r', encoding='utf-8') as infile:
                        outfile.write(infile.read())

                    outfile.write("\n" + "-"*80 + "\n\n")

# Usage Example
root_directory = "C:\\bot\\U2\\u2\\"
output_file = "merged_scripts.txt"

merge_py_files_to_text(root_directory, output_file)

print(f"All .py files merged into {output_file}")
