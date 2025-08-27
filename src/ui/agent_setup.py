"""
Module dédié à la configuration et à l'initialisation de l'agent.

Cette séparation permet d'isoler la logique de création de l'agent des décorateurs
Chainlit qui peuvent avoir des effets de bord lors de l'importation, notamment
dans un contexte de test.
"""

import chainlit as cl
from pydantic_ai.toolsets import FunctionToolset

from src.agent.agent import create_agent_from_profile
from src.agent.ui_tools import display_website, ask_for_cv
from src.core.profiles import AGENT_PROFILES


async def setup_agent():
    """
    Fonction d'assistance pour configurer l'agent basé sur le profil sélectionné.
    Déplace la logique de sélection de profil et de création d'agent ici.
    """
    profile_name = cl.user_session.get("chat_profile")

    if profile_name:
        profile = next(
            (p for p in AGENT_PROFILES.values() if p.name == profile_name), None
        )
    else:
        profile = AGENT_PROFILES.get("social_agent")

    if not profile:
        raise ValueError(f"Profil de chat '{profile_name}' non trouvé.")

    # Créer le toolset d'interface utilisateur
    ui_toolset = FunctionToolset(tools=[display_website, ask_for_cv])

    # Créer l'agent avec le toolset d'interface utilisateur
    agent = create_agent_from_profile(profile, ui_toolsets=[ui_toolset])
    cl.user_session.set("agent", agent)
    cl.user_session.set("selected_profile_id", profile.id)
