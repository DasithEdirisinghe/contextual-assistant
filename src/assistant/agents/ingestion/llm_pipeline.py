from __future__ import annotations

import json
import logging
import time

from langchain_core.messages import AIMessage
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda

from assistant.agents.ingestion.schemas import IngestionExtractedCardSchema
from assistant.config.settings import Settings
from assistant.llm.client import build_chat_model
from assistant.llm.parsing import extract_json_block
from assistant.prompts import load_prompt_versioned
from assistant.schemas.card import ExtractedCard

logger = logging.getLogger(__name__)


class IngestionLLMPipeline:
    def __init__(self, settings: Settings, prompt_version: str):
        self.settings = settings
        self.prompt_version = prompt_version
        self.parser = PydanticOutputParser(pydantic_object=IngestionExtractedCardSchema)
        self.prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "{system_prompt}\n\nReturn strictly valid JSON only.\n{format_instructions}",
                ),
                ("human", "{user_note}"),
            ]
        )
        self.llm = build_chat_model(settings)
        self.chain = (
            RunnableLambda(self._build_prompt_inputs_node)
            | RunnableLambda(self._build_messages_node)
            | RunnableLambda(self._invoke_llm_node)
            | RunnableLambda(self._parse_response_node)
            | RunnableLambda(self._to_domain_model_node)
        )

    def _build_prompt_inputs_node(self, payload: dict[str, str]) -> dict[str, str]:
        raw_text = payload["raw_text"]
        logger.debug("IngestionLLM node: build_prompt_inputs raw_text_len=%s", len(raw_text))
        rendered = load_prompt_versioned("ingestion", version=self.prompt_version, raw_note=raw_text)
        return {
            "system_prompt": rendered,
            "format_instructions": self.parser.get_format_instructions(),
            "user_note": raw_text,
        }

    def _build_messages_node(self, prompt_inputs: dict[str, str]):
        logger.debug("IngestionLLM node: build_messages")
        return self.prompt.format_messages(**prompt_inputs)

    def _invoke_llm_node(self, messages) -> tuple[AIMessage, int]:
        logger.debug("IngestionLLM node: invoke_llm")
        start = time.perf_counter()
        response = self.llm.invoke(messages)
        latency_ms = int((time.perf_counter() - start) * 1000)
        logger.debug("IngestionLLM node: invoke_llm_done latency_ms=%s", latency_ms)
        return response, latency_ms

    def _parse_response_node(self, payload: tuple[AIMessage, int]) -> tuple[IngestionExtractedCardSchema, int]:
        message, latency_ms = payload
        content = message.content if isinstance(message.content, str) else json.dumps(message.content)
        logger.debug("IngestionLLM node: parse_response content_len=%s", len(content))

        try:
            parsed = self.parser.parse(content)
            logger.debug("IngestionLLM node: parse_response_success primary")
            logger.debug("IngestionLLM node: parse_response_success primary parsed=%s", parsed)
            return parsed, latency_ms
        except Exception:
            logger.debug("IngestionLLM node: parse_response_primary_failed attempting_json_extract", exc_info=True)

        cleaned = extract_json_block(content)
        parsed = IngestionExtractedCardSchema.model_validate_json(cleaned)
        logger.debug("IngestionLLM node: parse_response_success fallback_json_extract")
        return parsed, latency_ms

    def _to_domain_model_node(self, payload: tuple[IngestionExtractedCardSchema, int]) -> tuple[ExtractedCard, int]:
        parsed, latency_ms = payload
        logger.debug("IngestionLLM node: to_domain_model")

        card = ExtractedCard(
            card_type=parsed.card_type,
            description=parsed.description.strip(),
            date_text=parsed.date_text,
            assignee=parsed.assignee,
            context_keywords=[k.strip().lower() for k in parsed.context_keywords if k.strip()],
            reasoning_steps=[step.strip() for step in parsed.reasoning_steps if step and step.strip()],
            confidence=parsed.confidence,
        )
        logger.debug("IngestionLLM node: to_domain_model_done")
        return card, latency_ms

    def extract(self, raw_text: str) -> tuple[ExtractedCard, int, str]:
        logger.debug("IngestionLLM pipeline start")
        card, latency = self.chain.invoke({"raw_text": raw_text})
        logger.debug("IngestionLLM pipeline end")
        return card, latency, self.prompt_version
