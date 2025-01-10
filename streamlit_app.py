import streamlit as st
from typing import List

from snowflake.snowpark import Session
from snowflake.core import Root

from trulens.apps.custom import instrument

from trulens.apps.custom import TruCustomApp
from trulens.core import TruSession
from trulens.connectors.snowflake import SnowflakeConnector
from trulens.providers.cortex.provider import Cortex
from trulens.core import Feedback
from trulens.core import Select
import numpy as np

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

#connection params
CONNECTION_PARAMS = {
    "account": st.secrets["snowflake"]["account"],
    "user": st.secrets["snowflake"]["user"],
    "password": st.secrets["snowflake"]["password"],
    "warehouse": st.secrets["snowflake"]["warehouse"],
    "database": st.secrets["snowflake"]["database"],
    "schema": st.secrets["snowflake"]["schema"]
}

# Initialize Snowflake session
session = Session.builder.configs(CONNECTION_PARAMS).create()
root = Root(session)

# Initialize TruLens session
tru_snowflake_connector = SnowflakeConnector(snowpark_session=session)
tru_session = TruSession(connector=tru_snowflake_connector)

class CortexSearchRetriever:

    def __init__(self, snowpark_session: Session, limit_to_retrieve: int = 4):
        self._snowpark_session = snowpark_session
        self._limit_to_retrieve = limit_to_retrieve

    def retrieve(self, query: str) -> List[str]:
        root = Root(self._snowpark_session)
        cortex_search_service = (
            root.databases[st.secrets["cortex_search"]["database"]]
            .schemas[st.secrets["cortex_search"]["schema"]]
            .cortex_search_services[st.secrets["cortex_search"]["service"]]
        )
        resp = cortex_search_service.search(
            query=query,
            columns=[
                "chunk",
                "relative_path"
            ],
            limit=self._limit_to_retrieve,
        )

        if resp.results:
            return [curr["chunk"] for curr in resp.results]
        else:
            return []

### Setting up the RAG class
class RAG:
    def __init__(self):
        self.retriever = CortexSearchRetriever(snowpark_session=session, limit_to_retrieve=4)

    @instrument
    def retrieve_context(self, query: str) -> list:
        return self.retriever.retrieve(query)

    @instrument
    def generate_completion(self, query: str, context_str: list) -> str:
        prompt = PROMPT.format(prompt_context=context_str, myquestion=query)
        df_response = session.sql("select snowflake.cortex.complete(?, ?) as response", params=[st.session_state.model_name, prompt]).collect()
        
        return df_response[0].RESPONSE

    @instrument
    def query(self, query: str) -> str:
        context_str = self.retrieve_context(query=query)
        return self.generate_completion(query, context_str)

rag = RAG()


provider = Cortex(session, "llama3.1-8b")

f_groundedness = (
    Feedback(provider.groundedness_measure_with_cot_reasons, name="Groundedness")
    .on(Select.RecordCalls.retrieve_context.rets[:].collect())
    .on_output()
)

f_context_relevance = (
    Feedback(provider.context_relevance, name="Context Relevance")
    .on_input()
    .on(Select.RecordCalls.retrieve_context.rets[:])
    .aggregate(np.mean)
)

f_answer_relevance = (
    Feedback(provider.relevance, name="Answer Relevance")
    .on_input()
    .on_output()
    .aggregate(np.mean)
)

tru_rag = TruCustomApp(
    rag,
    app_name="RAG",
    app_version="simple",
    feedbacks=[f_groundedness, f_answer_relevance, f_context_relevance],
)

# Still having the same error
# prompts = [
#     "How do I launch a streamlit app?",
#     "How can I capture the state of my session in streamlit?",
#     "How do I install streamlit?",
#     "How do I change the background color of a streamlit app?",
#     "What's the advantage of using a streamlit form?",
#     "What are some ways I should use checkboxes?",
#     "How can I conserve space and hide away content?",
#     "Can you recommend some resources for learning Streamlit?",
#     "What are some common use cases for Streamlit?",
#     "How can I deploy a streamlit app on the cloud?",
#     "How do I add a logo to streamlit?",
#     "What is the best way to deploy a Streamlit app?",
#     "How should I use a streamlit toggle?",
#     "How do I add new pages to my streamlit app?",
#     "How do I write a dataframe to display in my dashboard?",
#     "Can I plot a map in streamlit? If so, how?",
#     "How do vector stores enable efficient similarity search?",
# ]


# with tru_rag as recording:
#     for prompt in prompts:
#         rag.query(prompt)

# tru_session.get_leaderboard()


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
    
    init_app()
    init_messages()

    # Seems like the error only when I call rag.query(), if I comment this out
    # then the app runs fine
    # with tru_rag as recording:
    #     rag.query(
    #         "What is GX bank's cyber fraud protect product?"
    #     )

    # trulens_session.get_leaderboard()


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