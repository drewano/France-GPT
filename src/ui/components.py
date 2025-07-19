"""
Module de création de composants Chainlit pour l'interface utilisateur.

Ce module contient toutes les fonctions responsables de la création
des cl.Step pour l'affichage des appels d'outils et leurs résultats.
"""

import chainlit as cl
from typing import Dict, Any, Optional

# Imports des fonctions de formatage depuis formatters.py
from .formatters import (
    get_friendly_tool_name,
    format_arguments_for_display,
    format_result_for_display,
)


async def create_tool_call_step(
    tool_name: str,
    arguments: Dict[str, Any],
    parent_id: Optional[str] = None,
) -> cl.Step:
    """
    Crée et envoie un cl.Step pour un appel d'outil MCP.

    Args:
        tool_name: Nom de l'outil appelé
        arguments: Arguments passés à l'outil
        parent_id: ID du step parent (optionnel)

    Returns:
        cl.Step: Instance du step créé pour pouvoir le mettre à jour plus tard
    """

    # Nom convivial de l'outil
    friendly_name = get_friendly_tool_name(tool_name)

    # Formatage des arguments pour l'affichage
    args_formatted = format_arguments_for_display(arguments)

    # Créer le step avec les propriétés appropriées
    step = cl.Step(name=friendly_name, type="tool")

    # Assigner le parent_id si fourni
    if parent_id:
        step.parent_id = parent_id

    # Définir l'input avec les arguments formatés
    if arguments:
        step.input = args_formatted
    else:
        step.input = "*Aucun paramètre*"

    # Envoyer le step immédiatement
    await step.send()

    return step


async def update_tool_result_step(
    step: cl.Step,
    result: Any,
    duration: Optional[float] = None,
    is_error: bool = False,
) -> None:
    """
    Met à jour un cl.Step existant avec le résultat d'un outil.

    Args:
        step: Instance du cl.Step à mettre à jour
        result: Résultat de l'outil
        duration: Durée d'exécution en secondes (optionnel)
        is_error: Si True, affiche comme une erreur
    """

    # Formatage du résultat pour l'affichage
    result_formatted = format_result_for_display(result)

    # Construction du contenu de sortie
    if is_error:
        output_content = "❌ **Erreur lors de l'exécution**\n\n"
    else:
        output_content = "✅ **Résultat obtenu**\n\n"

    # Ajouter la durée si disponible
    if duration is not None:
        output_content += f"**Durée:** {duration:.3f}s\n\n"

    # Ajouter le résultat formaté
    output_content += f"**Données:**\n{result_formatted}"

    # Mettre à jour l'output du step
    step.output = output_content

    # Envoyer la mise à jour
    await step.update()


async def create_simple_step(
    name: str,
    content: str,
    parent_id: Optional[str] = None,
) -> cl.Step:
    """
    Crée un step simple avec un contenu donné.

    Args:
        name: Nom du step
        content: Contenu à afficher
        parent_id: ID du step parent (optionnel)

    Returns:
        cl.Step: Instance du step créé
    """

    step = cl.Step(name=name)

    if parent_id:
        step.parent_id = parent_id

    step.output = content

    await step.send()

    return step


async def create_nested_tool_workflow(
    workflow_name: str,
    tools_data: list[Dict[str, Any]],
) -> cl.Step:
    """
    Crée un workflow de plusieurs outils avec des steps imbriqués.

    Args:
        workflow_name: Nom du workflow principal
        tools_data: Liste de dictionnaires contenant les données des outils
                    Format: [{"tool_name": str, "arguments": dict, "result": any, "duration": float, "is_error": bool}]

    Returns:
        cl.Step: Step principal du workflow
    """

    # Créer le step principal du workflow
    main_step = cl.Step(name=f"🔄 {workflow_name}")

    main_step.input = f"Exécution de {len(tools_data)} outil(s)"

    await main_step.send()

    # Créer les steps enfants pour chaque outil
    child_steps = []

    try:
        for i, tool_data in enumerate(tools_data, 1):
            tool_name = tool_data.get("tool_name", f"Outil {i}")
            arguments = tool_data.get("arguments", {})
            result = tool_data.get("result")
            duration = tool_data.get("duration")
            is_error = tool_data.get("is_error", False)

            # Créer le step enfant pour cet outil
            child_step = await create_tool_call_step(
                tool_name=tool_name, arguments=arguments, parent_id=main_step.id
            )

            child_steps.append(child_step)

            # Si on a un résultat, mettre à jour le step
            if result is not None:
                await update_tool_result_step(
                    step=child_step, result=result, duration=duration, is_error=is_error
                )

        # Mettre à jour le step principal avec le résumé
        total_duration = sum(tool_data.get("duration", 0) for tool_data in tools_data)
        successful_tools = sum(
            1 for tool_data in tools_data if not tool_data.get("is_error", False)
        )
        failed_tools = len(tools_data) - successful_tools

        summary = "✅ **Workflow terminé**\n\n"
        summary += "**Résumé:**\n"
        summary += f"- Outils exécutés: {len(tools_data)}\n"
        summary += f"- Succès: {successful_tools}\n"
        if failed_tools > 0:
            summary += f"- Échecs: {failed_tools}\n"
        if total_duration > 0:
            summary += f"- Durée totale: {total_duration:.3f}s\n"

        main_step.output = summary
        await main_step.update()

    except Exception as e:
        # En cas d'erreur, mettre à jour le step principal
        main_step.output = f"❌ **Erreur dans le workflow:** {str(e)}"
        await main_step.update()
        raise

    return main_step
