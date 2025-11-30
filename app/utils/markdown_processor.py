"""
Markdown/MDX processor for extracting content and creating embeddings chunks
Handles parsing, chunking with overlap, and metadata extraction
"""
import re
import os
from typing import List, Dict, Any, Tuple
from pathlib import Path
from markdown_it import MarkdownIt
from markdown_it.token import Token
from app.config import CHUNK_SIZE, CHUNK_OVERLAP
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


def parse_mdx_file(file_path: str) -> Dict[str, Any]:
    """
    Parse MDX file and extract text content with metadata
    
    Args:
        file_path: Path to MDX file
    
    Returns:
        Dict with content, frontmatter, and metadata
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract frontmatter (YAML between --- delimiters)
        frontmatter = {}
        frontmatter_match = re.match(r'^---\n(.*?)\n---\n', content, re.DOTALL)
        if frontmatter_match:
            frontmatter_text = frontmatter_match.group(1)
            content = content[frontmatter_match.end():]
            
            # Parse simple YAML frontmatter
            for line in frontmatter_text.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    frontmatter[key.strip()] = value.strip().strip('"').strip("'")
        
        # Extract metadata from file path
        path_parts = Path(file_path).parts
        chapter = None
        lesson = None
        
        for part in path_parts:
            if part.startswith('chapter-'):
                chapter = part.replace('chapter-', '')
            elif part.startswith('lesson-') and part.endswith('.md'):
                lesson = part.replace('lesson-', '').replace('.md', '').replace('.mdx', '')
        
        return {
            'content': content,
            'frontmatter': frontmatter,
            'chapter': chapter or 'unknown',
            'lesson': lesson or 'unknown',
            'file_path': file_path,
            'cefr_level': frontmatter.get('cefr_level', frontmatter.get('level', 'B1'))
        }
    
    except Exception as e:
        logger.error(f"Failed to parse MDX file {file_path}: {e}")
        return None


def extract_text_from_markdown(markdown_content: str) -> str:
    """
    Extract plain text from Markdown
    """
    md = MarkdownIt()
    tokens = md.parse(markdown_content)
    
    text_parts = []
    
    for token in tokens:
        if token.type == 'inline':
            text_parts.append(token.content)
        elif token.type == 'fence' or token.type == 'code_block':
            text_parts.append(f"\n```\n{token.content}\n```\n")
        elif token.type == 'paragraph_open':
            text_parts.append('\n')
    
    text = ' '.join(text_parts)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.strip()
    
    return text


def count_tokens_approx(text: str) -> int:
    """Approximate token count: 1 token ≈ 4 characters"""
    return len(text) // 4


def create_chunks_with_overlap(
    text: str,
    chunk_size: int = 512,
    overlap: int = 100
) -> List[str]:
    """Split text into chunks with overlap"""
    char_chunk_size = chunk_size * 4
    char_overlap = overlap * 4
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + char_chunk_size
        chunk = text[start:end]
        
        if end < len(text):
            last_period = chunk.rfind('.')
            last_newline = chunk.rfind('\n')
            break_point = max(last_period, last_newline)
            
            if break_point > char_chunk_size // 2:
                chunk = text[start:start + break_point + 1]
                end = start + break_point + 1
        
        chunks.append(chunk.strip())
        start = end - char_overlap
        
        if start >= len(text):
            break
    
    return [chunk for chunk in chunks if chunk]


def extract_section_titles(markdown_content: str) -> List[Tuple[str, int]]:
    """Extract section titles with positions"""
    titles = []
    header_pattern = r'^#{1,6}\s+(.+)$'
    
    for match in re.finditer(header_pattern, markdown_content, re.MULTILINE):
        title = match.group(1).strip()
        position = match.start()
        titles.append((title, position))
    
    return titles


def find_section_for_position(position: int, sections: List[Tuple[str, int]]) -> str:
    """Find section title for a given position"""
    current_section = "Introduction"
    
    for title, section_pos in sections:
        if section_pos <= position:
            current_section = title
        else:
            break
    
    return current_section


def process_document_to_chunks(file_path: str) -> List[Dict[str, Any]]:
    """Process document into chunks with metadata"""
    doc_data = parse_mdx_file(file_path)
    if not doc_data:
        return []
    
    text = extract_text_from_markdown(doc_data['content'])
    sections = extract_section_titles(doc_data['content'])
    chunks = create_chunks_with_overlap(text)
    
    chunk_data = []
    current_position = 0
    
    for idx, chunk in enumerate(chunks):
        section_title = find_section_for_position(current_position, sections)
        
        chunk_data.append({
            'content': chunk,
            'chapter': doc_data['chapter'],
            'lesson': doc_data['lesson'],
            'section_title': section_title,
            'file_path': file_path,
            'chunk_index': idx,
            'cefr_level': doc_data['cefr_level'],
            'token_count': count_tokens_approx(chunk)
        })
        
        current_position += len(chunk)
    
    logger.info(f"Processed {file_path}: {len(chunks)} chunks created")
    return chunk_data


def find_all_lesson_files(docs_dir: str) -> List[str]:
    """Find all lesson markdown files"""
    lesson_files = []
    docs_path = Path(docs_dir)
    
    for file_path in docs_path.rglob('*.md'):
        lesson_files.append(str(file_path))
    
    for file_path in docs_path.rglob('*.mdx'):
        lesson_files.append(str(file_path))
    
    logger.info(f"Found {len(lesson_files)} lesson files in {docs_dir}")
    return sorted(lesson_files)
