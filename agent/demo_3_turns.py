"""Demonstração de conversa multi-turno (3 turnos) com o agente SupportDesk.

Uso (a partir da raiz do repositório):
    python -m agent.demo_3_turns
    python -m agent.demo_3_turns --interactive
    python -m agent.demo_3_turns --save-transcript agent/conversa_3_turnos.md
"""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
from typing import Sequence

from agents import Runner, TResponseInputItem

from .support_agent import SupportDeskConfig, build_support_agent

DEFAULT_USER_TURNS: tuple[str, ...] = (
    "Olá! Meu fone Bluetooth chegou ontem, mas não liga e a luz de carga nem acende.",
    "Já testei dois cabos USB-C diferentes e deixei 1 hora na tomada, sem sinal de vida. Quero meu dinheiro de volta.",
    "Obrigado! Antes de finalizar o reembolso, também notei duas cobranças na minha fatura do cartão. Como verifico isso?",
)


def _extract_tool_calls(new_items: Sequence[object]) -> list[tuple[str, str]]:
    """Extrai chamadas e saídas de ferramentas registradas no turno para exibição."""
    events: list[tuple[str, str]] = []
    for item in new_items:
        raw = getattr(item, "raw_item", None)
        item_type = getattr(item, "type", "")
        if item_type == "tool_call_item" and raw is not None:
            name = getattr(raw, "name", "tool")
            args = getattr(raw, "arguments", "")
            events.append(("tool_call", f"{name}({args})"))
        elif item_type == "tool_call_output_item":
            output = getattr(item, "output", "")
            events.append(("tool_output", str(output)))
    return events


async def run_conversation(
    turns: Sequence[str] = DEFAULT_USER_TURNS,
    interactive: bool = False,
) -> list[dict[str, object]]:
    """Executa uma conversa de múltiplos turnos mantendo o histórico via Runner.run."""
    config = SupportDeskConfig.from_env()
    agent, client = build_support_agent(config=config)
    history: str | list[TResponseInputItem] = []
    transcript: list[dict[str, object]] = []

    try:
        if interactive:
            print("Modo interativo SupportDesk (digite 'sair' para encerrar)\n")
            turn_index = 1
            while True:
                user_text = input(f"Turno {turn_index} - Cliente: ").strip()
                if not user_text or user_text.lower() in {"sair", "exit", "quit"}:
                    break
                turn_input: str | list[TResponseInputItem] = (
                    user_text
                    if not history
                    else [*history, {"role": "user", "content": user_text}]
                )
                result = await Runner.run(agent, turn_input)
                history = result.to_input_list()
                tool_events = _extract_tool_calls(result.new_items)
                for kind, detail in tool_events:
                    print(f"  [{kind}] {detail}")
                print(f"Turno {turn_index} - Agente: {result.final_output}\n")
                transcript.append(
                    {
                        "turn": turn_index,
                        "user": user_text,
                        "tools": tool_events,
                        "assistant": str(result.final_output),
                    }
                )
                turn_index += 1
        else:
            for turn_index, user_text in enumerate(turns, start=1):
                turn_input = (
                    user_text
                    if not history
                    else [*history, {"role": "user", "content": user_text}]
                )
                result = await Runner.run(agent, turn_input)
                history = result.to_input_list()
                tool_events = _extract_tool_calls(result.new_items)

                print(f"=== Turno {turn_index} ===")
                print(f"Cliente: {user_text}")
                for kind, detail in tool_events:
                    print(f"[{kind}] {detail}")
                print(f"Agente: {result.final_output}\n")

                transcript.append(
                    {
                        "turn": turn_index,
                        "user": user_text,
                        "tools": tool_events,
                        "assistant": str(result.final_output),
                    }
                )
    finally:
        await client.aclose()

    return transcript


def save_transcript_markdown(transcript: Sequence[dict[str, object]], output_path: Path) -> None:
    """Salva o histórico da conversa executada em Markdown para documentação do TP4."""
    lines = ["# Demonstração de Conversa — Agente SupportDesk (3 Turnos)", ""]
    for entry in transcript:
        lines.append(f"## Turno {entry['turn']}")
        lines.append(f"**Cliente:** {entry['user']}")
        lines.append("")
        tools = entry.get("tools") or []
        if tools:
            lines.append("**Chamadas de ferramenta (`POST /classify`):**")
            for kind, detail in tools:
                lines.append(f"- `{kind}`: `{detail}`")
            lines.append("")
        lines.append(f"**Agente:** {entry['assistant']}")
        lines.append("")
    output_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Executa demonstração de 3 turnos do agente SupportDesk (OpenAI Agents SDK + Groq)."
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Inicia chat interativo no terminal em vez dos 3 turnos padrão.",
    )
    parser.add_argument(
        "--save-transcript",
        type=Path,
        default=None,
        help="Caminho opcional para salvar a transcrição executada em Markdown.",
    )
    args = parser.parse_args()

    transcript = asyncio.run(run_conversation(interactive=args.interactive))
    if args.save_transcript and transcript:
        save_transcript_markdown(transcript, args.save_transcript)
        print(f"Transcrição salva em {args.save_transcript}")


if __name__ == "__main__":
    main()
