"""
Module de gestion du streaming de l'agent IA.

Ce module contient toute la logique de streaming et de traitement des nœuds
de l'agent pydantic-ai, séparée de l'interface utilisateur Gradio.
"""

import logging
from typing import List, Dict, AsyncGenerator
import gradio as gr
from pydantic_ai import Agent
from pydantic_ai.messages import (
    FinalResultEvent,
    FunctionToolCallEvent,
    FunctionToolResultEvent,
    PartDeltaEvent,
    PartStartEvent,
    TextPartDelta,
    ToolCallPartDelta,
    TextPart,
)

# Imports locaux
from .components import (
    create_tool_call_message,
    create_tool_result_message,
    create_error_message,
)
from ..agent.history import format_gradio_history
from ..core.logging import log_gradio_message

# Configuration du logging
logger = logging.getLogger("datainclusion.agent.streaming")


async def handle_agent_node(
    node, run_context, response_messages: List[gr.ChatMessage]
) -> AsyncGenerator[List[gr.ChatMessage], None]:
    """
    Gère un nœud de l'agent en déléguant à la fonction appropriée selon le type de nœud.

    Args:
        node: Le nœud de l'agent à traiter
        run_context: Le contexte d'exécution de l'agent
        response_messages: Liste des messages de réponse à modifier

    Yields:
        List[gr.ChatMessage]: Messages mis à jour pour le streaming
    """
    if Agent.is_user_prompt_node(node):
        # Nœud de prompt utilisateur
        logger.info(f"Traitement du message utilisateur: {node.user_prompt}")
        yield response_messages

    elif Agent.is_model_request_node(node):
        # Nœud de requête modèle - déléguer au streaming de la réponse
        async for messages in stream_model_response(
            node, run_context, response_messages
        ):
            yield messages

    elif Agent.is_call_tools_node(node):
        # Nœud d'appel d'outils - déléguer au streaming des appels d'outils
        async for messages in stream_tool_calls(node, run_context, response_messages):
            yield messages

    elif Agent.is_end_node(node):
        # Nœud de fin - traitement terminé
        logger.info("Traitement terminé avec succès")
        yield response_messages


async def stream_model_response(
    node, run_context, response_messages: List[gr.ChatMessage]
) -> AsyncGenerator[List[gr.ChatMessage], None]:
    """
    Gère le streaming de la réponse du modèle.

    Args:
        node: Le nœud de requête modèle
        run_context: Le contexte d'exécution de l'agent
        response_messages: Liste des messages de réponse à modifier

    Yields:
        List[gr.ChatMessage]: Messages mis à jour pour le streaming
    """
    logger.info("Streaming de la requête modèle...")

    # Ajouter un message assistant vide pour le streaming
    streaming_message = gr.ChatMessage(role="assistant", content="")
    response_messages.append(streaming_message)
    yield response_messages

    # Stream les tokens partiels
    async with node.stream(run_context) as request_stream:
        async for event in request_stream:
            if isinstance(event, PartStartEvent):
                logger.debug(f"Début de la partie {event.index}: {event.part}")
                # Traiter le contenu initial si c'est un TextPart
                if isinstance(event.part, TextPart) and event.part.content:
                    # Initialiser le contenu du message avec le contenu initial
                    streaming_message.content = event.part.content
                    yield response_messages

            elif isinstance(event, PartDeltaEvent):
                if isinstance(event.delta, TextPartDelta):
                    # Mettre à jour le message avec le contenu streamé
                    current_content = (
                        str(streaming_message.content)
                        if streaming_message.content
                        else ""
                    )
                    streaming_message.content = (
                        current_content + event.delta.content_delta
                    )
                    yield response_messages
                elif isinstance(event.delta, ToolCallPartDelta):
                    logger.debug(f"Appel d'outil en cours: {event.delta.args_delta}")

            elif isinstance(event, FinalResultEvent):
                logger.debug("Streaming de la réponse terminé")
                yield response_messages


async def stream_tool_calls(
    node, run_context, response_messages: List[gr.ChatMessage]
) -> AsyncGenerator[List[gr.ChatMessage], None]:
    """
    Gère le streaming des appels d'outils MCP.

    Args:
        node: Le nœud d'appel d'outils
        run_context: Le contexte d'exécution de l'agent
        response_messages: Liste des messages de réponse à modifier

    Yields:
        List[gr.ChatMessage]: Messages mis à jour pour le streaming
    """
    logger.info("Traitement des appels d'outils...")

    # Mapper les tool_call_id vers les noms d'outils
    tool_call_map = {}

    async with node.stream(run_context) as handle_stream:
        async for event in handle_stream:
            if isinstance(event, FunctionToolCallEvent):
                # Stocker le nom de l'outil pour usage ultérieur
                tool_call_map[event.part.tool_call_id] = event.part.tool_name

                # Afficher l'appel d'outil en utilisant l'utilitaire
                tool_call_message = create_tool_call_message(
                    event.part.tool_name,
                    event.part.args,
                    event.part.tool_call_id,
                )
                response_messages.append(tool_call_message)
                log_gradio_message(tool_call_message, "TOOL_CALL")
                yield response_messages

            elif isinstance(event, FunctionToolResultEvent):
                # Récupérer le nom de l'outil depuis le mapping
                tool_name = tool_call_map.get(event.tool_call_id, "Outil MCP")

                # Afficher le résultat de l'outil en utilisant l'utilitaire
                result_message = create_tool_result_message(
                    tool_name=tool_name,
                    result=event.result.content,
                    call_id=event.tool_call_id,
                )
                response_messages.append(result_message)
                log_gradio_message(result_message, "TOOL_RESULT")
                yield response_messages


async def process_agent_stream(
    agent, message: str, history: List[Dict[str, str]]
) -> AsyncGenerator[List[gr.ChatMessage], None]:
    """
    Traite le streaming complet d'un agent avec gestion des erreurs.

    Args:
        agent: Instance de l'agent pydantic-ai
        message: Message de l'utilisateur
        history: Historique des messages

    Yields:
        List[gr.ChatMessage]: Messages mis à jour pour le streaming
    """
    try:
        # Convertir l'historique Gradio au format pydantic-ai
        formatted_history = format_gradio_history(history)

        # Initialiser la liste des messages de réponse
        response_messages = []

        # Utiliser l'API avancée d'itération pour capturer les détails des outils
        async with agent.iter(message, message_history=formatted_history) as run:
            async for node in run:
                # Gérer le nœud avec la fonction d'aide appropriée et streamer les résultats
                async for messages in handle_agent_node(
                    node, run.ctx, response_messages
                ):
                    yield messages

                # Si c'est un nœud de fin, sortir de la boucle
                if Agent.is_end_node(node):
                    break

    except Exception as e:
        logger.error(f"Erreur lors du streaming: {e}")
        error_message = create_error_message(str(e))
        log_gradio_message(error_message, "ERROR")
        yield [error_message]
