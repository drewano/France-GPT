"""
Module for UI tools that can be used by agents to enhance the chat interface.
"""

import chainlit as cl


async def display_website(url: str) -> None:
    """
    Affiche une page web dans l'interface de chat à l'aide d'un élément personnalisé en iframe.
    
    Args:
        url (str): L'URL du site web à afficher
    """
    # Créer l'élément personnalisé WebsiteViewer
    website_element = cl.CustomElement(
        name="WebsiteViewer",
        props={"url": url},
        display="inline"
    )
    
    # Créer et envoyer le message avec l'élément
    message = cl.Message(
        content="Voici la page que vous avez demandée :",
        elements=[website_element]
    )
    await message.send()