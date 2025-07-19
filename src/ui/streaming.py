"""
Module de gestion du streaming modernisé pour Chainlit + pydantic-ai.

Cette implémentation suit les meilleures pratiques de pydantic-ai et chainlit
pour un code plus simple, plus maintenable et plus performant avec affichage des outils.
"""

import logging
import asyncio
from typing import List, Any, Optional
import chainlit as cl
from pydantic_ai import Agent
from pydantic_ai.messages import (
    ModelMessage,
    ToolCallPart,
    ToolReturnPart,
)

# Configuration du logging
logger = logging.getLogger("datainclusion.agent.chainlit_streaming")

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
    # Garder les messages les plus récents
    return messages[-MAX_HISTORY_LENGTH:]


async def process_agent_with_history_and_tools(
    agent: Agent, message: str, message_history: Optional[List[ModelMessage]] = None
) -> List[ModelMessage]:
    """
    Traite un agent avec gestion de l'historique et affichage des outils MCP.

    Cette implémentation moderne combine :
    - Gestion de l'historique avec pydantic-ai message_history
    - Affichage des étapes avec cl.Step
    - Streaming de la réponse
    - Récupération de l'historique avec result.all_messages()

    Args:
        agent: Instance de l'agent pydantic-ai
        message: Message de l'utilisateur
        message_history: Historique des messages au format pydantic-ai

    Returns:
        Liste mise à jour des messages
    """
    try:
        logger.info(f"Traitement avec historique pour: {message[:50]}...")

        # Utiliser un Step pour montrer le traitement
        async with cl.Step(name="Traitement avec Agent MCP", type="llm") as step:
            step.input = message

            # Traiter la requête avec l'agent
            if hasattr(agent, "run") and asyncio.iscoroutinefunction(agent.run):
                result = await agent.run(message, message_history=message_history or [])
            elif hasattr(agent, "run_sync"):
                result = agent.run_sync(message, message_history=message_history or [])
            else:
                result = await agent.run(message, message_history=message_history or [])

            # Extraire le contenu de la réponse
            result_text = (
                str(result.output) if hasattr(result, "output") else str(result.data)
            )
            step.output = result_text

            # Créer un message vide pour le streaming
            response_msg = cl.Message(content="")
            await response_msg.send()

            # Simuler le streaming en divisant la réponse
            lines = result_text.splitlines(
                True
            )  # Garde les caractères de nouvelle ligne
            for line in lines:
                await asyncio.sleep(
                    0.05
                )  # Délai entre les lignes pour l'effet de streaming
                await response_msg.stream_token(line)

            # Finaliser le message
            await response_msg.update()

            logger.info("Traitement terminé avec succès")

            # Retourner l'historique complet pour la session
            return result.all_messages() if hasattr(result, "all_messages") else []

    except Exception as e:
        logger.error(f"Erreur lors du traitement avec historique: {e}")

        error_message = cl.Message(
            content=f"❌ **Erreur lors du traitement de votre demande:**\n\n{str(e)}"
        )
        await error_message.send()
        return message_history or []


async def process_agent_stream_with_tools_display(
    agent: Agent, message: str, message_history: Optional[List[ModelMessage]] = None
) -> List[ModelMessage]:
    """
    Version avec streaming réel selon la documentation pydantic-ai.
    Utilise agent.run_stream() et crée des Steps individuels pour chaque outil MCP.

    Args:
        agent: Instance de l'agent pydantic-ai
        message: Message de l'utilisateur
        message_history: Historique des messages

    Returns:
        Liste mise à jour des messages pour l'historique
    """
    try:
        logger.info(f"Streaming avec affichage d'outils pour: {message[:50]}...")

        # Créer un message pour le streaming
        streaming_message = cl.Message(content="")
        await streaming_message.send()

        # Variables pour tracker les outils
        tool_calls_info = []

        # Utiliser agent.run_stream() comme recommandé par la documentation
        async with agent.run_stream(
            message, message_history=message_history or []
        ) as result:
            # Streaming du texte
            async for text in result.stream_text():
                await streaming_message.stream_token(text)

            # Finaliser le message de streaming
            await streaming_message.update()

            # Récupérer tous les messages pour analyser les outils
            all_messages = result.all_messages()

            # Analyser les messages pour trouver les outils utilisés
            for msg in all_messages:
                if hasattr(msg, "parts"):
                    for part in msg.parts:
                        # Détection des appels d'outils
                        if isinstance(part, ToolCallPart):
                            tool_calls_info.append(
                                {
                                    "tool_name": part.tool_name,
                                    "args": part.args,
                                    "tool_call_id": getattr(
                                        part, "tool_call_id", "unknown"
                                    ),
                                }
                            )

                        # Détection des résultats d'outils
                        elif isinstance(part, ToolReturnPart):
                            # Associer le résultat à l'appel correspondant
                            for tool_info in tool_calls_info:
                                if tool_info.get("tool_call_id") == getattr(
                                    part, "tool_call_id", None
                                ):
                                    tool_info["result"] = part.content
                                    break

            # Créer des Steps individuels pour chaque outil MCP
            for i, tool_info in enumerate(tool_calls_info, 1):
                tool_name = tool_info.get("tool_name", "unknown")
                tool_args = tool_info.get("args", {})
                tool_result = tool_info.get("result", "")

                # Step 1: Appel de l'outil avec arguments
                async with cl.Step(
                    name=f"🔧 {tool_name}",
                    type="tool",
                    show_input="json",
                    language="json",
                ) as call_step:
                    call_step.input = tool_args
                    call_step.output = f"Outil '{tool_name}' appelé avec succès"

                # Step 2: Résultats de l'outil
                if tool_result:
                    async with cl.Step(
                        name=f"✅ {tool_name} - Résultat",
                        type="tool",
                        language="json" if _is_json_like(str(tool_result)) else "text",
                    ) as result_step:
                        result_step.input = f"Résultat de l'outil '{tool_name}'"
                        result_step.output = str(tool_result)[
                            :1000
                        ]  # Limiter à 1000 chars pour l'affichage

                        logger.info(f"Step créé pour outil: {tool_name}")

            logger.info("Streaming terminé avec succès")
            return all_messages

    except Exception as e:
        logger.error(f"Erreur lors du streaming avec outils: {e}")

        # Fallback : essayer sans streaming
        try:
            logger.info("Fallback vers exécution simple...")
            result = await agent.run(message, message_history=message_history or [])

            # Afficher la réponse
            response_message = cl.Message(content=str(result.output))
            await response_message.send()

            return result.all_messages()

        except Exception as fallback_error:
            logger.error(f"Erreur même en fallback: {fallback_error}")

            error_message = cl.Message(
                content=f"❌ **Erreur lors du traitement de votre demande:**\n\n{str(e)}"
            )
            await error_message.send()
            return message_history or []


def _is_json_like(text: str) -> bool:
    """
    Détermine si le texte ressemble à du JSON pour choisir la coloration syntaxique.

    Args:
        text: Le texte à analyser

    Returns:
        True si le texte ressemble à du JSON
    """
    if not text:
        return False

    text = text.strip()
    return (
        (text.startswith("{") and text.endswith("}"))
        or (text.startswith("[") and text.endswith("]"))
        or '"' in text
        or text.lower() in ["true", "false", "null"]
    )


async def process_agent_modern_with_history(
    agent: Agent, message: str, message_history: Optional[List[ModelMessage]] = None
) -> List[ModelMessage]:
    """
    Version moderne principale qui combine streaming, historique et affichage d'outils.

    Cette fonction est le point d'entrée principal pour le traitement moderne des agents.

    Args:
        agent: Instance de l'agent pydantic-ai
        message: Message de l'utilisateur
        message_history: Historique des messages au format pydantic-ai

    Returns:
        Liste mise à jour des messages pour l'historique de session
    """
    logger.info("Début du traitement moderne avec historique")

    try:
        # Tenter le streaming avec affichage d'outils
        updated_messages = await process_agent_stream_with_tools_display(
            agent, message, message_history
        )

        # Limiter l'historique pour éviter les problèmes de mémoire
        trimmed_messages = trim_message_history(updated_messages)

        logger.info(f"Historique mis à jour avec {len(trimmed_messages)} messages")
        return trimmed_messages

    except Exception as e:
        logger.error(f"Erreur dans le traitement moderne: {e}")

        # En cas d'échec complet, essayer le traitement simple
        try:
            fallback_messages = await process_agent_with_history_and_tools(
                agent, message, message_history
            )
            return fallback_messages
        except Exception as fallback_error:
            logger.error(f"Échec du fallback: {fallback_error}")
            return message_history or []


# Fonctions de compatibilité avec l'ancien code
async def process_agent_stream_modern(
    agent: Agent, message: str, history: Optional[List[Any]] = None
) -> None:
    """
    Fonction de compatibilité qui utilise la nouvelle approche moderne.
    Convertit l'ancien format d'historique vers le nouveau.
    """
    # Convertir l'historique si nécessaire
    message_history: Optional[List[ModelMessage]] = None
    if history:
        # Si c'est déjà au bon format, on l'utilise directement
        if isinstance(history, list) and history and hasattr(history[0], "__class__"):
            # Vérifier si c'est déjà des ModelMessage
            if hasattr(history[0], "parts"):
                message_history = history

    # Traitement moderne - ignore la valeur de retour pour la compatibilité
    await process_agent_modern_with_history(agent, message, message_history)


async def process_agent_stream_chainlit(
    agent: Agent, message: str, history: Optional[List[Any]] = None
) -> None:
    """
    Fonction de compatibilité avec l'ancien nom.
    """
    await process_agent_stream_modern(agent, message, history)


async def create_simple_response_message(content: str) -> None:
    """
    Crée et envoie un message de réponse simple.

    Args:
        content: Contenu du message
    """
    message = cl.Message(content=content)
    await message.send()
