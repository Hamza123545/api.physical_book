"""Test Qdrant collection status"""
from app.services.embeddings_service import get_collection_info

info = get_collection_info()
if info:
    print("Collection Info:")
    for key, value in info.items():
        print(f"  {key}: {value}")
else:
    print("Collection not found or error occurred")
