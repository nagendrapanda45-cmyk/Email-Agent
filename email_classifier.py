from dataclasses import dataclass
import anthropic

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


@dataclass
class ClassificationResult:
    classification: str
    confidence: float
    reasoning: str


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
    except anthropic.APIError as e:
        raise ClassificationError(f"Anthropic API error: {e}") from e

    tool_use_block = next(
        (block for block in response.content if block.type == "tool_use"),
        None,
    )
    if tool_use_block is None:
        raise ClassificationError("Claude did not return a tool_use block")

    data = tool_use_block.input
    return ClassificationResult(
        classification=data["classification"],
        confidence=float(data["confidence"]),
        reasoning=data["reasoning"],
    )
