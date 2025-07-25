"""
Module for UI tools that can be used by agents to enhance the chat interface.
"""

import chainlit as cl


async def display_website(url: str) -> None:
    """
    Affiche une page web dans la barre latérale de l'interface de chat à l'aide d'un élément personnalisé en iframe.
    Args:
        url (str): L'URL du site web à afficher
    """
    # Créer l'élément personnalisé WebsiteViewer
    website_element = cl.CustomElement(
        name="WebsiteViewer",
        props={"url": url}
    )
    # Définir le titre de la barre latérale
    await cl.ElementSidebar.set_title("Visualiseur de site web")
    # Afficher l'élément dans la barre latérale
    await cl.ElementSidebar.set_elements([website_element])
    # Envoyer un message simple à l'utilisateur
    await cl.Message(content="J'ai ouvert la page que vous avez demandée dans le panneau latéral.").send()