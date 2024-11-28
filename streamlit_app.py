import streamlit as st
import requests
from requests.auth import HTTPBasicAuth
import xml.etree.ElementTree as ET
import pandas as pd
import io
import streamlit as st
import hmac
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(layout="wide")

def list_nextcloud_folder_files(folder_path="/specific-folder"):
    url = f"{NEXTCLOUD_URL}{folder_path}/"
    response = requests.request("PROPFIND", url, auth=HTTPBasicAuth(USERNAME, PASSWORD))

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
    else:
        print(f"Failed to list files. Status code: {response.status_code}")

    return file_list
def get_dpt_as_dataframe(file_path):
    url = f"{NEXTCLOUD_URL}{file_path}"
    response = requests.get(url, auth=HTTPBasicAuth(USERNAME, PASSWORD))

    if response.status_code == 200:
        dpt = response.content.decode('utf-8')
        df = pd.read_table(io.StringIO(dpt),
                           header=None,
                           names=['Wavenumber','Intensity'],
                           delimiter=',')
        return df
    else:
        print(f"Failed to download file. Status code: {response.status_code}")
        return None
def load_data(choices):
    sample_dic = {}
    for i in choices:
        sample_dic[i] = get_dpt_as_dataframe(f'/processed/{i}')
    st.write("Loaded!")
    return sample_dic
def Norm(ATR, min_value=0, max_value=1):
  min_val =  ATR.iloc[:, 1].min()
  max_val =  ATR.iloc[:, 1].max()
  ATR['norm'] = ((ATR.iloc[:, 1] - min_val) / (max_val - min_val)) * (max_value - min_value) + min_value
  return

# Connecting to the cloud
NEXTCLOUD_URL = st.secrets["nextcloud"]["NEXTCLOUD_URL"]
USERNAME = st.secrets["nextcloud"]["username"]
PASSWORD = st.secrets["nextcloud"]["next_cloudpass"]

file_list = list_nextcloud_folder_files("/processed")
#The app begins here
st.title("IR Visualization 🦦")
st.write('Connected to Brian NextCloud')
choice = st.multiselect('Select file',
                             options = ['All'] + file_list,
                             placeholder='Sample IR file')
option_c = None
if choice and 'All' not in choice:
    sample_dic = load_data(choice)
    option_c = choice
    for i in option_c:
        Norm(sample_dic[i])
elif 'All' in choice:
    sample_dic = load_data(file_list)
    option_c = file_list
    for i in option_c:
        Norm(sample_dic[i])
elif choice == None:
    st.write("None selected")

option_df = st.selectbox('Select a DataFrame to show',
                      option_c,
                      placeholder='Select .dpt')
# Create a button in Streamlit

if st.button('DataFrame'):
    if option_df != None:
        # Execute function when the button is clicked
        st.write(sample_dic[option_df])
    else:
        st.write("Select an Option first")

if st.button('Plot'):
    if choice != None:
        fig = go.Figure()
        y = 'Intensity'
        for i in sample_dic.keys():
            fig.add_trace(go.Scatter(x=sample_dic[i]['Wavenumber'], y=sample_dic[i][y],
                                     mode='lines', name=i[:-4]))

        fig.update_layout(
            xaxis=dict(range=[4000, 400]),  # Inverted x-axis range as in the original plot
            title='ATR-FTIR',
            xaxis_title='Wavelength',
            yaxis_title='Intensity (a.u)',
            width=1200,
            height=800
        )

        st.plotly_chart(fig,use_container_width=True)