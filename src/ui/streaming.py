# src/ui/streaming.py

"""
Module de streaming moderne pour Chainlit + Pydantic-AI.

Cette implémentation suit les meilleures pratiques officielles de Pydantic-AI et Chainlit
pour un streaming en temps réel avec affichage transparent des outils MCP.

Architecture:
- Utilise `agent.iter()` pour parcourir le graphe d'exécution nœud par nœud
- Traite les différents types de nœuds (UserPrompt, ModelRequest, CallTools, End)
- Utilise les événements de streaming de Pydantic-AI pour le temps réel
- Intègre parfaitement avec Chainlit (cl.Message.stream_token, cl.Step)
"""

import logging
from typing import List, Optional, Dict

import chainlit as cl
from pydantic_ai import Agent
from pydantic_ai.messages import (
    ModelMessage,
    PartStartEvent,
    PartDeltaEvent,
    FunctionToolCallEvent,
    FunctionToolResultEvent,
    TextPart,
    TextPartDelta,
    ToolCallPartDelta,
    ModelResponse,
)
from pydantic_ai.usage import UsageLimits
from pydantic_ai.exceptions import UsageLimitExceeded

from src.agent.agent import create_synthesis_agent

# Configuration du logging
logger = logging.getLogger("datainclusion.streaming")

# Constante pour limiter l'historique
MAX_HISTORY_LENGTH = 50


def trim_message_history(messages: List[ModelMessage]) -> List[ModelMessage]:
    """
    Limite l'historique des messages pour éviter les problèmes de mémoire.

    Args:
        messages: Liste des messages

    Returns:
        Liste tronquée des messages les plus récents
    """
    if len(messages) <= MAX_HISTORY_LENGTH:
        return messages
    return messages[-MAX_HISTORY_LENGTH:]


async def _handle_user_prompt_node(node) -> None:
    """Gère le nœud UserPromptNode."""
    logger.debug("📨 UserPromptNode: %s", node.user_prompt)
    # Pas d'affichage spécial nécessaire, le message utilisateur est déjà affiché


async def _handle_model_request_node(
    node, agent_run, response_message: Optional[cl.Message]
) -> cl.Message:
    """Gère le nœud ModelRequestNode avec streaming des tokens."""
    logger.debug("🧠 ModelRequestNode: Streaming de la réponse LLM...")
    # Streamer la réponse du modèle
    async with node.stream(agent_run.ctx) as request_stream:
        async for event in request_stream:
            response_message = await _handle_model_event(event, response_message)
    return response_message


async def _handle_model_event(
    event, response_message: Optional[cl.Message]
) -> cl.Message:
    """Gère un événement de streaming du modèle."""
    # Début d'une nouvelle partie de réponse
    if isinstance(event, PartStartEvent):
        logger.debug(
            "🔄 Début partie %s: %s",
            event.index,
            type(event.part).__name__,
        )
        # Si c'est une partie texte, créer le message de réponse
        if isinstance(event.part, TextPart) and event.part.content:
            if response_message is None:
                response_message = cl.Message(content="")
                await response_message.send()
            # Streamer le contenu initial
            if response_message:
                await response_message.stream_token(event.part.content)

    # Delta de texte - streaming en temps réel
    elif isinstance(event, PartDeltaEvent):
        if isinstance(event.delta, TextPartDelta):
            # Créer le message de réponse maintenant, quand on a du contenu
            if response_message is None and event.delta.content_delta:
                response_message = cl.Message(content="")
                await response_message.send()

            # Streamer chaque token vers Chainlit
            if event.delta.content_delta and response_message:
                await response_message.stream_token(event.delta.content_delta)

        elif isinstance(event.delta, ToolCallPartDelta):
            # Les appels d'outils sont traités dans CallToolsNode
            logger.debug("🔧 Tool call delta: %s", event.delta.args_delta)

    return response_message


async def _handle_call_tools_node(
    node,
    agent_run,
    active_tool_steps: Dict[str, cl.Step],
    tool_call_counter: int,
    parent_step: cl.Step,
) -> int:
    """Gère le nœud CallToolsNode avec affichage des outils."""
    logger.debug("🛠️ CallToolsNode: Traitement des outils MCP...")

    # Streamer les événements des outils
    async with node.stream(agent_run.ctx) as tools_stream:
        async for event in tools_stream:
            if isinstance(event, FunctionToolCallEvent):
                tool_call_counter += 1
                tool_call_counter = await _handle_tool_call_event(
                    event, active_tool_steps, tool_call_counter, parent_step
                )
            elif isinstance(event, FunctionToolResultEvent):
                await _handle_tool_result_event(event, active_tool_steps)

    return tool_call_counter


async def _handle_tool_call_event(
    event,
    active_tool_steps: Dict[str, cl.Step],
    tool_call_counter: int,
    parent_step: cl.Step,
) -> int:
    """Gère un événement d'appel d'outil."""
    tool_name = event.part.tool_name
    tool_args = event.part.args
    tool_call_id = event.part.tool_call_id

    logger.info("🔧 Appel outil: %s", tool_name)

    # Créer un Step pour l'appel d'outil
    step = cl.Step(
        name=f"{tool_name}",
        type="tool",
        show_input="json" if tool_args else False,
        language="json",
        parent_id=parent_step.id,
    )

    # Entrer explicitement dans le contexte du step enfant pour l'afficher sous le parent
    await step.__aenter__()

    # Configurer l'input du step et l'envoyer au client
    if tool_args:
        step.input = tool_args
        await step.update()

    # Stocker le Step pour récupérer le résultat plus tard
    active_tool_steps[tool_call_id] = step

    return tool_call_counter


async def _handle_tool_result_event(
    event, active_tool_steps: Dict[str, cl.Step]
) -> None:
    """Gère un événement de résultat d'outil."""
    tool_call_id = event.tool_call_id
    result_content = event.result.content

    # Récupérer le Step correspondant
    if tool_call_id in active_tool_steps:
        step = active_tool_steps[tool_call_id]

        # Configurer l'output du step
        step.output = str(result_content)[:1000]  # Limiter pour l'affichage

        # Finaliser le step
        await step.__aexit__(None, None, None)

        # Nettoyer le dictionnaire
        del active_tool_steps[tool_call_id]

        logger.info(
            "✅ Résultat outil reçu: %s chars",
            len(str(result_content)),
        )


async def _handle_end_node(node, response_message: Optional[cl.Message]) -> cl.Message:
    """Gère le nœud EndNode."""
    logger.info("🏁 EndNode: Exécution terminée")
    final_output = str(node.data.output)

    # Si pas encore de message de réponse créé, le créer maintenant
    if response_message is None:
        response_message = cl.Message(content=final_output)
        await response_message.send()
    # Si pas encore de contenu dans le message (cas rare), l'ajouter
    elif not response_message.content.strip():
        await response_message.stream_token(final_output)

    return response_message


async def _cleanup_on_error(active_tool_steps: Dict[str, cl.Step]) -> None:
    """Nettoie les steps en cas d'erreur."""
    for step in active_tool_steps.values():
        try:
            await step.__aexit__(None, None, None)
        except Exception:
            pass


async def _handle_usage_limit_exceeded(
    agent_run, message: str, message_history: List[ModelMessage]
) -> List[ModelMessage]:
    """Gère l'exception UsageLimitExceeded en streamant la réponse de synthèse."""
    logger.warning("⚠️ Limite d'appels d'outils atteinte. Démarrage de la synthèse.")

    # Récupérer l'historique complet pour donner le contexte à l'agent de synthèse.
    full_history = agent_run.ctx.state.message_history

    synthesis_agent = create_synthesis_agent()
    synthesis_prompt = (
        f"La limite d'appels d'outils a été atteinte. En te basant sur l'historique de "
        f"conversation, synthétise une réponse finale et complète à la dernière question de l'utilisateur : '{message}'"
    )

    response_message: Optional[cl.Message] = None

    # Utiliser la même logique de streaming que l'agent principal pour l'agent de synthèse.
    async with synthesis_agent:
        async with synthesis_agent.iter(
            synthesis_prompt, message_history=full_history
        ) as synthesis_run:
            async for node in synthesis_run:
                if Agent.is_model_request_node(node):
                    response_message = await _handle_model_request_node(
                        node, synthesis_run, response_message
                    )

    # Finaliser le message streamé.
    if response_message:
        await response_message.update()

    # S'assurer que le résultat du run de synthèse est bien récupéré.
    if synthesis_run.result:
        synthesis_text = str(synthesis_run.result.output)
        # Ajouter la réponse de synthèse à l'historique de la conversation principale.
        synthesis_response = ModelResponse(parts=[TextPart(content=synthesis_text)])
        full_history.append(synthesis_response)
    else:
        logger.error("Le run de l'agent de synthèse n'a pas produit de résultat.")

    # Retourner l'historique complet pour que la session puisse continuer.
    return full_history


async def process_agent_modern_with_history(
    agent: Agent,
    message: str,
    message_history: Optional[List[ModelMessage]] = None,
    tool_call_limit: Optional[int] = None,
) -> List[ModelMessage]:
    """
    Point d'entrée principal pour le traitement moderne avec streaming parfait.
    """
    logger.info("🎯 Traitement moderne avec streaming parfait")

    parent_tools_step: Optional[cl.Step] = None
    active_tool_steps: Dict[str, cl.Step] = {}

    try:
        usage_limits_config = (
            UsageLimits(request_limit=tool_call_limit) if tool_call_limit else None
        )

        logger.info("🚀 Démarrage du streaming parfait pour: %s...", message[:50])

        response_message: Optional[cl.Message] = None
        tool_call_counter = 0

        async with agent:
            try:
                async with agent.iter(
                    message,
                    message_history=message_history or [],
                    usage_limits=usage_limits_config,
                ) as agent_run:
                    async for node in agent_run:
                        if Agent.is_user_prompt_node(node):
                            await _handle_user_prompt_node(node)
                        elif Agent.is_model_request_node(node):
                            response_message = await _handle_model_request_node(
                                node, agent_run, response_message
                            )
                        elif Agent.is_call_tools_node(node):
                            if parent_tools_step is None:
                                parent_tools_step = cl.Step(
                                    name="data_gouv_fr", type="tool"
                                )
                                await parent_tools_step.__aenter__()
                            tool_call_counter = await _handle_call_tools_node(
                                node,
                                agent_run,
                                active_tool_steps,
                                tool_call_counter,
                                parent_tools_step,
                            )
                        elif Agent.is_end_node(node):
                            response_message = await _handle_end_node(
                                node, response_message
                            )

            except UsageLimitExceeded:
                # `agent_run` est disponible ici car l'exception est levée à l'intérieur du contexte.
                return await _handle_usage_limit_exceeded(
                    agent_run, message, message_history or []
                )

        if response_message is not None:
            await response_message.update()

        if parent_tools_step is not None:
            await parent_tools_step.__aexit__(None, None, None)

        if agent_run.result is not None:
            all_messages = agent_run.result.all_messages()
            trimmed_messages = trim_message_history(all_messages)
        else:
            logger.warning("agent_run.result est None, retour de l'historique original")
            trimmed_messages = message_history or []

        logger.info(
            "✅ Streaming terminé - Historique: %s messages", len(trimmed_messages)
        )
        return trimmed_messages

    except Exception as e:
        logger.error("❌ Erreur dans le streaming parfait: %s", e, exc_info=True)

        if parent_tools_step:
            try:
                parent_tools_step.is_error = True
                await parent_tools_step.__aexit__(None, None, None)
            except Exception:
                pass
        await _cleanup_on_error(active_tool_steps)

        error_msg = cl.Message(
            content=f"❌ **Erreur lors du traitement:**\n\n{str(e)}\n\nVeuillez réessayer ou reformuler votre question."
        )
        await error_msg.send()

        return message_history or []
