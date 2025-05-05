import fitz
import docx
import io


# ---------- 📄 Document Processor Functions ----------

def extract_pdf_text(file_bytes: bytes) -> str:
    text = ""
    pdf = fitz.open(stream=file_bytes, filetype="pdf")
    for page in pdf:
        text += page.get_text()
    pdf.close()
    return text

def extract_docx_text(file_bytes: bytes) -> str:
    text = ""
    doc = docx.Document(io.BytesIO(file_bytes))
    for para in doc.paragraphs:
        text += para.text + "\n"
    return text

def extract_txt_text(file_bytes: bytes) -> str:
    return file_bytes.decode(errors='ignore')

def get_file_type(filename: str, mime_type: str) -> str:
    ext = filename.lower().split('.')[-1]
    if ext in ['pdf']:
        return 'pdf'
    elif ext in ['docx', 'doc']:
        return 'docx'
    elif ext in ['txt']:
        return 'txt'
    # Fallback using mime_type
    if mime_type == 'application/pdf':
        return 'pdf'
    elif mime_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
        return 'docx'
    elif mime_type.startswith('text/'):
        return 'txt'
    else:
        return 'unsupported'