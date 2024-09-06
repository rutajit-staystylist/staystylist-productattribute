import streamlit as st
import zipfile
import os
import tempfile
import base64
import requests
from openpyxl import Workbook
from io import BytesIO

# OpenAI API Key - This should be stored securely, preferably as an environment variable
api_key = st.secrets["OPENAI_API_KEY"]

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def get_meta_attributes(image_path):
    base64_image = encode_image(image_path)
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    payload = {
        "model": "gpt-4-vision-preview",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Analyze the image and provide the following attributes of the dress: Dress Shape, Length, Pattern, Print, Neck, Sleeve-Length, Sleeve-Styling. Use the following options for each attribute:\n\nDress Shape: [A-Line, Anarkali, Balloon, Blazer Dresses, Blouson, Bodycon, Drop-Waist, Empire, Fit And Flare, Gown, Jumper Dress, Kaftan, Maxi, Peplum, Pinafore, Sheath, Shirt, T-Shirt, Wrap]\nLength: [Above Knee, Calf Length, Knee Length, Maxi, Mini, Midi]\nPattern: [Abstract, Bohemian, Floral, Accordion, Animal Graphic, Animal Print, Candy Stripes, Frayed Denim, Cherry Red, Colourblocked, Backless, Conversational, Bandana, Bling & Sparkly, Block Print, Costume Party, Crochet, Ethnic Print, Lace Frills Bohemian, Micro Pattern, Pocket Detail, Polka Dots, Sleek Utility, Tropical, Geometric, Monochrome, Nautical, Indie Florals, New Basics, Indie Prints, Indigo, Knits, Oversized, Placement, Retro Denims, Ruched, Schiffli, Seersucker, Sheer, Slip Dress, Smocked, Typography, Summer Checks, Utility Or Military, Tie And Dye, Tiered, Trapeze Dress, Tribal, Variegated Stripes, Waisted Dress, Wrap]\nPrint: [Abstract, Chevron, Alphanumeric, Colourblocked, Animal, Conversational, Bohemian, Brand Logo, Camouflage, Cartoon Characters, Checked, Embellished, Ethnic Motifs, Floral, Geometric, Graphic, Humour, Polka Dots, Tribal, Self Design, Solid, Stars, Typography, Striped, Superhero]\nNeck: [Above The Keyboard Collar, Keyhole Neck, Asymmetric Neck, Mandarin Collar, Boat Neck, Choker Neck, Cowl Neck, Halter Neck, High Neck, Hood, Mock Neck, Off-Shoulder, One Shoulder, Peter Pan Collar, Round Neck, Shirt Collar, Shoulder Straps, Strapless, Square Neck, Sweetheart Neck, Tie-Up Neck, V-Neck]\nSleeve-Length: [Long Sleeves, Short Sleeves, Sleeveless, Three-Quarter Sleeves]\nSleeve-Styling: [Batwing Sleeves, Bell Sleeves, Bishop Sleeves, Flared Sleeves, Flutter Sleeves, Kimono Sleeves, Cap Sleeves, Cape Sleeves, Puff Sleeves, Cold-Shoulder Sleeves, Cuffed Sleeves, Regular Sleeves, Roll-Up Sleeves, Shoulder Straps, Slit Sleeves, Extended Sleeves]\n\nProvide the output in the following format:\nDress Shape: [value]\nLength: [value]\nPattern: [value]\nPrint: [value]\nNeck: [value]\nSleeve-Length: [value]\nSleeve-Styling: [value]"
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
        "max_tokens": 300
    }

    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
    return response.json()

def process_images_and_generate_excel(folder_path, progress_bar):
    wb = Workbook()
    ws = wb.active
    ws.title = "Dress Attributes"
    ws_failed = wb.create_sheet(title="Failed Images")

    headers = ["IMAGE_FILE_NAME", "Dress Shape", "Length", "Pattern", "Print", "Neck", "Sleeve-Length", "Sleeve-Styling"]
    ws.append(headers)
    ws_failed.append(["IMAGE_FILE_NAME"])

    image_files = [f for f in os.listdir(folder_path) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    total_files = len(image_files)

    for i, filename in enumerate(image_files):
        image_path = os.path.join(folder_path, filename)
        try:
            meta_attributes = get_meta_attributes(image_path)
            if 'choices' in meta_attributes and meta_attributes['choices']:
                content = meta_attributes['choices'][0]['message']['content']
                attributes = content.split('\n')

                attribute_values = [filename]
                for header in headers[1:]:
                    found = False
                    for attribute in attributes:
                        if attribute.lower().startswith(header.lower()):
                            attribute_values.append(attribute.split(':')[1].strip())
                            found = True
                            break
                    if not found:
                        attribute_values.append("")

                if any(value.strip() for value in attribute_values[1:]):
                    ws.append(attribute_values)
                else:
                    ws_failed.append([filename])
            else:
                ws_failed.append([filename])
        except Exception as e:
            st.error(f"Error processing {filename}: {str(e)}")
            ws_failed.append([filename])

        progress_bar.progress((i + 1) / total_files)

    excel_data = BytesIO()
    wb.save(excel_data)
    excel_data.seek(0)
    return excel_data

st.title("Dress Attribute Extractor")

uploaded_file = st.file_uploader("Choose a ZIP file containing images", type="zip")

if uploaded_file is not None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        with zipfile.ZipFile(uploaded_file, 'r') as zip_ref:
            zip_ref.extractall(tmp_dir)

        progress_bar = st.progress(0)
        excel_data = process_images_and_generate_excel(tmp_dir, progress_bar)

        st.success("Processing complete!")
        st.download_button(
            label="Download Excel File",
            data=excel_data,
            file_name="DRESS_ATTRIBUTES.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )