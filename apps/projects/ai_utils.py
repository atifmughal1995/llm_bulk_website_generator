import openai
import anthropic
import logging
from typing import Optional

from django.conf import settings

logger = logging.getLogger(__name__)

openai.api_key = settings.OPENAI_KEY
anthropic_api_key = settings.ANTHROPIC_KEY


def call_openai_api(prompt: str, temperature: float = 0.5) -> dict:
    """Calls OpenAI API and returns a structured response."""
    try:
        logger.info('Calling OpenAI API')
        response = openai.ChatCompletion.create(
            model='gpt-4o-mini',
            messages=[{'role': 'user', 'content': prompt}],
            max_tokens=16384,
            temperature=temperature,
        )
        logger.info('Response received from OpenAI')
        return {'result': response.choices[0].message.content.strip(), 'error': False}

    except Exception as e:
        logger.error('OpenAI API error: %s', e)
        return {'result': str(e), 'error': True}


def call_anthropic_api(prompt: str) -> dict:
    """Calls Anthropic (Claude) API and returns a structured response."""
    try:
        client = anthropic.Anthropic(api_key=anthropic_api_key)
        logger.info('Calling Anthropic API')
        response = client.beta.messages.create(
            model='claude-3-7-sonnet-20250219',
            max_tokens=64000,
            timeout=1200.0,
            messages=[{'role': 'user', 'content': prompt}],
        )
        logger.info('Response received from Anthropic')
        return {'result': response.content[0].text, 'error': False}

    except Exception as e:
        logger.error('Anthropic API error: %s', e)
        return {'result': str(e), 'error': True}


def generate_content(prompt: str, temperature: float = 0.5, openai: bool = True) -> str:
    """Generate content using the specified AI provider."""
    if openai:
        result = call_openai_api(prompt, temperature)
    else:
        logger.debug('Anthropic prompt: %s', prompt)
        result = call_anthropic_api(prompt)
    return result['result'] if not result['error'] else f"Error: {result['result']}"