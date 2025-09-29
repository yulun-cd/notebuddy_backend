import json
import openai
import os
from typing import List, Dict
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

    async def generate_note_from_transcript(self, transcript_content: str) -> str:
        """Generate a structured note from transcript"""

        prompt = f"""
请分析以下内容，并生成一个结构化的笔记。保持生成的笔记与原内容使用同一种语言。

内容：
{transcript_content}

请结构化这个内容，使其观点表达更加清晰，并且列出内容中的逻辑链条。
不要擅自凭空生成内容，尽量忠于原本的事实。
保持生成笔记的长度大致相当于原内容长度，但是你不用非常遵守这个原则。
请直接从生成的结构化笔记开始返回，不要包含除结构化笔记外的任何内容。
请在title中返回一个简短的标题，在content中返回结构化笔记的内容。
请保持只使用最顶层的json格式，不要在title或者content中嵌套json。
不要在json object之前或之后添加任何多余的文本。
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

    async def generate_follow_up_questions(self, note_content: str) -> List[str]:
        """Generate follow-up questions based on the note content"""

        prompt = f"""
请分析以下笔记内容，并生成3-5个相关的后续问题。

笔记内容：
{note_content}

请生成能够帮助澄清、加深理解或补充笔记信息的问题。
你可以想象你是一个听者，在听完了上述笔记内容之后想要向演讲者提出问题。
请保持生成的问题与笔记内容为同一种语言。
请将问题在questions中返回为一个列表。
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
        self, note_content: str, question: str, answer: str
    ) -> str:
        """
        Update the note by incorporating a single answer to a follow-up question
        """

        prompt = f"""
请分析以下笔记内容和问答内容，然后通过整合答案来更新笔记。

原始笔记内容：
{note_content}

问答内容：
问题：{question}
回答：{answer}

请通过整合答案来更新原始笔记。
请保持新生成的笔记的结构和长度略长于原始笔记。
请保持使用同一种语言。
请直接从生成的结构化笔记开始返回，不要包含除结构化笔记外的任何内容。
请在title中返回一个简短的标题，在content中返回结构化笔记的内容。
请保持只使用最顶层的json格式，不要在title或者content中嵌套json。
不要在json object之前或之后添加任何多余的文本。
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
