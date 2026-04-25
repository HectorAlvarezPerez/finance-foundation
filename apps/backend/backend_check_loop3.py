from app.services.azure_document_intelligence_ocr_service import AzureDocumentIntelligenceOcrService
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient

service = AzureDocumentIntelligenceOcrService()
client = DocumentIntelligenceClient(
    endpoint=service.endpoint,
    credential=AzureKeyCredential(service.api_key),
)

try:
    with open('/home/hector/Escritorio/GitHub/finance-foundation/demo_transacciones.pdf', 'rb') as f:
        pdf_bytes = f.read()
    poller = client.begin_analyze_document(
        service.model_id,
        body=AnalyzeDocumentRequest(bytes_source=pdf_bytes),
        pages="3-4"
    )
    res = poller.result()
    print("Mismatched range pages:", len(getattr(res, 'pages', [])))
except Exception as e:
    print(f"Failed: {e}")
