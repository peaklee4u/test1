import streamlit as st
from openai import OpenAI
import pymysql
import os
from dotenv import load_dotenv
from datetime import datetime
import json

# 환경 변수 로드
load_dotenv()
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
MODEL = 'gpt-4o'

# OpenAI 클라이언트 설정
client = OpenAI(api_key=OPENAI_API_KEY)

# 초기 프롬프트 설정
initial_prompt = (
    "당신은 대학교 2학년 수학 과목을 가르치는 조교입니다."
    "학생이 수학 관련 질문을 하면, Finance.pdf 문서를 참고하여 친절하고 자세하게 답변해야 합니다."
    "학생이 어떤 개념을 묻는다면, 먼저 학생이 해당 개념을 제대로 이해하고 있는지 간단한 질문으로 확인하세요."
    "학생이 제대로 대답하지 못하면, 그 개념을 설명해주고 짧은 문제를 제시해 학생이 풀어보게 하세요."
    "학생이 풀이를 제출하면, 풀이 과정을 하나하나 질문하여 학생이 왜 그렇게 풀었는지 확인하세요."
    "풀이 과정에서 오류가 있을 경우, 직접 답을 알려주지 말고 학생 스스로 오류를 찾도록 질문을 통해 유도하세요."
    "학생이 모든 질문에 잘 답하고 풀이를 완성하면, 개념을 잘 이해했다고 칭찬해 주세요."
)
# DB에 저장하는 함수
def save_to_db():
    number = st.session_state.get('user_number', '').strip()
    name = st.session_state.get('user_name', '').strip()

    if not number or not name:
        st.error("학번과 이름을 입력해야 합니다.")
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
        INSERT INTO qna_math (number, name, chat, time)
        VALUES (%s, %s, %s, %s)
        """
        chat = json.dumps(st.session_state["messages"], ensure_ascii=False)
        val = (number, name, chat, now)

        cursor.execute(sql, val)
        cursor.close()
        db.close()
        st.success("대화가 성공적으로 저장되었습니다.")
        return True
    except pymysql.MySQLError as db_err:
        st.error(f"DB 오류: {db_err}")
        return False
    except Exception as e:
        st.error(f"알 수 없는 오류: {e}")
        return False

# GPT 응답 함수
def get_chatgpt_response(prompt):
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "system", "content": initial_prompt}] + st.session_state["messages"] + [{"role": "user", "content": prompt}]
    )
    answer = response.choices[0].message.content

    st.session_state["messages"].append({"role": "user", "content": prompt})
    st.session_state["messages"].append({"role": "assistant", "content": answer})
    return answer

# 페이지 1: 학번과 이름 입력
def page_1():
    st.title("수학 학습 지원 챗봇")
    st.write("학번과 이름을 입력하세요.")

    if "user_number" not in st.session_state:
        st.session_state["user_number"] = ""
    if "user_name" not in st.session_state:
        st.session_state["user_name"] = ""

    st.session_state["user_number"] = st.text_input("학번", value=st.session_state["user_number"])
    st.session_state["user_name"] = st.text_input("이름", value=st.session_state["user_name"])

    if st.button("다음"):
        if not st.session_state["user_number"].strip() or not st.session_state["user_name"].strip():
            st.error("모든 항목을 입력해주세요.")
        else:
            st.session_state["step"] = 2
            st.rerun()

# 페이지 2: 대화 진행
def page_2():
    st.title("수학 질문하기")
    st.write("모르는 수학 내용을 자유롭게 질문하세요!")

    if "messages" not in st.session_state:
        st.session_state["messages"] = []

    if "user_input_temp" not in st.session_state:
        st.session_state["user_input_temp"] = ""

    if "recent_message" not in st.session_state:
        st.session_state["recent_message"] = {"user": "", "assistant": ""}

    user_input = st.text_area(
        "질문 또는 풀이 입력:",
        value=st.session_state["user_input_temp"],
        key="user_input",
        on_change=lambda: st.session_state.update({"user_input_temp": st.session_state["user_input"]})
    )

    if st.button("전송") and user_input.strip():
        assistant_response = get_chatgpt_response(user_input)

        st.session_state["recent_message"] = {"user": user_input, "assistant": assistant_response}
        st.session_state["user_input_temp"] = ""
        st.rerun()

    st.subheader("📌 최근 대화")
    if st.session_state["recent_message"]["user"] or st.session_state["recent_message"]["assistant"]:
        st.write(f"**You:** {st.session_state['recent_message']['user']}")
        st.write(f"**조교:** {st.session_state['recent_message']['assistant']}")
    else:
        st.write("최근 대화가 없습니다.")

    st.subheader("📜 누적 대화")
    if st.session_state["messages"]:
        for message in st.session_state["messages"]:
            if message["role"] == "user":
                st.write(f"**You:** {message['content']}")
            elif message["role"] == "assistant":
                st.write(f"**조교:** {message['content']}")
    else:
        st.write("아직 대화 기록이 없습니다.")

    if st.button("대화 저장 및 종료"):
        save_to_db()

# 메인 로직
if "step" not in st.session_state:
    st.session_state["step"] = 1

if st.session_state["step"] == 1:
    page_1()
elif st.session_state["step"] == 2:
    page_2()

