# aiops-agent/agent/react_agent.py
# ============================================================
# INTELLIGENCE PLANE — Step 2: REASON + PLAN (v1: LLM-powered)
#
# AI Agent sử dụng ReAct pattern (Reasoning + Acting)
# với Local LLM (Ollama) hoặc Azure OpenAI.
#
# ReAct loop:
#   Thought → Action → Observation → Thought → ... → Final Answer
#
# Implements the ReAct pattern using Ollama REST API directly
# (no heavy LangChain dependency — more reliable, more educational)
# ============================================================

import os
import json
import logging
import re
import requests

from .tools.prometheus_tool import query_metrics
from .tools.scale_tool import scale_deployment
from .tools.networkpolicy_tool import apply_network_policy

logger = logging.getLogger("react-agent")

# --- Configuration ---
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:1.5b")
MAX_ITERATIONS = int(os.environ.get("MAX_REACT_ITERATIONS", "5"))

# --- Available Tools ---
TOOLS = {
    "query_metrics": {
        "func": query_metrics,
        "description": (
            "Query current system metrics from Prometheus. "
            "Input: metric name — one of: all, latency, error_rate, request_rate. "
            "Returns natural language description of current values."
        ),
    },
    "scale_deployment": {
        "func": lambda x: scale_deployment(int(x)),
        "description": (
            "Scale the target-app by setting replica count. "
            "Input: number of replicas (integer 1-10). "
            "Use when legitimate overload is detected (not DDoS)."
        ),
    },
    "apply_network_policy": {
        "func": apply_network_policy,
        "description": (
            "Block traffic from a suspicious IP CIDR. "
            "Input: CIDR string, e.g. '10.0.0.5/32'. "
            "Use when DDoS attack is suspected."
        ),
    },
}

# --- System Prompt ---
SYSTEM_PROMPT = """You are an AIOps Agent responsible for maintaining QoS (latency < 200ms) for a medical IoT system.

You have access to these tools:
{tools_desc}

Use the ReAct pattern. For EACH step, write EXACTLY in this format:
Thought: <your reasoning about the situation>
Action: <tool_name>
Action Input: <input for the tool>

After receiving an Observation, continue reasoning.
When you have enough information, give your final decision:
Thought: I have analyzed the situation and decided on the best action.
Final Answer: {{"action": "SCALE_UP|BLOCK_IP|NO_ACTION", "reason": "<brief explanation>", "details": {{}}}}

IMPORTANT RULES:
- Priority: Block malicious IP FIRST → Scale if still overloaded → Verify
- Never scale above 10 replicas
- If request rate > 100 req/s, suspect DDoS attack
- If latency p99 > 200ms with moderate request rate, it's legitimate overload
- Always explain your chain of thought
"""


def _build_tools_description() -> str:
    """Build tools description for the system prompt."""
    lines = []
    for name, info in TOOLS.items():
        lines.append(f"- {name}: {info['description']}")
    return "\n".join(lines)


def _call_ollama(messages: list[dict]) -> str:
    """Call Ollama chat API and return the response text."""
    try:
        resp = requests.post(
            f"{OLLAMA_HOST}/api/chat",
            json={
                "model": OLLAMA_MODEL,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "num_predict": 512,
                },
            },
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json().get("message", {}).get("content", "")
    except requests.exceptions.ConnectionError:
        logger.error(f"Cannot connect to Ollama at {OLLAMA_HOST}")
        return ""
    except Exception as e:
        logger.error(f"Ollama API error: {e}")
        return ""


def _parse_action(text: str) -> tuple[str, str] | None:
    """Parse Action and Action Input from LLM response."""
    action_match = re.search(r"Action:\s*(.+)", text)
    input_match = re.search(r"Action Input:\s*(.+)", text)
    if action_match and input_match:
        action = action_match.group(1).strip()
        action_input = input_match.group(1).strip()
        return action, action_input
    return None


def _parse_final_answer(text: str) -> dict | None:
    """Parse Final Answer JSON from LLM response."""
    if "Final Answer:" not in text:
        return None
    try:
        # Extract JSON after "Final Answer:"
        fa_text = text.split("Final Answer:")[-1].strip()
        # Find JSON object
        json_match = re.search(r'\{.*\}', fa_text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
    except (json.JSONDecodeError, IndexError):
        pass
    return None


def _execute_tool(action: str, action_input: str) -> str:
    """Execute a tool and return the observation."""
    if action in TOOLS:
        try:
            result = TOOLS[action]["func"](action_input)
            return str(result)
        except Exception as e:
            return f"Error executing {action}: {e}"
    return f"Unknown tool: {action}. Available tools: {list(TOOLS.keys())}"


def run_react_agent(context_prompt: str) -> dict:
    """Run the ReAct agent loop with the given context.

    Args:
        context_prompt: Natural language context from context_builder

    Returns:
        dict with keys: action, reason, details, reasoning_chain
    """
    tools_desc = _build_tools_description()
    system_msg = SYSTEM_PROMPT.format(tools_desc=tools_desc)

    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": context_prompt},
    ]

    reasoning_chain = []

    for iteration in range(MAX_ITERATIONS):
        logger.info(f"  ReAct iteration {iteration + 1}/{MAX_ITERATIONS}")

        # Call LLM
        response = _call_ollama(messages)
        if not response:
            logger.warning("  Empty LLM response, falling back")
            return {
                "action": "NO_ACTION",
                "reason": "LLM failed to respond",
                "details": {},
                "reasoning_chain": reasoning_chain,
            }

        logger.info(f"  LLM: {response[:200]}...")
        reasoning_chain.append({"iteration": iteration + 1, "llm_response": response})

        # Check for Final Answer
        final = _parse_final_answer(response)
        if final:
            logger.info(f"  ✅ Final Answer: {final}")
            final["reasoning_chain"] = reasoning_chain
            return final

        # Check for Action
        parsed = _parse_action(response)
        if parsed:
            action, action_input = parsed
            logger.info(f"  🔧 Action: {action}({action_input})")

            observation = _execute_tool(action, action_input)
            logger.info(f"  👀 Observation: {observation}")

            reasoning_chain.append({
                "action": action,
                "input": action_input,
                "observation": observation,
            })

            # Add to conversation for next iteration
            messages.append({"role": "assistant", "content": response})
            messages.append({
                "role": "user",
                "content": f"Observation: {observation}\n\nContinue your reasoning.",
            })
        else:
            # No action and no final answer — ask LLM to decide
            messages.append({"role": "assistant", "content": response})
            messages.append({
                "role": "user",
                "content": (
                    "Please provide either an Action to take, or your Final Answer "
                    "in the JSON format specified."
                ),
            })

    # Max iterations reached — extract best guess
    logger.warning("  Max iterations reached, forcing decision")
    return {
        "action": "NO_ACTION",
        "reason": "Max reasoning iterations reached without clear decision",
        "details": {},
        "reasoning_chain": reasoning_chain,
    }


def check_ollama_available() -> bool:
    """Check if Ollama is running and the model is available."""
    try:
        resp = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=5)
        if resp.status_code == 200:
            models = [m["name"] for m in resp.json().get("models", [])]
            if any(OLLAMA_MODEL in m for m in models):
                logger.info(f"Ollama ready: model {OLLAMA_MODEL} available")
                return True
            else:
                logger.warning(
                    f"Ollama running but model {OLLAMA_MODEL} not found. "
                    f"Available: {models}. Run: docker compose exec ollama ollama pull {OLLAMA_MODEL}"
                )
                return False
        return False
    except Exception:
        logger.warning(f"Ollama not available at {OLLAMA_HOST}")
        return False
