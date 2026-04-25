import sys
from app.services.azure_document_intelligence_ocr_service import AzureDocumentIntelligenceOcrService

service = AzureDocumentIntelligenceOcrService()
try:
    with open('/home/hector/Escritorio/GitHub/finance-foundation/demo_transacciones.pdf', 'rb') as f:
        pdf_bytes = f.read()
    res = service.extract_text(content=pdf_bytes)
    with open('out_tables.txt', 'w') as f:
        f.write(res.tables_markdown)
    with open('out_text.txt', 'w') as f:
        f.write(res.structured_text)
    print("Done")
except Exception as e:
    print(f"Failed: {e}")
