import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt
import plotly.express as px

st.set_page_config(page_title="Fentanyl Precursors Lookup", layout="wide")
# Global JS for copying text with a toast
st.markdown("""
<script>
function copyCAS(cas) {
    navigator.clipboard.writeText(cas).then(() => {
        let toast = document.createElement("div");
        toast.innerText = "✅ CAS Number copied!";
        toast.style.position = "fixed";
        toast.style.bottom = "20px";
        toast.style.right = "20px";
        toast.style.backgroundColor = "#333";
        toast.style.color = "#fff";
        toast.style.padding = "10px 15px";
        toast.style.borderRadius = "8px";
        toast.style.zIndex = "9999";
        toast.style.fontSize = "14px";
        document.body.appendChild(toast);
        setTimeout(() => { toast.remove(); }, 2000);
    });
}
</script>
""", unsafe_allow_html=True)

if "page" not in st.session_state:
    st.session_state.page = "home"
if "query" not in st.session_state:
    st.session_state.query = ""
if "nav" not in st.query_params:
    st.query_params["nav"] = "home"
if "selected_card_index" not in st.session_state:
    st.session_state.selected_card_index = None

def go_to(page):
    st.session_state.page = page

def top_navbar():
    st.markdown("""
        <style>
            .top-nav-container {
                display: flex;
                justify-content: center;
                margin-top: 10px;
                margin-bottom: 30px;
            }
            .top-nav {
                display: flex;
                gap: 20px;
                background-color: rgba(255, 255, 255, 0.9);
                padding: 12px 25px;
                border-radius: 12px;
                box-shadow: 2px 4px 10px rgba(0, 0, 0, 0.1);
                max-width: 950px;
                width: 100%;
                justify-content: space-around;
            }
            .top-nav button {
                background-color: #fcdeca;
                border: none;
                padding: 10px 18px;
                border-radius: 8px;
                font-weight: 600;
                font-size: 15px;
                cursor: pointer;
                transition: all 0.3s ease;
                flex-grow: 1;
            }
            .top-nav button:hover {
                background-color: #e0efff;
            }
            .top-nav form {
                width: 100%;
            }
        </style>
        <div class="top-nav-container">
            <form class="top-nav">
                <button name="nav" value="home">Home</button>
                <button name="nav" value="synonyms">Synonyms</button>
                <button name="nav" value="sources">Sources</button>
                <button name="nav" value="weight">Weight Tag</button>
            </form>
        </div>
    """, unsafe_allow_html=True)

    # Don’t override session state if manually set by button
    if "nav" in st.query_params and st.session_state.page not in ["add_delete"]:
        st.session_state.page = st.query_params["nav"]

def add_delete_button_centered():
    # This will center on all screen sizes (including mobile)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        st.markdown("&nbsp;", unsafe_allow_html=True)
    with col3:
        st.markdown("&nbsp;", unsafe_allow_html=True)

    with col2:
        st.markdown("""
            <style>
            .stButton > button {
                background-color: #4B0082;
                color: white;
                font-weight: 600;
                padding: 12px 20px;
                font-size: 16px;
                border-radius: 10px;
                width: 100%;
                min-width: 180px;
                max-width: 220px;
                margin: auto;
                display: block;
            }
            </style>
        """, unsafe_allow_html=True)

        if st.button("Add / Delete", key="top_add_delete"):
            st.session_state.page = "add_delete"


top_navbar()

# Hide border/shadow around form container
st.markdown("""
    <style>
        /* Remove the light background box around the form */
        div[data-testid="stForm"] {
            background-color: transparent !important;
            border: none !important;
            box-shadow: none !important;
            padding: 0 !important;
            margin: 0 !important;
        }

        /* Remove any margin from the form internally */
        div[data-testid="stForm"] > div {
            margin: 0 !important;
            padding: 0 !important;
        }

        /* Optional: style the input itself */
        div[data-testid="stTextInput"] input {
            border-radius: 10px;
            border: 1px solid #ccc;
            padding: 10px 15px;
            font-size: 16px;
        }
    </style>
""", unsafe_allow_html=True)

add_delete_button_centered()

# Background
bg_images = {
    "home": " https://media-hosting.imagekit.io/f50525be2f7b4834/UI%20Background.jpg?Expires=1838670630&Key-Pair-Id=K2ZIVPTIP2VGHC&Signature=qNKkYL54t8ru~ywvPDxUVuxLL1nb8scKbaH29DXBNEMvHyYnXoEJG6wgY7Efpuv01hvFR4lZuOYP41hB2QujPF4HhDS~qMsi2SgseJKuyuCeOK5zHi2sirpUtm8p1k~0twoTFwsk8o5K9VKQlPtNc2Z0w6Cf3QRDDgX1uChryJ0M5u9crhfGG-UhP052MhGq7ugL28GL1FMlt3wEsECeI6tRjfZ~AGkIEv69ygUSxcTF0GOwNOPzSduN0q9tmajCipzoFdDu2DySa33xVmqYJnwctp39v90riBOPVj848RddaHIUvR~yhH91RpraY0AapFEB5dP~EvKh7hLQsc5Opg__"
}
st.markdown(f"""
    <style>
        .stApp {{
            background-image: url('{bg_images.get(st.session_state.page, bg_images["home"])}');
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
        }}
        
    </style>
""", unsafe_allow_html=True)
# ------ Home --------
if st.session_state.page == "home":
    st.markdown("<h1 style='text-align: center; color: black;'>Fentanyl Precursors Lookup</h1>", unsafe_allow_html=True)

    
# Empty columns for spacing: [left, center, right]
    col1, col2, col3 = st.columns([2, 5, 2])

    with col2:
        with st.form("search_form", clear_on_submit=False):
            query = st.text_input(
                "",
                value=st.session_state.query,
                placeholder="Enter CAS number, substance name or synonym",
                label_visibility="collapsed"
            )
            submitted = st.form_submit_button(" Search")

            if submitted:
                st.session_state.query = query
                st.session_state.selected_card_index = None
    st.markdown("""
    <style>
    button[kind="primary"] {
        background-color: #4B0082;
        color: white;
        border-radius: 10px;
        padding: 10px 20px;
        font-weight: 600;
        font-size: 16px;
        margin-top: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

    if st.session_state.query:
        try:
            response = requests.get("http://localhost:8006/match", params={"query": st.session_state.query})
            results = response.json() if response.status_code == 200 else []

            if not results or results[0]["match_type"] == "no match":
                st.warning("No match found.")
            else:
                multiple = len(results) > 1

            # ✅ Show confirmation message at the top
                if multiple and st.session_state.selected_card_index is not None:
                    selected = results[st.session_state.selected_card_index]
                    st.markdown(f"""
                        <div style="
                            background-color:rgba(255, 255, 255, 0.7);
                            border-left: 5px solid #28a745;
                            padding: 15px 20px;
                            margin: 15px 0;
                            border-radius: 8px;
                            font-size: 16px;
                            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                        ">
                            You selected: <b>{selected['substance_name']} ({selected['substance_id']})</b>
                        </div>
                    """, unsafe_allow_html=True)
                if multiple:
                    st.markdown("""
                        <div style='margin: 10px 0 20px; padding: 10px 15px;
                        background-color: #ffffcc; color: #333; border-radius: 10px;
                        font-size: 15px; text-align: center; font-weight: 600;'>
                            Multiple results found. Please click on one to select.
                        </div>
                    """, unsafe_allow_html=True)

                for idx, r in enumerate(results):
                    is_selected = st.session_state.selected_card_index == idx
                    bg_color = "#E6FFE6" if is_selected else "#fcf9e8"

                    with st.container():
                        col = st.columns([1])[0]
                        with col:
                            if multiple:
                                if st.button(
                                    label=f"Select this result",
                                    key=f"select_btn_{idx}"
                                ):
                                    st.session_state.selected_card_index = idx
                                    st.rerun()
                            
                        
                            st.markdown(f"""
                                <div style="background-color: {bg_color}; padding: 15px;
                                            margin-bottom: 10px; border-left: 5px solid #4B0082;
                                            border-radius: 10px;">
                                    <b>CAS Number:</b> {r['substance_id']}<br>
                                    <b>Substance Name:</b> {r['substance_name']}<br>
                                    <b>Description:</b> {r['description']}<br>
                                    <b>Matched Text:</b> {r['matched_text']}<br>
                                    <b>Match Type:</b> {r['match_type']}<br>
                                    <b>Score:</b> {r['score']}%<br>
                                    {"<b>Total Synonyms:</b> " + str(r['total_synonyms_matched']) + "<br>" if r.get("total_synonyms_matched") else ""}
                                    {"<b>Weight Tag:</b> " + r['weight_tag_title'] + "<br>" if r.get("weight_tag_title") else ""}
                                </div>
                        """, unsafe_allow_html=True)

        except Exception as e:
            st.error(f"Backend error: {e}")



# ---------------- Synonyms ------------------
elif st.session_state.page == "synonyms":
    st.markdown("<h2 style='color: black; text-align: center;'>Synonym Analysis</h2>", unsafe_allow_html=True)
    st.markdown(f"""
            <div style="background-color:rgba(255, 255, 255, 0.9);padding:10px; border-radius:10px;">
            <h4>{"Search for Related Synonyms"}</h4>   
            </div> 
        """, unsafe_allow_html=True)
    with st.form("synonym_lookup_form"):
        term = st.text_input("", placeholder="e.g., Enter a synonym or substance name")
        find_clicked = st.form_submit_button("Find")

    if find_clicked and term:
        try:
            resp = requests.get("http://localhost:8006/synonyms_lookup", params={"term": term})
            if resp.status_code == 200:
                results = resp.json()
                if results:
                    for entry in results:
                        synonyms = entry.get("Substance_Sourcing_Local_Name", [])
                        synonyms_html = "".join(f"<tr><td>{i+1}</td><td>{syn}</td></tr>" for i, syn in enumerate(synonyms))
                        st.markdown(f"""<div style="background-color:#fffaf0;padding:15px;margin-bottom:10px;
                                    border-left: 4px solid #4B0082; border-radius:10px;">
                                    <b>CAS Number:</b> {entry['Substance_ID']}<br>
                                    <b>Substance Name:</b> {entry['Substance_Name']}<br><br>
                                    <div style="max-height:250px; overflow-y:auto; border:1px solid #ccc;
                                    background:#ffffff; padding:10px; border-radius:8px;">
                                    <table style="width:100%; border-collapse: collapse;">
                                    <thead style="background-color:#f2f2f2;">
                                    <tr>
                                    <th style="padding:8px; border:1px solid #ccc;">#</th>
                                    <th style="padding:8px; border:1px solid #ccc;">Synonym</th>
                                    </tr>
                                    </thead>
                                    <tbody>
                                    {synonyms_html}
                                    </tbody>
                                    </table>
                                    </div>
                                    </div>
                 """, unsafe_allow_html=True)
                else:
                    st.warning("No matching synonyms or substances found.")
            else:
                st.error("Error fetching related synonyms.")
        except Exception as e:
            st.error(f"Request failed: {e}")   
    
    try:
        response = requests.get("http://localhost:8006/synonyms")
        data = response.json()
    except Exception as e:
        st.error(f"Failed to fetch synonym insights: {e}")
        st.stop()
    def set_chart_style():
        plt.rcParams.update({
            "axes.titlesize": 12,
            "axes.labelsize": 10,
            "xtick.labelsize": 7,
            "ytick.labelsize": 7,
            "figure.autolayout": True,
            "figure.figsize": (8, 4)
        })
    st.markdown(f"""
            <div style="background-color:rgba(255, 255, 255, 0.8);padding:10px;margin-bottom:5px; border-radius:10px;">
            <h4>{"Summary Statistics"}</h4>   
            </div> 
        """, unsafe_allow_html=True)
    summary_data = pd.DataFrame({
        "Metric": ["Total Unique Synonyms", "Synonyms linked to one substance", "Synonyms linked to multiple substances"],
        "Count": [
            data.get("total_synonyms", 0),
            data.get("single_substance_synonyms_count", 0),
            data.get("multi_substance_synonyms_count", 0)
        ]
    })
    st.markdown("""
    <style>
        .custom-summary-table {
            background-color: white;
            border-collapse: collapse;
            width: 100%;
            margin-top:0px;
            margin: auto;
            font-size: 16px;
            border: 1px solid #ccc;
            border-radius: 12px;
            overflow: hidden;
                
        }
        .custom-summary-table th {
            border: 1px solid #ccc;
            padding: 10px;
            text-align: center;
            color: gray;
            font-size: 16px;
            
        }
        .custom-summary-table td {
            border: 1px solid #ccc;
            padding: 10px;
            text-align: left;
            color: black;
            
        }
                
        .custom-summary-table thead {
            background-color: #f0f0f0;
        }
    </style>
    """, unsafe_allow_html=True)

    st.markdown(summary_data.to_html(index=False, classes='custom-summary-table'), unsafe_allow_html=True)

    ambig_df = pd.DataFrame(data.get("ambiguous_top_10", []))
    if not ambig_df.empty:
        st.markdown(f"""
            <div style="background-color:rgba(255, 255, 255, 0.8);padding:10px;margin-bottom:5px; border-radius:10px;">
            <h4>{"Top 10 Ambiguous Synonyms (Mapped to Multiple Substances)"}</h4>   
            </div> 
        """, unsafe_allow_html=True)
        st.dataframe(ambig_df)
 
    dist_df = pd.DataFrame(data.get("distribution", []))
    if not dist_df.empty:
        st.markdown(f"""
            <div style="background-color:rgba(255, 255, 255, 0.8);padding:10px;margin-bottom:5px; border-radius:10px;">
            <h4>{"Synonym Mapping Distribution"}</h4>   
            </div> 
        """, unsafe_allow_html=True)
        dist_df["Mapped Substances"] = dist_df["Mapped Substances"].astype(str)
        fig = px.bar(dist_df, x="Mapped Substances", y="Synonym Count", text="Synonym Count")
        fig.update_traces(textposition="outside")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(dist_df)
 
    top_sub_df = pd.DataFrame(data.get("top_substances_by_synonyms", []))
    if not top_sub_df.empty:
        
        st.markdown(f"""
            <div style="background-color:rgba(255, 255, 255, 0.8);padding:10px;margin-bottom:5px; border-radius:10px;">
            <h4>{"Top 10 Substances with Most Synonyms"}</h4>   
            </div> 
        """, unsafe_allow_html=True)
        set_chart_style()
        fig, ax = plt.subplots()
        top_sub_df.plot(x="Substance_Name", y="Synonym Count", kind="bar", ax=ax, color="slateblue", legend=False)
        ax.set_ylabel("Synonym Count")
        st.pyplot(fig)
        st.dataframe(top_sub_df)
 
    single_df = pd.DataFrame(data.get("single_synonym_substances", []))
    if not single_df.empty:
        st.markdown(f"""
            <div style="background-color:rgba(255, 255, 255, 0.8);padding:10px;margin-bottom:5px; border-radius:10px;">
            <h4>{"Substances with Only One Synonym"}</h4>   
            </div> 
        """, unsafe_allow_html=True)
        set_chart_style()
        fig, ax = plt.subplots()
        single_df.plot(x="Substance_Name", y="Synonym Count", kind="bar", ax=ax, color="orange", legend=False)
        ax.set_ylabel("Synonym Count")
        #st.pyplot(fig)
        st.dataframe(single_df)
 
    avg_df = pd.DataFrame(data.get("avg_synonym_count_per_type", []))
    if not avg_df.empty:
        st.markdown(f"""
            <div style="background-color:rgba(255, 255, 255, 0.8);padding:10px;margin-bottom:5px; border-radius:10px;">
            <h4>{"Average Synonym Count per Substance Type"}</h4>   
            </div> 
        """, unsafe_allow_html=True)
        set_chart_style()
        fig, ax = plt.subplots()
        avg_df.plot(x="Substance_Type_Title", y="Synonym Count", kind="bar", ax=ax, color="steelblue", legend=False)
        ax.set_ylabel("Average Synonym Count")
        st.pyplot(fig)
 

# ---------------- Weight Tag ------------------
elif st.session_state.page == "weight":
    st.markdown("<h2 style='text-align: center; color: black;'>Weighting Tag Information</h2>", unsafe_allow_html=True)

    weight_data = pd.DataFrame([
        {"Weight Tag": "Illicit", "Description": "Refers to drugs whose production, distribution, or use is prohibited by law.", "Weight": 10},
        {"Weight Tag": "CSA Schedule I", "Description": "Substances with high abuse potential, no accepted medical use, and lack of safety under supervision.", "Weight": 20},
        {"Weight Tag": "CSA Schedule II", "Description": "High abuse potential, accepted medical use with restrictions, and risk of severe dependence.", "Weight": 15},
        {"Weight Tag": "CSA Schedule III", "Description": "Moderate to low physical dependence risk, accepted medical use, lower abuse potential than Schedules I and II.", "Weight": 10},
        {"Weight Tag": "CSA Schedule IV", "Description": "Low abuse potential compared to Schedule III, accepted medical use, and limited dependence risk.", "Weight": 5},
        {"Weight Tag": "CSA Schedule V", "Description": "Lowest abuse potential among CSA schedules, accepted medical use, limited dependence potential.", "Weight": 2},
        {"Weight Tag": "CSA NARC", "Description": "Refers to narcotics regulated under CSA, often used to dull pain and may be addictive.", "Weight": 2},
        {"Weight Tag": "Others", "Description": "Categories or substances not classified under CSA schedules or narcotic regulations.", "Weight": 5}
    ])

    st.markdown("""
        <style>
            .beautiful-table {
                width: 100%;
                border-collapse: collapse;
                margin-top: 20px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 15px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.05);
                border-radius: 8px;
                overflow: hidden;
            }
            .beautiful-table thead {
                background-color: #dedcdc;
                color: black;
                
            }
            .beautiful-table th {
                padding: 12px 16px;
                vertical-align: top;
                text-align: center;
           
            }
            .beautiful-table td {
                padding: 12px 16px;
                vertical-align: top;
                text-align: left;
            }
            .beautiful-table tbody tr {
                background-color: white;
                text-align: left;
            }
            .beautiful-table tbody tr:hover {
                background-color: white;
            }
        </style>
    """, unsafe_allow_html=True)

    st.markdown(weight_data.to_html(classes="beautiful-table", index=False, escape=False), unsafe_allow_html=True)


#------------- sources -------------------------------
elif st.session_state.page == "sources":
    st.markdown("<h2 style='color: black; text-align: center;'>Data Sources</h2>", unsafe_allow_html=True)

    st.markdown("""
        <style>
            .plain-link {
                color: black !important;
                text-decoration: none !important;
                word-break: break-word;
            }
            .plain-link:hover {
                color: #4B0082 !important;
                text-decoration: underline !important;
            }
        </style>
    """, unsafe_allow_html=True)

    sources = [
        {
            "name": "DEA Special Surveillance List (DEA_SSL)",
            "description": "This document, published in the Federal Register on October 24, 2023, by the U.S. Drug Enforcement Administration (DEA), outlines an updated Special Surveillance List. The list includes chemicals, products, materials, and equipment that are frequently used in the illicit manufacture of controlled substances. It is intended to raise awareness among suppliers and the public regarding items that may be misused for illegal drug production.",
            "url": "https://www.govinfo.gov/content/pkg/FR-2023-10-24/pdf/2023-23478.pdf",
            "license": "Public Domain (U.S. Government Work) As a publication of the Federal Register, it is not subject to copyright under 17 U.S.C. § 105 and may be freely used, reproduced, and distributed."
        },
        {
            "name": "Controlled Substances by CSA Schedule (CSA List)",
            "description": "This document, provided by the DEA's Diversion Control Division, lists all controlled substances classified under the Controlled Substances Act (CSA), organized by their respective schedules (Schedule I-V). It includes substance names, control numbers, and their legal classifications, serving as a reference for law enforcement, healthcare professionals, and regulatory agencies.",
            "url": "https://www.deadiversion.usdoj.gov/schedules/orangebook/e_cs_sched.pdf",
            "license": "Public Domain (U.S. Government Work) Produced by the U.S. Drug Enforcement Administration, this content is also not subject to copyright per 17 U.S.C. § 105 and can be used without restriction."
        },
        {
            "name": "PubChem REST API - Compound Synonyms by Name (CAS Number)",
            "description": "This RESTful API endpoint, provided by the National Center for Biotechnology Information (NCBI) via PubChem, retrieves synonym information for a compound using its CAS (Chemical Abstracts Service) number or name. The response is returned in JSON format and includes a list of alternative names and identifiers associated with the queried compound. This API is widely used in cheminformatics and bioinformatics applications for accessing chemical compound data programmatically.",
            "url": "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{CAS_Number}/synonyms/JSON",
            "license": "Public Domain (U.S. Government Work) - PubChem is a product of the U.S. National Institutes of Health (NIH) and its content is in the public domain under 17 U.S.C. § 105. Data retrieved from the API may be freely used, shared, and redistributed without restriction. Attribution is encouraged but not required."
        },
        {
            "name": "U.S. House Select Committee on the Chinese Communist Party (CCP)",
            "description": "This official website hosts resources, hearings, reports, and press releases related to the U.S. House Select Committee on the CCP. The Committee investigates economic, technological, and security threats posed by the Chinese Communist Party, including its role in the global illicit drug trade such as the trafficking of precursor chemicals used in the production of fentanyl and other controlled substances. The site provides insights into policy efforts aimed at combating these activities and includes government findings and legislative proposals related to supply chain control.",
            "url": "https://selectcommitteeontheccp.house.gov/",
            "license": "Public Domain (U.S. Government Work) - As a publication of the U.S. federal government, the content on this website is generally in the public domain under 17 U.S.C. § 105. Materials may be used, shared, or reproduced without restriction, although proper attribution is considered good practice."
        }
    ]

    for source in sources:
        url_note = ""
        if source['name'].startswith("PubChem"):
            url_note = "<p style='color: gray; font-size: 13px; margin-top: -10px;'>Note: Replace <code>{CAS_Number}</code> in the URL with an actual CAS number to retrieve synonyms.</p>"

        st.markdown(f"""
            <div style="background-color:#f7f7f7; padding:15px; margin-bottom:20px;
                        border-left:5px solid #4B0082; border-radius:10px;">
                <h4>{source['name']}</h4>
                <p><strong>Description:</strong> {source['description']}</p>
                <p><strong>URL:</strong> <a href="{source['url']}" target="_blank" class="plain-link">{source['name']}</a></p>{url_note}
                <p><strong>License:</strong> {source['license']}</p>
            </div>
        """, unsafe_allow_html=True)

#------------- add/ delete ----------------------------
elif st.session_state.page == "add_delete":
    st.markdown("<h2 style='color: black; text-align: center;'>Add / Delete </h2>", unsafe_allow_html=True)
    #st.info("This is the Add/Delete page. Here you'll allow users to modify data.")
    st.markdown(f"""
                <div style="background-color:rgba(255, 255, 255, 0.9);border-left:5px solid #4B0082;padding:15px; border-radius:10px;">
                <p>{"This is the Add/Delete page. Here you'll be able to modify data."}</p>   
                </div> 
      """, unsafe_allow_html=True)
    
    #margin-bottom:20px;