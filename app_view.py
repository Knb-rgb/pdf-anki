# AppView.py
import json
import streamlit as st
import fitz

class AppView:
    def __init__(self, actions):
        self.actions = actions

    def display(self):
        dev = True

        # TODO: Fix: Sometimes cards aren't added
        # TODO: Only do one check and then create button to check for Anki. Add button to refresh decks.
        if "no_ankiconnect" in st.session_state and st.session_state.no_ankiconnect == False:
            if "api_perms" not in st.session_state:
                self.actions.check_API()
        # TODO: Add all variable to session state
        range_good = False
        
        st.info("Before a login system is implemented you will have to enter an OpenAI API key each time to use the site without limitations. [Buy Me A Coffee](https://www.buymeacoffee.com/benno094) to support development of the site.")

        # TODO: Add small preview images to sidebar and maybe a slider to choose page range or selection of images
        with st.sidebar:
            if dev == True:
                st.session_state['API_KEY'] = st.secrets.OPENAI_API_KEY
            else:
                st.session_state['API_KEY'] = st.text_input("Enter OpenAI API key (Get one [here](https://platform.openai.com/account/api-keys))", type = "password")
            # TODO: Determine language from file
            languages = ['English', 'Bengali', 'French', 'German', 'Hindi', 'Urdu', 'Mandarin Chinese', 'Polish', 'Portuguese', 'Spanish', 'Arabic']
            st.session_state["lang"] = st.selectbox("Returned language", languages, on_change=self.clear_data)
            col1, col2 = st.columns(2)
            with col1:            
                start = st.number_input('Starting page', value=1, min_value=1, format='%i')
            with col2:
                if st.session_state['API_KEY'] == "":
                    num = st.number_input('Number of pages', value=1, format='%d', disabled = True)
                else:
                    num = st.number_input('Number of pages', value=10, min_value=1, format='%d')
            if st.session_state['API_KEY'] == "":
                st.warning("Enter API key to remove limitations")

            file = st.file_uploader("Choose a file", type=["pdf"])
            if file:
                with file:                
                    st.session_state["file_name"] = file.name
                    doc = fitz.open("pdf", file.read())
                    if "page_count" not in st.session_state:
                        st.session_state['page_count'] = len(doc)

                    if start > st.session_state['page_count']:
                        st.warning("Start page out of range")
                        range_good = False
                    else:
                        range_good = True

                    # Check if previews already exist
                    if f"image_{st.session_state['page_count'] - 1}" not in st.session_state:
                        xreflist = []

                        # Load the PDF and its previews and extract text for each page
                        for i, page in enumerate(doc):
                            print("Extracting page #", i)
                            pix = page.get_pixmap(dpi=100)
                            img = pix.tobytes(output='jpg', jpg_quality=80)

                            st.session_state['image_' + str(i)] = img
                            st.session_state['text_' + str(i)] = page.get_text()

                            # TODO: Remove images that appear on every slide (e.g. logos): https://github.com/pymupdf/PyMuPDF-Utilities/blob/master/examples/extract-images/extract-from-pages.py
                            # TODO: Get background images and vector images: https://github.com/pymupdf/PyMuPDF-Utilities/blob/master/examples/extract-vector-graphics/separate-figures.py
                            images = []
                            dimlimit = 100  # each image side must be greater than this
                            relsize = 0.05  # image : image size ratio must be larger than this (5%)
                            abssize = 2048  # absolute image size limit 2 KB: ignore if smaller

                            il = doc.get_page_images(i)
                            for img in il:
                                xref = img[0]
                                if xref in xreflist:
                                    continue
                                xreflist.append(xref)
                                width = img[2]
                                height = img[3]
                                if min(width, height) <= dimlimit:
                                    continue
                                image = self.actions.recoverpix(doc, img)
                                n = image["colorspace"]
                                imgdata = image["image"]

                                if len(imgdata) <= abssize:
                                    continue
                                if len(imgdata) / (width * height * n) <= relsize:
                                    continue

                                images.append(imgdata)
                            
                            p = i
                            new_rects = self.actions.detect_rects(page)
                            mat = fitz.Matrix(3, 3)  # high resolution matrix
                            for i, r in enumerate(new_rects):
                                pix = page.get_pixmap(matrix=mat, clip=r)
                                img = pix.tobytes(output='jpg', jpg_quality=80)
                                images.append(img)
                                
                            st.session_state[f"images_{p}"] = images

            else:
                if "image_0" in st.session_state:
                    self.clear_data()

            if "decks" in st.session_state:
                st.selectbox(
                'Choose a deck',
                st.session_state['decks'],
                key="deck"
                )
                if st.button("Refresh decks", key = "deck_refresh_btn"):
                    if "decks" in st.session_state:
                        del st.session_state["decks"]
                    self.actions.get_decks()
                st.markdown("**Note:** Note type ['Basic'](https://docs.ankiweb.net/getting-started.html#note-types) must exist for cards to be added.")
                st.session_state["no_ankiconnect"] = False
            else:
                st.checkbox(label = "Use without AnkiConnect", key = "no_ankiconnect")
                if st.session_state["no_ankiconnect"] == False:
                    self.actions.get_decks()
                    st.markdown("**To add flashcards to Anki:**\n- Anki needs to be running with AnkiConnect installed (Addon #: 2055492159)\n- A popup from Anki will appear $\\rightarrow$ choose yes.\n\n **Note:** If unable to connect, disable ad/tracker-blocker for the site.")
            st.divider()
            st.write("Disclaimer: Use at your own risk.")
            st.write("[Feedback](mailto:pdf.to.anki@gmail.com)")

        # TODO: Cache all created flashcards
    
        if range_good:
            if st.session_state["no_ankiconnect"] == False and "decks" in st.session_state or st.session_state["no_ankiconnect"] == True:
                # Loop through the pages
                for i in range(start - 1, start + num - 1):
                    if i == st.session_state['page_count']:
                        break
                    # st.toast("Generating flashcards for page " + str(i + 1) + "/" + str(st.session_state['page_count']))                
                    if f"{i}_is_title" not in st.session_state:
                        if "flashcards_" + str(i) not in st.session_state:
                            self.generate_flashcards(i)

                    # Create an expander for each image and its corresponding flashcards
                    # If cards have been added collapse
                    # TODO: Change variable when manually collapsed
                    if "flashcards_" + str(i) + "_added" in st.session_state:
                        coll = False
                    else:
                        coll = True

                    if f"status_label_{i}" in st.session_state:
                        label = f" - {st.session_state[f'status_label_{i}']}"
                    else:
                        label = ""

                    with st.expander(f"Page {i + 1}/{st.session_state.get('page_count', '')}{label}", expanded=coll):                    
                        if st.session_state['API_KEY'] == "":
                            st.warning("Enter API key to generate more than two flashcards")
                        col1, col2 = st.columns([0.6, 0.4])
                        # Display the image in the first column
                        with col1:
                            st.image(st.session_state['image_' + str(i)])

                        # If flashcards exist for the page, show them and show 'Add to Anki' button
                        # Otherwise, show 'generate flashcards' button              
                        if f"{i}_is_title" in st.session_state:
                            st.session_state['flashcards_' + str(i)] = "dummy cards"
                        with col2:
                            if 'flashcards_' + str(i) in st.session_state:

                                p = i
                                flashcards = json.loads(json.dumps(st.session_state['flashcards_' + str(i)]))

                                if f"{i}_is_title" in st.session_state and st.session_state[f"{i}_is_title"] == True:
                                    flashcards = None
                                    st.info("No flashcards generated for this slide as it doesn't contain relevant information.")

                                # Check if GPT returned something usable, else remove entry and throw error
                                if flashcards:
                                    if st.session_state['API_KEY'] == "":
                                        if len(flashcards) > 2:
                                            flashcards = flashcards[:2]
                                    length = len(flashcards)
                                else:
                                    del st.session_state['flashcards_' + str(i)]
                                    if st.button("Regenerate flashcards", key=f"reg_{i}"):
                                        self.generate_flashcards(i, regen = True)
                                    continue
                                # Create a tab for each flashcard
                                tabs = st.tabs([f"#{i+1}" for i in range(length)])
                                if "flashcards_" + str(i) + "_count" not in st.session_state:
                                    st.session_state["flashcards_" + str(i) + "_count"] = length
                                    st.session_state["flashcards_" + str(i) + "_to_add"] = length

                                for i, flashcard in enumerate(flashcards):
                                    with tabs[i]:
                                        # TODO: Add option to modify a flashcard using GPT with a individual prompt/button
                                        # TODO: Make function for creation of flashcards
                                        # Default state: display flashcard
                                        if f"fc_active_{p, i}" not in st.session_state:
                                            if st.session_state["flashcards_" + str(p) + "_count"] > 5:
                                                st.session_state[f"fc_active_{p, i}"] = False
                                                st.session_state["flashcards_" + str(p) + "_to_add"] = 0
                                                st.text_input(f"Front", value=flashcard["front"], key=f"front_{p, i}", disabled=True)
                                                st.text_area(f"Back", value=flashcard["back"], key=f"back_{p, i}", disabled=True)

                                                st.button("Enable flashcard", key=f"del_{p, i}", on_click=self.enable_flashcard, args=[p, i])
                                            else:                                           
                                                st.session_state[f"fc_active_{p, i}"] = True
                                                st.text_input(f"Front", value=flashcard["front"], key=f"front_{p, i}", disabled=False)
                                                st.text_area(f"Back", value=flashcard["back"], key=f"back_{p, i}", disabled=False)

                                                st.button("Disable flashcard", key=f"del_{p, i}", on_click=self.disable_flashcard, args=[p, i])
                                        elif f"fc_active_{p, i}" in st.session_state and st.session_state[f"fc_active_{p, i}"] == False:
                                            st.text_input(f"Front", value=flashcard["front"], key=f"front_{p, i}", disabled=True)
                                            st.text_area(f"Back", value=flashcard["back"], key=f"back_{p, i}", disabled=True)

                                            st.button("Enable flashcard", key=f"del_{p, i}", on_click=self.enable_flashcard, args=[p, i])
                                        else:                                    
                                            st.text_input(f"Front", value=flashcard["front"], key=f"front_{p, i}", disabled=False)
                                            st.text_area(f"Back", value=flashcard["back"], key=f"back_{p, i}", disabled=False)

                                            st.button("Disable flashcard", key=f"del_{p, i}", on_click=self.disable_flashcard, args=[p, i])
                                col1, col2 = st.columns([0.4,1])
                                with col1:
                                    # Blank out 'add to Anki' button if no cards
                                    if st.session_state["flashcards_" + str(p) + "_to_add"] == 0:
                                        no_cards = True
                                    else:
                                        no_cards = False                                
                                    if "flashcards_" + str(p) + "_added" not in st.session_state:
                                        st.button(f"Add {st.session_state['flashcards_' + str(p) + '_to_add']} flashcard(s) to Anki", key=f"add_{str(p)}", on_click=self.prepare_and_add_flashcards_to_anki, args=[p], disabled=no_cards)
                                with col2:
                                    if "flashcards_" + str(p) + "_tags" not in st.session_state:
                                        st.session_state["flashcards_" + str(p) + "_tags"] = st.session_state["file_name"].replace(' ', '_').replace('.pdf', '') + "_page_" + str(p + 1)
                                    st.text_input("Tag:", value = st.session_state["flashcards_" + str(p) + "_tags"], key = f"tag_{str(p)}")

                        if st.checkbox("Show images", key = f"show_images_{p}"):
                            no_images = len(st.session_state[f"images_{p}"])
                            cols = st.columns(no_images)
                            for i, img in enumerate(st.session_state[f"images_{p}"]):
                                with cols[i]:
                                    st.markdown(f"**Image #{i}**")
                                    st.image(img)
                        
            else:
                if "decks" not in st.session_state:
                    st.warning("Start Anki with AnkiConnect installed or tick checkbox to use without")

    def clear_data(self):
        for key in st.session_state.keys():
            if key == "decks" or key == "api_perms":
                continue
            del st.session_state[key]

    def disable_flashcard(self, page, num):
        st.session_state[f"fc_active_{page, num}"] = False
        st.session_state["flashcards_" + str(page) + "_to_add"] -= 1

    def enable_flashcard(self, page, num):
        st.session_state[f"fc_active_{page, num}"] = True        
        st.session_state["flashcards_" + str(page) + "_to_add"] += 1

    def add_card(self, page):
        if f"{page}_is_title" in st.session_state:
            st.session_state[f"{page}_is_title"] = False

    def prepare_and_add_flashcards_to_anki(self, page):
        prepared_flashcards = []

        for i in range(st.session_state["flashcards_" + str(page) + "_count"]):
            if st.session_state[f"fc_active_{page, i}"] != False:
                front_text = st.session_state[f"front_{page, i}"]
                back_text = st.session_state[f"back_{page, i}"]

                prepared_flashcards.append({"front": front_text, "back": back_text})

        try:
            # Total cards to add for current page
            st.session_state["flashcards_to_add"] = st.session_state["flashcards_" + str(page) + "_to_add"]
            success = self.actions.add_to_anki(prepared_flashcards, page)
            if success:
                # Add state for flashcards added
                st.session_state["flashcards_" + str(page) + "_added"] = True
                st.session_state[f"fc_active_{page, i}"] = True
                st.session_state["flashcards_" + str(page) + "_count"] = 0
                st.session_state["flashcards_" + str(page) + "_to_add"] = 0
                st.session_state[f"status_label_{page}"] = "Added!"
            else:
                raise Exception("Error 2:", success)

        except Exception as e:
            with st.sidebar:
                st.warning(e, icon="⚠️")

    def generate_flashcards(self, page, regen = None):
        if regen:
            if f"{page}_is_title" in st.session_state:
                del st.session_state[f"{page}_is_title"]
        # TODO: Receive in chunks so user knows something is happening
        flashcards = self.actions.send_to_gpt(page)

        if flashcards:
            flashcards_clean = self.actions.cleanup_response(flashcards)

            st.session_state['flashcards_' + str(page)] = flashcards_clean
