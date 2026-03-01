# AI Pipeline Contract
- Route order: rule -> faq/rag -> llm -> fallback
- Max clarify rounds: 1
- Escalate: только high-risk или после clarify без результата
- Возвращать structured result: text, route, confidence, evidence, debug