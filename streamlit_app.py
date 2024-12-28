import streamlit as st
from snowflake.snowpark import Session
from snowflake.core import Root

import json


### Default Values
NUM_CHUNKS = 10 # Num-chunks provided as context. Play with this to check how it affects your accuracy
slide_window = 7
cmd = """
            select snowflake.cortex.complete(?, ?) as response
          """

# service params
CORTEX_SEARCH_DATABASE = "GX_COMPANION"
CORTEX_SEARCH_SCHEMA = "DATA"
CORTEX_SEARCH_SERVICE = "GX_SEARCH_SERVICE"

#connection params
connection_params = {
    "account": st.secrets["snowflake"]["account"],
    "user": st.secrets["snowflake"]["user"],
    "password": st.secrets["snowflake"]["password"],
    "warehouse": st.secrets["snowflake"]["warehouse"],
    "database": st.secrets["snowflake"]["database"],
    "schema": st.secrets["snowflake"]["schema"]
}

# columns to query in the service
COLUMNS = [
    "chunk",
    "relative_path"
    # "category"
]

session = Session.builder.configs(connection_params).create()

root = Root(session)

svc = root.databases[CORTEX_SEARCH_DATABASE].schemas[CORTEX_SEARCH_SCHEMA].cortex_search_services[CORTEX_SEARCH_SERVICE]

### Functions
     
def config_options():

    st.sidebar.selectbox('Select your model:',(
                                    'mistral-large2'), key="model_name")

    # categories = session.table('docs_chunks_table').select('category').distinct().collect()

    # cat_list = ['ALL']
    # for cat in categories:
    #     cat_list.append(cat.CATEGORY)
            
    # st.sidebar.selectbox('Select what products you are looking for', cat_list, key = "category_value")

    st.sidebar.checkbox('Do you want that I remember the chat history?', key="use_chat_history", value = True)

    st.sidebar.checkbox('Debug: Click to see summary generated of previous conversation', key="debug", value = True)
    st.sidebar.button("Start Over", key="clear_conversation", on_click=init_messages)
    st.sidebar.expander("Session State").write(st.session_state)

def init_messages():

    # Initialize chat history
    if st.session_state.clear_conversation or "messages" not in st.session_state:
        st.session_state.messages = []

def get_similar_chunks_search_service(query):

    # if st.session_state.category_value == "ALL":
    #     response = svc.search(query, COLUMNS, limit=NUM_CHUNKS)
    # else: 
    #     filter_obj = {"@eq": {"category": st.session_state.category_value} }
    #     response = svc.search(query, COLUMNS, filter=filter_obj, limit=NUM_CHUNKS)

    response = svc.search(query, COLUMNS, limit=NUM_CHUNKS)
    st.sidebar.json(response.json())
    
    return response.json()  

def get_chat_history():
#Get the history from the st.session_stage.messages according to the slide window parameter
    
    chat_history = []
    
    start_index = max(0, len(st.session_state.messages) - slide_window)
    for i in range (start_index , len(st.session_state.messages) -1):
         chat_history.append(st.session_state.messages[i])

    return chat_history

def summarize_question_with_history(chat_history, question):
# To get the right context, use the LLM to first summarize the previous conversation
# This will be used to get embeddings and find similar chunks in the docs for context

    prompt = f"""
        You are a summarizer. 
        Based on the question and the chat history, figure out what the user is trying to ask.

        <chat_history>
        {chat_history}
        </chat_history>
        <question>
        {question}
        </question>

        <final_format>
        Original Question: Put the original question here without changing anything.

        Summarized Question: Using the chat history, create a comprehensive question. Do not provide any explanation or start with "considering", only provide the final question.
        </final_format>
        """

    df_response = session.sql(cmd, params=[st.session_state.model_name, prompt]).collect()
    res_text = df_response[0].RESPONSE
    


    if st.session_state.debug:
        st.sidebar.text("Summary to be used to find similar chunks in the docs:")
        st.sidebar.caption(res_text)

    res_text = res_text.replace("'", "")

    return res_text

def create_prompt (myquestion):

    if st.session_state.use_chat_history:
        chat_history = get_chat_history()

        if chat_history != []: #There is chat_history, so not first question
            question_summary = summarize_question_with_history(chat_history, myquestion)
            prompt_context =  get_similar_chunks_search_service(question_summary)
        else:
            prompt_context = get_similar_chunks_search_service(myquestion) #First question when using history
    else:
        prompt_context = get_similar_chunks_search_service(myquestion)
        chat_history = ""
  
# Dobby is a free assistant who chooses to help because of his enormous heart.",
#         "Extremely devoted and will go to any length to help his friends.",
#         "Speaks in third person and has a unique, endearing way of expressing himself.",
#         "Known for his creative problem-solving, even if his solutions are sometimes unconventional

    prompt = f"""
            <system_prompt>
            You are GX Companion, an expert customer service chat assistance of GX Bank.
            You are patient, helpful, kind, and courteous.
            You treat customers with respect and humility, you are never rude and never swear.
            Answer user queries in the context of GX bank and always answer in first person.
            You can extract information from the CONTEXT provided
            between <context> and </context> tags.
            You offer a chat experience considering the information included in the CHAT HISTORY
            provided between <chat_history> and </chat_history> tags..
            When ansering the question contained between <question> and </question> tags
            be concise and comprehensive to attend to the question and do not hallucinate. 
            Do not return answers that are too long, you can use bullet points where necessary.
            If you don´t have the information just say so.
            Include information from the context provided where you think might be useful.
            
            Do not mention the CONTEXT used in your answer.
            Do not mention the CHAT HISTORY used in your asnwer.

            Only anwer the question if you can extract it from the CONTEXT provideed.
            </system_prompt>
            
            <chat_history>
            {chat_history}
            </chat_history>
            <context>          
            {prompt_context}
            </context>
            <question>  
            {myquestion}
            </question>
            Answer: 
            """
    
    json_data = json.loads(prompt_context)

    relative_paths = set(item['relative_path'] for item in json_data['results'])

    return prompt, relative_paths


def answer_question(myquestion):

    prompt, relative_paths =create_prompt (myquestion)
    df_response = session.sql(cmd, params=[st.session_state.model_name, prompt]).collect()
    return df_response, relative_paths

def main():
    
    st.title(f":speech_balloon: Hi, I am your GX Companion")
    st.write("Ask me anything about GX Bank's products and campaigns.")
    st.write("AI can make mistakes, please check carefully.")
    st.write("Note: This app is a personal project and has no affliation with GX Bank Berhad.")
    # docs_available = session.sql("ls @docs").collect()
    # list_docs = []
    # for doc in docs_available:
    #     list_docs.append(doc["name"])
    # st.dataframe(list_docs)

    config_options()
    init_messages()
     
    # Display chat messages from history on app rerun
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Accept user input
    if question := st.chat_input("What do you want to know about your products?"):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": question})
        # Display user message in chat message container
        with st.chat_message("user"):
            st.markdown(question)
        # Display assistant response in chat message container
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
    
            question = question.replace("'","")
    
            with st.spinner(f"{st.session_state.model_name} thinking..."):
                response, relative_paths = answer_question(question)            
                res_text = response[0].RESPONSE
                res_text = res_text.replace("'", "")
                message_placeholder.markdown(res_text)

                if relative_paths != "None":
                    with st.sidebar.expander("Related Documents"):
                        for path in relative_paths:
                            cmd2 = f"select GET_PRESIGNED_URL(@docs, '{path}', 360) as URL_LINK from directory(@docs)"
                            df_url_link = session.sql(cmd2).to_pandas()
                            url_link = df_url_link._get_value(0,'URL_LINK')
                
                            display_url = f"Doc: [{path}]({url_link})"
                            st.sidebar.markdown(display_url)

        
        st.session_state.messages.append({"role": "assistant", "content": res_text})
    


if __name__ == "__main__":
    main()