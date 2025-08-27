"""
Module for UI tools that can be used by agents to enhance the chat interface.
"""

import asyncio
import uuid
import chainlit as cl
from src.core.s3_client import get_s3_client


async def ask_for_cv() -> str:
    """
    Demande à l'utilisateur de téléverser un CV au format PDF, le téléverse sur S3
    et retourne la clé de l'objet S3.
    """
    files = await cl.AskFileMessage(
        content="Veuillez téléverser votre CV au format PDF", accept=["application/pdf"]
    ).send()

    if not files:
        return "L'utilisateur n'a fourni aucun CV."

    file = files[0]

    # Obtenir le client S3
    s3_client = get_s3_client()
    if not s3_client:
        return "Erreur: Le client S3 n'est pas configuré."

    # Générer une clé d'objet S3 unique
    object_key = f"cvs/{uuid.uuid4()}-{file.name}"

    # Lire le contenu du fichier en binaire
    with open(file.path, "rb") as f:
        file_content = f.read()

    # Téléverser le fichier sur S3
    # Use a default mime type if file.mime is not available
    mime_type = getattr(file, "mime", "application/pdf")
    await asyncio.to_thread(
        s3_client.client.put_object,
        Bucket=s3_client.bucket,
        Key=object_key,
        Body=file_content,
        ContentType=mime_type,
    )

    # Retourner la clé de l'objet S3
    return object_key


async def display_website(url: str) -> None:
    """
    Affiche une page web dans la barre latérale de l'interface de chat à l'aide d'un élément personnalisé en iframe.
    Args:
        url (str): L'URL du site web à afficher
    """
    # Créer l'élément personnalisé WebsiteViewer
    website_element = cl.CustomElement(name="WebsiteViewer", props={"url": url})
    # Définir le titre de la barre latérale
    await cl.ElementSidebar.set_title("Visualiseur de site web")
    # Afficher l'élément dans la barre latérale
    await cl.ElementSidebar.set_elements([website_element])
    # Envoyer un message simple à l'utilisateur
    await cl.Message(
        content="J'ai ouvert la page que vous avez demandée dans le panneau latéral."
    ).send()
