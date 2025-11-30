"""
OpenAI Agents SDK service for RAG chatbot
Uses Agent, Runner, and Sessions from openai-agents package
Supports OpenAI models natively and Gemini models via LiteLLM (litellm/ prefix)
"""
from typing import List, Dict, Any, Optional, Iterator
from agents import Agent, Runner, Session
from app.config import CHAT_MODEL, USE_GEMINI, GEMINI_API_KEY
from app.utils.logger import setup_logger, log_external_api_call
import time
import os

logger = setup_logger(__name__)

# Setup model configuration
if USE_GEMINI and GEMINI_API_KEY:
    # Set Gemini API key for LiteLLM (Agents SDK uses LiteLLM for non-OpenAI models)
    os.environ["GEMINI_API_KEY"] = GEMINI_API_KEY
    # Force LiteLLM to use v1 API instead of v1beta (v1beta doesn't have all models)
    os.environ["GEMINI_API_VERSION"] = "v1"
    logger.info("Gemini API key configured for Agents SDK via LiteLLM (using v1 API)")
elif not os.getenv("OPENAI_API_KEY"):
    logger.warning("Neither OPENAI_API_KEY nor GEMINI_API_KEY set - Agents SDK will not work")


def create_rag_agent(context: str, chat_history: Optional[List[Dict[str, str]]] = None) -> Agent:
    """
    Create an Agent with RAG context and instructions
    Supports OpenAI models natively and Gemini models via LiteLLM (litellm/ prefix)
    
    Args:
        context: Retrieved context from Qdrant
        chat_history: Optional previous messages for context
    
    Returns:
        Configured Agent instance
    """
    # Build instructions with context
    instructions = f"""You are an expert AI assistant for the Physical AI and Humanoid Robotics textbook.

Your task is to answer questions based on the provided context from the textbook. Follow these guidelines:

1. **Answer based on context**: Use only the information from the provided sources
2. **Cite sources**: Reference specific chapters and lessons when answering
3. **Be accurate**: If the context doesn't contain enough information, say so
4. **Be clear**: Explain technical concepts in an accessible way
5. **Be helpful**: Provide examples and clarifications when useful

Context from textbook:
{context}

Answer the user's question using the context above. Include source citations in your response."""

    # Create agent with instructions and model
    # OpenAI Agents SDK supports:
    # - OpenAI models: gpt-4-turbo-preview, gpt-4, gpt-4o, gpt-5, etc.
    # - Gemini models (via LiteLLM): litellm/gemini/gemini-2.0-flash-exp, etc.
    agent = Agent(
        name="RAG Assistant",
        instructions=instructions,
        model=CHAT_MODEL  # Can be OpenAI model or litellm/gemini/... for Gemini
    )
    
    model_type = "Gemini (LiteLLM)" if CHAT_MODEL.startswith("litellm/") else "OpenAI"
    logger.info(f"Created RAG agent with {model_type} model: {CHAT_MODEL}")
    return agent


def create_selected_text_agent(selected_text: str) -> Agent:
    """
    Create an Agent for selected text queries
    Supports OpenAI models natively and Gemini models via LiteLLM (litellm/ prefix)
    
    Args:
        selected_text: Text selected by user
    
    Returns:
        Configured Agent instance
    """
    instructions = f"""You are an expert AI assistant for the Physical AI and Humanoid Robotics textbook.

The user has selected this text from the textbook:
\"\"\"{selected_text}\"\"\"

Answer their question about this specific text. Be clear, accurate, and helpful."""

    agent = Agent(
        name="Selected Text Assistant",
        instructions=instructions,
        model=CHAT_MODEL  # Can be OpenAI model or litellm/gemini/... for Gemini
    )
    
    model_type = "Gemini (LiteLLM)" if CHAT_MODEL.startswith("litellm/") else "OpenAI"
    logger.info(f"Created selected text agent with {model_type} model: {CHAT_MODEL}")
    return agent


async def run_agent_async(
    agent: Agent,
    user_message: str,
    session: Optional[Session] = None
) -> Optional[str]:
    """
    Run agent asynchronously and return response

    Args:
        agent: Agent instance
        user_message: User's question
        session: Optional session for conversation history

    Returns:
        Agent's response text or None if failed
    """
    try:
        start_time = time.time()

        # Run agent with Runner (async version)
        if session:
            result = await Runner.run(agent, user_message, session=session)
        else:
            result = await Runner.run(agent, user_message)

        duration_ms = (time.time() - start_time) * 1000

        # Extract response
        response_text = result.final_output if hasattr(result, 'final_output') else str(result)

        log_external_api_call(
            logger,
            service="OpenAI Agents SDK",
            operation="agent_run",
            duration_ms=duration_ms,
            success=True,
            model=CHAT_MODEL
        )

        logger.info(f"Agent response generated: {duration_ms:.2f}ms")

        return response_text

    except Exception as e:
        error_str = str(e)
        logger.error(f"Failed to run agent: {e}")
        
        # Check if it's a Gemini model not found error
        if "NotFoundError" in error_str or "404" in error_str or "not found" in error_str.lower():
            logger.warning(
                f"Gemini model {CHAT_MODEL} not available. "
                f"Try setting GEMINI_MODEL=gemini-1.5-pro or GEMINI_MODEL=gemini-1.5-flash-latest in .env"
            )
        
        log_external_api_call(
            logger,
            service="OpenAI Agents SDK",
            operation="agent_run",
            success=False,
            error=error_str
        )
        return None


def run_agent_stream(
    agent: Agent,
    user_message: str,
    session: Optional[Session] = None
) -> Iterator[str]:
    """
    Run agent with streaming response
    
    Args:
        agent: Agent instance
        user_message: User's question
        session: Optional session for conversation history
    
    Yields:
        Chunks of response text
    """
    try:
        # Run agent with streaming
        if session:
            for event in Runner.run_stream(agent, user_message, session=session):
                if hasattr(event, 'delta') and event.delta:
                    yield event.delta
                elif hasattr(event, 'content'):
                    yield event.content
        else:
            for event in Runner.run_stream(agent, user_message):
                if hasattr(event, 'delta') and event.delta:
                    yield event.delta
                elif hasattr(event, 'content'):
                    yield event.content
    
    except Exception as e:
        logger.error(f"Failed to stream agent response: {e}")
        yield f"Error: {str(e)}"


async def create_rag_completion_with_agent(
    user_question: str,
    retrieved_chunks: List[Dict[str, Any]],
    chat_history: Optional[List[Dict[str, str]]] = None
) -> Optional[str]:
    """
    Create a RAG-enhanced response using OpenAI Agents SDK

    Args:
        user_question: User's question
        retrieved_chunks: List of relevant chunks from vector search
        chat_history: Optional previous messages for context

    Returns:
        Assistant's response with citations
    """
    # Build context from retrieved chunks
    context_parts = []

    for i, chunk in enumerate(retrieved_chunks, 1):
        payload = chunk.get('payload', {})
        content = payload.get('content', '')
        chapter = payload.get('chapter', 'unknown')
        lesson = payload.get('lesson', 'unknown')
        section = payload.get('section_title', 'unknown')

        context_parts.append(
            f"[Source {i} - Chapter {chapter}, Lesson {lesson}, {section}]\n{content}\n"
        )

    context = "\n".join(context_parts)

    # Create agent with context
    agent = create_rag_agent(context, chat_history)

    # Create session if chat history provided
    session = None
    if chat_history:
        # Convert chat history to session format
        # Note: Agents SDK Sessions handle history automatically
        # We'll use the agent's built-in session management
        pass

    # Run agent
    return await run_agent_async(agent, user_question, session)


async def create_selected_text_completion_with_agent(
    user_question: str,
    selected_text: str
) -> Optional[str]:
    """
    Create response for selected text using OpenAI Agents SDK

    Args:
        user_question: User's question about the selected text
        selected_text: Text selected by user

    Returns:
        Assistant's response
    """
    # Create agent for selected text
    agent = create_selected_text_agent(selected_text)

    # Run agent
    return await run_agent_async(agent, user_question)

