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
from typing import List, Optional, Dict, Any

import chainlit as cl
from pydantic_ai import Agent
from pydantic_ai.messages import (
    ModelMessage,
    PartStartEvent,
    PartDeltaEvent,
    FunctionToolCallEvent,
    FunctionToolResultEvent,
    TextPartDelta,
    ToolCallPartDelta,
)

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


async def process_agent_with_perfect_streaming(
    agent: Agent, message: str, message_history: Optional[List[ModelMessage]] = None
) -> List[ModelMessage]:
    """
    Traite un agent avec streaming parfait selon les docs Pydantic-AI et Chainlit.

    Cette implémentation utilise:
    - agent.iter() pour parcourir le graphe d'exécution nœud par nœud
    - Events streaming de Pydantic-AI pour le temps réel
    - cl.Step pour afficher les outils MCP de manière transparente
    - cl.Message.stream_token() pour le streaming des tokens

    Args:
        agent: Instance de l'agent Pydantic-AI
        message: Message de l'utilisateur
        message_history: Historique des messages au format Pydantic-AI

    Returns:
        Liste mise à jour des messages pour l'historique
    """
    try:
        logger.info(f"🚀 Démarrage du streaming parfait pour: {message[:50]}...")

        # Ne pas créer le message de réponse tout de suite
        # Il sera créé seulement quand on commence à streamer du texte
        response_message: Optional[cl.Message] = None

        # Dictionnaire pour tracker les outils en cours
        active_tool_steps: Dict[str, cl.Step] = {}
        tool_call_counter = 0

        # Utiliser agent.iter() comme recommandé dans la documentation
        async with agent.iter(
            message, message_history=message_history or []
        ) as agent_run:
            # Parcourir chaque nœud du graphe d'exécution
            async for node in agent_run:
                # 1. UserPromptNode - Message utilisateur reçu
                if Agent.is_user_prompt_node(node):
                    logger.debug(f"📨 UserPromptNode: {node.user_prompt}")
                    # Pas d'affichage spécial nécessaire, le message utilisateur est déjà affiché

                # 2. ModelRequestNode - Requête vers le LLM avec streaming des tokens
                elif Agent.is_model_request_node(node):
                    logger.debug("🧠 ModelRequestNode: Streaming de la réponse LLM...")

                    # Streamer la réponse du modèle
                    async with node.stream(agent_run.ctx) as request_stream:
                        async for event in request_stream:
                            # Début d'une nouvelle partie de réponse
                            if isinstance(event, PartStartEvent):
                                logger.debug(
                                    f"🔄 Début partie {event.index}: {type(event.part).__name__}"
                                )

                            # Delta de texte - streaming en temps réel
                            elif isinstance(event, PartDeltaEvent):
                                if isinstance(event.delta, TextPartDelta):
                                    # Créer le message de réponse maintenant, quand on a du contenu
                                    if response_message is None and event.delta.content_delta:
                                        response_message = cl.Message(content="")
                                        await response_message.send()
                                    
                                    # Streamer chaque token vers Chainlit
                                    if event.delta.content_delta and response_message:
                                        await response_message.stream_token(
                                            event.delta.content_delta
                                        )

                                elif isinstance(event.delta, ToolCallPartDelta):
                                    # Les appels d'outils sont traités dans CallToolsNode
                                    logger.debug(
                                        f"🔧 Tool call delta: {event.delta.args_delta}"
                                    )

                # 3. CallToolsNode - Appels d'outils MCP avec affichage transparent
                elif Agent.is_call_tools_node(node):
                    logger.debug("🛠️ CallToolsNode: Traitement des outils MCP...")

                    # Streamer les événements des outils
                    async with node.stream(agent_run.ctx) as tools_stream:
                        async for event in tools_stream:
                            # Appel d'un outil MCP
                            if isinstance(event, FunctionToolCallEvent):
                                tool_call_counter += 1
                                tool_name = event.part.tool_name
                                tool_args = event.part.args
                                tool_call_id = event.part.tool_call_id

                                logger.info(f"🔧 Appel outil: {tool_name}")

                                # Créer un Step pour l'appel d'outil
                                step = cl.Step(
                                    name=f"🔧 {tool_name}",
                                    type="tool",
                                    show_input="json" if tool_args else False,
                                    language="json",
                                )

                                # Stocker le Step pour récupérer le résultat plus tard
                                active_tool_steps[tool_call_id] = step

                                # Configurer l'input du step
                                await step.__aenter__()
                                if tool_args:
                                    step.input = tool_args

                            # Résultat d'un outil MCP
                            elif isinstance(event, FunctionToolResultEvent):
                                tool_call_id = event.tool_call_id
                                result_content = event.result.content

                                # Récupérer le Step correspondant
                                if tool_call_id in active_tool_steps:
                                    step = active_tool_steps[tool_call_id]

                                    # Configurer l'output du step
                                    step.output = str(result_content)[
                                        :1000
                                    ]  # Limiter pour l'affichage

                                    # Finaliser le step
                                    await step.__aexit__(None, None, None)

                                    # Nettoyer le dictionnaire
                                    del active_tool_steps[tool_call_id]

                                    logger.info(
                                        f"✅ Résultat outil reçu: {len(str(result_content))} chars"
                                    )

                # 4. EndNode - Fin de l'exécution
                elif Agent.is_end_node(node):
                    logger.info("🏁 EndNode: Exécution terminée")
                    final_output = str(node.data.output)

                    # Si pas encore de message de réponse créé, le créer maintenant
                    if response_message is None:
                        response_message = cl.Message(content=final_output)
                        await response_message.send()
                    # Si pas encore de contenu dans le message (cas rare), l'ajouter
                    elif not response_message.content.strip():
                        await response_message.stream_token(final_output)

        # Finaliser le message de réponse s'il existe
        if response_message is not None:
            await response_message.update()

        # Récupérer l'historique complet (s'assurer que le result n'est pas None)
        if agent_run.result is not None:
            all_messages = agent_run.result.all_messages()
            trimmed_messages = trim_message_history(all_messages)
        else:
            logger.warning("agent_run.result est None, retour de l'historique original")
            trimmed_messages = message_history or []

        logger.info(
            f"✅ Streaming terminé - Historique: {len(trimmed_messages)} messages"
        )
        return trimmed_messages

    except Exception as e:
        logger.error(f"❌ Erreur dans le streaming parfait: {e}", exc_info=True)

        # Nettoyage des steps ouverts en cas d'erreur
        for step in active_tool_steps.values():
            try:
                await step.__aexit__(None, None, None)
            except Exception:
                pass

        # Message d'erreur à l'utilisateur
        error_msg = cl.Message(
            content=f"❌ **Erreur lors du traitement:**\n\n{str(e)}\n\n"
            "Veuillez réessayer ou reformuler votre question."
        )
        await error_msg.send()

        return message_history or []


async def process_agent_fallback_simple(
    agent: Agent, message: str, message_history: Optional[List[ModelMessage]] = None
) -> List[ModelMessage]:
    """
    Version de fallback simple sans streaming pour la robustesse.

    Args:
        agent: Instance de l'agent Pydantic-AI
        message: Message de l'utilisateur
        message_history: Historique des messages

    Returns:
        Liste mise à jour des messages
    """
    try:
        logger.info("🔄 Utilisation du fallback simple...")

        # Exécution simple sans streaming
        result = await agent.run(message, message_history=message_history or [])

        if result is None:
            raise Exception("L'agent a retourné un résultat null")

        # Afficher la réponse
        response_content = str(result.output)
        response_message = cl.Message(content=response_content)
        await response_message.send()

        # Retourner l'historique
        if hasattr(result, "all_messages"):
            return result.all_messages()
        else:
            logger.warning(
                "Result n'a pas d'attribut all_messages, retour historique original"
            )
            return message_history or []

    except Exception as e:
        logger.error(f"❌ Erreur même en fallback: {e}")

        error_message = cl.Message(
            content=f"❌ **Erreur système:**\n\n{str(e)}\n\n"
            "Veuillez contacter l'administrateur si le problème persiste."
        )
        await error_message.send()

        return message_history or []


async def process_agent_modern_with_history(
    agent: Agent, message: str, message_history: Optional[List[ModelMessage]] = None
) -> List[ModelMessage]:
    """
    Point d'entrée principal pour le traitement moderne avec streaming parfait.

    Cette fonction est le point d'entrée recommandé qui utilise la meilleure
    implémentation disponible avec fallback automatique en cas d'erreur.

    Args:
        agent: Instance de l'agent Pydantic-AI
        message: Message de l'utilisateur
        message_history: Historique des messages au format Pydantic-AI

    Returns:
        Liste mise à jour des messages pour l'historique de session
    """
    logger.info("🎯 Traitement moderne avec streaming parfait")

    try:
        # Tenter le streaming parfait
        return await process_agent_with_perfect_streaming(
            agent, message, message_history
        )

    except Exception as e:
        logger.warning(f"⚠️ Échec du streaming parfait, fallback: {e}")

        # En cas d'échec, utiliser le fallback simple
        return await process_agent_fallback_simple(agent, message, message_history)


# ================================
# Fonctions de compatibilité
# ================================


async def process_agent_stream_modern(
    agent: Agent, message: str, history: Optional[List[Any]] = None
) -> None:
    """
    Fonction de compatibilité avec l'ancien code.
    Utilise la nouvelle approche moderne en arrière-plan.
    """
    # Conversion de l'historique si nécessaire
    message_history: Optional[List[ModelMessage]] = None
    if history and isinstance(history, list) and history:
        # Si c'est déjà des ModelMessage, on les utilise
        if hasattr(history[0], "parts"):
            message_history = history

    # Appel de la fonction moderne (ignore le retour pour compatibilité)
    await process_agent_modern_with_history(agent, message, message_history)


async def process_agent_stream_chainlit(
    agent: Agent, message: str, history: Optional[List[Any]] = None
) -> None:
    """Alias de compatibilité."""
    await process_agent_stream_modern(agent, message, history)


async def create_simple_response_message(content: str) -> None:
    """Crée et envoie un message de réponse simple."""
    message = cl.Message(content=content)
    await message.send()
