import streamlit as st
from snowflake.snowpark import Session
from snowflake.core import Root

### Prompt
PROMPT = """
An excerpt from a document is given below.

---------------------
{prompt_context}
---------------------

Given the document excerpt, answer the following query.
If the context does not provide enough information, decline to answer.
Do not output anything that can't be answered from the context.

Question: {myquestion}
Answer:
"""

### Default Values
NUM_CHUNKS = 10 # Num-chunks provided as context. Play with this to check how it affects your accuracy
CMD = "select snowflake.cortex.complete(?, ?) as response"

#connection params
CONNECTION_PARAMS = {
    "account": st.secrets["snowflake"]["account"],
    "user": st.secrets["snowflake"]["user"],
    "password": st.secrets["snowflake"]["password"],
    "warehouse": st.secrets["snowflake"]["warehouse"],
    "database": st.secrets["snowflake"]["database"],
    "schema": st.secrets["snowflake"]["schema"]
}

# service params
CORTEX_SEARCH_DATABASE = "GX_COMPANION"
CORTEX_SEARCH_SCHEMA = "DATA"
CORTEX_SEARCH_SERVICE = "GX_SEARCH_SERVICE"

# columns to query in the service
COLUMNS = [
    "chunk",
    "relative_path"
    # "category"
]

session = Session.builder.configs(CONNECTION_PARAMS).create()
root = Root(session)
svc = root.databases[CORTEX_SEARCH_DATABASE].schemas[CORTEX_SEARCH_SCHEMA].cortex_search_services[CORTEX_SEARCH_SERVICE]

class RAG:
    def retrieve(self, query: str) -> list:
        context_retrieved = svc.search(query, COLUMNS, limit=NUM_CHUNKS)
        return context_retrieved

    def complete(self, query: str, context_str: list) -> str:
        prompt = PROMPT.format(prompt_context=context_str, myquestion=query)
        df_response = session.sql(CMD, params=[st.session_state.model_name, prompt]).collect()
        
        return df_response[0].RESPONSE

    def query(self, query: str) -> str:
        context_str = self.retrieve(query=query)
        completion = self.complete(
            query=query, context_str=context_str
        )
        return completion

### Functions

def init_app():
    st.title(f":speech_balloon: Hi, I am your GX Companion")
    st.write("AI can make mistakes, please check carefully.")
    st.write("Note: This app is a personal project and has no affliation with GX Bank Berhad.")

    st.sidebar.selectbox('Select your model:',(
                                    'mistral-large2'), key="model_name")

    st.sidebar.button("Start Over", key="clear_conversation", on_click=init_messages)
    st.sidebar.expander("Session State").write(st.session_state)

def init_messages():
    # Initialize chat history
    if st.session_state.clear_conversation or "messages" not in st.session_state:
        st.session_state.messages = []
    
    if not st.session_state.messages:
        st.session_state.messages.append({"role": "assistant", "content": "Ask me anything about GX Bank's products and campaigns!"})

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

def main():
    """Main function to run the application logic."""
    rag = RAG()
    init_app()
    init_messages()

    # Accept user input
    if question := st.chat_input("Message GX Companion"):
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
                res_text = rag.query(question);
                res_text = res_text.replace("'", "")
                message_placeholder.markdown(res_text)
        
        st.session_state.messages.append({"role": "assistant", "content": res_text})
    


if __name__ == "__main__":
    main()