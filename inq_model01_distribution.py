# Streamlit-based chatbot with image upload capability for scientific inquiry support
import streamlit as st
from openai import OpenAI
import os
import json
from datetime import datetime
from dotenv import load_dotenv
import base64
import pymysql
import fitz  # PyMuPDF
 
# Load environment variables
load_dotenv()
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
MODEL = "gpt-4o"

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

# Initial prompt
initial_prompt = (
    "당신은 중학생의 자유 탐구를 돕는 챗봇이며, 이름은 '과학탐구 도우미'입니다."
    "이 탐구는 중학교 1학년 학생들이 하는 탐구이므로, 중학교 1학년 수준에 맞게 설명해야 합니다."
    "과학 개념을 설명할 때는 14세 정도의 학생 수준으로 간결하게 설명하세요."

    "학생에게는 다음과 같은 절차로 챗봇을 활용하도록 안내되었습니다: "
    "① 먼저 인공지능에게 당신이 작성한 실험 가설과 과정을 알려주세요. "
    "② 인공지능은 당신의 실험 가설과 과정에 대해 잘한 점과 개선할 점을 알려줄 거예요. 인공지능의 피드백에 대해 궁금한 점을 질문하세요. "
    "③ 궁금한 것을 다 물어봤다면, 인공지능에게 '궁금한 건 다 물어봤어'라고 말해주세요. "
    "④ 그러면 인공지능이 당신의 생각을 물어볼 거예요. 그것을 고민해 답해보세요. 궁금한 게 있으면 인공지능에게 물어봐도 돼요. "
    "⑤ 충분히 대화가 이루어지면 인공지능이 [다음] 버튼을 눌러도 된다고 알려줘요. 인공지능이 [다음] 버튼을 누르라고 했을 때 버튼을 누르세요!"

    "첫 대화에서 학생이 실험 가설과 방법을 이야기하지 않으면, 우선적으로 가설과 방법을 요청하세요."

    "학생이 실험 가설과 방법을 이야기하면, 이를 평가하여 잘한 점과 개선할 점을 피드백 해주세요. "
    "이때 전반적으로 평가하는 것이 아니라 채점 기준 하나하나에 대하여 구체적으로 평가 및 피드백해야 합니다."

    "다음은 가설에 관한 채점 기준입니다: "
    "1. 독립 변인이 있는가? "
    "2. 종속 변인이 있는가? "
    "3. 기대되는 변화 또는 효과가 제시되었는가(A는 B에 영향을 준다)? "
    "4. 효과의 방향이 제시되었는가(A가 ~할수록 B가 ~하다)?"

    "다음은 실험 과정에 관한 채점 기준입니다: "
    "5. 각 독립변인 조절을 위한 구체적 조건을 제시하였는가? "
    "6. 일정하게 해야 할 변인을 통제하기 위한 구체적 언급이 있는가? "
    "7. 실제로 실험에 사용될 준비물을 제시하였는가? "
    "8. 가설에 제시된 독립변인을 조절한다는 언급이 있는가?"

    "아주 중요한 것이니까, 꼭 지켜줘. "
    "채점 결과를 제공할 때 항목마다 줄바꿈을 해 가독성이 좋게 제시하세요. "
    "특히 실험 과정의 채점 결과는 반드시 항목마다 줄바꿈하세요. 예: 실험 과정 채점 결과:\n\n"
    "5. 독립변인 조절의 조건\n\n 6. 변인 통제\n\n 7. 준비물\n\n 8. 독립변인 조절 언급"

    "학생의 가설과 과정 평가 이후에는 두 단계로 진행됩니다. "
    "1단계는 학생이 평가 결과와 관련해 궁금한 점을 질문하는 단계입니다. "
    "2단계는 당신이 학생에게 질문하며 가설과 과정을 개선하는 단계입니다."

    "1단계에서는 학생이 제시하는 질문에 답하면서, 평가 결과 제시된 개선점을 보완하도록 유도하세요."

    "학생이 궁금한 것을 다 물어봤다고 하거나, 더이상 질문이 없다고 한다면, 학생의 가설과 과정을 개선하는 2단계로 넘어갑니다. "
    "평가 결과 중 아직 개선되지 않은 항목에 대해 질문하며, 학생이 스스로 실험을 개선하도록 유도하세요."

    "2단계에서 최소 2개 이상의 질문을 하세요. "
    "피드백에서 개선 사항으로 언급된 항목들 중 학생이 질문하지 않은 항목을 하나도 빠짐 없이 모두 논의하세요."

    "2단계에서는 학생에게 여러 개의 내용을 한 번에 요구하면 학생이 대응하기 어려울 수 있으므로, 한 번에 하나의 내용만 요구하세요."

    "2단계까지 진행하고 나면 [다음] 버튼을 눌러 다음 단계로 진행하라고 이야기하세요. "
    "단, [다음] 버튼은 필요한 논의가 모두 끝난 후에 눌러야 합니다. "
    "그 전에는 [다음] 버튼을 누르지 말라고 안내하세요."

    "[다음] 버튼은 다음 두 가지 조건이 모두 충족됐을 때 누를 수 있습니다: "
    "① 평가 결과에서 개선 사항으로 언급된 항목을 하나도 빠짐 없이 모두 논의했다. "
    "② 2단계에서 2개 이상의 질문을 했다. "
    "이 조건이 충족되지 않았다면, 절대로 [다음] 버튼을 누르라고 하면 안 됩니다."

    "어떤 상황에서든 절대로 실험 가설이나 실험 과정을 직접적으로 알려줘서는 안 됩니다. "
    "당신이 할 일은 학생이 스스로 사고하여 실험 가설과 과정을 작성하도록 유도하는 것입니다."

    "첫 대화를 시작할 때 학생이 실험 가설과 방법을 이야기하지 않은 상태라면 어떠한 대화도 시작해서는 안됩니다. "
    "반드시 실험 가설과 방법을 먼저 이야기하도록 요청하세요. "
    "실험 가설과 방법을 이야기하지 않으면 어떤 질문에도 답하지 마세요."

    "학생이 실험 가설이나 과정을 모르겠다거나 못 쓰겠다고 하더라도 절대 알려주지 마세요. 간단하게라도 써 보도록 유도하세요."

    "당신의 역할은 정답을 알려주는 게 아니라, 학생이 사고하며 탐구를 설계하도록 교육적 지원을 하는 것입니다."

    "상호작용 1단계(즉 학생이 더이상 질문이 없다고 말하기 전)에는 어떤 상황이라도 절대 당신이 학생에게 질문해선 안 됩니다. "
    "질문은 학생이 더이상 질문이 없다고 말한 후, 2단계에서만 합니다."

    "학생에게 답변을 제공할 때는 그 내용과 관련해 참고할 만한 과학 지식이나 정보를 풍부하게 추가로 제공하세요."

    "학생에게 질문할 때는 한 번에 한 가지의 내용만 질문하세요. 모든 대화는 한 줄이 넘어가지 않게 하세요."

    "가독성을 고려해 적절히 줄바꿈을 사용하세요."
)


# Encode uploaded image
def encode_image(uploaded_file):
    return base64.b64encode(uploaded_file.read()).decode("utf-8")

# Generate response from OpenAI
def get_chatgpt_response(content):
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "system", "content": initial_prompt}] + st.session_state["messages"] + [{"role": "user", "content": content}]
    )
    answer = response.choices[0].message.content
    st.session_state["messages"].append({"role": "assistant", "content": answer})
    return answer

# Save to MySQL database
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
    except Exception as e:
        st.error(f"알 수 없는 오류가 발생했습니다: {e}")
        return False


# pdf extract
def extract_pdf_text(file):
    doc = fitz.open(stream=file.read(), filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    return text




# Page 1: User info input
def page_1():
    st.title("과학탐구 도우미")
    st.write("학번과 이름을 입력한 뒤 '다음' 버튼을 눌러주세요.")

    if "user_number" not in st.session_state:
        st.session_state["user_number"] = ""
    if "user_name" not in st.session_state:
        st.session_state["user_name"] = ""

    st.session_state["user_number"] = st.text_input("학번", value=st.session_state["user_number"])
    st.session_state["user_name"] = st.text_input("이름", value=st.session_state["user_name"])

    if st.button("다음"):
        if not st.session_state["user_number"].strip() or not st.session_state["user_name"].strip():
            st.error("학번과 이름을 모두 입력해주세요.")
        else:
            st.session_state["step"] = 2
            st.rerun()

# Page 2: Instruction
def page_2():
    st.title("탐구 도우미 활용 방법")
    st.write("""
    ※주의! '자동 번역'을 활성화하면 대화가 이상하게 번역되므로 활성화하면 안 돼요.

    ① 먼저 인공지능에게 당신이 작성한 실험 가설과 과정을 알려주세요.
    
    ② 인공지능은 당신의 실험 가설과 과정에 대해 잘한 점과 개선할 점을 알려줄 거예요.
    
    ③ 궁금한 것을 다 물어봤다면, 인공지능에게 '궁금한 건 다 물어봤어'라고 말해주세요.
    
    ④ 그러면 인공지능이 당신의 생각을 물어볼 거예요. 그것을 고민해 답해보세요.
    
    ⑤ 충분히 대화가 이루어지면 인공지능이 [다음] 버튼을 눌러도 된다고 알려줘요.
    """)
    if st.button("다음"):
        st.session_state["step"] = 3
        st.rerun()


# Page 3: Chat interface with optional image upload
def page_3():
    st.title("탐구 도우미 활용하기")
    st.write("탐구 도우미와 대화를 나누며 탐구를 설계하세요.")

    # 메시지 초기화
    if "messages" not in st.session_state:
        st.session_state["messages"] = []

    if "clear_input" not in st.session_state:
        st.session_state["clear_input"] = False

    # 입력창: 텍스트
    if st.session_state["clear_input"]:
        user_input = st.text_area("질문을 입력하세요:", value="", key="user_input_area")
        st.session_state["clear_input"] = False
    else:
        user_input = st.text_area("질문을 입력하세요:", key="user_input_area")

    # 파일 업로드: PDF 또는 이미지
    uploaded_file = st.file_uploader("📎 참고할 PDF 또는 이미지 파일을 업로드하세요:", type=["pdf", "png", "jpg", "jpeg"])

    # 파일 처리 결과
    extracted_pdf_text = None
    encoded_image = None

    if uploaded_file:
        if uploaded_file.type == "application/pdf":
            extracted_pdf_text = extract_pdf_text(uploaded_file)
            st.success("✅ PDF 문서를 성공적으로 불러왔어요!")
        elif uploaded_file.type.startswith("image/"):
            encoded_image = encode_image(uploaded_file)
            st.image(uploaded_file, caption="업로드한 이미지")
        else:
            st.warning("지원하지 않는 파일 형식입니다.")

    # 전송 버튼
    if st.button("전송"):
        if not user_input.strip() and not uploaded_file:
            st.warning("텍스트나 파일을 입력해주세요.")
        else:
            # 메시지 content 구성
            content = []
            if user_input.strip():
                content.append({"type": "text", "text": user_input})

            if encoded_image:
                content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{encoded_image}"}})
            elif extracted_pdf_text:
                # system 메시지로 PDF 요약 포함
                st.session_state["messages"].append({
                    "role": "system",
                    "content": f"학생이 참고한 PDF 문서의 주요 내용입니다:\n\n{extracted_pdf_text[:1500]}"
                })

            if len(content) == 1:
                content = content[0]  # 단일 텍스트/이미지만 있을 경우 list 아님

            # 메시지 추가 및 응답
            st.session_state["messages"].append({"role": "user", "content": content})
            get_chatgpt_response(content)

            st.session_state["clear_input"] = True
            st.rerun()

    # 최근 대화 출력
    if st.session_state["messages"]:
        st.subheader("📌 최근 대화")
        last_messages = st.session_state["messages"][-2:]
        for msg in last_messages:
            if msg["role"] == "user":
                st.markdown("**You:**")
                if isinstance(msg["content"], list):
                    for part in msg["content"]:
                        if part["type"] == "text":
                            st.write(part["text"])
                        elif part["type"] == "image_url":
                            st.image(part["image_url"]["url"], caption="업로드한 이미지")
                else:
                    st.write(msg["content"])
            elif msg["role"] == "assistant":
                st.markdown("**과학탐구 도우미:**")
                st.write(msg["content"])

    # 누적 대화 출력
    st.subheader("📜 누적 대화")
    for msg in st.session_state["messages"]:
        if msg["role"] == "user":
            st.markdown("**You:**")
            if isinstance(msg["content"], list):
                for part in msg["content"]:
                    if part["type"] == "text":
                        st.write(part["text"])
                    elif part["type"] == "image_url":
                        st.image(part["image_url"]["url"], caption="업로드한 이미지")
            else:
                st.write(msg["content"])
        elif msg["role"] == "assistant":
            st.markdown("**과학탐구 도우미:**")
            st.write(msg["content"])

    # 다음 단계로 이동
    if st.button("다음"):
        st.session_state["step"] = 4
        st.rerun()


# Page 4: Save and summarize
def page_4():
    st.title("탐구 도우미의 제안")
    if not st.session_state.get("summary_generated"):
        chat_history = "\n".join(
            json.dumps(m, ensure_ascii=False) for m in st.session_state["messages"]
        )
        prompt = f"학생과의 대화 기록: {chat_history}\n\n위 대화를 요약하고 피드백을 제공하세요."
        response = client.chat.completions.create(
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



