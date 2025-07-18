"""
Interface de chat Gradio pour l'agent IA d'inclusion sociale.

Ce module contient l'interface utilisateur Gradio pour interagir avec l'agent IA.
Il est responsable de créer et monter l'interface sur l'application FastAPI.
"""

import logging
from typing import List, Dict, AsyncGenerator
import gradio as gr
from fastapi import FastAPI

# Imports locaux
from .agent_streaming import process_agent_stream

# Configuration du logging
logger = logging.getLogger("datainclusion.agent")


def create_complete_interface(app: FastAPI):
    """
    Crée l'interface Gradio complète avec streaming et affichage des appels aux outils MCP.

    Args:
        app: Instance de l'application FastAPI contenant l'agent dans son état
    """

    async def chat_stream(
        message: str, history: List[Dict[str, str]], request: gr.Request
    ) -> AsyncGenerator[List[gr.ChatMessage], None]:
        """
        Fonction de streaming pour l'interface de chat avec affichage des appels aux outils MCP.

        Utilise l'API d'itération avancée de Pydantic AI (agent.iter) pour capturer
        et afficher chaque étape du processus de l'agent.

        Args:
            message: Message de l'utilisateur
            history: Historique des messages
            request: Objet Request de Gradio (non utilisé pour l'accès à l'agent)

        Yields:
            Listes de ChatMessage formatées incluant les détails des appels aux outils MCP
        """
        if not message or not message.strip():
            yield [
                gr.ChatMessage(
                    role="assistant", content="⚠️ Veuillez entrer un message valide."
                )
            ]
            return

        # Récupérer l'agent depuis l'état de l'application
        agent = getattr(app.state, "agent", None)
        if agent is None:
            yield [
                gr.ChatMessage(
                    role="assistant", content="❌ Erreur: Agent non initialisé"
                )
            ]
            return

        # Déléguer le streaming à la fonction dédiée
        async for messages in process_agent_stream(agent, message, history):
            yield messages

    # Exemples de conversation
    examples = [
        "Bonjour ! Comment puis-je vous aider aujourd'hui ?",
        "Trouve des structures d'aide près de 75001 Paris",
        "Quels services d'insertion professionnelle à Lyon ?",
        "Aide au logement d'urgence à Marseille",
        "Services pour personnes handicapées à Lille",
        "Comment obtenir une aide alimentaire ?",
        "Structures d'accueil pour familles monoparentales",
    ]

    # Créer l'interface ChatInterface
    chat_interface = gr.ChatInterface(
        fn=chat_stream,
        type="messages",
        title="🤖 Agent IA d'Inclusion Sociale",
        description="Assistant intelligent spécialisé dans l'inclusion sociale en France - Affichage des appels aux outils MCP",
        examples=examples,
        cache_examples=False,
        chatbot=gr.Chatbot(
            label="Assistant IA",
            height=1100,
            show_copy_button=True,
            type="messages",
            avatar_images=(
                "https://em-content.zobj.net/source/twitter/376/bust-in-silhouette_1f464.png",
                "https://em-content.zobj.net/source/twitter/376/robot-face_1f916.png",
            ),
            placeholder="Bienvenue ! Posez votre question sur l'inclusion sociale...",
        ),
        textbox=gr.Textbox(
            placeholder="Ex: Aide au logement près de 75001 Paris",
            lines=1,
            max_lines=3,
            show_label=False,
        ),
    )

    return chat_interface


def mount_gradio_interface(app: FastAPI) -> FastAPI:
    """
    Monte l'interface Gradio sur l'application FastAPI.

    Cette fonction centralise toute la logique de montage de l'interface Gradio,
    favorisant le découplage entre la logique de l'application et l'interface utilisateur.

    Args:
        app: Instance de l'application FastAPI sur laquelle monter l'interface

    Returns:
        Instance FastAPI avec l'interface Gradio montée
    """

    logger.info("🎨 Montage de l'interface Gradio sur l'application FastAPI...")

    # Créer l'interface Gradio complète
    gradio_interface = create_complete_interface(app)

    # Monter l'interface sur l'application FastAPI
    app = gr.mount_gradio_app(app=app, blocks=gradio_interface, path="/chat")

    logger.info("✅ Interface Gradio montée avec succès sur /chat")

    return app
