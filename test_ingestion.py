"""
Quick test script for embeddings ingestion
"""
import asyncio
from app.services.embeddings_service import create_qdrant_collection
from app.utils.markdown_processor import find_all_lesson_files, process_document_to_chunks

async def main():
    print("Finding lesson files...")
    docs_dir = "../book-source/docs"
    lesson_files = find_all_lesson_files(docs_dir)
    print(f"Found {len(lesson_files)} lesson files")

    if lesson_files:
        print(f"First file: {lesson_files[0]}")
        chunks = process_document_to_chunks(lesson_files[0])
        print(f"Processed into {len(chunks)} chunks")
        if chunks:
            print(f"First chunk: {chunks[0]}")

if __name__ == "__main__":
    asyncio.run(main())
