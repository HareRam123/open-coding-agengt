from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import streamlit as st

from agent.agent import Agent
from config.loader import load_config
from web_frontend.runner import run_prompt


def _ensure_state() -> None:
    if "config" not in st.session_state:
        st.session_state.config = load_config(cwd=Path.cwd())

    if "agent" not in st.session_state:
        st.session_state.agent = Agent(st.session_state.config)

    if "messages" not in st.session_state:
        st.session_state.messages = []


def _reset_chat() -> None:
    old_agent = st.session_state.get("agent")
    if old_agent is not None:
        try:
            asyncio.run(old_agent.__aexit__(None, None, None))
        except Exception:
            pass

    st.session_state.agent = Agent(st.session_state.config)
    st.session_state.messages = []


def _render_sidebar() -> None:
    config = st.session_state.config
    with st.sidebar:
        st.header("Session")
        st.write(f"Model: {config.model_name}")
        st.write(f"Working Dir: {config.cwd}")
        st.write(f"Max Turns: {config.max_turns}")
        st.write(f"Max Tool Output Tokens: {config.max_tool_output_tokens}")

        if st.button("Reset Chat", use_container_width=True):
            _reset_chat()
            st.rerun()

        if st.button("Show LLM Messages", use_container_width=True):
            payload = st.session_state.agent.session.context_manager.get_messages()
            st.session_state.latest_payload = payload

        payload = st.session_state.get("latest_payload")
        if payload is not None:
            st.caption("Serialized payload sent to the model")
            st.json(payload)
            st.download_button(
                "Download payload JSON",
                data=json.dumps(payload, indent=2, ensure_ascii=False),
                file_name="llm_messages.json",
                mime="application/json",
                use_container_width=True,
            )


def _render_history() -> None:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"] or "")

            for tool_event in msg.get("tool_events", []):
                name = tool_event.get("name", "unknown")
                phase = tool_event.get("phase", "")
                label = f"Tool {name} ({phase})"
                with st.expander(label, expanded=False):
                    st.json(tool_event)

            for error in msg.get("errors", []):
                st.error(error)


def _handle_prompt(prompt: str) -> None:
    st.session_state.messages.append({"role": "user", "content": prompt})

    result = asyncio.run(run_prompt(st.session_state.agent, prompt))
    assistant_text = result["response"] or "(no response)"

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": assistant_text,
            "tool_events": result["tool_events"],
            "errors": result["errors"],
        }
    )


def render() -> None:
    st.set_page_config(page_title="Open Coding Agent", page_icon="🧠", layout="wide")

    _ensure_state()

    st.title("Open Coding Agent")
    st.caption("Streamlit dashboard frontend for the existing agent runtime")

    _render_sidebar()
    _render_history()

    prompt = st.chat_input("Ask the agent...")
    if prompt:
        _handle_prompt(prompt)
        st.rerun()
