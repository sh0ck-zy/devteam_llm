import streamlit as st 
from dotenv import load_dotenv
from PyPDF2 import PdfReader
from langchain.text_splitter import CharacterTextSplitter
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationalRetrievalChain
from langchain_community.vectorstores import FAISS
from langchain_community.llms import HuggingFaceHub
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from htmlTemplates import css, bot_template, user_template

def get_pdf_text(pdf_docs):
    text=""
    for pdf in pdf_docs:
        pdf_reader = PdfReader(pdf)
        for page in pdf_reader.pages:
            text += page.extract_text()
    return text

def get_text_chunks(text):
    text_splitter = CharacterTextSplitter(
        separator="\n",
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len
    )
    chunks = text_splitter.split_text(text)
    return chunks

def get_vectorstore(text_chunks):
    embeddings = OpenAIEmbeddings()
    #embeddings = HuggingFaceInstructEmbeddings(model_name="hkunlp/instructor-xl")
    vectorstore = FAISS.from_texts(texts=text_chunks, embedding=embeddings)
    return vectorstore

def get_conversation_chain(vectorstore):
    llm = ChatOpenAI()
    #llm = HuggingFaceHub(repo_id="google/flan-t5-xxl", model_kwargs={"temperature":0.5, "max_length":512})
    memory = ConversationBufferMemory(mmemory_key='chat_history', return_messages=True)
    conversation_chain = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=vectorstore.as_retriever(),
        memory=memory
    )
    return conversation_chain

def handle_userinput(user_question):
    # Ensure chat_history is passed as part of the input to the conversation function
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    
    input_payload = {
        'question': user_question,
        'chat_history': st.session_state.chat_history  # Include chat_history in the input
    }
    
    response = st.session_state.conversation(input_payload)
    st.session_state.chat_history = response['chat_history']

    for i, message in enumerate(st.session_state.chat_history):
        if i % 2 == 0:
            st.write(user_template.replace("{{MSG}}", message.content), unsafe_allow_html=True)
        else:
            st.write(bot_template.replace("{{MSG}}", message.content), unsafe_allow_html=True)

def main():
    load_dotenv()
    st.set_page_config(page_title="VodafoneZiggo NaaS Buddy", page_icon=":robot_face:")
    st.write(css, unsafe_allow_html=True)

    # Initialize session states if they don't exist
    if "conversation" not in st.session_state:
        st.session_state.conversation = lambda question: {'chat_history': []}
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    st.header("Chat with VodafoneZiggo NaaS Buddy :robot_face:")
    user_question = st.text_input("Ask a question about VZ NaaS development")
    if user_question:
        handle_userinput(user_question)

    with st.sidebar:
        st.subheader("Documents")
        pdf_docs = st.file_uploader("Upload your pdf's here and click on 'Process'", accept_multiple_files=True)
        if st.button("Process"):
            if pdf_docs:
                with st.spinner("Processing documents..."):
                    try:
                        # get pdf text
                        st.write("Extracting text from PDFs...")
                        raw_text = get_pdf_text(pdf_docs)
                        st.write("Text extraction complete. Processing chunks...")
                        
                        # get text chunks
                        text_chunks = get_text_chunks(raw_text)
                        st.write(f"Created {len(text_chunks)} text chunks. Generating embeddings...")
                        
                        # create vector store
                        vectorstore = get_vectorstore(text_chunks)
                        st.write("Embeddings generated. Setting up conversation chain...")
                        
                        # create conversation chain (st.session_state makes var persistent)
                        st.session_state.conversation = get_conversation_chain(vectorstore)
                        st.write("Conversation chain ready.")
                    except Exception as e:
                        st.error(f"An error occurred: {e}")
            else:
                st.error("Please upload at least one PDF document.")
if __name__ == '__main__':
    main()