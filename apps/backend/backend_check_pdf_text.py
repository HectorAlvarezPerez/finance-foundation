from app.services.azure_document_intelligence_ocr_service import AzureDocumentIntelligenceOcrService

service = AzureDocumentIntelligenceOcrService()
try:
    with open('/home/hector/Escritorio/GitHub/finance-foundation/demo_transacciones.pdf', 'rb') as f:
        pdf_bytes = f.read()
    res = service.extract_text(content=pdf_bytes)
    print(res.text[-500:])
except Exception as e:
    print(f"Failed: {e}")
