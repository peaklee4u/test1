# Streamlit-based chatbot with image upload capability for scientific inquiry support
import streamlit as st
from openai import OpenAI
import openai
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
    "당신은 중학생의 자유 탐구 결과를 바탕으로 탐구보고서를 작성하도록 돕는 챗봇이며, 이름은 '탐구보고서 도우미'입니다."
    "이 탐구는 중학교 1학년 학생들이 수행한 것이지만, 과학에 관심이 많은 학생들이므로 중학교 3학년 수준이라고 생각하고 설명하세요."
    "과학 개념을 설명할 때는 15세 수준에 맞춰 간단하고 명확하게 설명하세요."

    "학생은 실험을 완료하고 결과(데이터표, 그래프, 관찰 결과 등)를 가지고 왔습니다. "
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
    "4. 그래프나 표에서 나타나는 경향을 해석했는가?"
    "5. 결론이 결과에 근거해 논리적으로 도출되었는가?"
    "6. 결론에서 가설을 지지하는지 또는 지지하지 않는지를 밝혔는가?"
    "7. 탐구의 오차나 한계를 인식했는가?"

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


# Encode uploaded image
def encode_image(uploaded_file):
    return base64.b64encode(uploaded_file.read()).decode("utf-8")

# Generate response from OpenAI - 수정된 함수
def get_chatgpt_response(content, pdf_context=None):
    # 시스템 프롬프트와 기존 대화 기록으로 메시지 구성
    messages = [{"role": "system", "content": initial_prompt}]
    
    # PDF 컨텍스트가 있으면 추가
    if pdf_context:
        messages.append({"role": "system", "content": f"학생이 참고한 PDF 문서 내용입니다:\n\n{pdf_context[:1500]}"})
    
    # 기존 대화 기록 추가
    messages.extend(st.session_state["messages"])
    
    # 현재 사용자 입력 추가
    messages.append({"role": "user", "content": content})

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages
        )
        answer = response.choices[0].message.content
        
        # 세션에 메시지들 저장
        st.session_state["messages"].append({"role": "user", "content": content})
        st.session_state["messages"].append({"role": "assistant", "content": answer})
        
        # 최근 대화 저장
        st.session_state["recent_message"] = {"user": content, "assistant": answer}
        
        return answer
    except Exception as e:
        st.error(f"❌ ChatGPT 응답 오류: {e}")
        return None
     

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

# 콘텐츠 표시 헬퍼 함수
def display_content(content):
    if isinstance(content, list):
        for part in content:
            if part.get("type") == "text":
                st.write(part.get("text", ""))
            elif part.get("type") == "image_url":
                st.image(part["image_url"]["url"], caption="업로드한 이미지", width=300)
    elif isinstance(content, dict):
        if content.get("type") == "text":
            st.write(content.get("text", ""))
        elif content.get("type") == "image_url":
            st.image(content["image_url"]["url"], caption="업로드한 이미지", width=300)
    else:
        # 문자열이고 base64 데이터가 포함된 경우 체크
        if isinstance(content, str) and "data:image" in content:
            st.write("📷 이미지가 업로드되었습니다.")
        else:
            st.write(content)


# Page 1: User info input
def page_1():
    st.title("과학탐구 분석 도우미")
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
    st.title("탐구 분석 도우미 활용 방법")
    st.write("""
    탐구를 마친 후, 실험 결과를 분석하고 탐구보고서를 잘 작성할 수 있도록 인공지능이 도와줄 거예요.

    ① 먼저 인공지능에게 실험 결과(데이터 표, 그래프, 결론 등)를 알려주세요.
    
    ② 인공지능은 결과를 분석하고, 어떤 점이 잘 되었는지, 어떤 점을 더 보완하면 좋은지 알려줄 거예요.
    
    ③ 궁금한 점이 있다면 인공지능에게 자유롭게 질문해 보세요.
    
    ④ 궁금한 것이 다 해결되면, '궁금한 건 다 물어봤어'라고 말해 주세요.
    
    ⑤ 그러면 인공지능이 여러분에게 질문을 하며, 결론이나 보고서를 더 잘 쓸 수 있도록 도와줄 거예요.
    
    ⑥ 대화가 충분히 이루어지면 인공지능이 [다음] 버튼을 눌러도 된다고 말해줄 거예요. 인공지능이 그렇게 말했을 때 [다음] 버튼을 눌러주세요!
     """)
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        if st.button("이전"):
            st.session_state["step"] = 1
            st.rerun()
            
    with col2:
        if st.button("다음"):
            st.session_state["step"] = 3
            st.rerun()


# Page 3: Chat interface with Form
def page_3():
    st.title("탐구 분석 도우미 활용하기")
    st.write("탐구 분석 도우미와 대화를 나누며 탐구를 설계하세요.")

    # 세션 초기화
    if "messages" not in st.session_state:
        st.session_state["messages"] = []
    
    if "recent_message" not in st.session_state:
        st.session_state["recent_message"] = {"user": "", "assistant": ""}

    # Form을 사용하여 입력창 관리
    with st.form(key="chat_form", clear_on_submit=True):
        user_input = st.text_area("You: ", height=100, placeholder="질문을 입력하세요...")
        
        # 전송 버튼
        submit_button = st.form_submit_button("전송")
    
    # 파일 업로드는 form 밖에서 처리
    uploaded_file = st.file_uploader("📎 참고할 PDF 또는 이미지 파일을 업로드하세요:", type=["pdf", "png", "jpg", "jpeg"])

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

    # Form submit 처리
    if submit_button and (user_input.strip() or uploaded_file):
        # 콘텐츠 구성
        if encoded_image:
            # 이미지가 있는 경우 멀티모달 형식
            content = []
            if user_input.strip():
                content.append({"type": "text", "text": user_input})
            content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{encoded_image}"}})
        elif user_input.strip():
            # 텍스트만 있는 경우
            content = user_input
        else:
            st.warning("텍스트나 이미지를 입력해주세요.")
            return

        # API 호출
        response = get_chatgpt_response(content, extracted_pdf_text)
        
        if response:
            st.rerun()  # 응답 후 페이지 새로고침

    # 최근 대화 표시
    st.subheader("📌 최근 대화")
    if st.session_state["recent_message"]["user"] or st.session_state["recent_message"]["assistant"]:
        # 사용자 메시지 표시
        if st.session_state["recent_message"]["user"]:
            st.write("**You:**")
            display_content(st.session_state["recent_message"]["user"])
        
        # 어시스턴트 메시지 표시
        if st.session_state["recent_message"]["assistant"]:
            st.write("**과학탐구 분석 도우미:**")
            st.write(st.session_state["recent_message"]["assistant"])
    else:
        st.write("아직 최근 대화가 없습니다.")

    # 누적 대화 표시
    st.subheader("📜 누적 대화 목록")
    if st.session_state["messages"]:
        for message in st.session_state["messages"]:
            if message["role"] == "user":
                st.write("**You:**")
                display_content(message["content"])
            elif message["role"] == "assistant":
                st.write("**과학탐구 분석 도우미:**")
                st.write(message["content"])
    else:
        st.write("아직 대화 기록이 없습니다.")

    # 이전/다음 버튼
    col1, col2 = st.columns([1, 1])
    
    with col1:
        if st.button("이전"):
            st.session_state["step"] = 2
            st.rerun()
            
    with col2:
        if st.button("다음"):
            st.session_state["step"] = 4
            st.session_state["feedback_saved"] = False  # 피드백 재생성 플래그 초기화
            st.rerun()


# Page 4: Save and summarize
def page_4():
    st.title("탐구 분석 도우미의 제안")
    st.write("탐구 분석 도우미가 대화 내용을 정리 중입니다. 잠시만 기다려주세요.")
    
    # 페이지 4로 돌아올 때마다 새로운 피드백 생성
    if not st.session_state.get("feedback_saved", False):
        try:
            # 대화 기록을 기반으로 탐구 계획 작성
            chat_history = "\n".join(f"{msg['role']}: {msg['content']}" for msg in st.session_state["messages"])
            prompt = f"다음은 학생과 과학탐구 분석 도우미의 대화 기록입니다:\n{chat_history}\n\n"
            prompt += "[다음] 버튼을 눌러도 된다는 대화가 포함되어 있는지 확인하세요. 포함되지 않았다면, '[이전] 버튼을 눌러 과학탐구 분석 도우미와 더 대화해야 합니다'라고 출력하세요. [다음] 버튼을 누르라는 대화가 포함되었음에도 이를 인지하지 못하는 경우가 많으므로, 대화를 철저히 확인하세요. 대화 기록에 [다음] 버튼을 눌러도 된다는 대화가 포함되었다면, 대화 기록을 바탕으로, 다음 내용을 포함해 탐구 내용과 피드백을 작성하세요: 1. 대화 내용 요약(대화에서 실험의 어떤 부분을 어떻게 수정하기로 했는지를 중심으로 빠뜨리는 내용 없이 요약해 주세요. 가독성이 좋도록 줄바꿈 하세요.) 2. 학생의 탐구 능력에 관한 피드백, 3. 예상 결과(주제와 관련된 과학적 이론과 실험 오차를 고려해, 실험 과정을 그대로 수행했을 때 나올 실험 결과를 표 등으로 제시해주세요. 이때 결과 관련 설명은 제시하지 말고, 결과만 제시하세요)."
            
            # OpenAI API 호출
            response = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "system", "content": prompt}]
            )
            st.session_state["experiment_plan"] = response.choices[0].message.content
            
        except Exception as e:
            st.error(f"피드백 생성 중 오류가 발생했습니다: {e}")
            st.session_state["experiment_plan"] = "피드백을 생성할 수 없습니다."

    # 피드백 출력
    st.subheader("📋 생성된 피드백")
    st.write(st.session_state["experiment_plan"])

    # 대화 내용과 피드백을 통합하여 데이터베이스에 저장
    if not st.session_state.get("feedback_saved", False):
        all_data_to_store = st.session_state["messages"] + [{"role": "assistant", "content": st.session_state["experiment_plan"]}]
        
        # MySQL에 저장
        if save_to_db(all_data_to_store):
            st.session_state["feedback_saved"] = True  # 저장 성공 시 플래그 설정
            st.success("데이터가 성공적으로 저장되었습니다.")
        else:
            st.error("저장에 실패했습니다. 다시 시도해주세요.")

    # 이전 버튼 (페이지 3으로 이동 시 피드백 삭제)
    if st.button("이전"):
        st.session_state["step"] = 3
        if "experiment_plan" in st.session_state:
            del st.session_state["experiment_plan"]  # 피드백 삭제
        st.session_state["feedback_saved"] = False  # 피드백 재생성 플래그 초기화
        st.rerun()

    # 처음으로 돌아가기 버튼
    if st.button("처음으로"):
        # 세션 초기화
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

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
