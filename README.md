# GX Companion
By bringing together valuable information and cutting-edge AI technology, GX Companion creates a more inclusive banking experience - one question at a time.
Try out the app: https://gxcompanion.streamlit.app/

## Inspiration 💡
With GX Bank being the first digital bank to launch in the Malaysian market, we have customers who are excited to find out more about the new digital banking products. However, the answer to their questions are often buried within long product disclosure sheets and T&C documents.

## Problem Statement 🚨
Valuable information are often locked away from customers in long PDF documents (e.g. product disclosure sheets, terms and conditions, etc)

## Our Solution - GXBank Companion 🤖
GXBank Companion is a RAG-powered chatbot that has access to a knowledge base containing product disclosure sheets and terms and conditions information about GX Bank's products and campaigns. Users can ask the chatbot directly and GXBank Companion will be able to respond with an accurate and helpful response backed by information in the knowledge base.

## Impact 💪
Without GXBank Companion, customers would have to either:
1) read the PDF documents themselves to find the answers or
2) ask other people who have read the PDF documents for answers.

With GXBank Companion, customers are empowered to better banking decisions through the ability to get quick and accurate answers to their questions.

## How we built it 🔧
Snowflake for text chunking and storage Snowflake Cortex Search for text search Mistral LLM (mistral-large2) on Snowflake Cortex for text generation Streamlit Community Cloud for front end

## Challenges we ran into ⚠️
Trying to set up Trulens - We wanted to implement Trulens in our project to be able to measure and optimize the RAG triad of our application. However, we ran into a lot of problems trying to set it up and wasn't able to do it in the end. We initially faced the issue of using Complete directly in our code which gave us an error, so we have to use sql("select snowflake.cortex.complete(?, ?)...). Then we ran into another issue setting up the instrumentation and logging, and we weren't able to figure out how to make it work even with Josh's help.
Trying to implement conversational history - We wanted to make the chatbot able to understand the historical context of the chat, but we didn't prioritise this as we were trying to figure out how to set up Trulens.

## Accomplishments that we're proud of 🏆
- Made a working MVP within a couple of days, addressing both technical complexity and social impact
- Learnt a lot about Snowflake, Mistral and Trulens and how to implement an application using all of them

## What we learned
- We don't know how to set up Trulens yet (rip)
- running mistral-large2 on Snowflake is pretty expensive

## What's next for GX Companion
- Set up Trulens to be able to measure and optimize our application
- Set up historical capability to allow for smoother conversational abilities

Disclaimer: This is not affliated or developed by GX Bank Berhad, this is solely personal project
