#!/usr/bin/env python3
"""
Thème personnalisé pour l'agent IA d'Inclusion Sociale.

Ce thème utilise les couleurs officielles françaises et les meilleures pratiques
d'accessibilité pour créer une interface moderne et professionnelle.

Fonctionnalités :
- Couleurs officielles françaises (bleu gouvernemental, vert inclusif)
- Police Marianne (officielle) avec fallbacks
- Optimisations pour l'accessibilité WCAG 2.1
- Design responsive et moderne
- Animations subtiles et professionnelles
- Support mode sombre/clair
"""

from __future__ import annotations
from typing import Iterable
import gradio as gr
from gradio.themes.base import Base
from gradio.themes.utils import colors, fonts, sizes


class InclusionTheme(Base):
    """
    Thème personnalisé pour l'agent IA d'Inclusion Sociale.
    
    Ce thème utilise les couleurs officielles françaises et optimise l'accessibilité
    pour créer une expérience utilisateur moderne et professionnelle.
    """
    
    def __init__(
        self,
        *,
        primary_hue: colors.Color | str = colors.blue,  # Bleu gouvernemental français
        secondary_hue: colors.Color | str = colors.green,  # Vert inclusif
        neutral_hue: colors.Color | str = colors.gray,  # Gris neutre accessible
        spacing_size: sizes.Size | str = sizes.spacing_md,
        radius_size: sizes.Size | str = sizes.radius_md,
        text_size: sizes.Size | str = sizes.text_md,
        font: fonts.Font | str | Iterable[fonts.Font | str] = (
            # Police Marianne officielle avec fallbacks
            fonts.GoogleFont("Marianne"),
            "Marianne",
            "-apple-system",
            "BlinkMacSystemFont",
            "Segoe UI",
            "Roboto",
            "Helvetica Neue",
            "Arial",
            "sans-serif"
        ),
        font_mono: fonts.Font | str | Iterable[fonts.Font | str] = (
            fonts.GoogleFont("JetBrains Mono"),
            "JetBrains Mono",
            "Fira Code",
            "Consolas",
            "Monaco",
            "monospace"
        ),
        **kwargs,
    ):
        """
        Initialise le thème InclusionTheme.
        
        Args:
            primary_hue: Couleur principale (bleu gouvernemental français)
            secondary_hue: Couleur secondaire (vert inclusif)
            neutral_hue: Couleur neutre (gris accessible)
            spacing_size: Taille des espacements
            radius_size: Taille des rayons de bordure
            text_size: Taille du texte
            font: Police principale
            font_mono: Police monospace
        """
        super().__init__(
            primary_hue=primary_hue,
            secondary_hue=secondary_hue,
            neutral_hue=neutral_hue,
            spacing_size=spacing_size,
            radius_size=radius_size,
            text_size=text_size,
            font=font,
            font_mono=font_mono,
            **kwargs,
        )
        
        # Personnalisation des variables CSS (utilisation des variables validées)
        self.set(
            # === COULEURS DE BASE ===
            # Arrière-plan principal avec dégradé subtil
            body_background_fill="linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%)",
            body_background_fill_dark="linear-gradient(135deg, #0f172a 0%, #1e293b 100%)",
            
            # Couleurs de fond
            background_fill_primary="*neutral_50",
            background_fill_primary_dark="*neutral_800",
            background_fill_secondary="*neutral_100",
            background_fill_secondary_dark="*neutral_700",
            
            # === BOUTONS ===
            # Bouton principal (bleu gouvernemental)
            button_primary_background_fill="linear-gradient(135deg, #0078D4 0%, #106EBE 100%)",
            button_primary_background_fill_hover="linear-gradient(135deg, #106EBE 0%, #0E5A9A 100%)",
            button_primary_background_fill_dark="linear-gradient(135deg, #005A9A 0%, #004B82 100%)",
            button_primary_text_color="white",
            button_primary_text_color_dark="white",
            
            # Bouton secondaire (vert inclusif)
            button_secondary_background_fill="linear-gradient(135deg, #16A085 0%, #138D75 100%)",
            button_secondary_background_fill_hover="linear-gradient(135deg, #138D75 0%, #117A65 100%)",
            button_secondary_background_fill_dark="linear-gradient(135deg, #0E6655 0%, #0D5346 100%)",
            button_secondary_text_color="white",
            button_secondary_text_color_dark="white",
            
            # === CHAMPS DE SAISIE ===
            # Champs de texte
            input_background_fill="white",
            input_background_fill_dark="*neutral_700",
            input_background_fill_focus="white",
            input_background_fill_focus_dark="*neutral_600",
            input_border_color="*neutral_300",
            input_border_color_dark="*neutral_500",
            input_border_color_focus="#0078D4",
            input_border_color_focus_dark="#106EBE",
            input_placeholder_color="*neutral_400",
            input_placeholder_color_dark="*neutral_400",
            
            # === BLOCS ET CONTENEURS ===
            # Blocs principaux
            block_background_fill="white",
            block_background_fill_dark="*neutral_800",
            block_border_color="*neutral_200",
            block_border_color_dark="*neutral_600",
            block_border_width="1px",
            block_shadow="0 2px 4px rgba(0, 0, 0, 0.1)",
            block_shadow_dark="0 2px 4px rgba(0, 0, 0, 0.3)",
            
            # Titres des blocs
            block_title_background_fill="linear-gradient(135deg, #0078D4 0%, #106EBE 100%)",
            block_title_background_fill_dark="linear-gradient(135deg, #005A9A 0%, #004B82 100%)",
            block_title_text_color="white",
            block_title_text_color_dark="white",
            block_title_text_weight="600",
            block_title_text_size="*text_md",
            
            # Labels
            block_label_background_fill="transparent",
            block_label_text_color="#0078D4",
            block_label_text_color_dark="#64B5F6",
            block_label_text_weight="600",
            block_label_text_size="*text_sm",
            
            # === SLIDERS ET CONTRÔLES ===
            # Sliders
            slider_color="#0078D4",
            slider_color_dark="#64B5F6",
            
            # === TYPOGRAPHIE ===
            # Couleurs de texte
            body_text_color="*neutral_700",
            body_text_color_dark="*neutral_200",
            body_text_color_subdued="*neutral_500",
            body_text_color_subdued_dark="*neutral_400",
            
            # Liens
            link_text_color="#0078D4",
            link_text_color_dark="#64B5F6",
            link_text_color_hover="#106EBE",
            link_text_color_hover_dark="#90CAF9",
            
            # === INDICATEURS DE CHARGEMENT ===
            # Indicateurs de chargement
            loader_color="#0078D4",
            loader_color_dark="#64B5F6",
        )


def get_inclusion_theme() -> InclusionTheme:
    """
    Retourne une instance du thème d'inclusion sociale.
    
    Returns:
        InclusionTheme: Instance du thème personnalisé
    """
    return InclusionTheme()


def get_inclusion_css() -> str:
    """
    Retourne le CSS personnalisé pour améliorer l'expérience utilisateur.
    
    Returns:
        str: CSS personnalisé pour l'interface
    """
    return """
    /* === VARIABLES CSS PERSONNALISÉES === */
    :root {
        --inclusion-primary: #0078D4;
        --inclusion-secondary: #16A085;
        --inclusion-success: #4CAF50;
        --inclusion-warning: #F57C00;
        --inclusion-error: #D32F2F;
        --inclusion-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        --inclusion-radius: 8px;
        --inclusion-transition: all 0.2s ease;
    }
    
    /* === CONTENEUR PRINCIPAL === */
    .gradio-container {
        max-width: 1400px;
        margin: 0 auto;
        font-family: 'Marianne', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        line-height: 1.6;
        color: #374151;
    }
    
    /* === AMÉLIORATIONS CHAT === */
    .chatbot {
        border-radius: var(--inclusion-radius);
        box-shadow: var(--inclusion-shadow);
        background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
    }
    
    .chatbot .message {
        padding: 16px;
        margin: 8px 0;
        border-radius: var(--inclusion-radius);
        transition: var(--inclusion-transition);
    }
    
    .chatbot .message:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    }
    
    /* Messages utilisateur */
    .chatbot .message.user {
        background: linear-gradient(135deg, var(--inclusion-primary) 0%, #106EBE 100%);
        color: white;
        margin-left: 20%;
        border-bottom-right-radius: 4px;
    }
    
    /* Messages assistant */
    .chatbot .message.bot {
        background: linear-gradient(135deg, var(--inclusion-secondary) 0%, #138D75 100%);
        color: white;
        margin-right: 20%;
        border-bottom-left-radius: 4px;
    }
    
    /* === BOUTONS AMÉLIORÉS === */
    .btn {
        font-weight: 500;
        text-transform: none;
        letter-spacing: 0.025em;
        transition: var(--inclusion-transition);
        border: none;
        cursor: pointer;
        position: relative;
        overflow: hidden;
    }
    
    .btn::before {
        content: '';
        position: absolute;
        top: 50%;
        left: 50%;
        width: 0;
        height: 0;
        background: rgba(255, 255, 255, 0.2);
        border-radius: 50%;
        transition: all 0.3s ease;
        transform: translate(-50%, -50%);
    }
    
    .btn:hover::before {
        width: 300px;
        height: 300px;
    }
    
    .btn:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    }
    
    .btn:active {
        transform: translateY(0);
    }
    
    /* === CHAMPS DE SAISIE === */
    .input-field {
        transition: var(--inclusion-transition);
        border: 2px solid #e5e7eb;
        border-radius: var(--inclusion-radius);
        padding: 12px 16px;
        font-size: 16px;
    }
    
    .input-field:focus {
        outline: none;
        border-color: var(--inclusion-primary);
        box-shadow: 0 0 0 3px rgba(0, 120, 212, 0.1);
        transform: scale(1.02);
    }
    
    .input-field::placeholder {
        color: #9ca3af;
        font-style: italic;
    }
    
    /* === INDICATEURS DE STATUT === */
    .status-indicator {
        padding: 8px 12px;
        border-radius: var(--inclusion-radius);
        font-weight: 500;
        font-size: 14px;
        display: inline-flex;
        align-items: center;
        gap: 8px;
    }
    
    .status-indicator.success {
        background: #e8f5e8;
        color: var(--inclusion-success);
        border: 1px solid #c8e6c9;
    }
    
    .status-indicator.warning {
        background: #fff3e0;
        color: var(--inclusion-warning);
        border: 1px solid #ffcc02;
    }
    
    .status-indicator.error {
        background: #ffebee;
        color: var(--inclusion-error);
        border: 1px solid #ffcdd2;
    }
    
    /* === ANIMATIONS === */
    @keyframes fadeIn {
        from {
            opacity: 0;
            transform: translateY(20px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    @keyframes slideIn {
        from {
            transform: translateX(-100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes pulse {
        0%, 100% {
            transform: scale(1);
        }
        50% {
            transform: scale(1.05);
        }
    }
    
    /* === INDICATEURS DE TYPING === */
    .typing-indicator {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        color: #6b7280;
        font-style: italic;
    }
    
    .typing-indicator::after {
        content: '●●●';
        animation: pulse 1.5s infinite;
    }
    
    /* === RESPONSIVE DESIGN === */
    @media (max-width: 768px) {
        .gradio-container {
            padding: 16px;
            margin: 0;
        }
        
        .chatbot .message.user {
            margin-left: 10%;
        }
        
        .chatbot .message.bot {
            margin-right: 10%;
        }
        
        .btn {
            padding: 12px 20px;
            font-size: 16px;
        }
        
        .input-field {
            font-size: 16px; /* Évite le zoom sur iOS */
        }
    }
    
    @media (max-width: 480px) {
        .chatbot .message.user,
        .chatbot .message.bot {
            margin-left: 0;
            margin-right: 0;
        }
        
        .gradio-container {
            padding: 8px;
        }
    }
    
    /* === ACCESSIBILITÉ === */
    @media (prefers-reduced-motion: reduce) {
        * {
            animation-duration: 0.01ms !important;
            animation-iteration-count: 1 !important;
            transition-duration: 0.01ms !important;
        }
    }
    
    /* Focus visible pour clavier */
    .btn:focus-visible,
    .input-field:focus-visible {
        outline: 2px solid var(--inclusion-primary);
        outline-offset: 2px;
    }
    
    /* Contraste élevé */
    @media (prefers-contrast: high) {
        .btn {
            border: 2px solid currentColor;
        }
        
        .input-field {
            border-width: 3px;
        }
    }
    
    /* === DARK MODE === */
    @media (prefers-color-scheme: dark) {
        :root {
            --inclusion-primary: #64B5F6;
            --inclusion-secondary: #4CAF50;
            --inclusion-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
        }
        
        .gradio-container {
            color: #f3f4f6;
        }
        
        .chatbot {
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        }
        
        .input-field {
            background: #374151;
            border-color: #4b5563;
            color: #f3f4f6;
        }
        
        .input-field::placeholder {
            color: #9ca3af;
        }
    }
    
    /* === PRINT STYLES === */
    @media print {
        .chatbot {
            box-shadow: none;
            background: white;
        }
        
        .btn {
            border: 1px solid #000;
        }
        
        .chatbot .message.user,
        .chatbot .message.bot {
            background: white;
            color: black;
            border: 1px solid #000;
        }
    }
    
    /* === LOADING STATES === */
    .loading {
        position: relative;
        pointer-events: none;
        opacity: 0.6;
    }
    
    .loading::after {
        content: '';
        position: absolute;
        top: 50%;
        left: 50%;
        width: 20px;
        height: 20px;
        margin: -10px 0 0 -10px;
        border: 2px solid transparent;
        border-top: 2px solid var(--inclusion-primary);
        border-radius: 50%;
        animation: spin 1s linear infinite;
    }
    
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
    
    /* === DRAG & DROP === */
    .drop-zone {
        border: 2px dashed #d1d5db;
        border-radius: var(--inclusion-radius);
        padding: 40px;
        text-align: center;
        transition: var(--inclusion-transition);
        background: #f9fafb;
    }
    
    .drop-zone.drag-over {
        border-color: var(--inclusion-primary);
        background: rgba(0, 120, 212, 0.05);
        transform: scale(1.02);
    }
    
    /* === TOOLTIPS === */
    .tooltip {
        position: relative;
        display: inline-block;
    }
    
    .tooltip::before {
        content: attr(data-tooltip);
        position: absolute;
        bottom: 125%;
        left: 50%;
        transform: translateX(-50%);
        background: #1f2937;
        color: white;
        padding: 8px 12px;
        border-radius: 4px;
        white-space: nowrap;
        opacity: 0;
        pointer-events: none;
        transition: opacity 0.2s ease;
        font-size: 14px;
        z-index: 1000;
    }
    
    .tooltip:hover::before {
        opacity: 1;
    }
    
    /* === SCROLLBAR PERSONNALISÉE === */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: #f1f5f9;
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb {
        background: #cbd5e1;
        border-radius: 4px;
        transition: background 0.2s ease;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: #94a3b8;
    }
    
    /* === TRANSITIONS GLOBALES === */
    * {
        transition: color 0.2s ease, background-color 0.2s ease, border-color 0.2s ease;
    }
    """


# Fonction utilitaire pour créer un thème avec CSS intégré
def create_inclusion_theme_with_css() -> tuple[InclusionTheme, str]:
    """
    Crée le thème d'inclusion avec le CSS personnalisé.
    
    Returns:
        tuple[InclusionTheme, str]: Thème et CSS personnalisé
    """
    theme = get_inclusion_theme()
    css = get_inclusion_css()
    return theme, css


# Export des constantes de couleur pour réutilisation
INCLUSION_COLORS = {
    "primary": "#0078D4",  # Bleu gouvernemental français
    "secondary": "#16A085",  # Vert inclusif
    "success": "#4CAF50",  # Vert succès
    "warning": "#F57C00",  # Orange avertissement
    "error": "#D32F2F",  # Rouge erreur
    "neutral": "#6B7280",  # Gris neutre
    "light": "#F8FAFC",  # Arrière-plan clair
    "dark": "#1F2937",  # Arrière-plan sombre
}


if __name__ == "__main__":
    # Test du thème
    import gradio as gr
    
    theme, css = create_inclusion_theme_with_css()
    
    with gr.Blocks(theme=theme, css=css) as demo:
        gr.Markdown("# Test du thème d'inclusion sociale")
        
        with gr.Row():
            with gr.Column():
                gr.Textbox(label="Nom", placeholder="Entrez votre nom")
                gr.Slider(label="Âge", minimum=0, maximum=100, value=25)
                
            with gr.Column():
                gr.Dropdown(
                    label="Région",
                    choices=["Île-de-France", "Provence-Alpes-Côte d'Azur", "Auvergne-Rhône-Alpes"],
                    value="Île-de-France"
                )
                gr.Checkbox(label="Accepter les conditions")
        
        with gr.Row():
            gr.Button("Valider", variant="primary")
            gr.Button("Annuler", variant="secondary")
        
        gr.Markdown("## Exemple de chat")
        gr.ChatInterface(
            fn=lambda x, history: f"Vous avez dit: {x}",
            examples=[
                "Bonjour !",
                "Comment allez-vous ?",
                "Merci pour votre aide"
            ]
        )
    
    demo.launch() 