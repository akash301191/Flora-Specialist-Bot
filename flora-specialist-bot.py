import tempfile
import streamlit as st

from agno.agent import Agent
from agno.media import Image
from agno.models.openai import OpenAIChat
from agno.tools.serpapi import SerpApiTools

from textwrap import dedent

def render_sidebar():
    st.sidebar.title("🔐 API Configuration")
    st.sidebar.markdown("---")

    # OpenAI API Key input
    openai_api_key = st.sidebar.text_input(
        "OpenAI API Key",
        type="password",
        help="Don't have an API key? Get one [here](https://platform.openai.com/account/api-keys)."
    )
    if openai_api_key:
        st.session_state.openai_api_key = openai_api_key
        st.sidebar.success("✅ OpenAI API key updated!")

    # SerpAPI Key input
    serp_api_key = st.sidebar.text_input(
        "Serp API Key",
        type="password",
        help="Don't have an API key? Get one [here](https://serpapi.com/manage-api-key)."
    )
    if serp_api_key:
        st.session_state.serp_api_key = serp_api_key
        st.sidebar.success("✅ Serp API key updated!")

    st.sidebar.markdown("---")

def render_plant_profile():
    st.markdown("---")
    col1, col2 = st.columns(2)

    # Column 1: Image Upload
    with col1:
        st.subheader("🌿 Upload Plant Image")
        uploaded_image = st.file_uploader(
            "Choose a plant photo to identify",
            type=["jpg", "jpeg", "png"]
        )

    return {
        "uploaded_image": uploaded_image,
    }

def generate_plant_report(plant_profile): 
    uploaded_image = plant_profile["uploaded_image"]
    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
        tmp.write(uploaded_image.getvalue())
        image_path = tmp.name

    plant_identifier = Agent(
        model=OpenAIChat(id="gpt-4o", api_key=st.session_state.openai_api_key),
        name="Plant Identifier",
        role="Identifies the species of a plant based on an uploaded photo and provides a brief confidence score and botanical name.",
        description=(
            "You are a plant identification expert. When given an image of a plant, your task is to "
            "analyze visual features (such as leaf shape, pattern, color, stem structure) and accurately "
            "identify the most likely plant species. You also provide a short, clear description of the plant type."
        ),
        instructions=[
            "Analyze the uploaded image carefully and identify the plant species or the most probable match.",
            "Return the common name and the scientific (botanical) name.",
            "Estimate a confidence level as a percentage.",
            "Describe key visual traits that helped in identification (e.g., leaf shape, size, pattern, flower color).",
            "Format your output clearly using markdown like this:\n\n"
            "**Common Name**: <Plant Name>\n"
            "**Scientific Name**: *<Botanical Name>*\n"
            "**Confidence**: <e.g., 92%>\n"
            "**Visual Traits**: <Short bullet list of features>",
            "If unsure, suggest possible close matches and clearly state uncertainty."
        ],
        markdown=True
    )

    identifier_response = plant_identifier.run(
        "Generate an identification of this plant", 
        images=[Image(filepath=image_path)]
    )
    plant_identification = identifier_response.content

    plant_researcher = Agent(
        name="Plant Care Researcher",
        role="Finds accurate plant care instructions using the plant’s name and a brief description.",
        model=OpenAIChat(id="gpt-4o", api_key=st.session_state.openai_api_key),
        description=dedent("""
            You are a plant care research specialist. Given the common and scientific name of a plant,
            along with a short description, your task is to generate a highly focused Google search query
            to find care instructions. Your goal is to return 10 useful links covering how to care for this plant,
            including watering, light needs, climate preferences, and common issues.
        """),
        instructions=[
            "Carefully read the common name, scientific name, and description of the plant.",
            "Generate exactly ONE focused Google search query—for example: 'Lucky Bamboo Dracaena sanderiana care guide'.",
            "Use `search_google` with that query.",
            "Review the results and return a clean list of the 10 most relevant links to plant care guides.",
            "Avoid duplicates, advertisements, and off-topic results.",
            "Do NOT summarize the results—just list URLs clearly in markdown list format.",
        ],
        tools=[SerpApiTools(api_key=st.session_state.serp_api_key)],
        add_datetime_to_instructions=True,
        markdown=True
    )

    research_response = plant_researcher.run(plant_identification)
    research_results = research_response.content 

    plant_advisor = Agent(
        name="Plant Care Advisor",
        role="Generates a structured report combining plant identification and personalized care guidance.",
        model=OpenAIChat(id='o3-mini', api_key=st.session_state.openai_api_key),
        description=dedent("""
            You are a plant care advisor. You are given:
            1. A structured plant identification summary, including common name, scientific name, visual traits, and confidence level.
            2. A list of URLs from trusted sources that explain how to care for this plant.

            Your job is to produce a well-formatted Markdown report with two main sections:
            - ## 🌿 Plant Identification
            - ## 🌿 Plant Care Guide
        """),
        instructions=[
            "Start the report with a ## 🌿 Plant Identification section.",
            "In that section, clearly list:",
            "- **Common Name**",
            "- **Scientific Name** (italicized)",
            "- **Confidence** (as a percentage)",
            "- **Visual Traits** (in a bullet list)",
            "- A short paragraph describing the plant, using the provided description.",
            "",
            "Then, add a ## 🌿 Plant Care Guide section with these subheadings (use ###):",
            "### 🌞 Light Requirements",
            "### 💧 Watering Needs",
            "### 🌡️ Temperature & Humidity",
            "### 🪴 Soil & Potting",
            "### 🐛 Common Issues & Solutions",
            "### 📌 Additional Tips",
            "",
            "Extract accurate information only from the given URLs—do NOT fabricate or assume care tips.",
            "Summarize each section clearly using bullet points or short, useful paragraphs.",
            "Embed hyperlinks where useful using Markdown (e.g., [source](https://example.com)).",
            "Avoid pasting raw URLs or adding redundant descriptions.",
            "Output only the report—do not include explanations of what you're doing or additional summaries."
        ],
        markdown=True,
        add_datetime_to_instructions=True
    )     

    advisor_prompt = f"""
    Plant Identification:
    {plant_identification}

    Research Results: 
    {research_results}

    Use these details to generate a comprehensive plant care report
    """

    advisor_response = plant_advisor.run(advisor_prompt)
    plant_care_guide = advisor_response.content 

    return plant_care_guide

def main() -> None:
    # Page config
    st.set_page_config(page_title="Flora Specialist Bot", page_icon="🌿", layout="wide")

    # Custom styling
    st.markdown(
        """
        <style>
        .block-container {
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }
        div[data-testid="stTextInput"] {
            max-width: 1200px;
            margin-left: auto;
            margin-right: auto;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    # Header and intro
    st.markdown("<h1 style='font-size: 2.5rem;'>🌿 Flora Specialist Bot</h1>", unsafe_allow_html=True)
    st.markdown(
        "Welcome to Flora Specialist Bot — your digital plant expert. Upload a photo of any plant and get instant identification along with a personalized care guide.",
        unsafe_allow_html=True
    )

    render_sidebar()
    plant_profile = render_plant_profile()

    st.markdown("---")

    if st.button("🌿 Generate Plant Report"):
        if not hasattr(st.session_state, "openai_api_key"):
            st.error("Please provide your OpenAI API key in the sidebar.")
        elif not hasattr(st.session_state, "serp_api_key"):
            st.error("Please provide your SerpAPI key in the sidebar.")
        elif "uploaded_image" not in plant_profile or not plant_profile["uploaded_image"]:
            st.error("Please upload a plant image before generating the report.")
        else:
            with st.spinner("Identifying the Plant and Generating a Comprehensive Plant Care Guide..."):
                report = generate_plant_report(plant_profile)
                st.session_state.plant_report = report

    # Display and download
    if "plant_report" in st.session_state:
        st.markdown(st.session_state.plant_report, unsafe_allow_html=True)

        st.download_button(
            label="📥 Download Plant Report",
            data=st.session_state.plant_report,
            file_name="plant_care_report.md",
            mime="text/markdown"
        )


if __name__ == "__main__":
    main()