import streamlit as st
import os
import base64
import requests
from openpyxl import Workbook
from io import BytesIO
import time

# OpenAI API Key - This should be stored securely, preferably as an environment variable
api_key = st.secrets["OPENAI_API_KEY"]

def encode_image(image_file):
    return base64.b64encode(image_file.read()).decode('utf-8')

def get_meta_attributes(image_file, max_retries=3):
    base64_image = encode_image(image_file)
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    payload = {
        "model": "gpt-4o",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "ATRIBUTE DATA:length = [Above Knee, Calf Length, Knee Length, Maxi, Mini, Midi]; pattern_trend = [Abstract, Bohemian, Floral, Accordion, Animal Graphic, Animal Print, Candy Stripes, Frayed Denim, Cherry Red, Colourblocked, Backless, Conversational, Bandana, Bling & Sparkly, Block Print, Costume Party, Crochet, Ethnic Print, Lace Frills Bohemian, Micro Pattern, Pocket Detail, Polka Dots, Sleek Utility, Tropical, Geometric, Monochrome, Nautical, Indie Florals, New Basics, Indie Prints, Indigo, Knits, Oversized, Placement, Retro Denims, Ruched, Schiffli, Seersucker, Sheer, Slip Dress, Smocked, Typography, Summer Checks, Utility Or Military, Tie And Dye, Tiered, Trapeze Dress, Tribal, Variegated Stripes, Waisted Dress, Wrap]; neck = [Above The Keyboard Collar, Keyhole Neck, Asymmetric Neck, Mandarin Collar, Boat Neck, Choker Neck, Cowl Neck, Halter Neck, High Neck, Hood, Mock Neck, Off-Shoulder, One Shoulder, Peter Pan Collar, Round Neck, Shirt Collar, Shoulder Straps, Strapless, Square Neck, Sweetheart Neck, Tie-Up Neck, V-Neck]; occasion = [Casual, Daily, Festive, Formal, Maternity, Party]; print_options = [Abstract, Chevron, Alphanumeric, Colourblocked, Animal, Conversational, Bohemian, Brand Logo, Camouflage, Cartoon Characters, Checked, Embellished, Ethnic Motifs, Floral, Geometric, Graphic, Humour, Polka Dots, Tribal, Self Design, Solid, Stars, Typography, Striped, Superhero]; shape = [A-Line, Anarkali, Balloon, Blazer Dresses, Blouson, Bodycon, Drop-Waist, Empire, Fit And Flare, Gown, Jumper Dress, Kaftan, Maxi, Peplum, Pinafore, Sheath, Shirt, T-Shirt, Wrap]; sleeve_length = [Long Sleeves, Short Sleeves, Sleeveless, Three-Quarter Sleeves]; sleeve_styling = [Batwing Sleeves, Bell Sleeves, Bishop Sleeves, Flared Sleeves, Flutter Sleeves, Kimono Sleeves, Cap Sleeves, Cape Sleeves, Puff Sleeves, Cold-Shoulder Sleeves, Cuffed Sleeves, Regular Sleeves, Roll-Up Sleeves, Shoulder Straps, Slit Sleeves, Extended Sleeves]; colors = [Black, Blue, Pink, White, Green, Red, Yellow, Navy Blue, Maroon, Purple, Beige, Brown, Orange, Grey, Peach, Multi, Off White, Lavender, Mustard, Teal, Burgundy, Olive, Cream, Sea Green, Rust, Silver, Mauve, Gold, Rose, Magenta, Lime Green, Coral, Turquoise Blue, Coffee Brown, Charcoal, Khaki, Nude, Fluorescent Green, Taupe, Metallic, Tan, Grey Melange, Steel, Copper, Bronze]. WHAT ARE THE META ATTRIBUTES OF THE GIVEN DRESS: OUTPUT FORMAT: Dress Shape, Length,Pattern,Print, Neck, Sleeve-Length, Sleeve-Styling.  "
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    }
                ]
            }
        ],
        "max_tokens": 60,
        "temperature": 0.5
    }

    for attempt in range(max_retries):
        try:
            response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
            response.raise_for_status()  # Raises an HTTPError for bad responses
            return response.json()
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:  # if it's not the last attempt
                time.sleep(2 ** attempt)  # exponential backoff
                continue
            else:
                raise e

def process_images_and_generate_excel(uploaded_files, progress_bar):
    wb = Workbook()
    ws = wb.active
    ws.title = "Dress Attributes"
    ws_failed = wb.create_sheet(title="Failed Images")

    headers = ["IMAGE_FILE_NAME", "Dress Shape", "Length", "Pattern", "Print", "Neck", "Sleeve-Length", "Sleeve-Styling"]
    ws.append(headers)
    ws_failed.append(["IMAGE_FILE_NAME"])

    total_files = len(uploaded_files)

    for i, file in enumerate(uploaded_files):
        try:
            meta_attributes = get_meta_attributes(file)
            if 'choices' in meta_attributes and meta_attributes['choices']:
                content = meta_attributes['choices'][0]['message']['content']
                attributes = content.split(',')

                attribute_values = [file.name] + [attr.strip() for attr in attributes]

                if any(value.strip() for value in attribute_values[1:]):
                    ws.append(attribute_values)
                else:
                    ws_failed.append([file.name])
            else:
                ws_failed.append([file.name])
        except Exception as e:
            st.error(f"Error processing {file.name}: {str(e)}")
            ws_failed.append([file.name])

        progress_bar.progress((i + 1) / total_files)

    excel_data = BytesIO()
    wb.save(excel_data)
    excel_data.seek(0)
    return excel_data

st.title("Stay Stylist")
st.header("Product Attribution")
st.subheader("Instantly Detect Product Attributes from Images")

uploaded_files = st.file_uploader("Choose image files", type=["png", "jpg", "jpeg"], accept_multiple_files=True)

if uploaded_files:
    progress_bar = st.progress(0)
    excel_data = process_images_and_generate_excel(uploaded_files, progress_bar)

    st.success("Processing complete!")
    st.download_button(
        label="Download Excel File",
        data=excel_data,
        file_name="DRESS_ATTRIBUTES.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
