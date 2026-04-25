import asyncio
from app.services.azure_document_intelligence_ocr_service import AzureDocumentIntelligenceOcrService

async def main():
    service = AzureDocumentIntelligenceOcrService()
    try:
        with open('/home/hector/Escritorio/GitHub/finance-foundation/demo_transacciones.pdf', 'rb') as f:
            pdf_bytes = f.read()
        res = service.extract_text(content=pdf_bytes)
        print("======== TABLES ========")
        print(res.tables_markdown)
        print("======== STRUCTURED TEXT ========")
        print(res.structured_text)
    except Exception as e:
        print(f"Failed: {e}")

asyncio.run(main())
