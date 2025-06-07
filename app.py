import streamlit as st
from google import genai
from google.genai import types
from dotenv import load_dotenv
import os
from PIL import Image
import io
from streamlit_cookies_manager import EncryptedCookieManager

# Load environment variables from .env file
load_dotenv()

st.set_page_config(page_title="Image Generator", page_icon="✨")

# Initialize cookie manager
cookies = EncryptedCookieManager(
    prefix="auth_",  # prefix for all cookies
    password=os.getenv("COOKIE_SECRET")  # use a secret from env
)
if not cookies.ready():
    st.stop()  # Wait until cookies are ready
    
# Check if already authenticated via cookie
if cookies.get("authenticated") == "true":
    st.session_state.authenticated = True

CORRECT_PASSCODE = os.getenv("APP_PASSCODE")
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.markdown("## 🔐 Authentication")
    with st.form("passcode_form"):
        passcode_input = st.text_input("Passcode", type="password")
        submitted = st.form_submit_button("Login")
        if submitted:
            if passcode_input == CORRECT_PASSCODE:
                st.session_state.authenticated = True
                cookies["authenticated"] = "true"
                cookies.save()
                st.success("✅ Access granted!")
                st.rerun()  # Reload to show app
            else:
                st.error("❌ Incorrect passcode. Try again.")
    st.stop()

# Configure Google Gemini API
try:
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
except Exception as e:
    st.error(f"Error configuring Gemini API. : {e}")
    st.stop() # Stop the app if API key is not configured
    
# Function to generate image  using Gemini API
def generate_image_with_gemini(prompt_text, include_text, story_context, aspect_ratio, resolution):
    """Generates an image using the Gemini API based on the provided text."""
    try:
        if aspect_ratio == "16:9":
            image_dimension = f"The image MUST have a precise **{aspect_ratio} widescreen aspect ratio**."
        else:
            image_dimension = f"It MUST have a {aspect_ratio} portrait aspect ratio, ideal for vertical display such as mobile screens or YouTube Shorts."
        if include_text:
            full_prompt = (
                f"GENERATE A PROFESSIONAL VISUAL IMAGE in a vibrant, highly detailed, animated illustration style. "
                f"{image_dimension}"
                f"Ensure that **the provided Hindi text or words are clearly visible and well-integrated** into the image design — like on banners, signs, papers, or visually appropriate elements. "
                f"The Hindi text must appear **readable, naturally embedded**, and **not distorted**. "
                f"Use the following story context to accurately generate the visual scene: {story_context}\n\n"
                f"Every element described in the following Hindi input must be included:\n\n"
                f"'{prompt_text}'"
            )
        else:
            context_description = f"एक दृश्य जिसमें {prompt_text} पूरी तरह से प्राकृतिक रूप से चित्रित हो। यह सिर्फ एक लेबल नहीं है, बल्कि एक पूर्ण वातावरण और दृश्य होना चाहिए। किसी भी प्रकार का पाठ या शब्द चित्र में नहीं होना चाहिए।"
            
            full_prompt = (
                f"STRICTLY GENERATE A VISUAL IMAGE. "
                f"The image MUST be a vibrant, highly detailed, professional **animated illustration**. "
                f"{image_dimension}"
                f"**DO NOT INCLUDE ANY TEXT OR WRITING** in the image — this includes but is not limited to signs, labels, posters, screens, papers, books, symbols, characters, or written language in any form. "
                f"The image MUST NOT contain any alphabetic or numeric characters. "
                f"**NO TEXT OR SYMBOLS** should appear anywhere in the final image. "
                f"CRITICALLY IMPORTANT: Every visual element, character, object, and environmental detail described in the following Hindi text MUST be visually represented with high fidelity. "
                f"DO NOT OMIT ANY DETAIL. "
                f"Use the following story context to accurately generate the visual scene: {story_context}\n\n"
                f"Generate a vivid and complete scene that perfectly visualizes the following Hindi description:\n\n"
                f"'{context_description}'"
            )

        st.info("Attempting to generate image... This may take a moment.")
        
        # Call generate_content with responseModalities to request image output
        response = client.models.generate_content(
            model="gemini-2.0-flash-preview-image-generation",
            contents=full_prompt,
            config=types.GenerateContentConfig(
            response_modalities=['TEXT', 'IMAGE']
            )
        )
        
        generated_image_found = False
        for part in response.candidates[0].content.parts:
            if part.text is not None:
                st.write("**Gemini's Text Response (if any):**")
                st.write(part.text)
            elif part.inline_data is not None:
                st.success("✅ Image successfully generated!")
                img = Image.open(io.BytesIO((part.inline_data.data)))
                
                # Resize to 1920x1080 / 1080X1920
                resized_img = img.resize(resolution, Image.LANCZOS)
                
                st.image(resized_img, caption="Generated Image")
                img_byte_arr = io.BytesIO()
                resized_img.save(img_byte_arr, format="PNG")
                img_bytes = img_byte_arr.getvalue()
                # Download button
                st.download_button(
                    label="⬇️ Download Image",
                    data=img_bytes,
                    file_name="animation.png", # You can make this dynamic
                    mime=part.inline_data.mime_type
                )
                generated_image_found = True
                break
        
        if not generated_image_found:
            st.warning("⚠️ Gemini API did not return an image directly for this prompt. It might have returned only text or encountered an internal issue.")
            if response.text:
                st.write("Full response text for debugging:")
                st.write(response.text)
            st.error("🛑 Please try a different prompt or check the Gemini API documentation for supported image generation formats and limitations.")

    except Exception as e:
        st.error(f"🛑 Error generating image: {e}")

# Streamlit UI

st.markdown("<h3 style='text-align: center;'>🎨 Image Generator 🎨</h3>", unsafe_allow_html=True)
st.markdown("""
### 📝 Description
Enter a Hindi prompt below and generate a **high-resolution animated-style image**.

🌟 The image will be:
- Professional
- Highly detailed
- With a 16:9 / 9:16 aspect ratio
""")

story_context = st.text_area(
    "Enter Story Context:",
    height=300
)

hindi_text_input = st.text_area(
    "💬 Enter Hindi text for your image:",
    placeholder="उदाहरण: एक जंगल में नाचती हुई एक छोटी परी, चमकती हुई पंखों के साथ।",
    height=100
)
include_text = st.checkbox("Image with Text")

# Define options with icons
orientation_options = {
    "Landscape (16:9) 📺": {"aspect_ratio": "16:9", "resolution": (1920, 1080)},
    "Portrait (9:16) 📱": {"aspect_ratio": "9:16", "resolution": (1080, 1920)},
}

# Radio button with default selection (Landscape)
selected_option = st.radio(
    "Choose an orientation:",
    options=list(orientation_options.keys()),
    index=0,  # Default is Landscape
    horizontal=True,
)

if st.button("✨ Generate Image"):
    if hindi_text_input and story_context:
        with st.spinner("🎨 Creating a beautiful image for you..."):
            # Get values based on selection
            selected_values = orientation_options[selected_option]
            aspect_ratio = selected_values["aspect_ratio"]
            resolution = selected_values["resolution"]
            generate_image_with_gemini(hindi_text_input, include_text, story_context, aspect_ratio, resolution)
            # generate_genai(hindi_text_input)
    else:
        st.warning("⚠️ Please enter some Hindi text for your image.")