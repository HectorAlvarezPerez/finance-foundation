import PyPDF2

try:
    with open('/home/hector/Escritorio/GitHub/finance-foundation/demo_transacciones.pdf', 'rb') as f:
        reader = PyPDF2.PdfReader(f)
        text = ""
        for i, page in enumerate(reader.pages):
            text += f"\n--- Page {i+1} ---\n"
            text += page.extract_text()
        print(text)
except Exception as e:
    print(f"Error: {e}")
