"""Claude API client for handling AI conversations."""
import anthropic
import base64
from typing import List, Dict, Optional
import config


class ClaudeClient:
    """Wrapper for Anthropic Claude API with conversation management."""

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=config.CLAUDE_API_KEY)
        self.model = config.CLAUDE_MODEL
        self.max_tokens = config.MAX_TOKENS

    def send_message(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None
    ) -> tuple[str, int, int]:
        """
        Send a message to Claude and get response.

        Args:
            messages: List of message dicts with 'role' and 'content'
            system_prompt: Optional system prompt

        Returns:
            Tuple of (response_text, input_tokens, output_tokens)
        """
        try:
            kwargs = {
                "model": self.model,
                "max_tokens": self.max_tokens,
                "messages": messages
            }

            if system_prompt:
                kwargs["system"] = system_prompt

            response = self.client.messages.create(**kwargs)

            # Extract text from response
            response_text = ""
            for block in response.content:
                if block.type == "text":
                    response_text += block.text

            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens

            return response_text, input_tokens, output_tokens

        except anthropic.APIError as e:
            raise Exception(f"Claude API error: {str(e)}")

    def send_message_with_image(
        self,
        messages: List[Dict],
        image_data: bytes,
        image_format: str,
        system_prompt: Optional[str] = None
    ) -> tuple[str, int, int]:
        """
        Send a message with an image to Claude.

        Args:
            messages: List of previous messages
            image_data: Raw image bytes
            image_format: Image format (jpeg, png, gif, webp)
            system_prompt: Optional system prompt

        Returns:
            Tuple of (response_text, input_tokens, output_tokens)
        """
        try:
            # Encode image to base64
            base64_image = base64.b64encode(image_data).decode('utf-8')

            # Get the last user message (should contain the question about the image)
            last_message = messages[-1] if messages else {"role": "user", "content": "What's in this image?"}

            # Convert last message to multimodal format
            if isinstance(last_message["content"], str):
                text_content = last_message["content"]
            else:
                text_content = last_message["content"]

            # Create message with image
            message_content = [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": f"image/{image_format}",
                        "data": base64_image,
                    },
                },
                {
                    "type": "text",
                    "text": text_content
                }
            ]

            # Update the last message with multimodal content
            messages_copy = messages[:-1] if len(messages) > 1 else []
            messages_copy.append({
                "role": "user",
                "content": message_content
            })

            kwargs = {
                "model": self.model,
                "max_tokens": self.max_tokens,
                "messages": messages_copy
            }

            if system_prompt:
                kwargs["system"] = system_prompt

            response = self.client.messages.create(**kwargs)

            # Extract text from response
            response_text = ""
            for block in response.content:
                if block.type == "text":
                    response_text += block.text

            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens

            return response_text, input_tokens, output_tokens

        except anthropic.APIError as e:
            raise Exception(f"Claude API error: {str(e)}")

    def send_message_with_document(
        self,
        messages: List[Dict],
        document_text: str,
        system_prompt: Optional[str] = None
    ) -> tuple[str, int, int]:
        """
        Send a message with document content to Claude.

        Args:
            messages: List of previous messages
            document_text: Extracted text from document
            system_prompt: Optional system prompt

        Returns:
            Tuple of (response_text, input_tokens, output_tokens)
        """
        # Add document context to the last user message
        last_message = messages[-1] if messages else {"role": "user", "content": "Analyze this document"}

        if isinstance(last_message["content"], str):
            text_content = last_message["content"]
        else:
            text_content = last_message["content"]

        # Prepend document content
        full_message = f"Document content:\n\n{document_text}\n\n{text_content}"

        messages_copy = messages[:-1] if len(messages) > 1 else []
        messages_copy.append({
            "role": "user",
            "content": full_message
        })

        return self.send_message(messages_copy, system_prompt)
