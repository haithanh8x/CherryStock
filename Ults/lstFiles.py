import os
from pathlib import Path
import zipfile
import pandas as pd

from lstPara import PROJECT_FOLDER

def list_files_in_folder(folder_path: str, file_extension: str | None = None) -> pd.DataFrame:
    """
    List all files in a folder and return the result as a pandas DataFrame.

    Parameters: 
        folder_path (str): Path to the folder.
        file_extension (str | None): File extension to filter by, for example:
                                     'pdf', '.pdf', 'xlsx'.
                                     If None, all file types will be returned.
    Returns:
        pd.DataFrame: A DataFrame containing file information with the following columns:
            - 'file_name' (str): The name of the file including its extension.
            - 'file_path' (str): The absolute or relative string path to the file.
            - 'file_extension' (str): The extension of the file (e.g., '.txt', '.pdf').
            - 'file_size_kb' (float): The size of the file in Kilobytes, rounded to 2 decimal places.
    """

    # Convert input path to a Path object
    folder = Path(folder_path)

    # Check if the folder exists
    if not folder.exists():
        raise FileNotFoundError(f"Folder does not exist: {folder_path}")

    # Check if the path is actually a folder
    if not folder.is_dir():
        raise NotADirectoryError(f"Path is not a folder: {folder_path}")

    # Normalize file extension if provided
    if file_extension:
        file_extension = file_extension.lower()
        if not file_extension.startswith("."):
            file_extension = f".{file_extension}"

    file_data = []

    # Loop through all items inside the folder
    for file in folder.iterdir():

        # Skip folders, keep only files
        if not file.is_file():
            continue

        # Filter by file extension if provided
        if file_extension and file.suffix.lower() != file_extension:
            continue

        # Append file information to the result list
        file_data.append({
            "file_name": file.name,
            "file_path": str(file),
            "file_extension": file.suffix,
            "file_size_kb": round(file.stat().st_size / 1024, 2)
        })

    # Convert the result list to a DataFrame
    df = pd.DataFrame(file_data)

    return df

def load_gitignore_patterns(current_dir):
    """ Tự động đọc file .gitignore và trả về tập hợp các thư mục/file cần bỏ qua """
    ignore_patterns = {'__pycache__', '.git'}  # Mặc định luôn bỏ qua 2 mục này
    gitignore_path = os.path.join(current_dir, '.gitignore')
    
    if os.path.exists(gitignore_path):
        print("📖 Đang đọc cấu hình bỏ qua từ file .gitignore...")
        with open(gitignore_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # Bỏ qua các dòng chú thích hoặc dòng trống trong .gitignore
                if not line or line.startswith('#'):
                    continue
                # Chuẩn hóa tên: xóa dấu gạch chéo ở cuối (ví dụ: '__pycache__/' -> '__pycache__')
                if line.endswith('/'):
                    line = line[:-1]
                ignore_patterns.add(line)
    else:
        print("⚠️ Không tìm thấy file .gitignore, sử dụng danh sách loại trừ mặc định.")
        
    return ignore_patterns

def pack_source_code(output_zip_name="CherryMon_Sources.zip"):
    # Danh sách các đuôi file code được phép nén
    allowed_extensions = {'.py', '.sql', '.ipynb', '.md', '.txt', '.json', '.yaml', '.yml'}
    current_dir = PROJECT_FOLDER
    
    # Tự động nạp danh sách loại trừ từ .gitignore
    ignore_list = load_gitignore_patterns(current_dir)
    #print(f"🚫 Danh sách loại trừ hiện tại: {ignore_list}")
    #print(f"📦 Bắt đầu quét và đóng gói thư mục: {current_dir}")
    
    count = 0
    with zipfile.ZipFile(output_zip_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(current_dir):
            # Bộ lọc thư mục: Loại bỏ các thư mục nằm trong danh sách ignore
            dirs[:] = [d for d in dirs if d not in ignore_list]
            
            for file in files:
                # Không tự nén chính file zip đầu ra hoặc file .gitignore
                if file in (output_zip_name, '.gitignore') or file in ignore_list:
                    continue
                    
                file_path = os.path.join(root, file)
                ext = os.path.splitext(file)[1].lower()
                
                # Kiểm tra điều kiện file code hợp lệ và không nằm trong danh sách ignore
                if ext in allowed_extensions:
                    relative_path = os.path.relpath(file_path, current_dir)
                    zipf.write(file_path, relative_path)
                    #print(f"  + Đã thêm: {relative_path}")
                    count += 1
    print(f"📦 Đóng gói hoàn tất. Tổng số file đã thêm: {count}")