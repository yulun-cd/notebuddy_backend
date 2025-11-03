import json
import openai
import os
from typing import List
from dotenv import load_dotenv
from pydantic import BaseModel
from .schemas import NoteBase

load_dotenv()


class DeepSeekService:
    def __init__(self):
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        # Configure OpenAI client for DeepSeek API
        self.client = openai.OpenAI(
            api_key=self.api_key, base_url="https://api.deepseek.com"
        )

    async def generate_note_from_transcript(
        self, transcript_content: str, language: str = "Chinese"
    ) -> str:
        """Generate a structured note from transcript"""

        # Language-specific prompts
        prompt = f"""
Please analyze the following content and generate a structured note. Keep the generated note in the same language as the original content.

Content:
{transcript_content}

Please structure this content to make the viewpoints clearer and list the logical chains in the content.
Do not fabricate content; stay as faithful as possible to the original facts.
Keep the generated note length roughly equivalent to the original content length, but you don't need to strictly adhere to this principle.
Please return directly with the structured note, without including any content other than the structured note.
Return a brief title in the title field and the structured note content in the content field.
Please maintain only the top-level JSON format, do not nest JSON in title or content.
Do not add any extra text before or after the JSON object.
Please generate in the following language: {language}.
"""

        response = await self._call_deepseek(
            prompt,
            response_format={
                "type": "json_schema",
                "json_schema": NoteBase.model_json_schema(),
            },
        )
        data = json.loads(response)
        return data["title"], data["content"]

    async def generate_follow_up_questions(
        self, note_content: str, language: str = "Chinese"
    ) -> List[str]:
        """Generate follow-up questions based on the note content"""

        # Language-specific prompts
        prompt = f"""
Please analyze the following note content and generate 3-5 related follow-up questions.

Note content:
{note_content}

Please generate questions that can help clarify, deepen understanding, or supplement the note information.
You can imagine you are a listener who wants to ask questions to the speaker after hearing the above note content.
Please keep the generated questions in the same language as the note content.
Return the questions as a list in the questions field.
Please generate the questions in the following language: {language}.
"""

        class QuestionsSchema(BaseModel):
            questions: List[str]

        response = await self._call_deepseek(
            prompt,
            response_format={
                "type": "json_schema",
                "json_schema": QuestionsSchema.model_json_schema(),
            },
        )
        data = json.loads(response)
        return data["questions"]

    async def update_note_with_answer(
        self, note_content: str, question: str, answer: str, language: str = "Chinese"
    ) -> str:
        """
        Update the note by incorporating a single answer to a follow-up question
        """

        # Language-specific prompts
        prompt = f"""
Please analyze the following note content and Q&A content, then update the note by incorporating the answer.

Original note content:
{note_content}

Q&A content:
Question: {question}
Answer: {answer}

Please update the original note by incorporating the answer.
Keep the structure and length of the newly generated note slightly longer than the original note.
Please maintain the same language.
Please return directly with the structured note, without including any content other than the structured note.
Return a brief title in the title field and the structured note content in the content field, keeping the content as plain text.
Please maintain only the top-level JSON format, do not nest JSON in title or content.
Do not add any extra text before or after the JSON object.
Please generate in the following language: {language}.
"""

        response = await self._call_deepseek(
            prompt,
            response_format={
                "type": "json_schema",
                "json_schema": NoteBase.model_json_schema(),
            },
        )
        data = json.loads(response)
        return data["title"], data["content"]

    async def _call_deepseek(
        self, prompt: str, max_tokens: int = 2000, response_format: dict = None
    ) -> str:
        """Make API call to DeepSeek using latest non-reasoner model"""

        try:
            # Using deepseek-chat as the latest non-reasoner model
            # This model is optimized for general chat and text generation tasks
            # For reasoning tasks, consider deepseek-reasoner models

            # Handle response_format properly
            if response_format is None:
                response_format = {"type": "text"}
            else:
                response_format = response_format.copy()
                response_format["type"] = "text"

            response = self.client.chat.completions.create(
                model="deepseek-chat",  # Latest non-reasoner model for general tasks
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=max_tokens,
                response_format=response_format,
            )

            return response.choices[0].message.content

        except Exception as e:
            raise Exception(f"DeepSeek API error: {str(e)}")


# Create a global instance
deepseek_service = DeepSeekService()
