from dataclasses import dataclass, field
import time
import anthropic

MAX_RETRIES = 4
RETRY_BACKOFF = [2, 4, 8, 16]
RETRYABLE_STATUS_CODES = {529, 500, 502, 503, 504}

# Pricing for claude-opus-4-7 per million tokens
_PRICE_INPUT = 5.00
_PRICE_OUTPUT = 25.00
_PRICE_CACHE_WRITE = 6.25   # 25% surcharge on cache creation
_PRICE_CACHE_READ = 0.50    # 90% discount on cache reads

SYSTEM_PROMPT = """You are an email classification assistant for a SaaS company.

Your job is to classify incoming emails into one of three categories:

1. **support** — The sender is an existing customer or user who needs help with a product
   issue, account problem, bug report, or technical question. Examples: login issues,
   billing problems, feature questions, error reports.

2. **lead** — The sender is a prospective customer interested in purchasing, evaluating,
   or learning more about the product. Examples: pricing inquiries, demo requests,
   enterprise sales inquiries, partnership proposals.

3. **unknown** — The email does not clearly fit either category (spam, internal,
   personal correspondence, ambiguous intent).

When classifying:
- If an email contains both support and lead signals, choose the PRIMARY intent based
  on the most urgent or prominent request.
- Provide a confidence score from 0.0 to 1.0 reflecting how certain you are.
- Provide a brief reasoning explaining your classification decision.

Always use the classify_email tool to return your structured response."""

CLASSIFICATION_TOOL = {
    "name": "classify_email",
    "description": "Classify an email as a support ticket, sales lead, or unknown.",
    "input_schema": {
        "type": "object",
        "properties": {
            "classification": {
                "type": "string",
                "enum": ["support", "lead", "unknown"],
                "description": "The email category",
            },
            "confidence": {
                "type": "number",
                "minimum": 0.0,
                "maximum": 1.0,
                "description": "Confidence score from 0.0 to 1.0",
            },
            "reasoning": {
                "type": "string",
                "description": "Brief explanation of the classification decision",
            },
        },
        "required": ["classification", "confidence", "reasoning"],
    },
}


def _calculate_cost(usage) -> float:
    input_tokens = usage.input_tokens
    output_tokens = usage.output_tokens
    cache_creation = getattr(usage, "cache_creation_input_tokens", 0) or 0
    cache_read = getattr(usage, "cache_read_input_tokens", 0) or 0
    regular_input = max(0, input_tokens - cache_creation - cache_read)
    return (
        regular_input * _PRICE_INPUT / 1_000_000
        + cache_creation * _PRICE_CACHE_WRITE / 1_000_000
        + cache_read * _PRICE_CACHE_READ / 1_000_000
        + output_tokens * _PRICE_OUTPUT / 1_000_000
    )


@dataclass
class ClassificationResult:
    classification: str
    confidence: float
    reasoning: str
    token_usage: dict = field(default_factory=dict)


class ClassificationError(Exception):
    pass


def classify_email(email: dict) -> ClassificationResult:
    from_field = email.get("from", "Unknown")
    subject = email.get("subject", "(no subject)")
    body = email.get("body", "")
    message_id = email.get("message_id", "")

    email_text = f"""Message-ID: {message_id}
From: {from_field}
Subject: {subject}

{body}"""

    client = anthropic.Anthropic()

    last_error = None
    response = None
    for attempt in range(MAX_RETRIES):
        try:
            response = client.messages.create(
                model="claude-opus-4-7",
                max_tokens=1024,
                system=[
                    {
                        "type": "text",
                        "text": SYSTEM_PROMPT,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                tools=[CLASSIFICATION_TOOL],
                tool_choice={"type": "tool", "name": "classify_email"},
                messages=[
                    {
                        "role": "user",
                        "content": f"Classify this email:\n\n{email_text}",
                    }
                ],
            )
            break
        except anthropic.APIStatusError as e:
            if e.status_code in RETRYABLE_STATUS_CODES and attempt < MAX_RETRIES - 1:
                wait = RETRY_BACKOFF[attempt]
                print(f"[classifier] API {e.status_code} on attempt {attempt + 1}/{MAX_RETRIES}, retrying in {wait}s...")
                time.sleep(wait)
                last_error = e
                continue
            raise ClassificationError(f"Anthropic API error: {e}") from e
        except anthropic.APIError as e:
            raise ClassificationError(f"Anthropic API error: {e}") from e
    else:
        raise ClassificationError(f"Anthropic API unavailable after {MAX_RETRIES} attempts: {last_error}")

    tool_use_block = next(
        (block for block in response.content if block.type == "tool_use"),
        None,
    )
    if tool_use_block is None:
        raise ClassificationError("Claude did not return a tool_use block")

    usage = response.usage
    token_usage = {
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "cache_creation_input_tokens": getattr(usage, "cache_creation_input_tokens", 0) or 0,
        "cache_read_input_tokens": getattr(usage, "cache_read_input_tokens", 0) or 0,
        "cost_usd": _calculate_cost(usage),
    }

    data = tool_use_block.input
    return ClassificationResult(
        classification=data["classification"],
        confidence=float(data["confidence"]),
        reasoning=data["reasoning"],
        token_usage=token_usage,
    )
