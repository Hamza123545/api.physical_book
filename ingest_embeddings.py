"""
Standalone script for ingesting textbook embeddings into Qdrant
Uses FastEmbed for FREE local embeddings
"""
import sys
import time
from app.services.embeddings_service import (
    create_qdrant_collection,
    create_embeddings_batch,
    upsert_vectors
)
from app.utils.markdown_processor import (
    find_all_lesson_files,
    process_document_to_chunks
)
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

def main():
    """Run the full ingestion pipeline"""
    start_time = time.time()

    print("\n" + "="*60)
    print("TEXTBOOK EMBEDDINGS INGESTION")
    print("="*60 + "\n")

    # Step 1: Create Qdrant collection
    print("[1] Step 1: Creating Qdrant collection...")
    collection_ready = create_qdrant_collection(force_recreate=False)

    if not collection_ready:
        print("[ERROR] Failed to create Qdrant collection!")
        sys.exit(1)

    print("[OK] Qdrant collection ready\n")

    # Step 2: Find all lesson files
    print("[2] Step 2: Finding lesson files...")
    docs_dir = "../book-source/docs"
    lesson_files = find_all_lesson_files(docs_dir)

    print(f"[OK] Found {len(lesson_files)} lesson files\n")

    if not lesson_files:
        print("[ERROR] No lesson files found!")
        sys.exit(1)

    # Step 3: Process all files into chunks
    print("[3]  Step 3: Processing files into chunks...")
    all_chunks = []

    for i, file_path in enumerate(lesson_files, 1):
        try:
            chunks = process_document_to_chunks(file_path)
            all_chunks.extend(chunks)

            if i % 10 == 0 or i == len(lesson_files):
                print(f"   Processed {i}/{len(lesson_files)} files... ({len(all_chunks)} chunks total)")
        except Exception as e:
            logger.error(f"Failed to process {file_path}: {e}")
            continue

    print(f"\n[OK] Created {len(all_chunks)} chunks from {len(lesson_files)} files\n")

    if not all_chunks:
        print("[ERROR] No chunks created!")
        sys.exit(1)

    # Step 4: Create embeddings in batches
    print("[4] Step 4: Creating embeddings with FastEmbed (FREE!)...")
    batch_size = 32  # FastEmbed batch size
    all_vectors = []
    all_payloads = []

    total_batches = (len(all_chunks) + batch_size - 1) // batch_size

    for i in range(0, len(all_chunks), batch_size):
        batch = all_chunks[i:i + batch_size]
        batch_num = (i // batch_size) + 1

        # Extract text content
        texts = [chunk['content'] for chunk in batch]

        # Create embeddings
        embeddings = create_embeddings_batch(texts)

        if not embeddings:
            print(f"   [WARN]  Batch {batch_num}/{total_batches} failed - skipping")
            continue

        all_vectors.extend(embeddings)

        # Prepare payloads (remove 'content' to save space, keep metadata)
        for chunk in batch:
            payload = {
                'chapter': chunk.get('chapter', 'unknown'),
                'lesson': chunk.get('lesson', 'unknown'),
                'section_title': chunk.get('section_title', 'Unknown'),
                'file_path': chunk.get('file_path', ''),
                'chunk_index': chunk.get('chunk_index', 0),
                'cefr_level': chunk.get('cefr_level', ''),
                'content': chunk.get('content', '')[:500]  # Store first 500 chars for debugging
            }
            all_payloads.append(payload)

        print(f"   Batch {batch_num}/{total_batches} complete - {len(embeddings)} embeddings created")

    print(f"\n[OK] Created {len(all_vectors)} embeddings (384-dimensional)\n")

    # Step 5: Upload vectors to Qdrant
    print("[5]  Step 5: Uploading vectors to Qdrant...")
    vectors_uploaded = upsert_vectors(
        vectors=all_vectors,
        payloads=all_payloads
    )

    print(f"[OK] Uploaded {vectors_uploaded} vectors to Qdrant\n")

    # Summary
    duration = time.time() - start_time
    print("="*60)
    print("[DONE] INGESTION COMPLETE!")
    print("="*60)
    print(f"[STATS] Statistics:")
    print(f"   - Files processed: {len(lesson_files)}")
    print(f"   - Chunks created: {len(all_chunks)}")
    print(f"   - Vectors uploaded: {vectors_uploaded}")
    print(f"   - Duration: {duration:.1f} seconds")
    print(f"   - Cost: $0.00 (FastEmbed is FREE!)")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
