import streamlit as st
import requests
from requests.auth import HTTPBasicAuth
import xml.etree.ElementTree as ET
import pandas as pd
import io
import plotly.graph_objects as go

# Set page configuration
st.set_page_config(layout="wide")

# Connecting to the cloud
NEXTCLOUD_URL = st.secrets["nextcloud"]["NEXTCLOUD_URL"]
USERNAME = st.secrets["nextcloud"]["username"]
PASSWORD = st.secrets["nextcloud"]["next_cloudpass"]

@st.cache_data
def get_csv_file_as_dataframe(file_path):
    url = f"{NEXTCLOUD_URL}{file_path}"
    try:
        response = requests.get(url, auth=HTTPBasicAuth(USERNAME, PASSWORD))
        if response.status_code == 200:
            csv_content = response.content.decode('utf-8')
            df = pd.read_csv(io.StringIO(csv_content))
            return df
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to Load the master: {e}")
        return []

# Function to list files in the specified folder on NextCloud
@st.cache_data
def list_nextcloud_folder_files(folder_path="/specific-folder"):
    url = f"{NEXTCLOUD_URL}{folder_path}/"
    try:
        response = requests.request("PROPFIND", url, auth=HTTPBasicAuth(USERNAME, PASSWORD))
        response.raise_for_status()  # Raise an error for bad responses
        file_list = []
        if response.status_code == 207:
            # Parse XML response to get file and folder names
            root = ET.fromstring(response.text)
            namespace = {'d': 'DAV:'}

            for response in root.findall("d:response", namespace):
                href = response.find("d:href", namespace).text
                if href.endswith('/'):
                    folder_name = href.split('/')[-2]
                    if folder_name != folder_path.strip('/'):
                        file_list.append(folder_name)
                else:
                    file_name = href.split('/')[-1]
                    file_list.append(file_name)
        return file_list
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to list files: {e}")
        return []

# Function to get data as a DataFrame
@st.cache_data
def get_dpt_as_dataframe(file_path):
    url = f"{NEXTCLOUD_URL}{file_path}"
    try:
        response = requests.get(url, auth=HTTPBasicAuth(USERNAME, PASSWORD))
        response.raise_for_status()  # Raise an error for bad responses
        dpt = response.content.decode('utf-8')
        df = pd.read_table(io.StringIO(dpt), header=None, names=['Wavenumber', 'Intensity'], delimiter=',')
        return df
    except requests.exceptions.RequestException as e:
        st.error(f"Error downloading file: {e}")
        return None

# Function to load and normalize data
@st.cache_data
def load_and_normalize_data(choices):
    sample_dic = {}
    for i in choices:
        df = get_dpt_as_dataframe(f'/processed/{i}')
        if df is not None:
            sample_dic[i] = Norm(df)
    st.write("Loaded and normalized!")
    return sample_dic

# Normalization function
def Norm(ATR, min_value=0, max_value=1):
    min_val = ATR.iloc[:, 1].min()
    max_val = ATR.iloc[:, 1].max()
    ATR['norm'] = ((ATR.iloc[:, 1] - min_val) / (max_val - min_val)) * (max_value - min_value) + min_value
    return ATR

# The app begins here
st.title("Welcome to AC/BC 🦦 Viz")

with st.spinner('Connecting to Brian NextCloud...'):
    master = get_csv_file_as_dataframe("/master.csv")
    file_list = list_nextcloud_folder_files("/processed")

with st.sidebar:
    choice = st.multiselect('Select sample', options=master['Code'], placeholder='Code')
    param = st.selectbox('Parameter', options=['BET','pH','Yield','pore size','pore volume'],
                           placeholder='Parameter')
st.write('Connected to Brian NextCloud')
st.write('''
### Master Biochar Inventory 📖
''')

st.dataframe(master,use_container_width=True)

st.write('''---
### Visualize information from the selected samples 👇 
---''')
col1, col2, col3 = st.columns((1,1,2))
if choice and param:
    with col1:
        st.dataframe(master[['Code',param]][master['Code'].isin(choice)],
                     use_container_width=False)
    with col3:
        fig = go.Figure(data=[
            go.Bar(name='Sample Data', x=choice, y=master[param][master['Code'].isin(choice)])
        ])

        fig.update_layout(
            title=f'Sample by {param}',
            xaxis_title='Sample',
            yaxis_title=f'{param}',
            template='plotly_white'  # Optional: set the background to white for better readability
        )
        st.plotly_chart(fig,use_container_width=True)
else:
    st.warning('Select the samples and parameters on the sidebar 👈')
# # Load data based on selection
# sample_dic = {}
# option_c = None
# if choice:
#     if 'All' in choice:
#         choice = file_list
#     sample_dic = load_and_normalize_data(choice)
#     option_c = choice
# else:
#     st.write("None selected")
#
# # Display DataFrame based on user selection
# if option_c:
#     option_df = st.selectbox('Select a DataFrame to show', option_c, placeholder='Select .dpt')
# else:
#     option_df = None
#
# # Display DataFrame button
# if st.button('DataFrame'):
#     if option_df is not None:
#         st.write(sample_dic[option_df])
#     else:
#         st.warning("Select an option first")
#
# # Plot button
# if st.button('Plot'):
#     if option_c:
#         fig = go.Figure()
#         y = 'norm' if plot_norm else 'Intensity'
#         for i in sample_dic.keys():
#             fig.add_trace(go.Scatter(x=sample_dic[i]['Wavenumber'], y=sample_dic[i][y],
#                                      mode='lines', name=i[:-4]))
#
#         fig.update_layout(
#             xaxis=dict(range=[4000, 400]),  # Inverted x-axis range as in the original plot
#             title='ATR-FTIR',
#             xaxis_title='Wavelength',
#             yaxis_title='Intensity (a.u)' if not plot_norm else 'Normalized Intensity',
#             width=1200,
#             height=800
#         )
#
#         st.plotly_chart(fig, use_container_width=True)
#     else:
#         st.warning("Select a graph to plot! 👈")
