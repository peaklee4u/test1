# Streamlit-based chatbot with file upload (text/PDF/DOCX) for scientific inquiry support
import streamlit as st
import openai
import os
import json
from datetime import datetime
from dotenv import load_dotenv
import base64
import pymysql
from PyPDF2 import PdfReader
import docx

# Load environment variables
load_dotenv()
openai.api_key = st.secrets["OPENAI_API_KEY"]
MODEL = "gpt-4o"

# Initial prompt
initial_prompt = (
    "당신은 중학생의 자유 탐구를 바탕으로 탐구보고서를 작성하도록 돕는 챗봇이며, 이름은 '탐구보고서 도우미'입니다."
    "이 탐구는 중학교 1학년 학생들이 수행한 것이지만, 과학에 관심이 많은 학생들이므로 중학교 3학년 수준이라고 생각하고 설명하세요."
    "과학 개념을 설명할 때는 15세 수준에 맞춰 간단하고 명확하게 설명하세요."

    "학생은 실험을 완료하고 결과(데이터표, 그래프, 관찰 결과 등)를 가지고 왔습니다."
    "당신은 학생의 결과를 분석하고, 신뢰성, 경향성, 해석, 결론이 타당한지 평가해 피드백을 제공해야 합니다."

    "학생은 다음과 같은 절차로 챗봇을 활용하도록 안내되었습니다:"
    "① 인공지능에게 실험 결과(데이터)와 결론을 알려주세요."
    "② 인공지능은 결과를 분석하고 피드백을 제공합니다. 피드백에 대해 궁금한 점은 언제든지 물어보세요."
    "③ 궁금한 것을 다 물어봤다면, 인공지능에게 '궁금한 건 다 물어봤어'라고 말해주세요."
    "④ 그러면 인공지능이 당신에게 몇 가지 질문을 하며 결론이나 보고서를 더 잘 쓰도록 도와줄 거예요."
    "⑤ 대화가 충분히 이루어지면 인공지능이 [다음] 버튼을 눌러도 된다고 알려줄 거예요."

    "처음 대화할 때 학생이 실험 결과(데이터)나 결론을 말하지 않으면, 우선 결과(데이터)를 먼저 알려달라고 요청하세요."
    "실험 결과 없이 질문하거나 보고서를 작성하려 해도 절대 진행하지 마세요."

    "피드백은 다음 기준에 따라 구체적으로 제시하세요:"
    "1. 실험 결과(데이터)가 반복 측정되었는가?"
    "2. 실험 결과(데이터)가 일정한 경향성을 보이는가?"
    "3. 결과(데이터)가 가설과 관련된 독립·종속변인을 반영하는가?"
    "4. 그래프를 제대로 그렸는가? 그래프의 작성 조건에 맞게 나타내었는가?"   
    "5. 그래프나 표에서 나타나는 경향을 해석했는가?"
    "6. 결론이 결과에 근거해 논리적으로 도출되었는가?"
    "7. 결론에서 가설을 지지하는지 또는 지지하지 않는지를 밝혔는가?"
    "8. 탐구의 오차나 한계를 인식했는가?"

    "절대 학생에게 결론을 대신 써주지 마세요. 학생이 스스로 결론을 완성하도록 질문과 피드백으로 유도하세요."

    "학생이 탐구 분석에 대한 궁금증을 다 물어봤다고 하면, 챗봇이 질문을 시작하여 학생이 더 깊이 해석하고 생각을 정리할 수 있도록 도와주세요."
    "이때는 최소 2개 이상의 질문을 하고, 미흡했던 평가 기준 항목은 모두 질문하세요."
    "한 번에 하나의 질문만 하세요. 간단한 문장으로 질문하고 줄바꿈을 적절히 사용해 가독성을 높이세요."

    "[다음] 버튼은 다음 두 가지 조건이 모두 충족되었을 때만 누르라고 안내하세요:"
    "① 피드백에서 지적된 미흡한 항목을 모두 논의함."
    "② 챗봇이 학생에게 최소 2개 이상의 질문을 함."

    "학생의 답변에 따라 관련된 과학 개념이나 배경 지식을 함께 설명해 주세요. 학생이 해석이나 결론을 더 잘 쓸 수 있도록 도와주는 것이 중요합니다."

    "절대 탐구보고서 문장을 직접 완성해서 제공하지 마세요. 학생이 작성하고 수정해나가도록 격려하세요."
)

# Helper to encode image
def encode_image(uploaded_file):
    return base64.b64encode(uploaded_file.read()).decode("utf-8")

# Helper to read uploaded document
@st.cache_data
def read_uploaded_document(uploaded_file):
    file_type = uploaded_file.type
    if file_type == "text/plain":
        return uploaded_file.read().decode("utf-8")
    elif file_type == "application/pdf":
        pdf = PdfReader(uploaded_file)
        return "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])
    elif file_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        doc = docx.Document(uploaded_file)
        return "\n".join([para.text for para in doc.paragraphs])
    else:
        return None

# Generate response from OpenAI
def get_chatgpt_response(content):
    try:
        response = openai.chat.completions.create(
            model=MODEL,
            messages=[{"role": "system", "content": initial_prompt}] + st.session_state["messages"] + [{"role": "user", "content": content}]
        )
        answer = response.choices[0].message.content
        st.session_state["messages"].append({"role": "assistant", "content": answer})
        return answer
    except Exception as e:
        st.error(f"OpenAI API 오류: {e}")
        return "오류가 발생했습니다. 다시 시도해주세요."

# Save chat to DB
def save_to_db(all_data):
    number = st.session_state.get('user_number', '').strip()
    name = st.session_state.get('user_name', '').strip()
    if not number or not name:
        st.error("사용자 학번과 이름을 입력해야 합니다.")
        return False
    try:
        db = pymysql.connect(
            host=st.secrets["DB_HOST"],
            user=st.secrets["DB_USER"],
            password=st.secrets["DB_PASSWORD"],
            database=st.secrets["DB_DATABASE"],
            charset="utf8mb4",
            autocommit=True
        )
        cursor = db.cursor()
        now = datetime.now()
        sql = """
            INSERT INTO qna (number, name, chat, time)
            VALUES (%s, %s, %s, %s)
        """
        chat = json.dumps(all_data, ensure_ascii=False)
        val = (number, name, chat, now)
        cursor.execute(sql, val)
        cursor.close()
        db.close()
        return True
    except pymysql.MySQLError as db_err:
        st.error(f"DB 처리 중 오류가 발생했습니다: {db_err}")
        return False

# Page 1: Input user info
def page_1():
    st.title("과학탐구 도우미")
    st.session_state["user_number"] = st.text_input("학번", value=st.session_state.get("user_number", ""))
    st.session_state["user_name"] = st.text_input("이름", value=st.session_state.get("user_name", ""))
    if st.button("다음"):
        if not st.session_state["user_number"].strip() or not st.session_state["user_name"].strip():
            st.error("학번과 이름을 모두 입력해주세요.")
        else:
            st.session_state["step"] = 2
            st.rerun()

# Page 2: Instruction
def page_2():
    st.title("탐구 도우미 활용 방법")
    st.markdown("""
    ① 실험 결과(표, 그래프, 결론 등)를 챗봇에게 알려주세요.  
    ② 챗봇은 피드백을 주고, 궁금한 점을 질문해 보세요.  
    ③ '궁금한 건 다 물어봤어'라고 말하면 챗봇이 질문을 시작해요.  
    ④ 대화가 끝나면 챗봇이 [다음] 버튼을 눌러도 된다고 알려줄 거예요.
    """)
    if st.button("다음"):
        st.session_state["step"] = 3
        st.rerun()

# Page 3: Chat interface
def page_3():
    st.title("탐구 도우미와 대화하기")
    if "messages" not in st.session_state:
        st.session_state["messages"] = []
    if "user_input" not in st.session_state:
        st.session_state["user_input"] = ""

    user_input = st.text_area("질문을 입력하세요:", value=st.session_state["user_input"], key="user_input_area")
    uploaded_file = st.file_uploader("탐구 결과 파일 업로드 (txt, pdf, docx):", type=["txt", "pdf", "docx"])
    uploaded_image = st.file_uploader("참고 이미지 업로드 (선택):", type=["jpg", "jpeg", "png"])

    if st.button("전송"):
        content = ""
        if uploaded_file:
            file_content = read_uploaded_document(uploaded_file)
            if file_content:
                content += f"[탐구 결과 업로드]\n{file_content}\n"
            else:
                st.warning("파일을 읽을 수 없습니다.")

        if user_input.strip():
            content += f"[사용자 입력]\n{user_input.strip()}"

        if not content:
            st.warning("내용을 입력하거나 파일을 업로드하세요.")
            return

        if uploaded_image:
            base64_img = encode_image(uploaded_image)
            content = [
                {"type": "text", "text": content},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_img}"}}
            ]

        st.session_state["messages"].append({"role": "user", "content": content})
        answer = get_chatgpt_response(content)
        st.session_state["user_input"] = ""
        st.rerun()

    if st.session_state["messages"]:
        st.subheader("📌 최근 대화")
        for msg in st.session_state["messages"][-2:]:
            if msg["role"] == "user":
                st.markdown("**You:**")
                st.write(msg["content"])
            elif msg["role"] == "assistant":
                st.markdown("**탐구 도우미:**")
                st.write(msg["content"])

# Page 4: Summarize
def page_4():
    st.title("탐구 도우미의 제안 요약")
    if "summary_generated" not in st.session_state:
        st.session_state["summary_generated"] = False

    if not st.session_state["summary_generated"]:
        chat_history = "\n".join(json.dumps(m, ensure_ascii=False) for m in st.session_state["messages"])
        prompt = f"학생과의 대화 기록: {chat_history}\n\n이 대화를 요약하고 피드백을 제공하세요."
        response = openai.chat.completions.create(
            model=MODEL,
            messages=[{"role": "system", "content": prompt}]
        )
        summary = response.choices[0].message.content
        st.session_state["summary"] = summary
        st.session_state["summary_generated"] = True
        save_to_db(st.session_state["messages"] + [{"role": "assistant", "content": summary}])

    st.write(st.session_state.get("summary", "요약 없음"))
    if st.button("처음으로"):
        st.session_state.clear()
        st.experimental_rerun()

# Main logic
if "step" not in st.session_state:
    st.session_state["step"] = 1

if st.session_state["step"] == 1:
    page_1()
elif st.session_state["step"] == 2:
    page_2()
elif st.session_state["step"] == 3:
    page_3()
elif st.session_state["step"] == 4:
    page_4()
