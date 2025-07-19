"""
Module de gestion du streaming de l'agent IA pour Chainlit.

Ce module contient toute la logique de streaming et de traitement des nœuds
de l'agent pydantic-ai, adaptée pour l'interface utilisateur Chainlit.
"""

import logging
from typing import Dict, Optional, List, Any
import chainlit as cl
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

# Imports des composants Chainlit
from .components import (
    create_tool_call_step,
    update_tool_result_step,
)
from ..agent.history import format_chainlit_history, get_chainlit_chat_history

# Configuration du logging
logger = logging.getLogger("datainclusion.agent.chainlit_streaming")


async def handle_agent_node_chainlit(
    node,
    run_context,
    streaming_message: Optional[cl.Message],
    tool_steps: Dict[str, cl.Step],
) -> Optional[cl.Message]:
    """
    Gère un nœud de l'agent en déléguant à la fonction appropriée selon le type de nœud.

    Args:
        node: Le nœud de l'agent à traiter
        run_context: Le contexte d'exécution de l'agent
        streaming_message: Message en cours de streaming (pour le texte)
        tool_steps: Dictionnaire des steps d'outils indexés par tool_call_id

    Returns:
        Optional[cl.Message]: Message de streaming mis à jour si applicable
    """
    if Agent.is_user_prompt_node(node):
        # Nœud de prompt utilisateur
        logger.info(f"Traitement du message utilisateur: {node.user_prompt}")
        return streaming_message

    elif Agent.is_model_request_node(node):
        # Nœud de requête modèle - déléguer au streaming de la réponse
        return await stream_model_response_chainlit(
            node, run_context, streaming_message
        )

    elif Agent.is_call_tools_node(node):
        # Nœud d'appel d'outils - déléguer au streaming des appels d'outils
        await stream_tool_calls_chainlit(node, run_context, tool_steps)
        return streaming_message

    elif Agent.is_end_node(node):
        # Nœud de fin - traitement terminé
        logger.info("Traitement terminé avec succès")
        return streaming_message

    return streaming_message


async def stream_model_response_chainlit(
    node, run_context, streaming_message: Optional[cl.Message]
) -> cl.Message:
    """
    Gère le streaming de la réponse du modèle avec Chainlit.

    Args:
        node: Le nœud de requête modèle
        run_context: Le contexte d'exécution de l'agent
        streaming_message: Message en cours de streaming (peut être None)

    Returns:
        cl.Message: Message de streaming créé ou mis à jour
    """
    logger.info("Streaming de la requête modèle...")

    # Créer un nouveau message de streaming si nécessaire
    if streaming_message is None:
        streaming_message = cl.Message(content="")
        await streaming_message.send()

    # Stream les tokens partiels
    async with node.stream(run_context) as request_stream:
        async for event in request_stream:
            if isinstance(event, PartStartEvent):
                logger.debug(f"Début de la partie {event.index}: {event.part}")
                # Traiter le contenu initial si c'est un TextPart
                if isinstance(event.part, TextPart) and event.part.content:
                    # Initialiser le contenu avec le contenu initial
                    await streaming_message.stream_token(event.part.content)

            elif isinstance(event, PartDeltaEvent):
                if isinstance(event.delta, TextPartDelta):
                    # Streamer le contenu au fur et à mesure
                    await streaming_message.stream_token(event.delta.content_delta)
                elif isinstance(event.delta, ToolCallPartDelta):
                    logger.debug(f"Appel d'outil en cours: {event.delta.args_delta}")

            elif isinstance(event, FinalResultEvent):
                logger.debug("Streaming de la réponse terminé")
                break

    # Mettre à jour le message final
    await streaming_message.update()
    return streaming_message


async def stream_tool_calls_chainlit(
    node, run_context, tool_steps: Dict[str, cl.Step]
) -> None:
    """
    Gère le streaming des appels d'outils MCP avec Chainlit.

    Args:
        node: Le nœud d'appel d'outils
        run_context: Le contexte d'exécution de l'agent
        tool_steps: Dictionnaire pour stocker les steps d'outils par tool_call_id
    """
    logger.info("Traitement des appels d'outils...")

    async with node.stream(run_context) as handle_stream:
        async for event in handle_stream:
            if isinstance(event, FunctionToolCallEvent):
                logger.info(f"Appel d'outil: {event.part.tool_name}")

                # Créer un step pour l'appel d'outil
                # S'assurer que les arguments sont un dictionnaire
                args = event.part.args if event.part.args else {}
                if isinstance(args, str):
                    # Si args est une chaîne, l'encapsuler dans un dictionnaire
                    args = {"raw_args": args}
                elif not isinstance(args, dict):
                    # Si ce n'est ni un dict ni une chaîne, convertir en dictionnaire
                    args = {"args": str(args)}

                tool_step = await create_tool_call_step(
                    tool_name=event.part.tool_name,
                    arguments=args,
                )

                # Stocker le step pour usage ultérieur
                tool_steps[event.part.tool_call_id] = tool_step

            elif isinstance(event, FunctionToolResultEvent):
                logger.info(f"Résultat d'outil pour ID: {event.tool_call_id}")

                # Récupérer le step correspondant
                tool_step = tool_steps.get(event.tool_call_id)

                if tool_step:
                    # Mettre à jour le step avec le résultat
                    await update_tool_result_step(
                        step=tool_step,
                        result=event.result.content,
                        is_error=False,  # TODO: Gérer les erreurs d'outils si nécessaire
                    )
                else:
                    logger.warning(
                        f"Step non trouvé pour tool_call_id: {event.tool_call_id}"
                    )


async def process_agent_stream_chainlit(
    agent, message: str, history: Optional[List[Any]] = None
) -> None:
    """
    Traite le streaming complet d'un agent avec Chainlit et gestion des erreurs.

    Args:
        agent: Instance de l'agent pydantic-ai
        message: Message de l'utilisateur
        history: Historique des messages (optionnel, récupéré automatiquement depuis Chainlit si non fourni)
    """
    try:
        # Récupérer l'historique de Chainlit si pas fourni
        if history is None:
            history = get_chainlit_chat_history()

        # Convertir l'historique Chainlit au format pydantic-ai
        formatted_history = format_chainlit_history(history)

        # Initialiser les variables de streaming
        streaming_message: Optional[cl.Message] = None
        tool_steps: Dict[str, cl.Step] = {}

        # Utiliser l'API avancée d'itération pour capturer les détails des outils
        async with agent.iter(message, message_history=formatted_history) as run:
            async for node in run:
                # Gérer le nœud avec la fonction d'aide appropriée
                streaming_message = await handle_agent_node_chainlit(
                    node, run.ctx, streaming_message, tool_steps
                )

                # Si c'est un nœud de fin, sortir de la boucle
                if Agent.is_end_node(node):
                    break

        logger.info("Streaming terminé avec succès")

    except Exception as e:
        logger.error(f"Erreur lors du streaming Chainlit: {e}")

        # Afficher un message d'erreur à l'utilisateur
        error_message = cl.Message(
            content=f"❌ **Erreur lors du traitement de votre demande:**\n\n{str(e)}"
        )
        await error_message.send()


async def create_simple_response_message(content: str) -> None:
    """
    Crée et envoie un message de réponse simple.

    Args:
        content: Contenu du message
    """
    message = cl.Message(content=content)
    await message.send()


async def stream_simple_text_response(text_generator) -> None:
    """
    Streame une réponse textuelle simple depuis un générateur.

    Args:
        text_generator: Générateur qui yield des tokens de texte
    """
    try:
        streaming_message = cl.Message(content="")
        await streaming_message.send()

        async for token in text_generator:
            await streaming_message.stream_token(token)

        await streaming_message.update()

    except Exception as e:
        logger.error(f"Erreur lors du streaming simple: {e}")
        await create_simple_response_message(f"❌ Erreur: {str(e)}")


# Note: Les fonctions de conversion d'historique sont maintenant dans agent/history.py
