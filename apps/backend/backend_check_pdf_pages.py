import sys
from app.services.azure_document_intelligence_ocr_service import AzureDocumentIntelligenceOcrService

service = AzureDocumentIntelligenceOcrService()
try:
    with open('/home/hector/Escritorio/GitHub/finance-foundation/demo_transactions.pdf', 'rb') as f:
        pdf_bytes = f.read()
    res = service.extract_text(content=pdf_bytes)
    print(f"demo_transactions Pages: {res.page_count}")
    print(f"demo_transactions Tables: {len(res.tables)}")
except Exception as e:
    print(f"Failed: {e}")
