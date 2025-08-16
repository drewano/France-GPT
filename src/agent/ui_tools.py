"""
Module for UI tools that can be used by agents to enhance the chat interface.
"""


import chainlit as cl
import geopandas as gpd
import matplotlib.pyplot as plt
from typing import Dict, Any

# Importez la fonction pynsee nécessaire
from pynsee.geodata import get_geodata

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

async def fetch_and_display_map(nom_couche: str, title: str = "Carte") -> str:
    """
    Récupère les données géographiques pour une couche donnée et les affiche directement sous forme de carte.
    C'est l'étape finale pour visualiser une carte.
    - nom_couche: L'identifiant exact de la couche à récupérer (ex: 'ADMINEXPRESS-COG.LATEST:region').
    - title: Le titre à afficher au-dessus de la carte.
    """
    try:
        # Étape 1 : Récupérer les données directement ici
        await cl.Message(content=f"Récupération des données pour la couche `{nom_couche}`...").send()
        gdf = get_geodata(nom_couche, update=True)

        if gdf is None or gdf.empty:
            error_message = f"Désolé, je n'ai trouvé aucune donnée géographique pour la couche '{nom_couche}'."
            await cl.Message(content=error_message).send()
            return error_message

        # Étape 2 : Créer la figure et l'afficher
        fig, ax = plt.subplots(1, 1, figsize=(10, 10))
        gdf.plot(ax=ax, edgecolor='black', facecolor='lightblue')
        
        ax.set_title(title, fontdict={'fontsize': '16', 'fontweight': '3'})
        ax.set_axis_off()
        plt.tight_layout()

        element = cl.Pyplot(name="map_plot", figure=fig, display="inline")
        await cl.Message(
            content=f"Voici la carte pour '{title}' :",
            elements=[element],
        ).send()
        
        return "La carte a été affichée avec succès à l'utilisateur."
    except Exception as e:
        error_message = f"Une erreur est survenue lors de la récupération ou de l'affichage de la carte : {e}"
        await cl.Message(content=error_message).send()
        return error_message